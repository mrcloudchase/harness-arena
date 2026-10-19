"""The blindness test, taken by the judges themselves, right after they rank.

A judge ranks a group of results without being told who wrote them. Only once its ranking is saved is it shown the names of the
harnesses that took part and asked to say who wrote which, in the same conversation if its harness can resume one (a fresh
turn with the results, if not). If any judge, all of them together, or any harness recognising its own work, does better
than chance, the judging was not blind.

Guesses are scored against the sealed map, which is open only after judging ends.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from harness_interface import Request

from .loop import Check, Loop
from .runner import Runner
from .stats import p_at_least
from .store import RunDir
from .submission import room

ALPHA = 0.05
TURN_TIMEOUT_S = 600
NAMES = ("CONTESTANTS.md lists the harnesses that took part; each result in ./submissions was written by a different one of them. "
         "Work out who wrote which. Write only this JSON to the file ./guess.json, using a shell command or a file tool; a guess in "
         'your reply does not count: {"<submission id>": "<harness name>", ...}. Every id once, and no name twice.')
FOLLOW_UP = "Your ranking is saved. Now you can be told who was in the contest. " + NAMES
FRESH = "The folders in ./submissions each hold one result of the same job. " + NAMES


def parse_guess(text: str, ids: list[str], names: list[str]) -> dict[str, str]:
    """The guess, if it names every id once and no harness twice. Raises ValueError otherwise."""
    guess = json.loads(text)
    if sorted(guess) != sorted(ids) or len(set(guess.values())) != len(ids) or not set(guess.values()) <= set(names):
        raise ValueError("the guess must name every id once, with a different harness from CONTESTANTS.md each")
    return guess


async def ask(runner: Runner, judge: str, root: Path, ids: list[str], names: list[str], workspace: Path,
              session_id: str) -> tuple[dict[str, str], str, bool]:
    """The judge's guess, why not (if no guess), and whether it was asked in the conversation it ranked in."""
    listed = {"CONTESTANTS.md": "\n".join(f"- {n}" for n in sorted(names))}
    out = {"resumed": bool(session_id), "where": workspace}

    async def step(n: int, feedback: str) -> None:
        tail = f" Rejected: {feedback}" if feedback else ""
        if session_id:                               # the same conversation, in the workspace it ranked in
            out["report"], _ = await runner.go(judge, Request(FOLLOW_UP + tail, files=listed, session_id=session_id), workspace,
                                               timeout_s=TURN_TIMEOUT_S, fresh=False)
        else:                                        # it cannot resume: a fresh turn with the results
            out["where"] = Path(tempfile.mkdtemp(prefix="judge-"))
            out["report"], _ = await runner.go(judge, Request(FRESH + tail, files=room(root, ids, listed)), out["where"],
                                               timeout_s=TURN_TIMEOUT_S)

    async def verify() -> Check:
        if out["report"].runner_error:
            return Check(False, out["report"].runner_error)
        try:
            out["guess"] = parse_guess((out["where"] / "guess.json").read_text(), ids, names)
            return Check(True)
        except (OSError, ValueError, KeyError, TypeError) as e:
            return Check(False, f"no usable guess.json: {e}")
    result = await Loop(step, verify, rounds=2).run()
    return out.get("guess", {}), "" if result.state == "success" else result.why, out["resumed"]


class GuessAudit:
    def __init__(self, run: RunDir):
        self.run = run

    def verdict(self) -> dict:
        """Per judge, pooled, and for recognising its own work: how many guesses were right and how likely that is by luck.
        Blind only if none beats chance (per judge at alpha divided by the number of judges, since many are tested)."""
        truth, rows = self.run.sealed(), [r for r in self.run.rows("guesses") if r["guess"]]
        judges = sorted({r["judge"] for r in rows})
        right = {j: [] for j in judges}
        own = []
        for r in rows:
            for sid, name in r["guess"].items():
                chance = 1 / r["names"]
                hit = truth[sid]["harness"] == name
                right[r["judge"]].append((hit, chance))
                if truth[sid]["harness"] == r["judge"]:
                    own.append((hit, chance))

        def test(pairs):
            k = sum(h for h, _ in pairs)
            return {"right": k, "n": len(pairs), "p": p_at_least(k, [c for _, c in pairs]) if pairs else 1.0}
        per_judge = {j: test(p) for j, p in right.items()}
        pooled, self_ = test([x for p in right.values() for x in p]), test(own)
        blind = (pooled["p"] >= ALPHA and self_["p"] >= ALPHA
                 and all(t["p"] >= ALPHA / max(1, len(judges)) for t in per_judge.values()))
        return {"blind": blind, "alpha": ALPHA, "pooled": pooled, "self": self_, "judges": per_judge,
                "resumed": sum(r["resumed"] for r in rows), "fresh": sum(not r["resumed"] for r in rows)}
