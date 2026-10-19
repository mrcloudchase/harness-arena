"""The scrub stage, as a loop: scrub every submission, ask the fingerprint classifier whether it can still tell the
harnesses apart, and feed what gave it away back into the scrubber.

The classifier is the cheap audit and runs before any judging. The harnesses' own guesses (guess.py) are the final one.
"""
from __future__ import annotations

import json
from pathlib import Path

from .fingerprint import ALPHA, classify, exclusive_terms
from .loop import Check, Loop, Result
from .scrub import Scrubber
from .store import RunDir
from .submission import prose, write


class Scrubbing:
    def __init__(self, run: RunDir, base_terms: set[str]):
        self.run, self.base, self.terms = run, set(base_terms), set(base_terms)
        self.redactions: dict[str, int] = {}

    def authors(self) -> dict[str, str]:
        """submission id -> harness, from the run records (never shown to a judge)."""
        return {r["submission"]: r["harness"] for r in self.run.runs().values() if r["submission"]}

    def raw(self) -> dict[str, dict[str, str]]:
        authors = self.authors()                     # a result with no run record is an orphan of an interrupted run
        return {i: {p.relative_to(d).as_posix(): p.read_text() for p in sorted(d.rglob("*")) if p.is_file()}
                for i in self.run.load("submissions", {}) if i in authors for d in [self.run.path / "raw" / i]}

    def scrub_all(self) -> None:
        scrub = Scrubber(self.terms)
        self.redactions = {i: write(self.run.path / "submissions" / i, files, scrub) for i, files in self.raw().items()}
        self.run.save("redactions", self.redactions)

    async def audit(self) -> Check:
        raw, authors = self.raw(), self.authors()
        scrub = Scrubber(self.terms)
        samples = [(authors[i], "\n".join(f"{n}\n{scrub(t)[0]}" for n, t in files.items()), scrub(prose(files))[0])
                   for i, files in raw.items()]
        right, p = classify([(h, text) for h, text, _ in samples])
        self.stats = {"right": right, "n": len(samples), "p": p}
        if p >= ALPHA:
            return Check(True)
        found = exclusive_terms(samples) - self.terms
        return Check(False, f"a classifier named the harness {right} of {len(samples)} times (p={p:.3f}); "
                            f"new terms: {', '.join(sorted(found)) or 'none in comments or prose'}")

    async def run_loop(self, rounds: int = 3) -> Result:
        async def step(n: int, feedback: str) -> None:
            if feedback and "new terms: " in feedback:
                self.terms |= {t.strip() for t in feedback.split("new terms: ")[1].split(",") if t.strip() and t.strip() != "none in comments or prose"}
            self.scrub_all()
        result = await Loop(step, self.audit, rounds).run()
        self.run.save("scrub", {"state": result.state, "why": result.why, "rounds": result.rounds,
                                "terms_added": sorted(self.terms - self.base), **self.stats})
        return result
