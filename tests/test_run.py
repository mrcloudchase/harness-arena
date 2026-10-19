"""The whole outer loop, end to end on fake harnesses: gate, contest, scrub, peer judging, audit, report."""
import argparse

import harness_arena.cli as cli
import pytest
from harness_interface import LocalRuntime

from harness_arena.benchmark import Benchmark
from harness_arena.store import Mode, RunDir


class NoDocker:
    async def recover(self):
        return None


@pytest.fixture
def local(monkeypatch, tmp_path, bench):
    monkeypatch.setattr(cli, "Docker", lambda logs: NoDocker())
    monkeypatch.setattr(cli, "docker_runtime", lambda logs, mounts=(): (lambda target: LocalRuntime()))
    monkeypatch.setattr(cli, "ROOT", tmp_path / "root")
    monkeypatch.setattr(cli.Benchmark, "load", classmethod(lambda cls, name, root=None: bench))


def args(**kw):
    return argparse.Namespace(benchmark="fake", harnesses="alpha,beta", tasks=None, repeat=1, workers=2, run_id="r1",
                              scrub_rounds=2, audit_groups=3, max_turns=None, no_relay=True, **kw)


async def test_the_whole_loop_runs_and_the_report_is_withheld_when_the_work_gives_itself_away(local, catalog, tmp_path, capsys):
    mode = Mode("defaults")
    assert await cli.contest(args(), mode, catalog) == 0
    run = RunDir(mode.run_dir("fake", "r1", tmp_path / "root"))
    assert len(run.rows("runs")) == 6 and len(run.rows("judgments")) == 6      # 2 harnesses x 3 tasks, and both judge every group
    assert {j["judge"] for j in run.rows("judgments")} == {"alpha", "beta"}
    assert len(run.rows("guesses")) == 6 and run.load("audit")["blind"] is False
    report = (tmp_path / "root" / "reports" / "defaults" / "fake.md").read_text()
    assert "BLINDNESS NOT VERIFIED: ranking withheld" in report
    assert (tmp_path / "root" / "reports" / "README.md").read_text().count("(defaults/fake.md)") == 1
    out = capsys.readouterr().out
    assert "scrub: " in out


async def test_a_benchmark_that_fails_the_gate_costs_nothing(local, catalog, bench, tmp_path, capsys):
    bench.module.reference = lambda task: {"solution.py": "wrong"}
    assert await cli.contest(args(), Mode("defaults"), catalog) == 1
    assert "gate: " in capsys.readouterr().out and not (tmp_path / "root" / "results").exists()      # nothing was run


async def test_one_harness_cannot_make_a_ranking(local, catalog, capsys):
    assert await cli.contest(argparse.Namespace(**{**vars(args()), "harnesses": "alpha"}), Mode("defaults"), catalog) == 1
    assert "at least two" in capsys.readouterr().out


async def test_the_turn_brake_stops_cleanly_and_a_rerun_continues(local, catalog, tmp_path, capsys):
    mode = Mode("defaults")
    assert await cli.contest(argparse.Namespace(**{**vars(args()), "max_turns": 3}), mode, catalog) == 2
    assert "exhausted" in capsys.readouterr().out
    assert await cli.contest(args(), mode, catalog) == 0                 # the same run id picks up where it stopped
    assert len(RunDir(mode.run_dir("fake", "r1", tmp_path / "root")).rows("judgments")) == 6
