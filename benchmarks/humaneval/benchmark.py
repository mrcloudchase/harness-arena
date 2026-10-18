"""humaneval: OpenAI's HumanEval, 164 hand-written Python function-completion problems.

Credit: Chen et al., "Evaluating Large Language Models Trained on Code" (2021), https://github.com/openai/human-eval,
MIT licence. The data is not in this repo: set HUMANEVAL_PATH to HumanEval.jsonl.gz, downloaded from there.
Contestants get only each problem's prompt; the tests and the reference solution never enter their workspace.
"""
import functools
import gzip
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from harness_arena.benchmark import Deterministic, Task


@functools.cache
def problems() -> dict[str, dict]:
    path = os.environ.get("HUMANEVAL_PATH")
    if not path:
        raise SystemExit("humaneval: set HUMANEVAL_PATH to HumanEval.jsonl.gz (github.com/openai/human-eval, MIT)")
    with gzip.open(path, "rt") as f:
        return {f"p{n:03d}": json.loads(line) for n, line in enumerate(f)}


def tasks():
    for id, p in problems().items():
        yield Task(id, "solution.py holds a Python function with a docstring and no body. Complete it so it does "
                       "what the docstring says, keeping its name and signature. Use only the standard library.",
                   {"solution.py": p["prompt"]})


def deliverables(task):
    return ["solution.py"]


def run_tests(task, submission, timeout_s=20):
    p = problems()[task.id]
    program = (submission / "solution.py").read_text() + f"\n\n{p['test']}\n\ncheck({p['entry_point']})\n"
    with tempfile.TemporaryDirectory() as work:
        Path(work, "run.py").write_text(program)
        try:
            done = subprocess.run([sys.executable, "-I", "run.py"], cwd=work, capture_output=True, text=True, timeout=timeout_s)
        except subprocess.TimeoutExpired:
            return 0.0, f"timed out after {timeout_s}s"
    return (1.0, "passed") if done.returncode == 0 else (0.0, (done.stderr.strip().splitlines() or ["failed"])[-1])


def judges(task):
    return [Deterministic(run_tests)]
