"""Deterministic checks a benchmark can reuse. They run on the host, on the submission directory, never
in a contestant's sandbox, with the benchmark's hidden material copied beside the submission."""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable

from .benchmark import Task


def pytest_check(tests: Path, timeout_s: int = 60) -> Callable[[Task, Path], tuple[float, str]]:
    """Run tests/test_<task id>.py against the submission: the share of tests that pass."""
    def check(task: Task, submission: Path) -> tuple[float, str]:
        with tempfile.TemporaryDirectory() as work:
            shutil.copytree(submission, work, dirs_exist_ok=True)
            shutil.copy(tests / f"test_{task.id}.py", work)
            try:
                out = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                                     cwd=work, capture_output=True, text=True, timeout=timeout_s).stdout
            except subprocess.TimeoutExpired:
                return 0.0, f"timed out after {timeout_s}s"
        counts = {k: sum(int(n) for n in re.findall(rf"(\d+) {k}", out)) for k in ("passed", "failed", "error")}
        total = sum(counts.values())
        return (counts["passed"] / total if total else 0.0), (out.strip().splitlines() or ["no output"])[-1]
    return check
