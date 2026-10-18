"""Every model call is checked against the named model; a run that called another is a finding, never scored."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import httpx
import pytest

from harness_arena.judging import Judging
from harness_arena.relay import Relay
from harness_arena.scrub import Scrubber

from conftest import REPORT, harness


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
    with httpx.Client(verify=str(relay.crt)) as client:
        for model in ("deepseek-chat", "small-fast-model"):
            r = client.post(f"{target.provider.url}/messages", json={"model": model}, headers={"authorization": "Bearer k"})
        assert r.text == 'echo {"model":"small-fast-model"}Bearer k'        # the key and the body arrive unchanged
        assert client.post(f"https://127.0.0.1:{relay.server.server_port}/nope/x", json={}).status_code == 404
    assert relay.foreign(tag, "deepseek-chat") == ["small-fast-model"] and relay.foreign(tag, "small-fast-model") == ["deepseek-chat"]
    relay.close()


class Stub:
    """A relay that saw a call to another model."""
    def register(self, target):
        return target, "t"

    def foreign(self, tag, model):
        return ["other-model"]


async def test_a_run_that_called_another_model_is_a_finding_and_never_judged(arena, bench):
    harness(arena.catalog.folder, "straying", "printf ANSWER > solution.py\n" + REPORT)
    arena.relay = Stub()
    await arena.play(bench, ["straying"], bench.tasks()[:1], 1, Scrubber(set()))
    (row,) = arena.run.rows("runs")
    assert "other-model" in row["finding"] and row["submission"] == "" and not arena.run.load("submissions")
    await Judging(arena.run, bench, {}).run_all()
    assert arena.run.rows("verdicts") == []
