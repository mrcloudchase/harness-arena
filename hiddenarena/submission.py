"""A submission: only the files matching a task's deliverables, scrubbed, copied into a fresh directory.

Everything else a harness leaves behind (its output, logs, .home/, instruction files, files outside the
deliverables) carries its fingerprints and never leaves the workspace.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .benchmark import Task

INSTRUCTION_FILES = {"AGENTS.md", "CLAUDE.md", "QWEN.md", "__pycache__"}


@dataclass(frozen=True)
class Submission:
    """What a judge is given: the task and a scrubbed directory under an opaque id. Nothing says who wrote it."""
    id: str
    task: Task
    path: Path

    def files(self) -> dict[str, str]:
        return {p.relative_to(self.path).as_posix(): p.read_text() for p in sorted(self.path.rglob("*")) if p.is_file()}


def new_id() -> str:
    return f"S-{secrets.token_hex(3)}"


def internal(rel: Path) -> bool:
    """A path a harness or its CLI owns: a dotfile or directory (.hi, .home, .git, .aider*) or an instruction file."""
    return any(part.startswith(".") or part in INSTRUCTION_FILES for part in rel.parts)


def extract(workspace: Path, patterns: list[str], dest: Path, scrub: Callable[[str], tuple[str, int]]) -> int:
    """Copy the deliverables, scrubbed, into dest. Returns how many redactions that took. Binary files and
    links that leave the workspace are not copied."""
    dest.mkdir(parents=True, exist_ok=True)
    root, redactions, seen = workspace.resolve(), 0, set()
    for pattern in patterns:
        for path in sorted(workspace.glob(pattern)):
            rel = path.relative_to(workspace)
            if rel in seen or not path.is_file() or internal(rel) or not path.resolve().is_relative_to(root):
                continue
            try:
                text = path.read_text()
            except UnicodeDecodeError:
                continue
            seen.add(rel)
            name, n1 = scrub(rel.as_posix())
            body, n2 = scrub(text)
            (dest / name).parent.mkdir(parents=True, exist_ok=True)
            (dest / name).write_text(body)
            redactions += n1 + n2
    return redactions
