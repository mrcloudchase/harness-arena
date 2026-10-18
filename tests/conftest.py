"""Fakes: harness folders written from a shell body, and a benchmark folder, run on LocalRuntime."""
import json
import textwrap
from pathlib import Path

import pytest
from harness_interface import LocalRuntime

from harness_arena.arena import Arena
from harness_arena.benchmark import Benchmark
from harness_arena.catalog import Catalog
from harness_arena.store import Mode, RunDir
from harness_arena.turns import Turns

KEYS = {"DEEPSEEK_API_KEY": "k", "OPENAI_API_KEY": "k", "ANTHROPIC_API_KEY": "k", "GEMINI_API_KEY": "k"}
SOLVED = "# written by alphacli on deepseek-chat\nANSWER\n# Co-Authored-By: Alpha <a@example.com>\n"


def harness(root: Path, name: str, body: str, provider: str = "anthropic", description: str = "") -> None:
    """A fake harness: `name`, on `provider`, whose run.sh is `body`."""
    folder = root / name
    folder.mkdir(parents=True)
    spec = {"name": name, "description": description, "provider": provider, "files": {"AGENTS.md": "{instructions}"},
            "run": {"timeout_s": 20}}
    (folder / "harness.json").write_text(json.dumps(spec))
    (folder / "run.sh").write_text("set -e\n" + textwrap.dedent(body))


REPORT = """printf '{"status":"ok","cost_usd":0.01,"usage":{"input_tokens":1}}' > "$HI_OUTPUT"\n"""
ALPHA = f"""
echo "Alpha Agent v1 (alphacli) transcript SECRET-TRANSCRIPT on $HI_MODEL"
echo "alphacli stderr banner" >&2
printf '%s' '{SOLVED}' > solution.py
echo "SECRET-OTHER-FILE alpha" > notes.txt
""" + REPORT
BETA = "printf 'wrong\\n' > solution.py\n" + REPORT


@pytest.fixture
def harnesses(tmp_path) -> Path:
    root = tmp_path / "harnesses"
    harness(root, "alpha", ALPHA, "anthropic", "Alpha Agent (alphacli), headless.")
    harness(root, "beta", BETA, "openai", "Beta Bot, headless.")
    return root


@pytest.fixture
def catalog(harnesses) -> Catalog:
    return Catalog(harnesses, KEYS)


@pytest.fixture
def bench(tmp_path) -> Benchmark:
    """Two tasks; a submission is correct when it contains ANSWER."""
    folder = tmp_path / "benchmarks" / "fake"
    (folder / "hidden").mkdir(parents=True)
    (folder / "hidden" / "answer.txt").write_text("the hidden answer")
    (folder / "benchmark.py").write_text(textwrap.dedent("""
        from harness_arena.benchmark import Deterministic, Task
        def tasks():
            yield Task("one", "Write solution.py containing ANSWER.")
            yield Task("two", "Write solution.py containing ANSWER, again.")
        def deliverables(task):
            return ["solution.py"]
        def judges(task):
            return [Deterministic(lambda t, p: (1.0 if "ANSWER" in (p / "solution.py").read_text() else 0.0, "checked"))]
    """))
    return Benchmark(folder)


@pytest.fixture
def turns() -> Turns:
    return Turns(lambda target: LocalRuntime(), retries=1, backoff_s=0)


@pytest.fixture
def arena(catalog, turns, tmp_path):
    return Arena(catalog, turns, Mode("compare", "deepseek/deepseek-chat"), RunDir(tmp_path / "run"), workers=2)
