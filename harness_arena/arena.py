"""The contest: probe each harness on the model, then run every supported harness on every task,
repeatedly, recording one line per run and keeping only the scrubbed submission for the judges.

Rerunning a run id resumes it: probes and runs already recorded are skipped.
"""
from __future__ import annotations

import dataclasses
import secrets
import tempfile
from pathlib import Path

from harness_interface import Request

from .benchmark import Benchmark, Task
from .catalog import Catalog, Unavailable
from .pool import limited
from .relay import Relay
from .scrub import Scrubber
from .store import Mode, RunDir
from .submission import extract, new_id
from .turns import Report, Turns

PROBE = "Reply with the single word: ok"
PROBE_TIMEOUT_S = 240                               # a trivial turn that takes longer says the harness can't run this model


class Arena:
    def __init__(self, catalog: Catalog, turns: Turns, mode: Mode, run: RunDir, workers: int = 4,
                 relay: Relay | None = None):
        self.catalog, self.turns, self.mode, self.run, self.workers = catalog, turns, mode, run, workers
        self.relay = relay                           # compare mode: records which model every call used
        self.scratch = Path(tempfile.mkdtemp(prefix="arena-"))      # workspaces here: no harness, model or benchmark in the path

    def workspace(self) -> Path:
        return self.scratch / f"w-{secrets.token_hex(4)}"

    async def probe(self, names: list[str]) -> dict[str, str]:
        """One trivial turn per harness on the mode's model. Maps each harness to "" if it can take part,
        or to why it can't. A harness that fails is unsupported: skipped, listed, never scored. One that
        works only without the relay is run without it, and listed as unverified."""
        known, direct = self.run.load("probe", {}), set(self.run.load("direct", []))

        async def attempt(name: str, relay: Relay | None) -> str:
            target = self.catalog.target(name, self.mode.model)
            if relay:
                target, _ = relay.register(target)
            run = dataclasses.replace(target.harness.run, timeout_s=min(target.harness.run.timeout_s, PROBE_TIMEOUT_S))
            target = dataclasses.replace(target, harness=dataclasses.replace(target.harness, run=run))
            report = await self.turns.run(target, Request(PROBE, model=target.model), self.workspace())
            ok = report.result.status == "ok" and not report.runner_error
            return "" if ok else (report.runner_error or f"probe {report.result.status}: {report.tail[-200:]}")

        async def one(name: str) -> None:
            try:
                self.catalog.target(name, self.mode.model)
            except Unavailable as e:
                known[name] = str(e)
                return
            known[name] = await attempt(name, self.relay)
            if known[name] and self.relay:
                known[name] = await attempt(name, None)
                if not known[name]:
                    direct.add(name)
        await limited(self.workers, [lambda n=n: one(n) for n in names if n not in known])
        self.run.save("probe", known)
        self.run.save("direct", sorted(direct))
        return known

    async def play(self, bench: Benchmark, names: list[str], tasks: list[Task], repeat: int,
                   scrub: Scrubber) -> None:
        """Every missing (harness, task, repeat), `workers` at a time."""
        done = {k for k, r in self.run.runs().items() if r["status"] != "runner_error"}
        jobs = [lambda k=(n, t, r): self.once(bench, *k, scrub)
                for n in names for t in tasks for r in range(1, repeat + 1) if (n, t.id, r) not in done]
        await limited(self.workers, jobs)

    async def once(self, bench: Benchmark, name: str, task: Task, repeat: int, scrub: Scrubber) -> None:
        target = self.catalog.target(name, self.mode.model)
        provider = target.provider.name
        tag = ""
        if self.relay and name not in self.run.load("direct", []):
            target, tag = self.relay.register(target)
        workspace = self.workspace()
        report = await self.turns.run(target, Request(task.instruction, model=target.model, files=dict(task.files)),
                                      workspace)
        row = self.record(name, provider, task.id, repeat, workspace, report)
        if tag and (foreign := self.relay.foreign(tag, target.model)) and not row["error"]:
            row["finding"] = f"called {', '.join(foreign)}, not the named model {target.model}"
        if row["status"] != "runner_error" and not row.get("finding"):
            row["submission"] = new_id()
            dest = self.run.path / "submissions" / row["submission"]
            row["redactions"] = extract(workspace, bench.deliverables(task), dest, scrub)
            index = self.run.load("submissions", {})
            self.run.save("submissions", {**index, row["submission"]: task.id})
        self.run.append("runs", row)

    def record(self, name: str, provider: str, task: str, repeat: int, workspace: Path, report: Report) -> dict:
        r = report.result
        return {"mode": self.mode.kind, "harness": name, "provider": provider, "model": self.mode.model,
                "task": task, "repeat": repeat, "status": "runner_error" if report.runner_error else r.status,
                "exit_code": r.exit_code, "wall_s": round(report.wall_s, 2), "cost_usd": r.cost_usd,
                "usage": r.usage, "files": list(r.files), "workspace": str(workspace), "submission": "",
                "redactions": 0, "error": report.runner_error, "finding": ""}
