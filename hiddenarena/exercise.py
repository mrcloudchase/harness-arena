"""The harness judge: a held-out harness, one that is not a contestant, runs the submission in its own
sandbox, in a fresh workspace holding only the scrubbed submission, the task and the rubric, and writes
its verdict to a JSON file. It runs once per judge model.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from harness_interface import Request

from .catalog import Catalog
from .models import Scored, check_panel, parse_scores
from .submission import Submission
from .turns import Turns

VERDICT = "verdict.json"
BRIEF = ("Exercise the work in ./submission as the task below describes: run it and try it, do not just read it. A server must be started in the background "
         "(with &) and stopped when you are done, or your command never returns.\n"
         "Then score it against all %d items of the rubric in RUBRIC.md, each item from 0 (not met) to 1 (fully met), and write "
         'only this JSON to the file ./%s, using a shell command or a file tool; a verdict given in your reply does not '
         'count: {"items": {"1": {"score": 0.0, "reason": "..."}}}\n\nTask:\n%s')


class Exerciser:
    def __init__(self, catalog: Catalog, turns: Turns, harness: str, models: list[str], contestants: list[str],
                 compared: str = ""):
        if harness in contestants:
            raise SystemExit(f"{harness} is a contestant in this run, so it can't be a held-out judge")
        check_panel(models, compared)
        self.catalog, self.turns, self.harness, self.models = catalog, turns, harness, models

    async def score(self, sub: Submission, rubric: tuple[str, ...]) -> dict[str, Scored]:
        out = {}
        for model in self.models:
            files = {f"submission/{p}": t for p, t in sub.files().items()}
            files["RUBRIC.md"] = "\n".join(f"{i}. {item}" for i, item in enumerate(rubric, 1))
            target = self.catalog.target(self.harness, model)
            for attempt in range(2):                 # a judge that forgets to write its verdict gets one more go
                workspace = Path(tempfile.mkdtemp(prefix="judge-"))    # a neutral path: no run, model or harness in it
                report = await self.turns.run(target, Request(BRIEF % (len(rubric), VERDICT, sub.task.instruction),
                                                              model=target.model, files=files), workspace)
                try:
                    out[f"{self.harness}@{model}"] = parse_scores((workspace / VERDICT).read_text(), len(rubric))
                    break
                except (OSError, ValueError, KeyError, TypeError):
                    if attempt:
                        raise RuntimeError(f"{self.harness}@{model} wrote no usable verdict: {report.tail[-200:]}") from None
        return out
