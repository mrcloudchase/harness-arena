"""Judges see the work, never the worker."""
import pytest

from harness_arena.benchmark import Task
from harness_arena.judging import Judging
from harness_arena.models import Panel
from harness_arena.scrub import Scrubber, harness_terms, model_terms
from harness_arena.store import RunDir, Sealed
from harness_arena.submission import Submission, extract

from conftest import SOLVED

NAMES = ["alpha", "alphacli", "Alpha Agent", "beta", "Beta Bot", "deepseek", "deepseek-chat", "anthropic", "openai"]


class Spy:
    """A judge that records every prompt it is shown."""
    def __init__(self, name, family, reply):
        self.name, self.family, self.reply, self.prompts = name, family, reply, []

    async def ask(self, prompt):
        self.prompts.append(prompt)
        return self.reply(prompt) if callable(self.reply) else self.reply


def scrubber(catalog):
    terms = {t for n in catalog.names() for t in harness_terms(catalog.folder / n)}
    return Scrubber(terms | {"anthropic", "openai", *model_terms("deepseek/deepseek-chat")})


def test_terms_are_built_from_the_harness_folders(catalog):
    assert {"alpha", "alphacli", "Alpha Agent", "Alpha", "beta", "Beta Bot"} <= harness_terms(catalog.folder / "alpha") | harness_terms(catalog.folder / "beta")


def test_scrub_redacts_every_name_and_trailer_and_counts(catalog):
    text, n = scrubber(catalog)("Alpha Agent via alphacli, on DeepSeek-Chat (deepseek, OpenAI)\nGenerated with Beta Bot\nplain")
    assert text == "[REDACTED] via [REDACTED], on [REDACTED] ([REDACTED], [REDACTED])\n[REDACTED]\nplain" and n == 6
    assert scrubber(catalog)("alphabet soup")[1] == 0          # a name inside a word is not a name


def test_only_deliverables_are_extracted_and_scrubbed(tmp_path, catalog):
    ws = tmp_path / "ws"
    for rel, text in {"solution.py": SOLVED, "notes.txt": "SECRET-OTHER-FILE", "AGENTS.md": "x", ".home/state": "x",
                      ".aider.chat.history.md": "x", "src/a.py": "ok", "src/.hidden": "x", "blob.bin": ""}.items():
        (ws / rel).parent.mkdir(parents=True, exist_ok=True)
        (ws / rel).write_text(text)
    (ws / "bin.dat").write_bytes(b"\xff\xfe")
    (tmp_path / "outside.txt").write_text("outside")
    (ws / "link.py").symlink_to(tmp_path / "outside.txt")
    dest = tmp_path / "sub"
    redactions = extract(ws, ["solution.py", "src/**", "*.dat", "link.py", "AGENTS.md", ".home/**"], dest, scrubber(catalog))
    assert sorted(p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file()) == ["solution.py", "src/a.py"]
    assert redactions == 3 and "alphacli" not in (dest / "solution.py").read_text()


async def test_a_judge_never_sees_a_name_a_transcript_or_another_file(arena, bench, catalog):
    await arena.play(bench, ["alpha", "beta"], bench.tasks(), 1, scrubber(catalog))
    reply = lambda p: '{"winner": "tie"}' if "Which satisfies" in p else '{"items": {"1": {"score": 1, "reason": "fine"}}}'
    spy, spy2 = Spy("openai/judge", "openai", reply), Spy("google/judge", "google", reply)
    from harness_arena.benchmark import Model
    bench.module.judges = lambda task: [Model(("It works",), pairwise=True)]
    judging = Judging(arena.run, bench, {"llm": Panel([spy, spy2])})
    arena.run.save("submissions", arena.run.load("submissions"))     # the index the runner wrote
    arena.run.append("verdicts", {"submission": "-", "kind": "x", "judge": "x", "score": 0, "reasons": ""})
    await judging.run_all()
    prompts = spy.prompts + spy2.prompts
    assert prompts and all("ANSWER" in p or "wrong" in p for p in prompts)
    assert not any("Write solution.py" in p for p in prompts)         # not even the task: the work and the rubric only
    for p in prompts:
        for forbidden in (*NAMES, "SECRET-TRANSCRIPT", "SECRET-OTHER-FILE", "banner", "Co-Authored", "AGENTS"):
            assert forbidden.lower() not in p.lower(), forbidden


async def test_judging_never_reads_the_sealed_map(arena, bench, catalog, monkeypatch):
    await arena.play(bench, ["alpha"], bench.tasks(), 1, scrubber(catalog))
    arena.run.seal({r["submission"]: {"harness": r["harness"]} for r in arena.run.runs().values()})
    with pytest.raises(Sealed):
        arena.run.sealed()                                        # sealed until judging ends
    monkeypatch.setattr(RunDir, "sealed", lambda self: pytest.fail("judging read the sealed map"))
    await Judging(arena.run, bench, {}).run_all()
    monkeypatch.undo()
    arena.run.finish_judging()
    assert arena.run.sealed()
    arena.run.seal({})                                            # a resumed run is sealed again until judged
    with pytest.raises(Sealed):
        arena.run.sealed()


def test_submission_ids_are_opaque_and_the_map_names_them(arena):
    from harness_arena.submission import new_id
    assert len({new_id() for _ in range(50)}) == 50 and new_id().startswith("S-")
