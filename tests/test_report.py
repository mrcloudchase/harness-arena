"""The report's numbers match its records, it needs the sealed map, and it withholds a ranking whose blindness is unverified."""
import pytest

from harness_arena.report import render
from harness_arena.store import Mode, RunDir, Sealed

BLIND = {"blind": True, "alpha": 0.05, "pooled": {"right": 9, "n": 24, "p": 0.4}, "self": {"right": 3, "n": 8, "p": 0.5},
         "judges": {"alpha": {"right": 5, "n": 12, "p": 0.5}, "beta": {"right": 4, "n": 12, "p": 0.6}}}


def run_row(h, task, repeat, sub, wall, cost=None, status="ok", **extra):
    return {"harness": h, "task": task, "repeat": repeat, "submission": sub, "wall_s": wall, "cost_usd": cost, "status": status,
            "error": "", "finding": "", "files": ["solution.py"], **extra}


def judgment(judge, repeat, ranking, **extra):
    return {"judge": judge, "task": "t", "repeat": repeat, "ranking": ranking, "error": "", "finding": "", "reasons": {}, **extra}


def make(tmp_path, audit=BLIND):
    run = RunDir(tmp_path / "r")
    for r in [run_row("alpha", "t", 1, "S-1", 10, 0.5), run_row("alpha", "t", 2, "S-2", 20, 0.25),
              run_row("beta", "t", 1, "S-3", 30), run_row("beta", "t", 2, "S-4", 5, 1.0),
              run_row("beta", "u", 1, "", 9, None, "runner_error", error="429 rate limit"),
              run_row("gamma", "t", 1, "", 3, None, finding="called other-model")]:
        run.append("runs", r)
    run.seal({"S-1": {"harness": "alpha"}, "S-2": {"harness": "alpha"}, "S-3": {"harness": "beta"}, "S-4": {"harness": "beta"}})
    for j in [judgment("alpha", 1, ["S-1", "S-3"]), judgment("beta", 1, ["S-1", "S-3"]),
              judgment("alpha", 2, ["S-4", "S-2"]), judgment("beta", 2, ["S-2", "S-4"]), judgment("gamma", 2, [], error="no usable ranking.json")]:
        run.append("judgments", j)
    run.save("probe", {"alpha": "", "beta": "", "gamma": "", "delta": "needs ANTHROPIC_API_KEY"})
    run.save("config", {"repeat": 2, "harnesses": ["alpha", "beta", "gamma", "delta"]})
    run.save("anchors", {"S-1": 1.0, "S-2": 1.0, "S-3": 0.0, "S-4": 1.0})
    run.save("redactions", {"S-1": 2, "S-2": 0, "S-3": 0, "S-4": 1})
    run.append("guesses", {"judge": "gamma", "task": "t", "repeat": 1, "guess": {}, "error": "no usable guess.json"})
    run.save("scrub", {"state": "success", "why": "", "rounds": 2, "right": 3, "n": 4, "p": 0.31, "terms_added": ["zorbx"]})
    if audit:
        run.save("audit", audit)
    run.finish_judging()
    return run


def test_the_report_needs_judging_to_have_ended(tmp_path):
    run = make(tmp_path)
    run.seal({})
    with pytest.raises(Sealed):
        render(Mode("defaults"), "smoke", run)


def test_numbers_match_the_records(tmp_path):
    text = render(Mode("compare", "deepseek/deepseek-chat"), "smoke", make(tmp_path))
    assert text.startswith("# Compare · deepseek/deepseek-chat · smoke") and "BLIND VERIFIED" in text
    # t#1: S-1 gets 1.0 from both judges, S-3 0.0.  t#2: S-4 1.0 + 0.0 and S-2 0.0 + 1.0, so both 0.5.
    # alpha: (1.0 + 0.5) / 2 = 0.75; beta: (0.0 + 0.5) / 2 = 0.25.
    rows = [l.split(" | ") for l in text.splitlines() if l.startswith("| 1 ") or l.startswith("| 2 ")]
    (first, second) = rows
    assert first[1] == "alpha" and first[2] == "0.75" and second[1] == "beta" and second[2] == "0.25"
    assert first[7].startswith("100% (100%–100%)") and second[7].startswith("50% (0%–100%)")     # hidden-check pass rates and spread
    assert first[8] == "15.0" and first[9] == "30" and first[10] == "0.7500"                        # median wall, total wall, total cost
    assert "BLIND VERIFIED" in text and "Kendall" in text
    assert "no usable ranking.json" in text and "called other-model (1 runs)" in text and "429 rate limit" in text
    assert "**delta**: needs ANTHROPIC_API_KEY" in text and "3 in total over 4 results, at most 2 in one" in text
    assert "zorbx" in text and "9 of 24" in text
    assert "ranked by 2 judges" in text                                   # gamma's ranking failed, so it is not counted
    assert "Could not take the test (no usable guess): gamma" in text


@pytest.mark.parametrize("audit", [None, {**BLIND, "blind": False}])
def test_a_ranking_whose_blindness_is_unverified_is_withheld(tmp_path, audit):
    text = render(Mode("defaults"), "smoke", make(tmp_path, audit))
    assert "BLINDNESS NOT VERIFIED: ranking withheld" in text and "| Rank |" not in text
    assert "Defaults · each harness on its own default model · smoke" in text
