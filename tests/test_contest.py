"""The contest: modes, probe, resume, runner errors, timeouts, pins, the relay."""
import dataclasses
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import httpx
import pytest

from harness_arena.catalog import Catalog
from harness_arena.contest import Contest
from harness_arena.relay import Relay
from harness_arena.runner import Exhausted, Runner
from harness_arena.store import Mode, RunDir
from harness_arena.turns import REFUSAL

from conftest import REPORT, harness


def test_the_two_modes_never_share_results(tmp_path):
    a, b = Mode("compare", "deepseek/deepseek-chat"), Mode("defaults")
    da, db = a.run_dir("smoke", "r1", tmp_path), b.run_dir("smoke", "r1", tmp_path)
    assert da != db and not da.is_relative_to(db) and not db.is_relative_to(da)
    assert a.report("smoke", tmp_path) != b.report("smoke", tmp_path)
    assert "deepseek/deepseek-chat" in a.title and "Compare" in a.title and "Defaults" in b.title


def test_modes_refuse_what_would_mix_them():
    for bad in (("compare", ""), ("defaults", "deepseek/deepseek-chat"), ("compare", "../x/y"), ("compare", "nomodel")):
        with pytest.raises(SystemExit):
            Mode(*bad)


async def test_the_probe_excludes_what_cannot_run_the_model(harnesses, turns, mode, tmp_path):
    harness(harnesses, "denied", 'echo "403 Forbidden: model not allowed" >&2; exit 1\n')
    harness(harnesses, "crashes", "exit 3\n")
    probe = await Contest(Runner(Catalog(harnesses, {"DEEPSEEK_API_KEY": "k"}), turns, mode, RunDir(tmp_path / "r"))).probe(
        ["alpha", "beta", "denied", "crashes"])
    assert probe["alpha"] == "" and probe["beta"] == ""            # deepseek serves both API shapes
    assert "provider refused" in probe["denied"] and "probe fail" in probe["crashes"]
    only_openai = Contest(Runner(Catalog(harnesses, {"OPENAI_API_KEY": "k"}), turns, Mode("compare", "openai/gpt-4o"), RunDir(tmp_path / "o")))
    assert "no anthropic-shaped endpoint" in (await only_openai.probe(["alpha"]))["alpha"]


async def test_resume_skips_what_is_recorded(contest, bench, tmp_path):
    harness(contest.runner.catalog.folder, "counter", f'echo x >> {tmp_path}/calls; printf ANSWER > solution.py\n' + REPORT)
    tasks = bench.tasks()[:2]
    await contest.play(bench, ["counter"], tasks, 2)
    calls = lambda: len((tmp_path / "calls").read_text().split())
    assert calls() == 4 and len(contest.run.rows("runs")) == 4
    await contest.play(bench, ["counter"], tasks, 2)
    assert calls() == 4 and len(contest.run.rows("runs")) == 4
    await contest.play(bench, ["counter"], tasks, 3)              # a third repeat adds only the missing runs
    assert calls() == 6


async def test_a_refusal_is_retried_then_a_runner_error_and_never_judged(contest, bench, tmp_path):
    harness(contest.runner.catalog.folder, "limited", f'echo x >> {tmp_path}/n; echo "429 rate limit" >&2; exit 1\n')
    await contest.play(bench, ["limited"], bench.tasks()[:1], 1)
    (row,) = contest.run.rows("runs")
    assert len((tmp_path / "n").read_text().split()) == 2          # one try and one retry
    assert row["status"] == "runner_error" and row["submission"] == "" and "provider refused" in row["error"]
    assert not contest.run.load("submissions")
    await contest.play(bench, ["limited"], bench.tasks()[:1], 1)    # a resume tries it again
    assert len(contest.run.rows("runs")) == 2


async def test_a_timeout_is_graded_as_it_stands(contest, bench):
    harness(contest.runner.catalog.folder, "slow", "printf ANSWER > solution.py; sleep 30\n")
    spec = json.loads((contest.runner.catalog.folder / "slow/harness.json").read_text())
    spec["run"]["timeout_s"] = 1
    (contest.runner.catalog.folder / "slow/harness.json").write_text(json.dumps(spec))
    await contest.play(bench, ["slow"], bench.tasks()[:1], 1)
    (row,) = contest.run.rows("runs")
    assert row["status"] == "timeout" and row["submission"]
    assert (contest.run.path / "raw" / row["submission"] / "solution.py").read_text() == "ANSWER"


async def test_the_record_has_what_the_spec_lists(contest, bench):
    await contest.play(bench, ["alpha"], bench.tasks()[:1], 1)
    (row,) = contest.run.rows("runs")
    assert {"mode", "harness", "provider", "model", "task", "repeat", "status", "exit_code", "wall_s", "cost_usd",
            "usage", "files", "workspace", "submission"} <= set(row)
    assert row["mode"] == "compare" and row["provider"] == "deepseek" and row["cost_usd"] == 0.01
    assert row["wall_s"] > 0 and "solution.py" in row["files"] and row["submission"].startswith("S-")

    assert "alpha" not in row["workspace"] and "deepseek" not in row["workspace"] and "fake" not in row["workspace"]


async def test_the_turn_brake_stops_a_run_cleanly(runner, bench):
    runner.max_turns = 1
    contest = Contest(runner, workers=1)
    with pytest.raises(Exhausted):
        await contest.play(bench, ["alpha"], bench.tasks()[:2], 1)
    assert len(runner.run.rows("runs")) == 1                       # what ran is recorded, so a rerun continues


def test_a_named_model_pins_every_model_slot_a_harness_has(catalog):
    env = catalog.target("alpha", "deepseek/deepseek-chat").harness.run.env
    assert {env[k] for k in ("ANTHROPIC_SMALL_FAST_MODEL", "ANTHROPIC_DEFAULT_HAIKU_MODEL")} == {"deepseek-chat"}
    assert "ANTHROPIC_SMALL_FAST_MODEL" not in catalog.target("alpha").harness.run.env      # defaults mode pins nothing


def test_only_a_provider_refusal_looks_like_one():
    for refused in ("API Error: 429 rate limit", "HTTP 403 Forbidden", "status: 401", "invalid api key", "Overloaded"):
        assert REFUSAL.search(refused), refused
    for plain in ('"duration_ms":429', "took 403 steps", "AssertionError: 1 != 2", '"output_tokens":4031'):
        assert not REFUSAL.search(plain), plain


@pytest.fixture
def upstream():
    class Echo(BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"echo " + body + self.headers["authorization"].encode())

        def log_message(self, *a):
            pass
    server = HTTPServer(("127.0.0.1", 0), Echo)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}/v1"
    server.shutdown()


def test_the_relay_records_each_calls_model_and_passes_it_through(catalog, upstream):
    relay = Relay("127.0.0.1")
    target, tag = relay.register(catalog.target("alpha", "deepseek/deepseek-chat"))
    relay.upstreams[tag] = upstream
    assert target.provider.host == f"127.0.0.1:{relay.server.server_port}" and target.harness.run.env["SSL_CERT_FILE"]
    import ssl
    with httpx.Client(verify=ssl.create_default_context(cafile=str(relay.crt))) as client:
        for model in ("deepseek-chat", "small-fast-model"):
            r = client.post(f"{target.provider.url}/messages", json={"model": model}, headers={"authorization": "Bearer k"})
        assert r.text == 'echo {"model":"small-fast-model"}Bearer k'        # the key and the body arrive unchanged
        assert client.post(f"https://127.0.0.1:{relay.server.server_port}/nope/x", json={}).status_code == 404
    assert relay.foreign(tag, "deepseek-chat") == ["small-fast-model"]
    relay.close()


class Stub:
    """A relay that saw a call to another model."""
    def register(self, target):
        return target, "t"

    def foreign(self, tag, model):
        return ["other-model"]


async def test_a_run_that_called_another_model_is_a_finding_and_never_judged(runner, bench):
    runner.relay = Stub()
    await Contest(runner).play(bench, ["alpha"], bench.tasks()[:1], 1)
    (row,) = runner.run.rows("runs")
    assert "other-model" in row["finding"] and row["submission"] == "" and not runner.run.load("submissions")


async def test_a_harness_the_relay_breaks_is_run_without_it_and_listed(runner, harnesses):
    harness(harnesses, "shy", 'test -n "$VIA_RELAY" && exit 1\nprintf ok > x\n' + REPORT)

    class Strict:                                    # points a harness at a "relay" it can't live with
        def register(self, target):
            run = dataclasses.replace(target.harness.run, env={**target.harness.run.env, "VIA_RELAY": "1"})
            return dataclasses.replace(target, harness=dataclasses.replace(target.harness, run=run)), "t"

        def foreign(self, tag, model):
            return []
    runner.relay = Strict()
    assert await Contest(runner).probe(["shy"]) == {"shy": ""} and runner.run.load("direct") == ["shy"]


async def test_when_one_job_fails_the_others_are_cancelled_and_stop_writing():
    import asyncio
    from harness_arena.pool import limited
    wrote = []

    async def slow():
        await asyncio.sleep(0.2)
        wrote.append("late")

    async def bad():
        raise Exhausted("spent")
    with pytest.raises(Exhausted):
        await limited(3, [slow, bad, slow])
    await asyncio.sleep(0.4)
    assert wrote == []
