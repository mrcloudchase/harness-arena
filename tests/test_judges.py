"""Harness judges are held out and see only the submission; calibration measures agreement; shipped benchmarks are sound."""
import json

import pytest

from hiddenarena.benchmark import BENCHMARKS, Benchmark
from hiddenarena.calibrate import calibrate
from hiddenarena.exercise import Exerciser
from hiddenarena.submission import Submission

from conftest import harness

JUDGE = """
find . -type f -not -path './.hi/*' -not -path './.git/*' | sort > {listing}
echo "$PWD" >> {listing}
printf '{{"items": {{"1": {{"score": 0.75, "reason": "ran it"}}}}}}' > verdict.json
"""


def submission(tmp_path, task):
    (tmp_path / "S-1").mkdir()
    (tmp_path / "S-1" / "solution.py").write_text("ANSWER")
    return Submission("S-1", task, tmp_path / "S-1")


async def test_a_contestant_cannot_be_the_harness_judge(catalog, turns):
    with pytest.raises(SystemExit):
        Exerciser(catalog, turns, "alpha", ["deepseek/deepseek-chat"], contestants=["alpha", "beta"])


async def test_the_harness_judge_sees_only_the_submission_the_task_and_the_rubric(catalog, turns, bench, tmp_path):
    listing = tmp_path / "listing"
    harness(catalog.folder, "judge", JUDGE.format(listing=listing))
    ex = Exerciser(catalog, turns, "judge", ["deepseek/deepseek-chat"], contestants=["alpha", "beta"])
    (score, reasons), = (await ex.score(submission(tmp_path, bench.tasks()[0]), ("it works",))).values()
    assert score == 0.75 and reasons["1"]["reason"] == "ran it"
    *files, cwd = listing.read_text().split("\n")[:-1]
    assert files == ["./AGENTS.md", "./RUBRIC.md", "./submission/solution.py"]
    assert not any(n in cwd for n in ("alpha", "beta", "deepseek", "run"))        # a neutral path, too


async def test_the_harness_judge_names_its_judge_by_harness_and_model(catalog, turns, bench, tmp_path):
    harness(catalog.folder, "judge", JUDGE.format(listing=tmp_path / "l"))
    out = await Exerciser(catalog, turns, "judge", ["deepseek/deepseek-chat", "deepseek/deepseek-reasoner"], []).score(
        submission(tmp_path, bench.tasks()[0]), ("x",))
    assert set(out) == {"judge@deepseek/deepseek-chat", "judge@deepseek/deepseek-reasoner"}


async def test_calibration_measures_each_judges_agreement_with_the_humans():
    bench = Benchmark.load("readme")
    human = {e.path.name: e.human for e in bench.calibration()}

    class Scorer:
        async def score(self, sub, rubric):
            return {"tracks": (human[sub.path.name], {}), "inverse": (1 - human[sub.path.name], {}), "flat": (0.5, {})}
    cal = await calibrate(bench, {"llm": Scorer()})
    judges = cal["llm"]["judges"]
    assert judges["tracks"]["agreement"] == pytest.approx(1) and judges["inverse"]["agreement"] == pytest.approx(-1)
    assert judges["flat"]["agreement"] == 0 and judges["tracks"]["n"] == len(human) and cal["llm"]["threshold"] == 0.6


@pytest.mark.parametrize("name", sorted(p.name for p in BENCHMARKS.iterdir() if p.name != "humaneval" and p.is_dir()))
def test_shipped_benchmarks_are_sound(name):
    bench = Benchmark.load(name)
    tasks = bench.tasks()
    assert tasks and len({t.id for t in tasks}) == len(tasks)
    for t in tasks:
        assert not bench.leaks(t) and bench.deliverables(t)
        judges = bench.judges(t)
        assert judges and judges[0].kind == "deterministic"        # a deterministic judge first, wherever the task allows
        text = (t.instruction + json.dumps(dict(t.files))).lower()
        assert not any(w in text for w in ("hiddenarena", "harness", "claude", "codex", "deepseek"))
    judged = [j for t in tasks for j in bench.judges(t) if j.kind != "deterministic"]
    if judged:                                                      # every judged benchmark ships calibration
        examples = bench.calibration()
        assert len(examples) >= 4 and all(e.path.is_dir() and 0 <= e.human <= 1 for e in examples)
        assert {e.task for e in examples} <= {t.id for t in tasks} and len({e.human for e in examples}) >= 3
