"""Judging: apply each task's judges, in the benchmark's order, to the submissions in random order.

This module sees only submissions: their opaque ids, their tasks and their directories. It never opens
the run records or the sealed map, so no judge's input can say who did the work.
"""
from __future__ import annotations

import asyncio
import itertools
import random
from collections import defaultdict
from typing import Mapping

from .benchmark import Benchmark, Model
from .pool import limited
from .store import RunDir
from .submission import Submission


class Judging:
    def __init__(self, run: RunDir, bench: Benchmark, scorers: Mapping[str, object], workers: int = 4):
        """scorers maps a judge kind ("llm", "harness") to the object that scores with it."""
        self.run, self.bench, self.scorers, self.workers = run, bench, scorers, workers

    def submissions(self) -> list[Submission]:
        tasks = {t.id: t for t in self.bench.tasks()}
        index = self.run.load("submissions", {})
        return [Submission(i, tasks[t], self.run.path / "submissions" / i) for i, t in index.items()]

    async def run_all(self) -> None:
        subs = self.submissions()
        random.shuffle(subs)                         # the order carries nothing about who wrote what
        done = {(v["submission"], v["kind"], v.get("other", "")) for v in self.run.rows("verdicts")}
        await limited(self.workers, [lambda s=s, j=j: self.apply(j, s, done)
                                     for s in subs for j in self.bench.judges(s.task)])
        await self.pairs(subs, done)

    def add(self, sub: str, kind: str, judge: str, score: float, reasons, other: str = "") -> None:
        self.run.append("verdicts", {"submission": sub, "kind": kind, "judge": judge, "score": score,
                                     "reasons": reasons, **({"other": other} if other else {})})

    async def apply(self, spec, sub: Submission, done: set) -> None:
        if (sub.id, spec.kind, "") in done:
            return
        if spec.kind == "deterministic":
            score, why = await asyncio.to_thread(spec.check, sub.task, sub.path)
            self.add(sub.id, spec.kind, spec.name, score, why)
        else:
            for judge, (score, reasons) in (await self.scorers[spec.kind].score(sub, spec.rubric)).items():
                self.add(sub.id, spec.kind, judge, score, reasons)

    async def pairs(self, subs: list[Submission], done: set) -> None:
        """Every two submissions of a task, judged in both orders to cancel position bias."""
        by_task = defaultdict(list)
        for s in subs:
            by_task[s.task.id].append(s)
        jobs = []
        for group in by_task.values():
            spec = next((j for j in self.bench.judges(group[0].task) if isinstance(j, Model) and j.pairwise), None)
            jobs += [lambda a=a, b=b, spec=spec: self.pair(spec, a, b, done)
                     for a, b in itertools.combinations(group, 2) if spec and (a.id, "pairwise", b.id) not in done]
        await limited(self.workers, jobs)

    async def pair(self, spec: Model, a: Submission, b: Submission, done: set) -> None:
        for judge, (score, reasons) in (await self.scorers["llm"].prefer(a, b, spec.rubric)).items():
            self.add(a.id, "pairwise", judge, score, reasons, other=b.id)
            self.add(b.id, "pairwise", judge, 1 - score, reasons, other=a.id)
