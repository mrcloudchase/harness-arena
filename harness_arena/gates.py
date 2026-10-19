"""The intake gate: is this benchmark sound enough to spend money on? Deterministic checks only, no harness runs."""
from __future__ import annotations

import tempfile
from pathlib import Path

from .benchmark import Benchmark, Task


def gate(bench: Benchmark, tasks: list[Task]) -> list[str]:
    """What is wrong with the benchmark, if anything."""
    problems = []
    if not tasks or len({t.id for t in tasks}) != len(tasks):
        problems.append("tasks are missing or their ids repeat")
    for t in tasks:
        if not bench.deliverables(t):
            problems.append(f"{t.id}: no deliverables")
        if not str(bench.criteria(t)).strip():
            problems.append(f"{t.id}: no criteria")
        problems += [f"{t.id}: input file {p} repeats hidden material" for p in bench.leaks(t)]
        with tempfile.TemporaryDirectory() as empty:
            scored = bench.check(t, Path(empty))
        if scored is None:
            continue
        if scored[0] != 0:
            problems.append(f"{t.id}: an empty submission scores {scored[0]}, not 0")
        reference = bench.reference(t)
        if reference is None:
            problems.append(f"{t.id}: has a check but no reference solution to prove it passes")
            continue
        with tempfile.TemporaryDirectory() as work:
            for name, text in reference.items():
                (Path(work) / name).parent.mkdir(parents=True, exist_ok=True)
                (Path(work) / name).write_text(text)
            full = bench.check(t, Path(work))
        if full[0] != 1:
            problems.append(f"{t.id}: the reference solution scores {full[0]}, not 1 ({full[1]})")
    return problems
