"""The recording relay: every harness's model calls pass through here on their way to the provider, so
each call's `model` can be checked against the model the run was told to use (compare mode).

A harness is pointed at https://<host>:<port>/<tag> instead of its provider, and told to trust the
relay's self-signed certificate. Its sandbox may then reach the relay and nothing else. A harness that
can't talk to the relay fails its probe and is unsupported, not scored.
"""
from __future__ import annotations

import dataclasses
import json
import secrets
import ssl
import subprocess
import tempfile
import threading
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
from harness_interface import Provider

from .catalog import Target

SKIP = {"host", "content-length", "connection", "transfer-encoding"}
TRUST = ("SSL_CERT_FILE", "NODE_EXTRA_CA_CERTS", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE", "GIT_SSL_CAINFO")


def gateway() -> str:
    """The address a sandboxed run reaches this machine at: Docker's bridge gateway."""
    out = subprocess.run(["docker", "network", "inspect", "bridge", "-f", "{{(index .IPAM.Config 0).Gateway}}"],
                         capture_output=True, text=True, check=True).stdout.strip()
    return out


class Relay:
    def __init__(self, host: str):
        self.host = host
        self.certs = Path(tempfile.mkdtemp(prefix="relay-"))
        self.crt = self.certs / "relay.crt"
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "2", "-subj", "/CN=relay",
                        "-addext", f"subjectAltName=IP:{host}", "-keyout", str(self.certs / "relay.key"),
                        "-out", str(self.crt)], check=True, capture_output=True)
        self.upstreams: dict[str, str] = {}
        self.models: dict[str, list[str]] = defaultdict(list)     # tag -> the model of each call
        self.server = ThreadingHTTPServer(("0.0.0.0", 0), self._handler())
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(self.crt, self.certs / "relay.key")
        self.server.socket = tls.wrap_socket(self.server.socket, server_side=True)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.server.shutdown()

    def register(self, target: Target) -> tuple[Target, str]:
        """The target, pointed at the relay under a fresh tag, and the tag its calls are recorded under."""
        tag = secrets.token_hex(4)
        self.upstreams[tag] = target.provider.url.rstrip("/")
        provider = Provider(target.provider.name, f"https://{self.host}:{self.server.server_port}/{tag}", target.provider.key)
        run = dataclasses.replace(target.harness.run, env={**target.harness.run.env, **dict.fromkeys(TRUST, str(self.crt))})
        return dataclasses.replace(target, provider=provider, harness=dataclasses.replace(target.harness, run=run)), tag

    def foreign(self, tag: str, model: str) -> list[str]:
        """The models this run called that were not `model`."""
        return sorted(set(self.models[tag]) - {model})

    def _handler(self):
        relay = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"                 # the body ends when the connection closes: streams pass through

            def log_message(self, *args):
                pass

            def forward(self):
                tag, _, rest = self.path[1:].partition("/")
                if tag not in relay.upstreams:
                    return self.send_error(404)
                body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
                try:
                    relay.models[tag].append(str(json.loads(body)["model"]))
                except (ValueError, KeyError, TypeError):
                    pass                                  # not a model call
                headers = {k: v for k, v in self.headers.items() if k.lower() not in SKIP}
                with httpx.Client(timeout=None) as client, \
                        client.stream(self.command, f"{relay.upstreams[tag]}/{rest}", content=body, headers=headers) as r:
                    self.send_response(r.status_code)
                    for k, v in r.headers.items():
                        if k.lower() not in SKIP:
                            self.send_header(k, v)
                    self.end_headers()
                    for chunk in r.iter_raw():
                        self.wfile.write(chunk)
                        self.wfile.flush()

            do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = forward
        return Handler
