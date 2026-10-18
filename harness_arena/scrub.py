"""Scrubbing: redact what could identify the harness, vendor or model that wrote a submission.

The names come from the harness folders, the providers and the models in use, never from a hand-kept list.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REDACTED = "[REDACTED]"
TRAILERS = re.compile(r"^.*(?:co-authored-by:|generated (?:with|by)|🤖).*$", re.I | re.M)
GENERIC = {"the", "cli", "code", "agent", "harness"}


def harness_terms(folder: Path) -> set[str]:
    """A harness's folder name, its name, its display name ("Claude Code", "Claude") and the CLI names its
    description mentions in parentheses or backticks."""
    spec = json.loads((folder / "harness.json").read_text())
    desc = spec.get("description", "")
    terms = {folder.name, spec["name"], *re.findall(r"\(([\w-]+)\)", desc), *re.findall(r"`([\w-]+)", desc)}
    if display := re.match(r"([A-Z][\w-]*(?: [A-Z][\w-]*){0,2})\b", desc):
        terms |= {display.group(1), display.group(1).split()[0]}
    return terms


def model_terms(model: str) -> set[str]:
    """A model's id and its family word: deepseek/deepseek-chat -> deepseek-chat, deepseek."""
    name = model.rpartition("/")[2]
    return {name, re.split(r"[-_.:]", name)[0]} if name else set()


class Scrubber:
    def __init__(self, terms: set[str]):
        words = sorted({t for t in terms if len(t) >= 3 and t.lower() not in GENERIC}, key=len, reverse=True)
        self.terms = words
        self.pattern = re.compile(r"(?<![A-Za-z0-9])(?:%s)(?![A-Za-z0-9])" % "|".join(map(re.escape, words)),
                                  re.I) if words else None

    def __call__(self, text: str) -> tuple[str, int]:
        """The text with every identifying name and trailer redacted, and how many were."""
        text, count = TRAILERS.subn(REDACTED, text)
        if self.pattern:
            text, more = self.pattern.subn(REDACTED, text)
            count += more
        return text, count
