"""The loop core every stage is built on: do a step, verify it with something that can't be argued with,
feed the failure back, and stop on a named state.

    success    the verifier passed
    blocked    the verifier says iterating can't help (a human is needed)
    stalled    the same failure came back twice
    exhausted  out of rounds or time

An error or a spent budget is never success.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Awaitable, Callable


@dataclass(frozen=True)
class Check:
    """A verifier's answer: whether it passed, and what to tell the next step if not."""
    ok: bool
    feedback: str = ""
    blocked: bool = False


@dataclass(frozen=True)
class Result:
    state: str                                       # success, blocked, stalled or exhausted
    why: str
    rounds: int


class Loop:
    def __init__(self, step: Callable[[int, str], Awaitable], verify: Callable[[], Awaitable[Check]],
                 rounds: int = 3, seconds: float | None = None):
        self.step, self.verify, self.rounds, self.seconds = step, verify, rounds, seconds

    async def run(self) -> Result:
        start, feedback, seen = time.monotonic(), "", set()
        for n in range(1, self.rounds + 1):
            await self.step(n, feedback)
            check = await self.verify()
            if check.ok:
                return Result("success", "", n)
            if check.blocked:
                return Result("blocked", check.feedback, n)
            if check.feedback in seen:
                return Result("stalled", f"the same failure twice: {check.feedback}", n)
            seen.add(check.feedback)
            feedback = check.feedback
            if self.seconds is not None and time.monotonic() - start > self.seconds:
                return Result("exhausted", f"out of time after round {n}", n)
        return Result("exhausted", f"{self.rounds} rounds without success: {feedback}", self.rounds)
