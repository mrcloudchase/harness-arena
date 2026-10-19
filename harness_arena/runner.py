"""Runs one turn of a named harness on the mode's model, the way every stage does: pointed at the relay when
there is one (compare mode), timed, and counted against the run's turn brake.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

from harness_interface import Request

from .catalog import Catalog
from .relay import Relay
from .store import Mode, RunDir
from .turns import Report, Turns


class Exhausted(Exception):
    """The run's turn budget is spent. Rerun the run id to continue where it stopped."""


class Runner:
    def __init__(self, catalog: Catalog, turns: Turns, mode: Mode, run: RunDir, relay: Relay | None = None,
                 max_turns: int | None = None):
        self.catalog, self.turns, self.mode, self.run, self.relay, self.max_turns = catalog, turns, mode, run, relay, max_turns
        self.used = 0

    async def go(self, name: str, request: Request, workspace: Path, relay: bool = True,
                 timeout_s: int | None = None) -> tuple[Report, list[str]]:
        """The turn, and the models it called that were not the one named (compare mode, through the relay)."""
        if self.max_turns is not None and self.used >= self.max_turns:
            raise Exhausted(f"{self.used} turns used")
        self.used += 1
        target, tag = self.catalog.target(name, self.mode.model), ""
        if timeout_s:
            run = dataclasses.replace(target.harness.run, timeout_s=min(target.harness.run.timeout_s, timeout_s))
            target = dataclasses.replace(target, harness=dataclasses.replace(target.harness, run=run))
        if self.relay and relay and name not in self.run.load("direct", []):
            target, tag = self.relay.register(target)
        report = await self.turns.run(target, dataclasses.replace(request, model=target.model), workspace)
        return report, (self.relay.foreign(tag, target.model) if tag and not report.runner_error else [])
