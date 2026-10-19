"""A submission: only the files matching a task's deliverables, scrubbed, under an opaque id.

Everything else a harness leaves behind (its output, logs, .home/, instruction files, files outside the
deliverables) carries its fingerprints and never leaves the workspace. The unscrubbed deliverables are kept
privately under raw/, so a scrub can be redone with new terms; judges only ever get the scrubbed copy.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

INSTRUCTION_FILES = {"AGENTS.md", "CLAUDE.md", "QWEN.md", "__pycache__"}
PROSE_SUFFIXES = {".md", ".txt", ".rst"}
COMMENT = ("#", "//", "--", "*", "/*", "<!--")


def new_id() -> str:
    return f"S-{secrets.token_hex(3)}"


def internal(rel: Path) -> bool:
    """A path a harness or its CLI owns: a dotfile or directory (.hi, .home, .git, .aider*) or an instruction file."""
    return any(part.startswith(".") or part in INSTRUCTION_FILES for part in rel.parts)


def collect(workspace: Path, patterns: list[str]) -> dict[str, str]:
    """The deliverables as {path: text}. Binary files and links that leave the workspace are not collected."""
    root, files = workspace.resolve(), {}
    for pattern in patterns:
        for path in sorted(workspace.glob(pattern)):
            rel = path.relative_to(workspace)
            if rel.as_posix() in files or not path.is_file() or internal(rel) or not path.resolve().is_relative_to(root):
                continue
            try:
                files[rel.as_posix()] = path.read_text()
            except UnicodeDecodeError:
                continue
    return files


def prose(files: dict[str, str]) -> str:
    """The text that can be redacted without changing what the work does: comments and prose files."""
    out = []
    for name, text in files.items():
        if Path(name).suffix in PROSE_SUFFIXES:
            out.append(text)
        else:
            out += [line for line in text.splitlines() if line.strip().startswith(COMMENT)]
    return "\n".join(out)


def write(dest: Path, files: dict[str, str], scrub: Callable[[str], tuple[str, int]]) -> int:
    """Write the files, scrubbed, into a fresh dest. Returns how many redactions that took."""
    dest.mkdir(parents=True, exist_ok=True)
    for old in sorted(dest.rglob("*"), reverse=True):
        old.unlink() if old.is_file() else old.rmdir()
    redactions = 0
    for name, text in files.items():
        name, n1 = scrub(name)
        body, n2 = scrub(text)
        (dest / name).parent.mkdir(parents=True, exist_ok=True)
        (dest / name).write_text(body)
        redactions += n1 + n2
    return redactions


@dataclass(frozen=True)
class Submission:
    """What a judge is given: an id, its group (task and repeat) and a scrubbed directory. Nothing says who wrote it."""
    id: str
    task: str
    repeat: int
    path: Path

    def files(self) -> dict[str, str]:
        return {p.relative_to(self.path).as_posix(): p.read_text() for p in sorted(self.path.rglob("*")) if p.is_file()}


NO_FILES = "This result contains no files."


def room(root: Path, ids: list[str], extra: dict[str, str]) -> dict[str, str]:
    """The files of a judge's workspace: each submission under its id, in the order given, plus the extras."""
    files = dict(extra)
    for sid in ids:
        theirs = Submission(sid, "", 0, root / "submissions" / sid).files()
        files.update({f"submissions/{sid}/{p}": t for p, t in theirs.items()} or {f"submissions/{sid}/NO_FILES.txt": NO_FILES})
    return files
