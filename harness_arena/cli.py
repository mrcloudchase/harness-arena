"""harness-arena: compare, defaults, gate and report.

Each of compare and defaults is the whole loop for one benchmark: gate, contest, scrub, peer judging, blindness
audit, report. Rerun a run id to resume it.
"""
from __future__ import annotations

import argparse
import asyncio
import time

from harness_interface import Docker

from .benchmark import Benchmark
from .blind import Scrubbing
from .catalog import ENDPOINTS, Catalog
from .contest import Contest
from .gates import gate
from .guess import GuessAudit
from .judge import PeerJudging
from .relay import Relay, gateway
from .report import render
from .runner import Exhausted, Runner
from .scrub import harness_terms, model_terms
from .store import ROOT, Mode, RunDir
from .tally import anchor_scores
from .turns import Turns, docker_runtime


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="harness-arena", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("benchmark")
    shared.add_argument("--harnesses", default="all", help="a,b or all: they compete, and then they all judge")
    shared.add_argument("--tasks", type=int, help="only the first N tasks")
    shared.add_argument("--repeat", type=int, default=3)
    shared.add_argument("--workers", type=int, default=4)
    shared.add_argument("--run-id")
    shared.add_argument("--scrub-rounds", type=int, default=3, help="rounds of scrub-then-classify before judging")
    shared.add_argument("--audit-groups", type=int, default=5, help="groups of results the judges try to attribute")
    shared.add_argument("--max-turns", type=int, help="stop cleanly after this many harness turns; rerun to continue")
    c = sub.add_parser("compare", parents=[shared])
    c.add_argument("--model", required=True, help="provider/model")
    c.add_argument("--no-relay", action="store_true", help="don't record and check each call's model")
    sub.add_parser("defaults", parents=[shared])
    sub.add_parser("gate").add_argument("benchmark")
    r = sub.add_parser("report")
    r.add_argument("mode", choices=["compare", "defaults"])
    r.add_argument("benchmark")
    r.add_argument("run_id", nargs="?")
    r.add_argument("--model", default="")
    return p


def write_report(mode: Mode, benchmark: str, run: RunDir):
    out = mode.report(benchmark, ROOT)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(mode, benchmark, run))
    reports = sorted(p for p in (ROOT / "reports").rglob("*.md") if p.name != "README.md")
    (ROOT / "reports" / "README.md").write_text("# Reports\n\n" + "\n".join(
        f"- [{p.relative_to(ROOT / 'reports').as_posix()[:-3]}]({p.relative_to(ROOT / 'reports').as_posix()})" for p in reports) + "\n")
    return out


def run_gate(bench: Benchmark, tasks) -> list[str]:
    problems = gate(bench, tasks)
    for p in problems:
        print(f"gate: {p}")
    return problems


async def contest(args, mode: Mode, catalog: Catalog) -> int:
    bench = Benchmark.load(args.benchmark)
    tasks = bench.tasks()[:args.tasks]
    if run_gate(bench, tasks):
        print("blocked: the benchmark failed its intake gate; nothing was run")
        return 1
    run = RunDir(mode.run_dir(args.benchmark, args.run_id or time.strftime("%Y%m%d-%H%M%S"), ROOT))
    wanted = args.harnesses.split(",") if args.harnesses != "all" else catalog.names()
    config = run.load("config") or {"run_id": run.path.name, "benchmark": args.benchmark, "repeat": args.repeat,
                                    "harnesses": wanted, "tasks": [t.id for t in tasks]}
    run.save("config", config)               # a resumed run keeps its settings

    logs = ROOT / "results" / "docker-logs"
    await Docker(logs).recover()             # whatever an earlier crash left behind
    relay = Relay(gateway()) if mode.kind == "compare" and not args.no_relay else None
    runner = Runner(catalog, Turns(docker_runtime(logs, (relay.certs,) if relay else ())), mode, run, relay, args.max_turns)
    try:
        arena = Contest(runner, args.workers)
        probe = await arena.probe(config["harnesses"])
        names = [n for n in config["harnesses"] if not probe[n]]
        if len(names) < 2:
            print(f"blocked: {len(names)} harness(es) can run this; ranking needs at least two")
            return 1
        await arena.play(bench, names, [t for t in tasks if t.id in config["tasks"]], config["repeat"])
        runs = run.runs().values()
        run.seal({r["submission"]: {k: r[k] for k in ("harness", "provider", "model", "task", "repeat")}
                  for r in runs if r["submission"]})
        judges = sorted({r["harness"] for r in runs if r["submission"]})      # everyone who ran in the contest judges
        if run.load("scrub") is None:
            terms = {t for n in catalog.names() for t in harness_terms(catalog.folder / n)} | set(ENDPOINTS) | model_terms(mode.model)
            result = await Scrubbing(run, terms).run_loop(args.scrub_rounds)
            print(f"scrub: {result.state} after {result.rounds} round(s)")
        await PeerJudging(runner, bench, args.workers).run_all(judges)
        run.finish_judging()
        run.save("anchors", anchor_scores(run, bench))
        guess = GuessAudit(runner, args.audit_groups, args.workers)
        await guess.run_all(judges)
        run.save("audit", guess.verdict())
    except Exhausted as e:
        print(f"exhausted: {e}; rerun with --run-id {run.path.name} to continue")
        return 2
    print(write_report(mode, args.benchmark, run))
    return 0


def main() -> None:
    args = parser().parse_args()
    if args.cmd in ("compare", "defaults"):
        raise SystemExit(asyncio.run(contest(args, Mode(args.cmd, getattr(args, "model", "")), Catalog())))
    if args.cmd == "gate":
        bench = Benchmark.load(args.benchmark)
        raise SystemExit(1 if run_gate(bench, bench.tasks()) else print("gate passed"))
    mode = Mode(args.mode, args.model)
    print(write_report(mode, args.benchmark, RunDir(mode.run_dir(args.benchmark, args.run_id or mode.latest(args.benchmark, ROOT), ROOT))))
