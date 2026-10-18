"""The contest: probe each harness on the model, then run every supported harness on every task,
repeatedly, recording one line per run and keeping only the scrubbed submission for the judges.

Rerunning a run id resumes it: probes and runs already recorded are skipped.
"""
from __future__ import annotations

from pathlib import Path

from harness_interface import Request

from .benchmark import Benchmark, Task
from .catalog import Catalog, Unavailable
from .pool import limited
from .scrub import Scrubber
from .store import Mode, RunDir
from .submission import extract, new_id
from .turns import Report, Turns

PROBE = "Reply with the single word: ok"


class Arena:
    def __init__(self, catalog: Catalog, turns: Turns, mode: Mode, run: RunDir, workers: int = 4):
        self.catalog, self.turns, self.mode, self.run, self.workers = catalog, turns, mode, run, workers

    async def probe(self, names: list[str]) -> dict[str, str]:
        """One trivial turn per harness on the mode's model. Maps each harness to "" if it can take part,
        or to why it can't. A harness that fails is unsupported: skipped, listed, never scored."""
        known = self.run.load("probe", {})

        async def one(name: str) -> None:
            try:
                target = self.catalog.target(name, self.mode.model)
            except Unavailable as e:
                known[name] = str(e)
                return
            report = await self.turns.run(target, Request(PROBE, model=target.model),
                                          self.run.path / "probes" / name)
            ok = report.result.status == "ok" and not report.runner_error
            known[name] = "" if ok else (report.runner_error or f"probe {report.result.status}: {report.tail[-200:]}")
        await limited(self.workers, [lambda n=n: one(n) for n in names if n not in known])
        self.run.save("probe", known)
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
        workspace = self.run.path / "workspaces" / name / f"{task.id}-{repeat}"
        report = await self.turns.run(target, Request(task.instruction, model=target.model, files=dict(task.files)),
                                      workspace)
        row = self.record(name, target.provider.name, task.id, repeat, workspace, report)
        if row["status"] != "runner_error":
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
                "redactions": 0, "error": report.runner_error}
