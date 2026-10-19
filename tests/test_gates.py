"""The intake gate stops a benchmark that can't be trusted before any harness is run."""
from harness_arena.benchmark import Task
from harness_arena.gates import gate


def test_a_sound_benchmark_passes(bench):
    assert gate(bench, bench.tasks()) == []


def test_a_reference_that_does_not_pass_its_own_check_is_caught(bench):
    bench.module.reference = lambda task: {"solution.py": "nothing"}
    assert any("reference solution scores 0.0" in p for p in gate(bench, bench.tasks()))


def test_a_check_that_scores_an_empty_submission_is_caught(bench):
    bench.module.check = lambda task, path: (1.0, "always")
    assert any("empty submission scores 1.0" in p for p in gate(bench, bench.tasks()))


def test_a_check_with_no_reference_is_caught(bench):
    del bench.module.reference
    assert any("no reference solution" in p for p in gate(bench, bench.tasks()))


def test_missing_criteria_and_deliverables_are_caught(bench):
    bench.module.criteria = lambda task: "  "
    bench.module.deliverables = lambda task: []
    problems = gate(bench, bench.tasks())
    assert any("no criteria" in p for p in problems) and any("no deliverables" in p for p in problems)


def test_a_task_that_repeats_hidden_material_is_caught(bench):
    tasks = [Task("x", "do", {"notes.txt": "the hidden answer"})]
    assert any("notes.txt repeats hidden material" in p for p in gate(bench, tasks))


def test_a_benchmark_without_a_check_still_passes(bench):
    del bench.module.check, bench.module.reference                 # ranked by the peers alone
    assert gate(bench, bench.tasks()) == []
