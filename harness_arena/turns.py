"""One harness turn, the way every part of harness-arena runs one: on a runtime the caller chose, timed
here, with provider refusals retried so they are never held against the harness.
"""
from __future__ import annotations

import asyncio
import re
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from harness_interface import Docker, DockerRuntime, Request, Result, Runtime, Turn
from harness_interface.resources import DEFAULT_SANDBOX

from .catalog import Target

REFUSAL = re.compile(r"\b(401|403|429|529|unauthori[sz]ed|rate.?limit|quota|insufficient|overloaded|"
                     r"invalid api key|authentication)\b", re.I)
RuntimeFor = Callable[[Target], Runtime]


def docker_runtime(logs: Path, mounts: tuple[Path, ...] = ()) -> RuntimeFor:
    """Each run in the default sandbox, reaching only its provider (or the relay in front of it)."""
    engine = Docker(logs)
    return lambda t: DockerRuntime(engine, DEFAULT_SANDBOX, egress=[t.provider.host], mounts=[t.folder, *mounts])


@dataclass(frozen=True)
class Report:
    result: Result
    wall_s: float                                    # measured here, not reported by the harness
    runner_error: str = ""                           # why this says nothing about the harness
    tail: str = ""                                   # the end of its output, for the reader of a failure


class Turns:
    def __init__(self, runtime_for: RuntimeFor, retries: int = 3, backoff_s: float = 5.0):
        self.runtime_for, self.retries, self.backoff_s = runtime_for, retries, backoff_s

    async def run(self, target: Target, request: Request, workspace: Path) -> Report:
        """The turn in a fresh workspace. A turn that never ran, or was refused by its provider, is retried
        and, if it keeps failing, reported as a runner error."""
        for attempt in range(self.retries + 1):
            shutil.rmtree(workspace, ignore_errors=True)
            start = time.monotonic()
            turn = await Turn.start(self.runtime_for(target), target.harness, target.provider, request,
                                    workspace, target.folder)
            tail = bytearray()
            async for event in turn.events():
                tail += event.data
                del tail[:-4096]
            result = await turn.result()
            text = tail.decode(errors="replace")
            refusal = REFUSAL.search(text) if result.status == "fail" else None
            error = result.error or (f"provider refused: {refusal.group(0)}" if refusal else "")
            if not error:
                break
            await asyncio.sleep(self.backoff_s * 2 ** attempt)
        return Report(result, time.monotonic() - start, error, text[-300:])
