"""hiddenarena: compare, defaults, report, calibrate and blindcheck.

Each of compare and defaults is the whole pipeline: probe, run, judge, report. Rerun a run id to resume it.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import time
from pathlib import Path

import httpx

from .arena import Arena
from .benchmark import Benchmark, Exercise, Model
from .blindcheck import blindcheck
from .calibrate import calibrate
from .catalog import ENDPOINTS, Catalog
from .exercise import Exerciser
from .judging import Judging
from .models import Judge, Panel
from .report import index, render
from .scrub import Scrubber, harness_terms, model_terms
from .store import ROOT, Mode, RunDir
from .turns import Turns, docker_runtime

JUDGES = os.environ.get("HA_JUDGES", "openai/gpt-4.1-mini,anthropic/claude-haiku-4-5")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="hiddenarena", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("benchmark")
    shared.add_argument("--harnesses", default="all", help="a,b or all")
    shared.add_argument("--tasks", type=int, help="only the first N tasks")
    shared.add_argument("--repeat", type=int, default=3)
    shared.add_argument("--workers", type=int, default=4)
    shared.add_argument("--run-id")
    shared.add_argument("--judges", default=JUDGES, help="provider/model,provider/model: the model-judge panel")
    shared.add_argument("--judge-harness", default="claude-code", help="the held-out harness for harness judges")
    sub.add_parser("compare", parents=[shared]).add_argument("--model", required=True, help="provider/model")
    sub.add_parser("defaults", parents=[shared])
    r = sub.add_parser("report")
    r.add_argument("mode", choices=["compare", "defaults"])
    r.add_argument("benchmark")
    r.add_argument("run_id", nargs="?")
    r.add_argument("--model", default="")
    c = sub.add_parser("calibrate")
    c.add_argument("benchmark")
    c.add_argument("--judges", default=JUDGES)
    c.add_argument("--judge-harness", default="claude-code")
    b = sub.add_parser("blindcheck")
    b.add_argument("run_dir", type=Path)
    b.add_argument("--judges", default=JUDGES)
    return p


def calibration_file(benchmark: str) -> Path:
    return ROOT / "results" / "calibration" / f"{benchmark}.json"


def write_report(mode: Mode, bench: str, run: RunDir) -> Path:
    cal = RunDir(calibration_file(bench).parent).load(bench, {})
    out = mode.report(bench)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(mode, bench, run, cal))
    (ROOT / "reports" / "README.md").write_text(index(ROOT / "reports"))
    return out


def scrubber(catalog: Catalog, models: list[str]) -> Scrubber:
    """Every harness, provider and model name in play, built from the folders and the catalog."""
    terms = {t for n in catalog.names() for t in harness_terms(catalog.folder / n)} | set(ENDPOINTS)
    return Scrubber(terms.union(*(model_terms(m) for m in models)))


def panel(specs: str, compared: str, client: httpx.AsyncClient) -> Panel:
    return Panel([Judge(s, os.environ, client) for s in specs.split(",")], compared)


async def contest(args, mode: Mode, catalog: Catalog) -> None:
    bench = Benchmark.load(args.benchmark)
    run = RunDir(mode.run_dir(args.benchmark, args.run_id or time.strftime("%Y%m%d-%H%M%S")))
    saved = run.load("config")                       # a resumed run keeps its panel and settings
    wanted = args.harnesses.split(",") if args.harnesses != "all" else catalog.names()
    tasks = bench.tasks()[:args.tasks]
    config = saved or {"run_id": run.path.name, "benchmark": args.benchmark, "repeat": args.repeat, "judges": args.judges,
                       "judge_harness": args.judge_harness, "harnesses": wanted, "tasks": [t.id for t in tasks]}
    run.save("config", config)
    for t in tasks:
        for leak in bench.leaks(t):
            run.append("findings", {"task": t.id, "finding": f"input file {leak} repeats hidden material"})
    tasks = [t for t in tasks if not bench.leaks(t)]
    kinds = {j.kind for t in tasks for j in bench.judges(t)}

    turns = Turns(docker_runtime(ROOT / "results" / "docker-logs"))
    arena = Arena(catalog, turns, mode, run, args.workers)
    probe = await arena.probe(config["harnesses"])
    names = [n for n, why in probe.items() if not why and n in config["harnesses"]]
    judge_models = config["judges"].split(",")
    await arena.play(bench, names, tasks, config["repeat"], scrubber(catalog, [mode.model, *judge_models]))
    rows = run.runs().values()
    run.seal({r["submission"]: {k: r[k] for k in ("harness", "provider", "model", "task", "repeat")}
              for r in rows if r["submission"]})

    async with httpx.AsyncClient(timeout=300) as client:
        scorers = {}
        if "llm" in kinds:
            scorers["llm"] = panel(config["judges"], mode.model.partition("/")[0], client)
        if "harness" in kinds:
            scorers["harness"] = Exerciser(catalog, turns, config["judge_harness"], judge_models, names)
        await Judging(run, bench, scorers, args.workers).run_all()
    run.finish_judging()
    print(write_report(mode, args.benchmark, run))


async def calibration(args, catalog: Catalog) -> None:
    bench = Benchmark.load(args.benchmark)
    kinds = {j.kind for t in bench.tasks() for j in bench.judges(t)}
    async with httpx.AsyncClient(timeout=300) as client:
        scorers = {}
        if "llm" in kinds:
            scorers["llm"] = panel(args.judges, "", client)
        if "harness" in kinds:
            scorers["harness"] = Exerciser(catalog, Turns(docker_runtime(ROOT / "results" / "docker-logs")),
                                           args.judge_harness, args.judges.split(","), [])
        result = await calibrate(bench, scorers)
    RunDir(calibration_file(args.benchmark).parent).save(args.benchmark, result)
    print(result)


async def blind(args) -> None:
    run = RunDir(args.run_dir)
    bench = Benchmark.load(run.load("config")["benchmark"])
    async with httpx.AsyncClient(timeout=300) as client:
        judges = panel(args.judges, "", client).judges
        run.save("blindcheck", await blindcheck(run, Judging(run, bench, {}).submissions(), judges))
    print(run.load("blindcheck"))


def main() -> None:
    args = parser().parse_args()
    catalog = Catalog()
    if args.cmd in ("compare", "defaults"):
        asyncio.run(contest(args, Mode(args.cmd, getattr(args, "model", "")), catalog))
    elif args.cmd == "report":
        mode = Mode(args.mode, args.model)
        print(write_report(mode, args.benchmark, RunDir(mode.run_dir(args.benchmark, args.run_id or mode.latest(args.benchmark)))))
    elif args.cmd == "calibrate":
        asyncio.run(calibration(args, catalog))
    else:
        asyncio.run(blind(args))
