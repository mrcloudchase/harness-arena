"""The report: join the run records, the judgments and the audits through the sealed map, only after judging, and render
the final ranking, but only if blindness was verified, with everything that qualifies it."""
from __future__ import annotations

from collections import Counter, defaultdict
from statistics import mean, median

from .store import Mode, RunDir
from .tally import tally


def one_line(text: str, limit: int = 200) -> str:
    return " ".join(text.split())[-limit:]


def pct(x: float | None) -> str:
    return "–" if x is None else f"{x:.0%}"


def num(x: float | None, places: int = 2) -> str:
    return "–" if x is None else f"{x:.{places}f}"


def table(headers: list[str], rows: list[list[str]]) -> str:
    return "\n".join(["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers),
                      *("| " + " | ".join(r) + " |" for r in rows)])


def section(title: str, lines: list[str]) -> list[str]:
    return [f"## {title}", "", *(lines or ["None."]), ""]


def render(mode: Mode, benchmark: str, run: RunDir) -> str:
    config, probe, audit, scrub = run.load("config", {}), run.load("probe", {}), run.load("audit"), run.load("scrub", {})
    runs, sealed, anchors = run.runs(), run.sealed(), run.load("anchors", {})
    authors = {sid: m["harness"] for sid, m in sealed.items()}
    result = tally(run.rows("judgments"), authors, anchors)
    blind = bool(audit and audit["blind"])
    scored = defaultdict(list)
    for r in runs.values():
        if r["status"] != "runner_error" and not r["finding"]:
            scored[r["harness"]].append(r)
    out = [f"# {mode.title} · {benchmark}", "",
           f"Run `{run.path.name}` · {config.get('repeat', '?')} repeats · {len(sealed)} results ranked by {len(config.get('harnesses', []))} "
           f"candidate judges · **{'BLIND VERIFIED' if blind else 'BLINDNESS NOT VERIFIED: ranking withheld'}**", ""]
    if blind:
        rows = []
        for place, s in enumerate(result.standings, 1):
            rs = scored[s.harness]
            passed = [anchors[r["submission"]] == 1 for r in rs if r["submission"] in anchors]
            by_repeat = defaultdict(list)
            for r in rs:
                if r["submission"] in anchors:
                    by_repeat[r["repeat"]].append(anchors[r["submission"]] == 1)
            spread = [mean(v) for v in by_repeat.values()]
            rows.append([str(place), s.harness, num(s.score), num(s.mean_rank, 1), str(s.firsts), str(s.groups),
                         num(s.self_bias, 3), (f"{pct(mean(passed))} ({pct(min(spread))}–{pct(max(spread))})" if passed else "–"),
                         f"{median(r['wall_s'] for r in rs):.1f}", f"{sum(r['wall_s'] for r in rs):.0f}",
                         f"{sum(r['cost_usd'] or 0 for r in rs):.4f}", str(sum(r["cost_usd"] is None for r in rs))])
        out += [table(["Rank", "Harness", "Score (0–1)", "Mean place", "1st places", "Groups", "Self-bias",
                       "Hidden-check pass rate (repeat spread)", "Median wall (s)", "Total wall (s)", "Cost (USD)",
                       "No cost reported"], rows), ""]
        out += [f"Score is each harness's results' mean Borda points across every judge's ranking (1 = ranked best by everyone, "
                f"0 = worst by everyone). Judge agreement (Kendall's W): {num(result.agreement)}. "
                f"Agreement with the hidden check where it varies: {num(result.anchor)}.", ""]
    out += section("Blindness verification", blindness(audit, scrub))
    expected = len(config.get("harnesses", []))
    errors = [j for j in run.rows("judgments") if j["error"] or j["finding"]]
    out += section("Judging coverage", [f"- {result.judgments} valid rankings from {len({j['judge'] for j in run.rows('judgments')})} judges"
                                        + (f"; {len(errors)} judgments failed or were excluded" if errors else "")]
                   + [f"- {j['judge']} · {j['task']} #{j['repeat']}: {one_line(j['error'] or j['finding'])}" for j in errors])
    out += section("Unsupported harnesses (neither compete nor judge)",
                   [f"- **{n}**: {one_line(why)}" for n, why in sorted(probe.items()) if why])
    out += section("Model not verified (run without the relay, which these harnesses can't use)",
                   [f"- {n}" for n in run.load("direct", [])] if mode.kind == "compare" else [])
    found = Counter((r["harness"], r["finding"]) for r in runs.values() if r["finding"])
    out += section("Findings (never scored)", [f"- {h}: {why} ({n} runs)" for (h, why), n in sorted(found.items())]
                   + [f"- {f['task']}: {f['finding']}" for f in run.rows("findings")])
    wrote = defaultdict(list)
    for r in runs.values():
        if r["status"] == "ok":
            wrote[r["harness"]].append(bool(r["files"]))
    out += section("Finished ok without writing a file in any run (check the harness's integration, not its skill)",
                   [f"- {h}" for h, w in sorted(wrote.items()) if not any(w)])
    out += section("Runner errors (retried, not held against the harness)",
                   [f"- {r['harness']} · {r['task']} #{r['repeat']}: {one_line(r['error'])}" for r in runs.values()
                    if r["status"] == "runner_error"])
    redactions = run.load("redactions", {})
    out += section("Redactions", [f"- {sum(redactions.values())} in total over {len(redactions)} results, at most {max(redactions.values())} in one"]
                   if redactions else [])
    return "\n".join(out).rstrip() + "\n"


def blindness(audit: dict | None, scrub: dict) -> list[str]:
    lines = []
    if scrub:
        lines.append(f"- Scrub loop: **{scrub['state']}** after {scrub['rounds']} round(s). A classifier named the author of "
                     f"{scrub['right']} of {scrub['n']} results (p={scrub['p']:.3f})."
                     + (f" Terms it taught the scrubber: {', '.join(scrub['terms_added'])}." if scrub["terms_added"] else ""))
    if not audit:
        return lines + ["- The harnesses' guess test has not run."]
    p, s = audit["pooled"], audit["self"]
    lines += [f"- All judges together guessed {p['right']} of {p['n']} authors right (p={p['p']:.3f}).",
              f"- Judges recognising their own work: {s['right']} of {s['n']} (p={s['p']:.3f}).",
              f"- Verdict: {'**blind**: nobody beat chance.' if audit['blind'] else '**NOT blind**: someone beat chance.'}", ""]
    lines.append(table(["Judge", "Right", "Guesses", "p (by luck)"],
                       [[j, str(t["right"]), str(t["n"]), f"{t['p']:.3f}"] for j, t in sorted(audit["judges"].items())]))
    return lines
