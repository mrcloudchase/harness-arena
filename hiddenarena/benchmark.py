"""A benchmark plug-in: the folder benchmarks/<name>/ with a benchmark.py that exposes tasks(),
deliverables(task) and judges(task). This module loads one, and says what a judge spec looks like.

Hidden material (answers, hidden tests, rubrics, calibration) lives in the folder and never reaches a
contestant: a task whose input files repeat anything under hidden/ or calibration/ is a leak.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, ClassVar, Mapping

BENCHMARKS = Path(__file__).resolve().parents[1] / "benchmarks"


@dataclass(frozen=True)
class Task:
    """What a contestant is given. It never names its benchmark, its dataset or any harness."""
    id: str
    instruction: str
    files: Mapping[str, str] = field(default_factory=dict)      # path -> content


@dataclass(frozen=True)
class Deterministic:
    """A check run on the submission directory: score in [0, 1] and why."""
    check: Callable[[Task, Path], tuple[float, str]]
    name: str = "hidden-tests"
    kind: ClassVar[str] = "deterministic"


@dataclass(frozen=True)
class Model:
    """A panel of model judges scores the submission against the rubric."""
    rubric: tuple[str, ...]
    min_agreement: float = 0.6                       # with the human scores in calibration/
    pairwise: bool = False                           # also judge every pair of submissions, in both orders
    kind: ClassVar[str] = "llm"


@dataclass(frozen=True)
class Exercise:
    """A held-out harness runs the submission and scores it against the rubric, on each judge model."""
    rubric: tuple[str, ...]
    min_agreement: float = 0.6
    kind: ClassVar[str] = "harness"


@dataclass(frozen=True)
class Example:
    """A calibration submission and the score a human gave it."""
    task: str
    path: Path
    human: float


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

    def judges(self, task: Task) -> list:
        return list(self.module.judges(task))

    def calibration(self) -> list[Example]:
        index = self.folder / "calibration" / "examples.json"
        rows = json.loads(index.read_text()) if index.is_file() else []
        return [Example(r["task"], index.parent / r["dir"], float(r["human"])) for r in rows]

    def leaks(self, task: Task) -> list[str]:
        """Input files that repeat hidden material."""
        hidden = {hashlib.sha256(p.read_bytes()).hexdigest()
                  for d in ("hidden", "calibration") for p in (self.folder / d).rglob("*") if p.is_file()}
        return [path for path, text in task.files.items()
                if hashlib.sha256(text.encode()).hexdigest() in hidden]
