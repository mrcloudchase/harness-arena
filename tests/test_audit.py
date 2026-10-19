"""Blindness is verified, not assumed: a classifier before judging, the harnesses' own guesses after."""
from harness_arena.blind import Scrubbing
from harness_arena.fingerprint import classify, exclusive_terms
from harness_arena.guess import GuessAudit, parse_guess
from harness_arena.submission import new_id

import pytest

from test_blinding import play_and_scrub


def populate(run, samples):
    """samples: (harness, {path: text}). Writes the run records, the submission index and the raw deliverables."""
    index = {}
    for n, (h, files) in enumerate(samples):
        sid = new_id()
        run.append("runs", {"harness": h, "task": "t", "repeat": n, "submission": sid, "status": "ok", "finding": ""})
        index[sid] = {"task": "t", "repeat": n}
        for name, text in files.items():
            (run.path / "raw" / sid / name).parent.mkdir(parents=True, exist_ok=True)
            (run.path / "raw" / sid / name).write_text(text)
    run.save("submissions", index)


def test_the_classifier_beats_chance_only_when_something_gives_the_author_away():
    giveaway = [("a", "total = value\n# zorbx tuned"), ("a", "count = value\n# zorbx tuned"), ("a", "index = value\n# zorbx tuned"),
                ("b", "total = value"), ("b", "count = value"), ("b", "index = value")]
    right, p = classify(giveaway)
    assert right == 6 and p < 0.05
    assert classify([(h, "same text") for h in "aabb"])[1] > 0.05
    assert exclusive_terms([("a", "x\n# zorbx tuned", "# zorbx tuned")] * 2 + [("b", "x", "")] * 2) == {"zorbx", "tuned"}


async def test_a_fingerprint_in_a_comment_is_found_scrubbed_and_the_classifier_then_passes(run):
    populate(run, [("a", {"solution.py": f"v{i} = {i}\n# zorbx tuned\n"}) for i in range(4)]
                  + [("b", {"solution.py": f"v{i} = {i}\n"}) for i in range(4)])
    scrubbing = Scrubbing(run, set())
    result = await scrubbing.run_loop(3)
    assert result.state == "success" and result.rounds == 2
    saved = run.load("scrub")
    assert {"zorbx", "tuned"} <= set(saved["terms_added"])
    for sid in run.load("submissions"):
        text = (run.path / "submissions" / sid / "solution.py").read_text()
        assert "zorbx" not in text and text.startswith("v")           # the work is untouched
    raw = [(run.path / "raw" / sid / "solution.py").read_text() for sid in run.load("submissions")]
    assert sum("zorbx" in t for t in raw) == 4                       # the private raw copies keep what the judges never see


async def test_a_difference_in_the_code_itself_is_never_scrubbed_away(run):
    populate(run, [("a", {"solution.py": f"zorbx_cache{i} = 1\n"}) for i in range(4)]
                  + [("b", {"solution.py": f"other_cache{i} = 1\n"}) for i in range(4)])
    result = await Scrubbing(run, set()).run_loop(3)
    assert result.state == "stalled" and "none in comments or prose" in result.why      # reported, not hidden
    assert any("zorbx_cache" in (d / "solution.py").read_text() for d in (run.path / "submissions").iterdir())
    assert run.load("scrub")["state"] == "stalled"


def test_a_guess_must_name_every_result_and_every_harness_once():
    assert parse_guess('{"a": "x", "b": "y"}', ["a", "b"], ["x", "y"]) == {"a": "x", "b": "y"}
    for bad in ('{"a": "x", "b": "x"}', '{"a": "x"}', '{"a": "x", "b": "z"}'):
        with pytest.raises(ValueError):
            parse_guess(bad, ["a", "b"], ["x", "y"])


def seal_groups(run, judges, groups, guesses):
    """Groups of one result per harness; guesses(judge, harness_to_id) -> {id: name}."""
    truth, rows = {}, []
    for g in range(groups):
        ids = {h: new_id() for h in judges}
        truth.update({i: {"harness": h, "task": "t", "repeat": g} for h, i in ids.items()})
        rows += [{"judge": j, "task": "t", "repeat": g, "guess": guesses(j, ids), "error": ""} for j in judges]
    run.seal(truth)
    run.finish_judging()
    for r in rows:
        run.append("guesses", r)


def verdict(runner):
    return GuessAudit(runner).verdict()


def test_judges_who_cannot_tell_the_harnesses_apart_are_blind(runner):
    names = ["alpha", "beta", "gamma"]
    seal_groups(runner.run, names, 8, lambda j, ids: {ids[h]: names[(names.index(h) + 1) % 3] for h in names})     # always wrong
    v = verdict(runner)
    assert v["blind"] and v["pooled"]["right"] == 0 and v["pooled"]["n"] == 72


def test_judges_who_can_tell_the_harnesses_apart_are_not_blind(runner):
    names = ["alpha", "beta", "gamma"]
    seal_groups(runner.run, names, 8, lambda j, ids: {ids[h]: h for h in names})                                   # always right
    v = verdict(runner)
    assert not v["blind"] and v["pooled"]["p"] < 1e-6 and all(t["p"] < 0.05 / 3 for t in v["judges"].values())


def test_a_harness_that_recognises_its_own_work_is_caught_even_if_it_cannot_tell_the_others(runner):
    names = ["alpha", "beta", "gamma"]

    def own_only(judge, ids):                        # right about its own result, wrong about the other two
        others = [h for h in names if h != judge]
        return {ids[judge]: judge, ids[others[0]]: others[1], ids[others[1]]: others[0]}
    seal_groups(runner.run, names, 8, own_only)
    v = verdict(runner)
    assert v["self"]["right"] == v["self"]["n"] == 24 and v["self"]["p"] < 0.05 and not v["blind"]
    assert v["pooled"]["p"] > 0.05                                                      # only the self test sees it


async def test_the_guess_audit_gives_the_harnesses_only_the_results_and_the_names(contest, bench, catalog, run, runner):
    await play_and_scrub(contest, bench, catalog, run)
    run.seal({r["submission"]: {k: r[k] for k in ("harness", "task", "repeat")} for r in run.runs().values()})
    run.finish_judging()
    audit = GuessAudit(runner, sample=3)
    await audit.run_all(["alpha", "beta"])
    rows = run.rows("guesses")
    assert len(rows) == 6 and all(len(r["guess"]) == 2 and not r["error"] for r in rows)
    v = audit.verdict()
    assert v["pooled"]["right"] == v["pooled"]["n"] == 12 and not v["blind"]    # the fake work gives itself away: caught
