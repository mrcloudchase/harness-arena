"""Fakes: harness folders written from a shell body, and a benchmark folder, run on LocalRuntime.

Each fake harness can compete (writes solution.py), judge (a workspace with CRITERIA.md: ranks the results by size,
longest first) and guess (a workspace with CONTESTANTS.md: names the author by a marker in the work).
"""
import json
import textwrap
from pathlib import Path

import pytest
from harness_interface import LocalRuntime

from harness_arena.benchmark import Benchmark
from harness_arena.catalog import Catalog
from harness_arena.contest import Contest
from harness_arena.runner import Runner
from harness_arena.store import Mode, RunDir
from harness_arena.turns import Turns

KEYS = {"DEEPSEEK_API_KEY": "k", "OPENAI_API_KEY": "k", "ANTHROPIC_API_KEY": "k", "GEMINI_API_KEY": "k"}
SOLVED = "# written by alphacli on deepseek-chat\nANSWER\n# Co-Authored-By: Alpha <a@example.com>\n"
REPORT = """printf '{"status":"ok","cost_usd":0.01,"usage":{"input_tokens":1}}' > "$HI_OUTPUT"\n"""

JUDGE = """
if [ -f CRITERIA.md ]; then
  { find . -type f -not -path './.hi/*' -not -path './.git/*' -not -path './.home/*' | sort; echo "PWD=$PWD"; cat CRITERIA.md; } >> SEEN
  python3 - <<'PY'
import json, os
ids = sorted(os.listdir("submissions"))
size = lambda i: sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk("submissions/" + i) for f in fs)
json.dump({"ranking": sorted(ids, key=lambda i: (-size(i), i)), "reasons": {i: "by size" for i in ids}}, open("ranking.json", "w"))
PY
elif [ -f CONTESTANTS.md ]; then
  python3 - <<'PY'
import json, os
guess = {}
for i in os.listdir("submissions"):
    text = "".join(open(os.path.join(r, f)).read() for r, _, fs in os.walk("submissions/" + i) for f in fs)
    guess[i] = "alpha" if "ANSWER" in text else "beta"
json.dump(guess, open("guess.json", "w"))
PY
else
"""
PLAYER = {"alpha": f"  printf '%s' '{SOLVED}' > solution.py\n  echo 'SECRET-OTHER-FILE alpha' > notes.txt\n  echo 'Alpha Agent v1 (alphacli) SECRET-TRANSCRIPT'\n",
          "beta": "  printf 'wrong\\n' > solution.py\n"}


def harness(root: Path, name: str, body: str, provider: str = "anthropic", description: str = "") -> None:
    """A fake harness: `name`, on `provider`, whose run.sh is `body`."""
    folder = root / name
    folder.mkdir(parents=True)
    spec = {"name": name, "description": description, "provider": provider, "files": {"AGENTS.md": "{instructions}"},
            "run": {"timeout_s": 20}}
    (folder / "harness.json").write_text(json.dumps(spec))
    (folder / "run.sh").write_text("set -e\n" + textwrap.dedent(body))


def contestant(root: Path, name: str, seen: Path, player: str | None = None, provider: str = "anthropic",
               description: str = "") -> None:
    """A harness that competes as `player`'s work, and judges and guesses by the rules above."""
    harness(root, name, JUDGE.replace("SEEN", str(seen)) + PLAYER[player or name] + "fi\n" + REPORT, provider, description)


@pytest.fixture
def seen(tmp_path) -> Path:
    return tmp_path / "seen"


@pytest.fixture
def harnesses(tmp_path, seen) -> Path:
    root = tmp_path / "harnesses"
    contestant(root, "alpha", seen, provider="anthropic", description="Alpha Agent (alphacli), headless.")
    contestant(root, "beta", seen, provider="openai", description="Beta Bot, headless.")
    return root


@pytest.fixture
def catalog(harnesses) -> Catalog:
    return Catalog(harnesses, KEYS)


@pytest.fixture
def bench(tmp_path) -> Benchmark:
    """Three tasks; a result is correct when it contains ANSWER. Longer is better, per its criteria."""
    folder = tmp_path / "benchmarks" / "fake"
    (folder / "hidden").mkdir(parents=True)
    (folder / "hidden" / "answer.txt").write_text("the hidden answer")
    (folder / "benchmark.py").write_text(textwrap.dedent("""
        from harness_arena.benchmark import Task
        def tasks():
            for id in ("one", "two", "three"):
                yield Task(id, f"Write solution.py containing ANSWER ({id}).")
        def deliverables(task):
            return ["solution.py"]
        def criteria(task):
            return "A result that contains ANSWER is better; longer is better still."
        def check(task, p):
            return (1.0 if (p / "solution.py").is_file() and "ANSWER" in (p / "solution.py").read_text() else 0.0), "checked"
        def reference(task):
            return {"solution.py": "ANSWER"}
    """))
    return Benchmark(folder)


@pytest.fixture
def turns() -> Turns:
    return Turns(lambda target: LocalRuntime(), retries=1, backoff_s=0)


@pytest.fixture
def mode() -> Mode:
    return Mode("compare", "deepseek/deepseek-chat")


@pytest.fixture
def run(tmp_path) -> RunDir:
    return RunDir(tmp_path / "run")


@pytest.fixture
def runner(catalog, turns, mode, run) -> Runner:
    return Runner(catalog, turns, mode, run)


@pytest.fixture
def contest(runner) -> Contest:
    return Contest(runner, workers=2)
