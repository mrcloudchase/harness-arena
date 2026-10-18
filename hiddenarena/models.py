"""Model judges: plain calls to a provider over httpx, at temperature 0, with keys from the environment.

A judge is shown the task, the rubric and a scrubbed submission under its opaque id, and nothing else:
no prompt here names a harness, a vendor or a model.
"""
from __future__ import annotations

import asyncio
import json
import re
from statistics import mean
from typing import Mapping

import httpx

from .catalog import ENDPOINTS, endpoint
from .submission import Submission

Scored = tuple[float, dict]                          # a score in [0, 1], and its reasons per rubric item


class Judge:
    def __init__(self, spec: str, env: Mapping[str, str], client: httpx.AsyncClient):
        self.name, (self.family, _, self.model) = spec, spec.partition("/")
        self.shape = "openai" if "openai" in ENDPOINTS.get(self.family, {}) else "anthropic"
        self.url, self.key = endpoint(self.family, self.shape, env)
        self.client = client

    async def ask(self, prompt: str) -> str:
        messages = [{"role": "user", "content": prompt}]
        for attempt in range(4):
            if self.shape == "openai":
                r = await self.client.post(f"{self.url}/chat/completions", headers={"Authorization": f"Bearer {self.key}"},
                                           json={"model": self.model, "temperature": 0, "messages": messages})
            else:
                r = await self.client.post(f"{self.url}/v1/messages", json={
                    "model": self.model, "temperature": 0, "max_tokens": 2048, "messages": messages},
                    headers={"x-api-key": self.key, "anthropic-version": "2023-06-01"})
            if r.status_code not in (429, 500, 502, 503, 529):
                break
            await asyncio.sleep(2 ** attempt)
        r.raise_for_status()
        body = r.json()
        return body["choices"][0]["message"]["content"] if self.shape == "openai" else body["content"][0]["text"]


def files_text(sub: Submission, limit: int = 60_000) -> str:
    return "\n\n".join(f"=== {path} ===\n{text}" for path, text in sub.files().items())[:limit]


def pointwise(sub: Submission, rubric: tuple[str, ...]) -> str:
    items = "\n".join(f"{i}. {item}" for i, item in enumerate(rubric, 1))
    return (f"You are grading one submission to a task.\n\nTask given to its author:\n{sub.task.instruction}\n\n"
            f"Rubric. Score every item from 0 (not met) to 1 (fully met):\n{items}\n\n"
            f"Submission {sub.id}:\n{files_text(sub)}\n\n"
            'Reply with JSON only, in this shape: {"items": {"1": {"score": 0.0, "reason": "..."}}}')


def pairwise(a: Submission, b: Submission, rubric: tuple[str, ...]) -> str:
    items = "\n".join(f"{i}. {item}" for i, item in enumerate(rubric, 1))
    return (f"You are comparing two submissions to a task.\n\nTask given to their authors:\n{a.task.instruction}\n\n"
            f"Rubric:\n{items}\n\nSubmission {a.id}:\n{files_text(a)}\n\nSubmission {b.id}:\n{files_text(b)}\n\n"
            f'Which satisfies the task and rubric better? Reply with JSON only: {{"winner": "{a.id}" or "{b.id}" '
            'or "tie", "reason": "..."}')


def _json(reply: str) -> dict:
    found = re.search(r"\{.*\}", reply, re.S)
    if not found:
        raise ValueError("no JSON in the reply")
    return json.loads(found.group(0))


def parse_scores(reply: str, count: int) -> Scored:
    """The mean of the rubric items' scores, and each item's score and reason. Raises ValueError on any other shape."""
    items = _json(reply)["items"]
    reasons = {str(i): {"score": min(1.0, max(0.0, float(items[str(i)]["score"]))),
                        "reason": str(items[str(i)].get("reason", ""))} for i in range(1, count + 1)}
    return mean(r["score"] for r in reasons.values()), reasons


def parse_winner(reply: str, ids: tuple[str, str]) -> str:
    winner = str(_json(reply)["winner"])
    if winner not in (*ids, "tie"):
        raise ValueError(f"winner {winner!r} is neither submission")
    return winner


class Panel:
    """Judges from at least two model families, fixed for a run. The score is the panel's median; each
    judge's own score is kept beside it."""

    def __init__(self, judges: list, compared: str = ""):
        families = {j.family for j in judges}
        if len(families) < 2:
            raise SystemExit("the judge panel needs models from at least two families")
        if compared in families:
            raise SystemExit(f"the judge panel includes a {compared} model, the family being compared")
        self.judges = judges

    async def _ask(self, judge, prompt: str, parse):
        for _ in range(3):
            try:
                return parse(await judge.ask(prompt))
            except (ValueError, KeyError, TypeError):
                continue
        raise RuntimeError(f"{judge.name} gave no usable answer")

    async def score(self, sub: Submission, rubric: tuple[str, ...]) -> dict[str, Scored]:
        prompt = pointwise(sub, rubric)
        answers = await asyncio.gather(*(self._ask(j, prompt, lambda r: parse_scores(r, len(rubric)))
                                         for j in self.judges))
        return {j.name: a for j, a in zip(self.judges, answers)}

    async def prefer(self, a: Submission, b: Submission, rubric: tuple[str, ...]) -> dict[str, Scored]:
        """For each judge, a's score against b: the mean over both orders (1 win, 0.5 tie, 0 loss)."""
        ids = (a.id, b.id)
        prompts = [pairwise(a, b, rubric), pairwise(b, a, rubric)]
        out = {}
        for judge in self.judges:
            winners = [await self._ask(judge, p, lambda r: parse_winner(r, ids)) for p in prompts]
            out[judge.name] = (mean({a.id: 1.0, "tie": 0.5}.get(w, 0.0) for w in winners), {"winners": winners})
        return out
