"""The report's numbers match its records, and it needs the sealed map."""
import pytest

from harness_arena.blindcheck import blindcheck, p_value
from harness_arena.calibrate import agreement
from harness_arena.report import index, judged_kinds_ok, render, summarize
from harness_arena.store import Mode, RunDir, Sealed
from harness_arena.submission import Submission
from harness_arena.benchmark import Task


def run_row(h, task, repeat, sub, wall, cost=None, status="ok", **extra):
    return {"harness": h, "task": task, "repeat": repeat, "submission": sub, "wall_s": wall, "cost_usd": cost,
            "status": status, "redactions": 2, "error": "", **extra}


def make(tmp_path):
    run = RunDir(tmp_path / "r")
    rows = [run_row("a", "t1", 1, "S-1", 10, 0.5), run_row("a", "t1", 2, "S-2", 20, 0.25),
            run_row("a", "t2", 1, "S-3", 30), run_row("b", "t1", 1, "S-4", 5, 1.0),
            run_row("b", "t2", 1, "", 9, None, "runner_error", error="429")]
    for r in rows:
        run.append("runs", r)
    scores = {"S-1": 1.0, "S-2": 0.0, "S-3": 1.0, "S-4": 0.5}
    for sub, score in scores.items():
        run.append("verdicts", {"submission": sub, "kind": "deterministic", "judge": "tests", "score": score, "reasons": ""})
    for sub, (j1, j2) in {"S-1": (0.8, 0.6), "S-2": (0.2, 0.4)}.items():
        for j, s in (("m/1", j1), ("n/2", j2)):
            run.append("verdicts", {"submission": sub, "kind": "llm", "judge": j, "score": s, "reasons": ""})
    run.seal({s: {"harness": h, "task": t, "repeat": r} for s, (h, t, r) in
              {"S-1": ("a", "t1", 1), "S-2": ("a", "t1", 2), "S-3": ("a", "t2", 1), "S-4": ("b", "t1", 1)}.items()})
    run.save("probe", {"a": "", "b": "", "c": "needs ANTHROPIC_API_KEY"})
    run.save("config", {"repeat": 2})
    return run


def test_numbers_match_the_records(tmp_path):
    run = make(tmp_path)
    run.finish_judging()
    a, b = summarize(run.runs(), run.rows("verdicts"), run.sealed(), set())
    assert (a.harness, a.tasks, a.graded) == ("a", 2, 3)
    assert a.pass_rate == pytest.approx(2 / 3) and a.spread == (0.0, 1.0)         # repeat 1: 2/2, repeat 2: 0/1
    assert a.deterministic == pytest.approx(2 / 3)
    assert a.judges == {"m/1": pytest.approx(0.5), "n/2": pytest.approx(0.5)} and a.panel == pytest.approx(0.5)
    assert (a.wall_median, a.wall_total, a.cost, a.no_cost, a.redactions) == (20, 60, 0.75, 1, 6)
    assert (b.tasks, b.pass_rate, b.deterministic, b.wall_total, b.cost) == (1, 0.0, 0.5, 5, 1.0)   # its runner error is not scored
    assert b.judges == {} and b.panel is None


def test_the_report_needs_judging_to_have_ended_and_states_its_mode(tmp_path):
    run = make(tmp_path)
    mode = Mode("compare", "deepseek/deepseek-chat")
    with pytest.raises(Sealed):
        render(mode, "smoke", run, {})
    run.finish_judging()
    text = render(mode, "smoke", run, {})
    assert text.startswith("# Compare · deepseek/deepseek-chat · smoke")
    assert "67% (0%–100%)" in text and "c**: needs ANTHROPIC_API_KEY" in text and "b · t2 #1: 429" in text
    assert "not calibrated" in text and "m/1" not in text.split("## Unsupported")[0]     # judged scores withheld
    cal = {"llm": {"threshold": 0.6, "judges": {"m/1": {"agreement": 0.9, "n": 4}, "n/2": {"agreement": 0.7, "n": 4}}}}
    assert "m/1" in render(mode, "smoke", run, cal).split("## Unsupported")[0]
    assert render(Mode("defaults"), "smoke", run, {}).startswith("# Defaults · each harness on its own default model · smoke")


def test_judged_scores_need_every_judge_to_pass_calibration():
    v = [{"kind": "llm", "judge": "m/1"}, {"kind": "llm", "judge": "n/2"}]
    ok = {"llm": {"threshold": 0.6, "judges": {"m/1": {"agreement": 0.9}, "n/2": {"agreement": 0.6}}}}
    assert judged_kinds_ok(v, ok) == {"llm": ""}
    assert "n/2" in judged_kinds_ok(v, {"llm": {"threshold": 0.7, "judges": ok["llm"]["judges"]}})["llm"]
    assert judged_kinds_ok(v, {}) == {"llm": "not calibrated"}
    assert agreement([0.1, 0.5, 0.9], [0, 0.5, 1]) > 0.99 and agreement([0.5, 0.5], [0, 1]) == 0.0


def test_a_leaking_blinding_flags_the_judged_scores(tmp_path):
    run = make(tmp_path)
    run.finish_judging()
    run.save("blindcheck", {"contestants": ["a", "b"], "judges": {"m/1": {"n": 4, "correct": 4, "chance": 0.5, "p": 0.06, "leaking": True}}})
    cal = {"llm": {"threshold": 0.6, "judges": {"m/1": {"agreement": 0.9, "n": 4}, "n/2": {"agreement": 0.9, "n": 4}}}}
    text = render(Mode("defaults"), "smoke", run, cal)
    assert "Panel median ⚠" in text and "LEAKING" in text


async def test_blindcheck_flags_a_judge_that_guesses_better_than_chance(tmp_path):
    run = make(tmp_path)
    run.seal({f"S-{i}": {"harness": "ab"[i % 2], "task": "t", "repeat": i} for i in range(1, 6)})
    subs = [Submission(f"S-{i}", Task("t", "i"), run.path / "x") for i in range(1, 6)]
    for s in subs:
        s.path.mkdir(exist_ok=True)
    (run.path / "x" / "f").write_text("code")
    with pytest.raises(Sealed):
        await blindcheck(run, subs, [])                                          # not before judging ends
    run.finish_judging()
    truth = run.sealed()

    class Guesser:
        def __init__(self, name, right):
            self.name, self.right = name, right

        async def ask(self, prompt):
            sid = next(s for s in truth if s in prompt)
            return truth[sid]["harness"] if self.right else "neither"
    out = await blindcheck(run, subs, [Guesser("sees", True), Guesser("blind", False)])
    assert out["judges"]["sees"]["correct"] == 5 and out["judges"]["blind"]["correct"] == 0
    assert out["judges"]["sees"]["p"] == pytest.approx(0.5 ** 5) and out["judges"]["sees"]["leaking"]
    assert not out["judges"]["blind"]["leaking"]
    assert p_value(0, 5, 0.5) == 1 and p_value(5, 5, 0.5) == pytest.approx(1 / 32)


def test_the_index_lists_every_report(tmp_path):
    for rel in ("compare/m/x/smoke.md", "defaults/smoke.md"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("#")
    assert "(compare/m/x/smoke.md)" in index(tmp_path) and "(defaults/smoke.md)" in index(tmp_path)
