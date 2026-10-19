"""The blindness audit by the judges themselves. Every harness that judged is shown groups of results and the names of the
harnesses that wrote them, and must say who wrote what. If any of them, or all of them together, or any harness
recognising its own work, does better than chance, the judging was not blind.

Run after judging, on a sample of groups. Guesses are scored against the sealed map, which is open only then.
"""
from __future__ import annotations

import random
import tempfile
from pathlib import Path

from harness_interface import Request

from .judge import groups, room
from .loop import Check, Loop
from .pool import limited
from .runner import Runner
from .stats import p_at_least
from .store import RunDir

ALPHA = 0.05
TURN_TIMEOUT_S = 600
BRIEF = ("The folders in ./submissions each hold the work of one of the harnesses named in CONTESTANTS.md; each harness wrote "
         "exactly one. Work out who wrote which. Write only this JSON to the file ./guess.json, using a shell command or a "
         'file tool; a guess in your reply does not count: {"<submission id>": "<harness name>", ...}. Every id once and every '
         "name once.")


def parse_guess(text: str, ids: list[str], names: list[str]) -> dict[str, str]:
    import json
    guess = json.loads(text)
    if sorted(guess) != sorted(ids) or sorted(guess.values()) != sorted(names):
        raise ValueError("the guess must name every id once and every harness once")
    return guess


class GuessAudit:
    def __init__(self, runner: Runner, sample: int = 5, workers: int = 4):
        self.runner, self.run, self.sample, self.workers = runner, runner.run, sample, workers

    def chosen(self) -> list[tuple[str, int]]:
        keys = sorted(groups(self.run))
        return sorted(random.Random(self.run.path.name).sample(keys, min(self.sample, len(keys))))

    async def run_all(self, judges: list[str]) -> None:
        truth = self.run.sealed()                    # after judging ends: the names, never shown to a judge as ids
        done = {(r["judge"], r["task"], r["repeat"]) for r in self.run.rows("guesses") if not r["error"]}
        ids_of = groups(self.run)
        await limited(self.workers, [lambda j=j, k=k: self.one(j, *k, ids_of[k], sorted({truth[i]["harness"] for i in ids_of[k]}))
                                     for k in self.chosen() for j in judges if (j, *k) not in done])

    async def one(self, judge: str, task: str, repeat: int, ids: list[str], names: list[str]) -> None:
        order, out = random.sample(ids, len(ids)), {}
        files = room(self.run, order, {"CONTESTANTS.md": "\n".join(f"- {n}" for n in names)})

        async def step(n: int, feedback: str) -> None:
            workspace = Path(tempfile.mkdtemp(prefix="judge-"))
            out["report"], _ = await self.runner.go(judge, Request(BRIEF + (f" Rejected: {feedback}" if feedback else ""), files=files), workspace, timeout_s=TURN_TIMEOUT_S)
            out["workspace"] = workspace

        async def verify() -> Check:
            if out["report"].runner_error:
                return Check(False, out["report"].runner_error)
            try:
                out["guess"] = parse_guess((out["workspace"] / "guess.json").read_text(), ids, names)
                return Check(True)
            except (OSError, ValueError, KeyError, TypeError) as e:
                return Check(False, f"no usable guess.json: {e}")
        result = await Loop(step, verify, rounds=2).run()
        self.run.append("guesses", {"judge": judge, "task": task, "repeat": repeat, "guess": out.get("guess", {}),
                                    "error": "" if result.state == "success" else result.why})

    def verdict(self) -> dict:
        """Per judge, pooled, and for recognising its own work: how many guesses were right and how likely that is by luck.
        Blind only if none beats chance (per judge at alpha divided by the number of judges, since many are tested)."""
        truth, rows = self.run.sealed(), [r for r in self.run.rows("guesses") if r["guess"]]
        judges = sorted({r["judge"] for r in rows})
        right = {j: [] for j in judges}
        own = []
        for r in rows:
            for sid, name in r["guess"].items():
                chance = 1 / len(r["guess"])
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
        return {"blind": blind, "alpha": ALPHA, "pooled": pooled, "self": self_, "judges": per_judge}
