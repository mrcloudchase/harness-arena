"""The contest: probe each harness on the model, then run every supported harness on every task, repeatedly,
recording one line per run and keeping the deliverables for the blind stages.

Rerunning a run id resumes it: probes and runs already recorded are skipped.
"""
from __future__ import annotations

import secrets
import tempfile
from pathlib import Path

from harness_interface import Request

from .benchmark import Benchmark, Task
from .catalog import Unavailable
from .pool import limited
from .relay import Relay
from .runner import Runner
from .submission import collect, new_id

PROBE = "Reply with the single word: ok"
PROBE_TIMEOUT_S = 240                                # a trivial turn that takes longer says the harness can't run this model


class Contest:
    def __init__(self, runner: Runner, workers: int = 4):
        self.runner, self.run, self.mode, self.workers = runner, runner.run, runner.mode, workers
        self.scratch = Path(tempfile.mkdtemp(prefix="arena-"))      # workspaces here: no harness, model or benchmark in the path

    def workspace(self) -> Path:
        return self.scratch / f"w-{secrets.token_hex(4)}"

    async def probe(self, names: list[str]) -> dict[str, str]:
        """One trivial turn per harness. Maps each to "" if it can take part, or to why it can't. One that works
        only without the relay is run without it, and listed as unverified."""
        known, direct = self.run.load("probe", {}), set(self.run.load("direct", []))

        async def attempt(name: str, relay: bool) -> str:
            report, _ = await self.runner.go(name, Request(PROBE), self.workspace(), relay, PROBE_TIMEOUT_S)
            ok = report.result.status == "ok" and not report.runner_error
            return "" if ok else (report.runner_error or f"probe {report.result.status}: {report.tail[-200:]}")

        async def one(name: str) -> None:
            try:
                self.runner.catalog.target(name, self.mode.model)
            except Unavailable as e:
                known[name] = str(e)
                return
            known[name] = await attempt(name, True)
            if known[name] and self.runner.relay:
                known[name] = await attempt(name, False)
                if not known[name]:
                    direct.add(name)
        await limited(self.workers, [lambda n=n: one(n) for n in names if n not in known])
        self.run.save("probe", known)
        self.run.save("direct", sorted(direct))
        return known

    async def play(self, bench: Benchmark, names: list[str], tasks: list[Task], repeat: int) -> None:
        """Every missing (harness, task, repeat), `workers` at a time."""
        done = {k for k, r in self.run.runs().items() if r["status"] != "runner_error"}
        await limited(self.workers, [lambda k=(n, t, r): self.once(bench, *k)
                                     for n in names for t in tasks for r in range(1, repeat + 1) if (n, t.id, r) not in done])

    async def once(self, bench: Benchmark, name: str, task: Task, repeat: int) -> None:
        workspace = self.workspace()
        report, foreign = await self.runner.go(name, Request(task.instruction, files=dict(task.files)), workspace)
        r = report.result
        row = {"mode": self.mode.kind, "harness": name, "provider": self.runner.catalog.target(name, self.mode.model).provider.name,
               "model": self.mode.model, "task": task.id, "repeat": repeat,
               "status": "runner_error" if report.runner_error else r.status, "exit_code": r.exit_code,
               "wall_s": round(report.wall_s, 2), "cost_usd": r.cost_usd, "usage": r.usage, "files": list(r.files),
               "workspace": str(workspace), "submission": "", "error": report.runner_error, "finding": ""}
        if foreign:
            row["finding"] = f"called {', '.join(foreign)}, not the named model {self.mode.model.partition('/')[2]}"
        if row["status"] != "runner_error" and not row["finding"]:
            row["submission"] = new_id()
            files = collect(workspace, bench.deliverables(task))
            raw = self.run.path / "raw" / row["submission"]
            for name_, text in files.items():
                (raw / name_).parent.mkdir(parents=True, exist_ok=True)
                (raw / name_).write_text(text)
            raw.mkdir(parents=True, exist_ok=True)
            self.run.save("submissions", {**self.run.load("submissions", {}),
                                          row["submission"]: {"task": task.id, "repeat": repeat}})
        self.run.append("runs", row)
