"""The report: join the run records and the verdicts through the sealed map, only after judging, and
render one markdown table per run plus everything that qualifies it."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from statistics import mean, median

from .store import Mode, RunDir


@dataclass
class Row:
    harness: str
    tasks: int = 0                                   # tasks with at least one graded run
    graded: int = 0
    pass_rate: float | None = None
    spread: tuple[float, float] | None = None        # lowest and highest pass rate over the repeats
    deterministic: float | None = None
    judges: dict[str, float] = field(default_factory=dict)
    panel: float | None = None                       # the mean over runs of the panel's median
    wins: float | None = None                        # the mean pairwise score, both orders
    wall_median: float = 0.0
    wall_total: float = 0.0
    cost: float = 0.0
    no_cost: int = 0
    redactions: int = 0


def avg(xs) -> float | None:
    xs = list(xs)
    return mean(xs) if xs else None


def judged_kinds_ok(verdicts: list[dict], calibration: dict) -> dict[str, str]:
    """For each judged kind with verdicts: "" if every judge reached the threshold, else why not."""
    out = {}
    for kind in {v["kind"] for v in verdicts if v["kind"] in ("llm", "harness")}:
        cal = calibration.get(kind)
        judges = {v["judge"] for v in verdicts if v["kind"] == kind}
        if not cal:
            out[kind] = "not calibrated"
        elif bad := sorted(j for j in judges if cal["judges"].get(j, {}).get("agreement", -1) < cal["threshold"]):
            out[kind] = f"below the threshold {cal['threshold']}: {', '.join(bad)}"
        else:
            out[kind] = ""
    return out


def summarize(runs: dict, verdicts: list[dict], sealed: dict, withheld: set[str]) -> list[Row]:
    """One row per harness, every number computed from the records."""
    graded = defaultdict(lambda: defaultdict(list))  # (harness, task, repeat) -> kind -> [(judge, score)]
    for v in verdicts:
        m = sealed[v["submission"]]
        graded[(m["harness"], m["task"], m["repeat"])][v["kind"]].append((v["judge"], v["score"]))
    scored = defaultdict(list)
    for r in runs.values():
        if r["status"] != "runner_error" and not r.get("finding"):
            scored[r["harness"]].append(r)
    rows = []
    for harness, rs in sorted(scored.items()):
        row = Row(harness, wall_median=median(r["wall_s"] for r in rs), wall_total=sum(r["wall_s"] for r in rs),
                  cost=sum(r["cost_usd"] or 0 for r in rs), no_cost=sum(r["cost_usd"] is None for r in rs),
                  redactions=sum(r["redactions"] for r in rs))
        det, per_repeat, per_judge, panel, wins = [], defaultdict(list), defaultdict(list), [], []
        graded_tasks = set()
        for r in rs:
            kinds = graded.get((harness, r["task"], r["repeat"]), {})
            if not any(k != "pairwise" for k in kinds):
                continue
            row.graded += 1
            graded_tasks.add(r["task"])
            if "deterministic" in kinds:
                score = mean(s for _, s in kinds["deterministic"])
                det.append(score)
                per_repeat[r["repeat"]].append(score == 1)
            judged = [(j, s) for k in ("llm", "harness") if k not in withheld for j, s in kinds.get(k, [])]
            for j, s in judged:
                per_judge[j].append(s)
            if judged:
                panel.append(median(s for _, s in judged))
            wins += [s for _, s in kinds.get("pairwise", [])]
        row.tasks = len(graded_tasks)
        row.deterministic = avg(det)
        row.pass_rate = avg(s == 1 for s in det)
        rates = [mean(v) for v in per_repeat.values()]
        row.spread = (min(rates), max(rates)) if rates else None
        row.judges = {j: mean(v) for j, v in sorted(per_judge.items())}
        row.panel, row.wins = avg(panel), avg(wins)
        rows.append(row)
    return rows


def pct(x: float | None) -> str:
    return "–" if x is None else f"{x:.0%}"


def num(x: float | None) -> str:
    return "–" if x is None else f"{x:.2f}"


def table(headers: list[str], rows: list[list[str]]) -> str:
    return "\n".join(["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers),
                      *("| " + " | ".join(r) + " |" for r in rows)])


def render(mode: Mode, benchmark: str, run: RunDir, calibration: dict) -> str:
    config, probe = run.load("config", {}), run.load("probe", {})
    runs, verdicts, sealed = run.runs(), run.rows("verdicts"), run.sealed()
    problems = judged_kinds_ok(verdicts, calibration)
    blind = run.load("blindcheck")
    leaking = bool(blind) and any(j["leaking"] for j in blind["judges"].values())
    rows = summarize(runs, verdicts, sealed, {k for k, why in problems.items() if why})
    judges = sorted({j for r in rows for j in r.judges})
    flag = " ⚠" if leaking else ""
    head = ["Harness", "Tasks graded", "Pass rate (repeat spread)", "Deterministic", *(f"{j}{flag}" for j in judges),
            *([f"Panel median{flag}"] if judges else []), *(["Pairwise wins"] if any(r.wins is not None for r in rows) else []),
            "Median wall (s)", "Total wall (s)", "Cost (USD)", "No cost reported"]
    body = [[r.harness, f"{r.tasks}", f"{pct(r.pass_rate)} ({pct(r.spread[0])}–{pct(r.spread[1])})" if r.spread else "–",
             num(r.deterministic), *(num(r.judges.get(j)) for j in judges), *([num(r.panel)] if judges else []),
             *([num(r.wins)] if "Pairwise wins" in head else []), f"{r.wall_median:.1f}", f"{r.wall_total:.0f}",
             f"{r.cost:.4f}", f"{r.no_cost}"] for r in sorted(rows, key=lambda r: (-(r.pass_rate or 0), -(r.deterministic or 0)))]
    out = [f"# {mode.title} · {benchmark}", "",
           f"Run `{run.path.name}` · {config.get('repeat', '?')} repeats · {len(sealed)} graded submissions", "",
           table(head, body), ""]
    out += section("Unsupported harnesses", [f"- **{n}**: {why}" for n, why in sorted(probe.items()) if why])
    out += section("Findings (never scored)", [f"- {r['harness']} · {r['task']} #{r['repeat']}: {r['finding']}"
                                                for r in runs.values() if r.get("finding")]
                   + [f"- {f['task']}: {f['finding']}" for f in run.rows("findings")])
    out += section("Runner errors (retried, not held against the harness)",
                   [f"- {r['harness']} · {r['task']} #{r['repeat']}: {r['error']}" for r in runs.values()
                    if r["status"] == "runner_error"])
    cal = [f"- {kind}: " + ("; ".join(f"{j} {c['agreement']:.2f} (n={c['n']})" for j, c in sorted(calibration[kind]["judges"].items()))
                            + f", threshold {calibration[kind]['threshold']}" if kind in calibration else "no calibration")
           + (f" — **judged scores withheld, {why}**" if why else "") for kind, why in sorted(problems.items())]
    out += section("Calibration agreement", cal)
    out += section("Blindness check", [
        f"- {j}: {c['correct']}/{c['n']} guessed, chance {c['chance']:.0%}, p={c['p']:.3f}" + (" — **LEAKING**" if c["leaking"] else "")
        for j, c in sorted(blind["judges"].items())] + ([f"- ⚠ judged scores are flagged: blinding leaks"] if leaking else [])
        if blind else [])
    counts = [r["redactions"] for r in runs.values() if r["submission"]]
    out += section("Redactions", [f"- {sum(counts)} in total over {len(counts)} submissions, at most {max(counts)} in one"] if counts else [])
    return "\n".join(out).rstrip() + "\n"


def section(title: str, lines: list[str]) -> list[str]:
    return [f"## {title}", "", *(lines or ["None."]), ""]


def index(root) -> str:
    """reports/README.md: every report, by mode."""
    reports = sorted(p for p in root.rglob("*.md") if p.name != "README.md")
    return "# Reports\n\n" + "\n".join(f"- [{p.relative_to(root).as_posix()[:-3]}]({p.relative_to(root).as_posix()})"
                                       for p in reports) + "\n"
