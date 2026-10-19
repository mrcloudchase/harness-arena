# harness-arena

A blind arena for coding harnesses, built on [harness-interface](https://github.com/mrcloudchase/harness-interface) v1.0.2
as a Python library (no server). Pick a benchmark; the harnesses compete on it; then **the same harnesses judge each other's
work, blind**, and the arena checks that they could not tell whose work was whose. The final order is a tally of every
judge's ranking.

```bash
uv sync
harness-arena gate smoke                                        # is the benchmark sound? (no spend)
harness-arena compare smoke --model deepseek/deepseek-chat      # every harness on one model
harness-arena defaults smoke                                    # every harness on its own default model
harness-arena report compare smoke --model deepseek/deepseek-chat
```

`compare` and `defaults` are the whole loop for one benchmark, and resume if you give them the same `--run-id`:

```
gate ─► contest ─► scrub ◄──► classifier ─► peer judging ─► blindness test ─► report
                     └─ new fingerprints ─┘   (all contestants     (all contestants guess
                                                rank every group)     who wrote what)
```

## The loop

Every stage is built on `loop.py`: do a step, verify it with something that can't be argued with, feed the failure back,
and stop on a named state: `success`, `blocked`, `stalled` (the same failure twice) or `exhausted`. An error or a spent
budget is never success.

1. **Gate** (`gates.py`, free). The benchmark must have deliverables and criteria, repeat no hidden material in task inputs,
   and, if it has a deterministic check, that check must score its reference solution 1 and an empty submission 0.
2. **Contest** (`contest.py`). Probe each harness with one trivial turn on the model; one that fails is unsupported: it
   neither competes nor judges. Run every supported harness on every task, `--repeat` times. Provider refusals are runner
   errors, retried and not held against the harness. In compare mode a recording relay checks every model call used the
   named model; a run that called another is a finding and is never ranked.
3. **Scrub** (`blind.py`). Only the files matching `deliverables(task)` are kept, with names derived from the harness folders,
   providers and models deleted (not marked: a marker would itself give a result away), under an opaque id. A text
   classifier then tries to tell the harnesses apart from the scrubbed results; what gave it away in comments and prose is fed
   back to the scrubber, and it goes again. Identifiers in the code itself are never rewritten.
4. **Peer judging** (`judge.py`). **Every harness that ran in the contest judges.** For each group of results (one task, one
   repeat) a judge gets all of them in its own random order, plus the benchmark's criteria, and nothing else: no names, no
   task, no hidden tests, no logs. It runs and inspects them and writes a full ranking, best first. This module never opens
   the run records or the sealed map.
5. **Blindness test** (`guess.py`). After judging, every harness is shown groups of results and the names of the harnesses
   that wrote them, and must say who wrote which. The ranking only stands if no judge, nor all judges together, nor any
   harness recognising its own work, beats chance (an exact Poisson-binomial test; per judge at alpha divided by the number of
   judges).
6. **Tally** (`tally.py`). Each ranking gives its best result 1 point and its worst 0, evenly between (a Borda count). A result's
   score is its mean over all judges; a harness's final score is the mean of its results' scores; the harnesses are ranked by
   it. The report also shows judge agreement (Kendall's W), each harness's self-bias (what it gave its own results minus what
   the others gave them), and agreement with the benchmark's hidden check where there is one.
7. **Report** (`report.py`). One table per run, stamped **BLIND VERIFIED**, or, if blindness could not be verified, **the
   ranking is withheld** and the evidence is shown. Below it: the audits, judging coverage, unsupported harnesses, findings,
   runner errors and redactions.

## A benchmark is a folder

`benchmarks/<name>/benchmark.py` exposes

- `tasks()`: yields `Task(id, instruction, files)`. A task never names its benchmark, dataset or any harness.
- `deliverables(task)`: glob patterns of the files that make up a result. Only these are ever judged.
- `criteria(task)`: what makes one result better than another, written to stand alone: judges never see the task.
- `check(task, dir)` (optional): a deterministic `(score, why)`, used as an anchor for the peer ranking, never as the ranking.
- `reference(task)` (optional): `{path: text}` of a correct submission, which the gate needs if there is a `check`.

`hidden/` and `reference/` beside it never enter a contestant's workspace. A dataset under another licence stays outside the
repo, at a path given by an environment variable (`benchmarks/humaneval`).

| Benchmark | Anchor | |
|---|---|---|
| `smoke` | hidden pytest tests | five small Python tasks |
| `readme` | none: peers alone | write a README for a codebase |
| `todoapi` | none: peers alone | a JSON API the judges must run |
| `humaneval` | hidden tests | HumanEval, read from `HUMANEVAL_PATH` (MIT, github.com/openai/human-eval) |

## Options

`--harnesses a,b|all` (they compete, then all judge), `--tasks N`, `--repeat K` (default 3), `--workers W`, `--run-id`,
`--scrub-rounds` (default 3), `--audit-groups` (groups the judges try to attribute, default 5), `--max-turns` (stop cleanly
after this many harness turns; rerun the run id to continue), and `--no-relay` (compare only).

Results go to `results/compare/<provider>/<model>/<benchmark>/<run-id>/` and `results/defaults/<benchmark>/<run-id>/`, and
the two modes never share a directory. Reports go to `reports/`, indexed by `reports/README.md`.

## Limits worth knowing

- **Judges share the contestants' model** in compare mode, so they share its blind spots. The anchor, the self-bias column and
  the blindness test are there to make that visible, not to remove it.
- **A harness that can't judge** (for example one that only edits files it is told about) shows up as failed judgments in the
  coverage section; the tally uses the judges that did produce rankings.
- **Style can leak** where no scrubbing can reach (structure, habits). The classifier and the guess test measure it; they don't
  pretend it away.
- Deterministic checks run on the host, on model-written code, with a timeout.

```bash
uv run pytest        # no Docker or keys needed
```
