"""Where things live. A Mode says which comparison a result belongs to, so the two never share a
directory; a RunDir is one run's records, verdicts, submissions and sealed map.

The sealed map (opaque id -> harness, model, task, repeat) is written before judging and can be read
only after judging is marked finished: nothing that judges can see the key.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parents[1]
MODEL = re.compile(r"^(?!.*\.\.)[\w.-]+(/[\w.:-]+)+$")


class Sealed(Exception):
    """The sealed map was asked for before judging ended."""


@dataclass(frozen=True)
class Mode:
    kind: Literal["compare", "defaults"]
    model: str = ""                                  # provider/model; compare has one, defaults none

    def __post_init__(self) -> None:
        if (self.kind == "compare") != bool(self.model):
            raise SystemExit("compare needs --model provider/model; defaults takes none")
        if self.model and not MODEL.match(self.model):
            raise SystemExit(f"--model must look like provider/model, not {self.model!r}")

    @property
    def rel(self) -> Path:
        return Path(self.kind) / self.model

    @property
    def title(self) -> str:
        return f"Compare · {self.model}" if self.model else "Defaults · each harness on its own default model"

    def run_dir(self, benchmark: str, run_id: str, root: Path = ROOT) -> Path:
        return root / "results" / self.rel / benchmark / run_id

    def latest(self, benchmark: str, root: Path = ROOT) -> str:
        runs = sorted((root / "results" / self.rel / benchmark).glob("*"), key=lambda p: p.stat().st_mtime)
        if not runs:
            raise SystemExit(f"no {self.kind} run of {benchmark} yet")
        return runs[-1].name

    def report(self, benchmark: str, root: Path = ROOT) -> Path:
        return root / "reports" / self.rel / f"{benchmark}.md"


class RunDir:
    def __init__(self, path: Path):
        self.path = path.resolve()
        self.path.mkdir(parents=True, exist_ok=True)

    def append(self, name: str, row: dict) -> None:
        with open(self.path / f"{name}.jsonl", "a") as f:
            f.write(json.dumps(row) + "\n")

    def rows(self, name: str) -> list[dict]:
        p = self.path / f"{name}.jsonl"
        return [json.loads(line) for line in p.read_text().splitlines()] if p.exists() else []

    def load(self, name: str, default=None):
        p = self.path / f"{name}.json"
        return json.loads(p.read_text()) if p.exists() else default

    def save(self, name: str, value) -> None:
        (self.path / f"{name}.json").write_text(json.dumps(value, indent=1))

    def runs(self) -> dict[tuple, dict]:
        """The latest record of each (harness, task, repeat); a retried run replaces its earlier one."""
        return {(r["harness"], r["task"], r["repeat"]): r for r in self.rows("runs")}

    def seal(self, mapping: dict[str, dict]) -> None:
        (self.path / "sealed").mkdir(exist_ok=True)
        (self.path / "sealed" / "map.json").write_text(json.dumps(mapping, indent=1))
        (self.path / "sealed" / "judged").unlink(missing_ok=True)    # new submissions: judging has not ended

    def finish_judging(self) -> None:
        (self.path / "sealed" / "judged").touch()

    def sealed(self) -> dict[str, dict]:
        if not (self.path / "sealed" / "judged").exists():
            raise Sealed("the sealed map is read only after judging has ended")
        return json.loads((self.path / "sealed" / "map.json").read_text())
