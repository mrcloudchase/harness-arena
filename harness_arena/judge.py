"""Peer judging: every harness that ran in the contest judges, blind. For each group of results (one task, one
repeat) a judge is given the results in a random order under opaque ids, plus what makes a result better, and ranks
them all, best first. It is never told who wrote what, nor what the task said. Once its ranking is saved it is
asked to guess who wrote what (guess.py), which is the blindness test.

This module sees only submissions: their ids, groups and directories. It never opens the run records or the sealed map.
"""
from __future__ import annotations

import json
import random
import tempfile
from collections import defaultdict
from pathlib import Path

from harness_interface import Request

from .benchmark import Benchmark
from .loop import Check, Loop
from .pool import limited
from .runner import Runner
from .store import RunDir
from .guess import ask
from .submission import NO_FILES, Submission, room

BRIEF = ("The folders in ./submissions each hold one result of the same job. CRITERIA.md says what makes a result better. "
         "Inspect and run every result (start a server in the background with &, and stop it when you are done), then rank "
         "all %d from best to worst. Write only this JSON to the file ./ranking.json, using a shell command or a file tool; a "
         'ranking in your reply does not count: {"ranking": ["<id of the best>", "...", "<id of the worst>"], '
         '"reasons": {"<id>": "why"}}. Every id exactly once. Judge only the work in front of you.')
TURN_TIMEOUT_S = 600                                 # a judge that has not written its file by now is hung


def parse_ranking(text: str, ids: list[str]) -> tuple[list[str], dict]:
    """The ranking, if it names every id exactly once. Raises ValueError otherwise."""
    data = json.loads(text)
    ranking = data["ranking"]
    if sorted(ranking) != sorted(ids):
        raise ValueError(f"the ranking must list exactly these ids, once each: {', '.join(sorted(ids))}")
    return ranking, data.get("reasons", {})


def groups(run: RunDir) -> dict[tuple[str, int], list[str]]:
    """Submission ids by (task, repeat), only where there is something to rank."""
    out = defaultdict(list)
    for sid, g in run.load("submissions", {}).items():
        out[(g["task"], g["repeat"])].append(sid)
    return {k: v for k, v in out.items() if len(v) > 1}


class PeerJudging:
    def __init__(self, runner: Runner, bench: Benchmark, workers: int = 4):
        self.runner, self.run, self.bench, self.workers = runner, runner.run, bench, workers
        self.tasks = {t.id: t for t in bench.tasks()}

    async def run_all(self, judges: list[str], names: list[str] | None = None) -> None:
        """Every judge ranks every group, and then says who it thinks wrote what, out of `names` (default: the judges)."""
        self.names = names or judges
        done = {(r["judge"], r["task"], r["repeat"]) for r in self.run.rows("judgments") if not r["error"]}
        await limited(self.workers, [lambda j=j, k=k, ids=ids: self.one(j, *k, ids)
                                     for k, ids in sorted(groups(self.run).items()) for j in judges if (j, *k) not in done])

    async def one(self, judge: str, task: str, repeat: int, ids: list[str]) -> None:
        order = random.sample(ids, len(ids))         # each judge sees its own order: position carries nothing
        files = room(self.run.path, order, {"CRITERIA.md": self.bench.criteria(self.tasks[task])})
        out: dict = {}

        async def step(n: int, feedback: str) -> None:
            workspace = Path(tempfile.mkdtemp(prefix="judge-"))        # a neutral path: no run, model or harness in it
            brief = BRIEF % len(ids) + (f" Your last attempt was rejected: {feedback}" if feedback else "")
            out["report"], out["foreign"] = await self.runner.go(judge, Request(brief, files=files), workspace, timeout_s=TURN_TIMEOUT_S)
            out["workspace"] = workspace

        async def verify() -> Check:
            if out["report"].runner_error:
                return Check(False, out["report"].runner_error)
            try:
                out["ranking"], out["reasons"] = parse_ranking((out["workspace"] / "ranking.json").read_text(), ids)
                return Check(True)
            except (OSError, ValueError, KeyError, TypeError) as e:
                return Check(False, f"no usable ranking.json: {e}")
        result = await Loop(step, verify, rounds=2).run()
        self.run.append("judgments", {"judge": judge, "task": task, "repeat": repeat, "ranking": out.get("ranking", []),
                                      "reasons": out.get("reasons", {}), "error": "" if result.state == "success" else result.why,
                                      "finding": f"called {', '.join(out['foreign'])}" if out.get("foreign") else ""})
        if result.state == "success":                # the ranking is saved: now, and only now, it is told who took part
            guess, error, resumed = await ask(self.runner, judge, self.run.path, order, self.names, out["workspace"],
                                              out["report"].result.session_id)
            self.run.append("guesses", {"judge": judge, "task": task, "repeat": repeat, "guess": guess, "error": error,
                                        "resumed": resumed, "names": len(self.names)})
