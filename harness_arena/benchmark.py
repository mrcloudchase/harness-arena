"""A benchmark plug-in: the folder benchmarks/<name>/ with a benchmark.py exposing

    tasks()              the tasks: an id, an instruction and input files. A task never names its benchmark,
                         its dataset or any harness.
    deliverables(task)   glob patterns of the files that make up a submission. Only these are ever judged.
    criteria(task)       what makes one result better than another, written to stand alone: judges never see
                         the task, only the results and this.
    check(task, dir)     optional: a deterministic (score, why) used as a ground-truth anchor, never as the ranking.
    reference(task)      optional: {path: text} of a correct submission, for the intake gate.

Hidden material (answers, hidden tests, reference solutions) lives in the folder and never reaches a contestant.
"""
from __future__ import annotations

import hashlib
import importlib.util
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

BENCHMARKS = Path(__file__).resolve().parents[1] / "benchmarks"


@dataclass(frozen=True)
class Task:
    id: str
    instruction: str
    files: Mapping[str, str] = field(default_factory=dict)      # path -> content


class Benchmark:
    def __init__(self, folder: Path):
        self.folder, self.name = folder, folder.name
        spec = importlib.util.spec_from_file_location(f"benchmark_{self.name}", folder / "benchmark.py")
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    @classmethod
    def load(cls, name: str, root: Path = BENCHMARKS) -> Benchmark:
        if not (root / name / "benchmark.py").is_file():
            raise SystemExit(f"no benchmark {name!r}: expected {root / name / 'benchmark.py'}")
        return cls(root / name)

    def tasks(self) -> list[Task]:
        return list(self.module.tasks())

    def deliverables(self, task: Task) -> list[str]:
        return list(self.module.deliverables(task))

    def criteria(self, task: Task) -> str:
        return self.module.criteria(task)

    def check(self, task: Task, submission: Path) -> tuple[float, str] | None:
        return self.module.check(task, submission) if hasattr(self.module, "check") else None

    def reference(self, task: Task) -> dict[str, str] | None:
        return self.module.reference(task) if hasattr(self.module, "reference") else None

    def leaks(self, task: Task) -> list[str]:
        """Input files that repeat hidden material."""
        hidden = {hashlib.sha256(p.read_bytes()).hexdigest()
                  for d in ("hidden", "reference") for p in (self.folder / d).rglob("*") if p.is_file()}
        return [path for path, text in task.files.items() if hashlib.sha256(text.encode()).hexdigest() in hidden]
