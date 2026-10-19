"""Every contestant judges; rankings become points; the points are tallied into the final order."""
import json

import pytest

from harness_arena.judge import PeerJudging, groups, parse_ranking
from harness_arena.stats import kendall_w, p_at_least, spearman
from harness_arena.tally import borda, tally

from conftest import REPORT, harness
from test_blinding import play_and_scrub


def test_a_ranking_must_name_every_result_once():
    assert parse_ranking('{"ranking": ["b", "a"], "reasons": {"a": "x"}}', ["a", "b"])[0] == ["b", "a"]
    for bad in ('{"ranking": ["a"]}', '{"ranking": ["a", "a"]}', '{"ranking": ["a", "b", "c"]}', "not json", "{}"):
        with pytest.raises((ValueError, KeyError)):
            parse_ranking(bad, ["a", "b"])


async def test_every_harness_that_ran_judges_every_group(contest, bench, catalog, run, runner):
    await play_and_scrub(contest, bench, catalog, run)
    await PeerJudging(runner, bench).run_all(["alpha", "beta"])
    rows = run.rows("judgments")
    assert sorted((r["judge"], r["task"]) for r in rows) == sorted((j, t) for j in ("alpha", "beta") for t in ("one", "three", "two"))
    assert all(len(r["ranking"]) == 2 and not r["error"] for r in rows)
    await PeerJudging(runner, bench).run_all(["alpha", "beta"])         # resume: nothing is judged twice
    assert len(run.rows("judgments")) == 6


async def test_a_judge_that_will_not_write_a_ranking_is_retried_once_then_recorded(contest, bench, catalog, run, runner, tmp_path):
    harness(catalog.folder, "mute", f'echo x >> {tmp_path}/tries\n[ -f CRITERIA.md ] || {{ printf ANSWER > solution.py; }}\n' + REPORT)
    await contest.play(bench, ["alpha", "beta"], bench.tasks()[:1], 1)
    from harness_arena.blind import Scrubbing
    Scrubbing(run, set()).scrub_all()
    await PeerJudging(runner, bench).run_all(["mute"])
    (row,) = run.rows("judgments")
    assert len((tmp_path / "tries").read_text().split()) == 2 and row["ranking"] == [] and "no usable ranking.json" in row["error"]
    # a failed judgment is excluded from the tally, and a resume tries it again
    await PeerJudging(runner, bench).run_all(["mute"])
    assert len(run.rows("judgments")) == 2


def test_borda_gives_best_one_and_worst_zero():
    assert borda(["a", "b", "c"]) == {"a": 1.0, "b": 0.5, "c": 0.0}
    assert borda(["a", "b"]) == {"a": 1.0, "b": 0.0}


def row(judge, task, ranking, repeat=1, **extra):
    return {"judge": judge, "task": task, "repeat": repeat, "ranking": ranking, "error": "", "finding": "", **extra}


def test_the_tally_matches_hand_computed_numbers():
    authors = {"a1": "alpha", "b1": "beta", "g1": "gamma", "a2": "alpha", "b2": "beta", "g2": "gamma"}
    judgments = [row("alpha", "t1", ["a1", "b1", "g1"]), row("beta", "t1", ["b1", "a1", "g1"]), row("gamma", "t1", ["a1", "g1", "b1"]),
                 row("alpha", "t2", ["b2", "a2", "g2"]), row("beta", "t2", ["b2", "g2", "a2"]), row("gamma", "t2", ["b2", "a2", "g2"]),
                 row("beta", "t3", [], error="no usable ranking.json"), row("gamma", "t3", ["a1", "b1", "g1"], finding="called other")]
    result = tally(judgments, authors)
    scores = {s.harness: s for s in result.standings}
    # t1 points: a1 = (1 + .5 + 1)/3, b1 = (.5 + 1 + 0)/3, g1 = (0 + 0 + .5)/3; t2: b2 = 1, a2 = (.5 + 0 + .5)/3, g2 = (0 + .5 + 0)/3
    assert scores["alpha"].score == pytest.approx(((2.5 / 3) + (1 / 3)) / 2)
    assert scores["beta"].score == pytest.approx(((1.5 / 3) + 1) / 2)
    assert scores["gamma"].score == pytest.approx(((0.5 / 3) + (0.5 / 3)) / 2)
    assert [s.harness for s in result.standings] == ["beta", "alpha", "gamma"] and result.judgments == 6      # failures aren't tallied
    assert (scores["alpha"].firsts, scores["beta"].firsts, scores["gamma"].firsts) == (1, 1, 0)
    assert scores["alpha"].mean_rank == pytest.approx(1.5)
    # alpha gave its own a1 1.0 against the others' mean of (.5 + 1)/2, and its own a2 0.5 against (0 + .5)/2
    assert scores["alpha"].self_bias == pytest.approx(((1 - .75) + (.5 - .25)) / 2)
    assert 0 < result.agreement < 1 and result.anchor is None


def test_the_anchor_is_how_well_the_ranking_agrees_with_the_hidden_check():
    authors = {"a": "alpha", "b": "beta", "c": "gamma"}
    judgments = [row("alpha", "t", ["a", "b", "c"]), row("beta", "t", ["a", "b", "c"])]
    assert tally(judgments, authors, {"a": 1.0, "b": 0.5, "c": 0.0}).anchor == pytest.approx(1)
    assert tally(judgments, authors, {"a": 0.0, "b": 0.5, "c": 1.0}).anchor == pytest.approx(-1)
    assert tally(judgments, authors, {"a": 1.0, "b": 1.0, "c": 1.0}).anchor is None        # a check everyone passes says nothing


def test_statistics():
    assert kendall_w([["a", "b", "c"], ["a", "b", "c"]]) == pytest.approx(1)
    assert kendall_w([["a", "b"], ["b", "a"]]) == pytest.approx(0)
    assert p_at_least(0, [0.5] * 4) == pytest.approx(1) and p_at_least(4, [0.5] * 4) == pytest.approx(1 / 16)
    assert p_at_least(2, [0.5, 0.25]) == pytest.approx(0.125)
    assert spearman([1, 2, 3], [10, 20, 30]) == pytest.approx(1) and spearman([1, 2, 3], [5, 5, 5]) is None


def test_groups_need_two_results_to_be_ranked(run):
    run.save("submissions", {"a": {"task": "t", "repeat": 1}, "b": {"task": "t", "repeat": 1}, "c": {"task": "u", "repeat": 1}})
    assert groups(run) == {("t", 1): ["a", "b"]}
