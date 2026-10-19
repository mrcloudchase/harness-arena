"""Judges see the work, never the worker: what they are shown, and what they can't reach."""
import pytest

from harness_arena.blind import Scrubbing
from harness_arena.judge import PeerJudging
from harness_arena.scrub import Scrubber, harness_terms, model_terms
from harness_arena.store import RunDir, Sealed
from harness_arena.submission import collect, new_id, write

from conftest import SOLVED

NAMES = ["alpha", "alphacli", "alpha agent", "beta", "beta bot", "deepseek", "deepseek-chat", "anthropic", "openai"]


def terms(catalog):
    return {t for n in catalog.names() for t in harness_terms(catalog.folder / n)} | {"anthropic", "openai"} | model_terms("deepseek/deepseek-chat")


def test_terms_are_built_from_the_harness_folders(catalog):
    assert {"alpha", "alphacli", "Alpha Agent", "Alpha", "beta", "Beta Bot"} <= terms(catalog)


def test_scrub_deletes_every_name_and_trailer_and_counts(catalog):
    scrub = Scrubber(terms(catalog))
    text, n = scrub("Alpha Agent via alphacli, on DeepSeek-Chat (deepseek, OpenAI)\nGenerated with Beta Bot\nplain")
    assert text == " via , on  (, )\nplain" and n == 6              # nothing is left behind to mark where a name was
    assert scrub("alphabet soup")[1] == 0                           # a name inside a word is not a name


def test_only_deliverables_are_collected_and_scrubbed(tmp_path, catalog):
    ws = tmp_path / "ws"
    for rel, text in {"solution.py": SOLVED, "notes.txt": "SECRET-OTHER-FILE", "AGENTS.md": "x", ".home/state": "x",
                      ".aider.chat.history.md": "x", "src/a.py": "ok", "src/.hidden": "x"}.items():
        (ws / rel).parent.mkdir(parents=True, exist_ok=True)
        (ws / rel).write_text(text)
    (ws / "bin.dat").write_bytes(b"\xff\xfe")
    (tmp_path / "outside.txt").write_text("outside")
    (ws / "link.py").symlink_to(tmp_path / "outside.txt")
    files = collect(ws, ["solution.py", "src/**", "*.dat", "link.py", "AGENTS.md", ".home/**"])
    assert sorted(files) == ["solution.py", "src/a.py"]
    dest = tmp_path / "sub"
    redactions = write(dest, files, Scrubber(terms(catalog)))
    assert redactions == 3 and "alphacli" not in (dest / "solution.py").read_text()


async def play_and_scrub(contest, bench, catalog, run):
    await contest.play(bench, ["alpha", "beta"], bench.tasks(), 1)
    scrubbing = Scrubbing(run, terms(catalog))
    scrubbing.scrub_all()
    return scrubbing


async def test_a_judge_never_sees_a_name_a_transcript_another_file_or_the_task(contest, bench, catalog, run, runner, seen):
    await play_and_scrub(contest, bench, catalog, run)
    await PeerJudging(runner, bench).run_all(["alpha", "beta"])
    shown = seen.read_text()
    assert "CRITERIA.md" in shown and shown.count("/solution.py") >= 12      # 2 judges x 3 groups x 2 results
    for forbidden in (*NAMES, "SECRET-TRANSCRIPT", "SECRET-OTHER-FILE", "banner", "Co-Authored", "Write solution.py"):
        assert forbidden.lower() not in shown.lower(), forbidden
    listing = [l for l in shown.splitlines() if l.startswith("./submissions/")]
    assert listing and all(l.endswith("/solution.py") for l in listing)          # nothing of a result but its deliverable
    cwd = [line for line in shown.splitlines() if line.startswith("PWD=")]
    assert cwd and not any(n in line for line in cwd for n in ("alpha", "beta", "deepseek", "fake", "run"))      # neutral paths
    assert "ANSWER" in shown                                          # criteria text reaches the judge, and only that


async def test_judging_never_reads_the_sealed_map_or_the_run_records(contest, bench, catalog, run, runner, monkeypatch):
    await play_and_scrub(contest, bench, catalog, run)
    run.seal({r["submission"]: {"harness": r["harness"]} for r in run.runs().values()})
    with pytest.raises(Sealed):
        run.sealed()                                                  # sealed until judging ends
    monkeypatch.setattr(RunDir, "sealed", lambda self: pytest.fail("judging read the sealed map"))
    monkeypatch.setattr(RunDir, "runs", lambda self: pytest.fail("judging read the run records"))
    await PeerJudging(runner, bench).run_all(["alpha", "beta"])
    monkeypatch.undo()
    run.finish_judging()
    assert run.sealed()
    run.seal({})                                                      # a resumed run is sealed again until judged
    with pytest.raises(Sealed):
        run.sealed()


def test_submission_ids_are_opaque():
    assert len({new_id() for _ in range(50)}) == 50 and new_id().startswith("S-")
