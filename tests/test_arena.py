"""The loop: modes, probe, resume, runner errors, timeouts, leaks."""
import json

from hiddenarena.benchmark import Task
from hiddenarena.judging import Judging
from hiddenarena.scrub import Scrubber
from hiddenarena.store import Mode, RunDir

from conftest import REPORT, harness

NONE = Scrubber(set())


def test_the_two_modes_never_share_results(tmp_path):
    a, b = Mode("compare", "deepseek/deepseek-chat"), Mode("defaults")
    da, db = a.run_dir("smoke", "r1", tmp_path), b.run_dir("smoke", "r1", tmp_path)
    assert da != db and not da.is_relative_to(db) and not db.is_relative_to(da)
    assert a.report("smoke", tmp_path) != b.report("smoke", tmp_path)
    assert "deepseek/deepseek-chat" in a.title and "Compare" in a.title and "Defaults" in b.title


def test_modes_refuse_what_would_mix_them():
    import pytest
    for bad in (("compare", ""), ("defaults", "deepseek/deepseek-chat"), ("compare", "../x/y"), ("compare", "nomodel")):
        with pytest.raises(SystemExit):
            Mode(*bad)


async def test_the_probe_excludes_what_cannot_run_the_model(harnesses, turns, tmp_path):
    from hiddenarena.arena import Arena
    from hiddenarena.catalog import Catalog
    harness(harnesses, "denied", 'echo "403 Forbidden: model not allowed" >&2; exit 1\n')
    harness(harnesses, "crashes", "exit 3\n")
    arena = Arena(Catalog(harnesses, {"DEEPSEEK_API_KEY": "k"}), turns, Mode("compare", "deepseek/deepseek-chat"),
                  RunDir(tmp_path / "r"))
    probe = await arena.probe(["alpha", "beta", "denied", "crashes"])
    assert probe["alpha"] == "" and probe["beta"] == ""            # deepseek serves both API shapes
    assert "provider refused" in probe["denied"] and "probe fail" in probe["crashes"]
    openai_only = Arena(Catalog(harnesses, {"OPENAI_API_KEY": "k"}), turns, Mode("compare", "openai/gpt-4o"), RunDir(tmp_path / "o"))
    assert "no anthropic-shaped endpoint" in (await openai_only.probe(["alpha", "beta"]))["alpha"]
    assert (await openai_only.probe(["beta"]))["beta"] == ""


async def test_resume_skips_what_is_recorded(arena, bench, tmp_path):
    harness(arena.catalog.folder, "counter", f'echo x >> {tmp_path}/calls; printf ANSWER > solution.py\n' + REPORT)
    await arena.play(bench, ["counter"], bench.tasks(), 2, NONE)
    assert len((tmp_path / "calls").read_text().split()) == 4 and len(arena.run.rows("runs")) == 4
    await arena.play(bench, ["counter"], bench.tasks(), 2, NONE)
    assert len((tmp_path / "calls").read_text().split()) == 4 and len(arena.run.rows("runs")) == 4
    await arena.play(bench, ["counter"], bench.tasks(), 3, NONE)      # a third repeat adds only the missing runs
    assert len((tmp_path / "calls").read_text().split()) == 6


async def test_a_refusal_is_retried_then_a_runner_error_and_never_scored(arena, bench, tmp_path):
    harness(arena.catalog.folder, "limited", f'echo x >> {tmp_path}/n; echo "429 rate limit" >&2; exit 1\n')
    await arena.play(bench, ["limited"], bench.tasks()[:1], 1, NONE)
    (row,) = arena.run.rows("runs")
    assert len((tmp_path / "n").read_text().split()) == 2          # one try and one retry
    assert row["status"] == "runner_error" and row["submission"] == "" and "provider refused" in row["error"]
    assert not arena.run.load("submissions")
    await arena.play(bench, ["limited"], bench.tasks()[:1], 1, NONE)  # a resume tries it again
    assert len(arena.run.rows("runs")) == 2


async def test_a_timeout_is_graded_as_it_stands(arena, bench):
    harness(arena.catalog.folder, "slow", "printf ANSWER > solution.py; sleep 30\n")
    spec = json.loads((arena.catalog.folder / "slow/harness.json").read_text())
    spec["run"]["timeout_s"] = 1
    (arena.catalog.folder / "slow/harness.json").write_text(json.dumps(spec))
    await arena.play(bench, ["slow"], bench.tasks()[:1], 1, NONE)
    (row,) = arena.run.rows("runs")
    assert row["status"] == "timeout" and row["submission"]
    await Judging(arena.run, bench, {}).run_all()
    assert arena.run.rows("verdicts")[0]["score"] == 1.0


async def test_the_record_has_what_the_spec_lists(arena, bench):
    await arena.play(bench, ["alpha"], bench.tasks()[:1], 1, NONE)
    (row,) = arena.run.rows("runs")
    assert {"mode", "harness", "provider", "model", "task", "repeat", "status", "exit_code", "wall_s", "cost_usd",
            "usage", "files", "workspace", "submission", "redactions"} <= set(row)
    assert row["mode"] == "compare" and row["provider"] == "deepseek" and row["cost_usd"] == 0.01
    assert row["wall_s"] > 0 and "solution.py" in row["files"] and row["submission"].startswith("S-")


def test_a_task_that_repeats_hidden_material_is_a_leak(bench):
    assert bench.leaks(Task("x", "do", {"solution.py": "fine", "tests.txt": "the hidden answer"})) == ["tests.txt"]
    assert bench.leaks(Task("x", "do", {"a": "fine"})) == []


def test_a_named_model_pins_every_model_slot_a_harness_has(catalog):
    env = catalog.target("alpha", "deepseek/deepseek-chat").harness.run.env
    assert {env[k] for k in ("ANTHROPIC_SMALL_FAST_MODEL", "ANTHROPIC_DEFAULT_HAIKU_MODEL")} == {"deepseek-chat"}
    assert "ANTHROPIC_SMALL_FAST_MODEL" not in catalog.target("alpha").harness.run.env      # defaults mode pins nothing


def test_only_a_provider_refusal_looks_like_one():
    from hiddenarena.turns import REFUSAL
    for refused in ("API Error: 429 rate limit", "HTTP 403 Forbidden", "status: 401", "invalid api key", "Overloaded"):
        assert REFUSAL.search(refused), refused
    for plain in ('"duration_ms":429', "took 403 steps", "AssertionError: 1 != 2", '"output_tokens":4031'):
        assert not REFUSAL.search(plain), plain


async def test_a_harness_the_relay_breaks_is_run_without_it_and_listed(arena, harnesses):
    harness(harnesses, "shy", 'test -n "$VIA_RELAY" && exit 1\nprintf ok > x\n' + REPORT)

    class Strict:                                    # points a harness at a "relay" it can't live with
        def register(self, target):
            import dataclasses
            run = dataclasses.replace(target.harness.run, env={**target.harness.run.env, "VIA_RELAY": "1"})
            return dataclasses.replace(target, harness=dataclasses.replace(target.harness, run=run)), "t"
    arena.relay = Strict()
    probe = await arena.probe(["shy"])
    assert probe == {"shy": ""} and arena.run.load("direct") == ["shy"]
