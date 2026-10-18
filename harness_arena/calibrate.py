"""Calibration: how well each judge's scores agree with the human scores a benchmark ships.

Agreement is the correlation between a judge's scores and the humans' over the calibration examples.
Judged scores are reported only for judges whose agreement reaches the benchmark's threshold.
"""
from __future__ import annotations

from statistics import StatisticsError, correlation
from typing import Mapping

from .benchmark import Benchmark
from .submission import Submission


def agreement(judged: list[float], human: list[float]) -> float:
    try:
        return correlation(judged, human)
    except StatisticsError:                          # fewer than two examples, or a judge that never varies
        return 0.0


async def calibrate(bench: Benchmark, scorers: Mapping[str, object]) -> dict:
    """{kind: {"threshold", "judges": {judge: {"agreement", "n"}}}} for each judged kind the benchmark uses."""
    tasks = {t.id: t for t in bench.tasks()}
    scores: dict[str, dict[str, list]] = {}
    thresholds = {}
    for n, ex in enumerate(bench.calibration()):
        task = tasks[ex.task]
        for spec in (j for j in bench.judges(task) if j.kind != "deterministic"):
            thresholds[spec.kind] = spec.min_agreement
            for judge, (score, _) in (await scorers[spec.kind].score(Submission(f"C-{n}", task, ex.path), spec.rubric)).items():
                scores.setdefault(spec.kind, {}).setdefault(judge, []).append((score, ex.human))
    return {kind: {"threshold": thresholds[kind],
                   "judges": {j: {"agreement": agreement(*zip(*pairs)), "n": len(pairs)} for j, pairs in judges.items()}}
            for kind, judges in scores.items()}
