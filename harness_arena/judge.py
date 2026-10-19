"""Peer judging: every harness that ran in the contest judges, blind. For each group of results (one task, one
repeat) a judge is given the results in a random order under opaque ids, plus what makes a result better, and ranks
them all, best first. It is never told who wrote what, nor what the task said.

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
from .submission import Submission

BRIEF = ("The folders in ./submissions each hold one result of the same job. CRITERIA.md says what makes a result better. "
         "Inspect and run every result (start a server in the background with &, and stop it when you are done), then rank "
         "all %d from best to worst. Write only this JSON to the file ./ranking.json, using a shell command or a file tool; a "
         'ranking in your reply does not count: {"ranking": ["<id of the best>", "...", "<id of the worst>"], '
         '"reasons": {"<id>": "why"}}. Every id exactly once. Judge only the work in front of you.')
NO_FILES = "This result contains no files."


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


def room(run: RunDir, ids: list[str], extra: dict[str, str]) -> dict[str, str]:
    """The files of a judge's workspace: each submission under its id, in the order given, plus the extras."""
    files = dict(extra)
    for sid in ids:
        theirs = Submission(sid, "", 0, run.path / "submissions" / sid).files()
        files.update({f"submissions/{sid}/{p}": t for p, t in theirs.items()} or {f"submissions/{sid}/NO_FILES.txt": NO_FILES})
    return files


class PeerJudging:
    def __init__(self, runner: Runner, bench: Benchmark, workers: int = 4):
        self.runner, self.run, self.bench, self.workers = runner, runner.run, bench, workers
        self.tasks = {t.id: t for t in bench.tasks()}

    async def run_all(self, judges: list[str]) -> None:
        done = {(r["judge"], r["task"], r["repeat"]) for r in self.run.rows("judgments") if not r["error"]}
        await limited(self.workers, [lambda j=j, k=k, ids=ids: self.one(j, *k, ids)
                                     for k, ids in sorted(groups(self.run).items()) for j in judges if (j, *k) not in done])

    async def one(self, judge: str, task: str, repeat: int, ids: list[str]) -> None:
        order = random.sample(ids, len(ids))         # each judge sees its own order: position carries nothing
        files = room(self.run, order, {"CRITERIA.md": self.bench.criteria(self.tasks[task])})
        out: dict = {}

        async def step(n: int, feedback: str) -> None:
            workspace = Path(tempfile.mkdtemp(prefix="judge-"))        # a neutral path: no run, model or harness in it
            brief = BRIEF % len(ids) + (f" Your last attempt was rejected: {feedback}" if feedback else "")
            out["report"], out["foreign"] = await self.runner.go(judge, Request(brief, files=files), workspace)
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
