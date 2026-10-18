"""The blindness check: ask each model judge which harness wrote each submission. A judge that guesses
better than chance, by a one-sided binomial test, means blinding is leaking."""
from __future__ import annotations

import re
from math import comb

from .store import RunDir
from .submission import Submission
from .models import files_text

SIGNIFICANT = 0.05


def p_value(correct: int, n: int, chance: float) -> float:
    """The probability of guessing at least `correct` of `n` right by luck."""
    return sum(comb(n, k) * chance ** k * (1 - chance) ** (n - k) for k in range(correct, n + 1))


def guess_prompt(sub: Submission, names: list[str]) -> str:
    return (f"One of these coding harnesses produced the submission below: {', '.join(names)}.\n\n"
            f"Task it was given:\n{sub.task.instruction}\n\nSubmission {sub.id}:\n{files_text(sub)}\n\n"
            "Which harness produced it? Reply with exactly one name from the list.")


def pick(reply: str, names: list[str]) -> str:
    found = [n for n in sorted(names, key=len, reverse=True) if re.search(rf"(?<![\w-]){re.escape(n)}(?![\w-])", reply, re.I)]
    return found[0] if found else ""


async def blindcheck(run: RunDir, subs: list[Submission], judges: list) -> dict:
    """Needs the sealed map, so it can only run once judging has ended."""
    truth = run.sealed()
    names = sorted({m["harness"] for m in truth.values()})
    out = {}
    for judge in judges:
        correct = sum([pick(await judge.ask(guess_prompt(s, names)), names) == truth[s.id]["harness"] for s in subs])
        p = p_value(correct, len(subs), 1 / len(names))
        out[judge.name] = {"n": len(subs), "correct": correct, "chance": 1 / len(names), "p": p,
                           "leaking": p < SIGNIFICANT}
    return {"contestants": names, "judges": out}
