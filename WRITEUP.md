# Building harness-arena on harness-interface: what I did, step by step

For the author of [harness-interface](https://github.com/mrcloudchase/harness-interface). Everything below was done against
v1.0.2 used as a Python library (no server), without modifying it. The repo was built twice: a first version judged with model
panels and held-out harness judges (branch `harness-arena`), then rebuilt around loop engineering (branch `rebuild`, this
document). Where harness-interface got in the way I say exactly what was missing and what harness-arena does instead (section 5).

## 1. What it is

A benchmark goes in; harnesses compete on it; then **the same harnesses judge each other's work, blind**, and the arena
verifies that they could not tell whose work was whose. The final order is a tally of every judge's ranking.

```
gate ─► contest ─► scrub ◄──► classifier ─► peer judging ─► blindness test ─► report
```

About 1,450 lines in 21 small modules (`harness_arena/`), 4 benchmark folders, 56 tests that need neither Docker nor keys.
Two live runs on `deepseek/deepseek-chat` (both **BLIND VERIFIED**):

| Run | Ranking, best first (score 0 to 1) | Blindness test |
|---|---|---|
| `readme`, 6 harnesses, 2 repeats | kimi-code 0.73, goose 0.61, qwen-code 0.55, claude-code 0.53, grok-cli 0.53, aider 0.05 (aider could not judge: see 6) | 32 of 174 guesses right (p=0.30); own work recognised 7 of 29 (p=0.20); classifier 1 of 36 |
| `smoke`, 5 harnesses, 2 repeats | goose 0.72, kimi-code 0.66, grok-cli 0.43, qwen-code 0.36, claude-code 0.33 (all five pass every hidden test) | 11 of 100 right (p=0.99); own work 2 of 20 (p=0.93); classifier 1 of 30 |

Reports: `reports/compare/deepseek/deepseek-chat/{readme,smoke}.md`. Read them as a demonstration of the loop, not a verdict on the
harnesses: small samples, one model, tasks everyone solves (on `smoke` the peers ranked only code quality, since the hidden check
was uninformative: everyone passed).

## 2. What changed from the first version, and why

| First version | Rebuild | Why |
|---|---|---|
| Model panel (2 families) and a held-out harness judge, calibrated against hand-written scores | Every harness that ran in the contest judges | the judges are the contestants: ranking by peers, like people grading each other's work |
| Per-result rubric scores | Each judge ranks a whole group, best first; rankings are tallied (Borda) | order is what matters; one call per judge per group |
| Blindness: model judges guessed the harness | Every judge harness guesses who wrote what; exact test per judge, pooled, and for recognising its own work; plus a classifier before judging | self-votes are allowed *because* this is verified |
| Scrub replaced names with `[REDACTED]` | Scrub deletes them | a marker present in only some results is itself a fingerprint |
| Stages were a pipeline | One `Loop` core (step, verify, feedback, named stop states); scrub-then-classify is a real feedback loop | loop engineering |
| Calibration against human scores | An intake gate (reference solution scores 1, empty submission 0, no leak, criteria present) and a deterministic anchor | no human raters; the gate caught a real bug (HumanEval's check crashed on an empty submission) |
| Pool used `asyncio.gather` | Cancels siblings when one job fails | after a turn brake, orphaned jobs kept writing records and produced duplicates |

## 3. Procedure

1. **Read harness-interface first** (README, how-it-works, library, harness-contract, providers, sandboxes, security,
   conventions, harnesses README, the library source). The design rests on: a turn is `Turn.start(runtime, harness, provider,
   Request(...), workspace, scripts)`; a harness's provider is just a name, so running harness H on model M means a different
   `Provider` and `Request.model`; each shipped harness speaks one API shape (anthropic or openai), which fixes which vendor
   endpoints it can reach; `DockerRuntime` is the sandbox and `LocalRuntime` is what tests use with fake harness folders.
2. **Catalog** (`catalog.py`): keep a harness's shape, swap its provider for the vendor's endpoint of that shape, pass the model.
3. **Turns and runner** (`turns.py`, `runner.py`): one timed turn; a turn that never ran or was refused by its provider (401/403/
   429, quota) is retried and then a runner error, not held against the harness; a turn brake (`--max-turns`) stops cleanly and a
   rerun continues.
4. **Contest** (`contest.py`): probe each harness on the model (one trivial turn, 240 s timeout; one that fails is unsupported
   and neither competes nor judges); run every supported harness on every task, one JSON line per run; keep the deliverables
   privately under `raw/`.
5. **Relay** (`relay.py`): a recording HTTPS reverse proxy; every model call's `model` is checked against the one named; a run
   that called another is a finding and never ranked. A harness that cannot use the relay is re-probed without it, run without
   it, and listed as "model not verified".
6. **Scrub loop** (`blind.py`, `fingerprint.py`, `scrub.py`): only the deliverables, names from the harness folders, providers and
   models deleted, opaque ids; a leave-one-out naive Bayes classifier tries to tell the harnesses apart; the words that gave one
   away in comments and prose (never in code) go back to the scrubber, until it passes, stalls or runs out of rounds.
7. **Peer judging** (`judge.py`): for each (task, repeat) group, every harness gets the results in its own random order, the
   benchmark's criteria, and nothing else (not the task, not the hidden tests); it writes `ranking.json`; a missing or invalid
   ranking is retried once with the reason fed back, then recorded as a failed judgment. This module never opens the run
   records or the sealed map; a test fails if it does.
8. **Blindness test** (`guess.py`): after judging, every harness is shown groups of results and the names of the harnesses that
   wrote them and must attribute each; the exact Poisson-binomial probability of doing that well by luck is computed per judge
   (alpha divided by the number of judges), pooled, and for each harness's own work. The ranking is withheld unless nobody beat chance.
9. **Tally** (`tally.py`): Borda points per ranking (best 1, worst 0), mean over judges per result, mean over results per harness;
   also Kendall's W between judges, each harness's self-bias, and agreement with the hidden check.
10. **Gate** (`gates.py`) runs first, free, and stops a benchmark that cannot be trusted before any harness runs.
11. **Tests** (`tests/`): `LocalRuntime` and fake harness folders that compete, judge and guess. They prove, among others, that a
    judge's workspace holds only the results and the criteria; the sealed map is unreadable until judging ends and never read
    during it; every contestant judges every group; a failed ranking is retried and then excluded; the tally matches hand-computed
    numbers; a planted fingerprint in a comment is found and scrubbed while one in code is reported and left alone; a judge who
    recognises its own work is caught even if it cannot tell the others apart; the report withholds an unverified ranking; the
    whole loop runs end to end; the turn brake stops cleanly and a rerun continues.

## 4. Running it live

The default sandbox image would not build in this environment: the proxy re-terminates TLS and the Dockerfile has no way to
trust its CA. I built a local base image tagged `node:22-bookworm-slim` that adds the CA, then built the unmodified default
Dockerfile on it under its own tag, so `Docker.image()` found it and skipped the build (3.3 GB).

## 5. What harness-interface was missing, and what I did instead

| # | What blocked or hurt | Workaround in harness-arena | Suggested change |
|---|---|---|---|
| 1 | No declared API shape per harness; retargeting a harness at another vendor needs a hard-coded table of provider name to (vendor, shape). | `SHIPPED` in `catalog.py` | a `shape` field in `harness.json` |
| 2 | `Result` has no wall time, and a provider refusal looks like a harness failure. | time it; regex the last 4 KB of output | `wall_s`, and `report.py` writing `error_kind: "provider"` into `HI_OUTPUT` |
| 3 | `cost_usd` is reported by 2 of the harnesses I ran (claude-code, opensquilla); claude-code's is its own Claude price table, not the provider's. | the report counts runs with no cost | say which cost is real; count tokens in the library |
| 4 | claude-code's `run.sh` doesn't pin its other model slots, so on a named model it still called `claude-haiku-4-5-...` (the relay caught it). | `catalog.PIN` sets `ANTHROPIC_SMALL_FAST_MODEL` and `ANTHROPIC_DEFAULT_{HAIKU,SONNET,OPUS}_MODEL` to the named model | set them from `HI_MODEL` in `run.sh` |
| 5 | `harness-engineering` called `claude-sonnet-5-5` on every run; `deepseek-harness` called `deepseek-flash`. | listed as findings, never ranked | honour `HI_MODEL` everywhere |
| 6 | `nanobot` writes into `.home/.nanobot/workspace/`, not the task workspace, so it finishes "ok" with no files. | the report flags any harness that finishes ok but never writes a file | run it with its workspace set to `HI_WORKSPACE` |
| 7 | The sandbox image can't be customised (build args, CA); its build log is written only at the end, so a hung build is silent. | pre-built the same tag behind a CA-trusting base image | accept build args or extra CA files; stream the log |
| 8 | The 15-minute `run.timeout_s` also applies to a one-word probe. | `dataclasses.replace` on `Run.timeout_s` for probes | a per-turn timeout on `Turn.start` |
| 9 | A harness can't say "this model or API shape is not for me": codex on DeepSeek spins on "Reconnecting..."; cline, gajae, jcode, kilo, mimo, omp, opencode, openhands and pi fail on `deepseek-chat` with catalog or key errors. | the probe lists each as unsupported with the tail of its output | fail fast with a clear error |
| 10 | goose and grok-cli can't use a TLS relay though they work direct. | probe falls back to no relay; listed "model not verified" | document how each CLI trusts a CA |
| 11 | **aider can't be a judge**: it only edits files it is told about, so it never wrote `ranking.json` or `guess.json` (all 12 turns failed). | recorded as failed judgments in the coverage section; the tally uses the judges that did rank | a way for a harness to declare "can act on files beyond the ones named" |
| 12 | **Some harnesses hang on read-and-reason tasks**: kimi-code's blindness-guess turns sat until the 15-minute timeout, twice, and were the slowest part of both runs. | a failed turn is retried once, then recorded | an earlier give-up for turns that make no progress |
| 13 | A caller can choose a workspace path that names the harness, model or benchmark, and the CLI sees it as its cwd. | neutral temp paths | a note in `library.md` |

## 6. Limits

- **Judges share the contestants' model** in compare mode, so they share its blind spots and may prefer outputs like their own.
  The self-bias column and the blindness test make that visible; the anchor (where a benchmark has a deterministic check that
  varies) shows whether the peers agree with the truth. On `smoke` everyone passed, so the anchor said nothing.
- **Blindness is verified statistically, not proven.** A test with few guesses can miss a weak leak; the report prints how many
  guesses each judge made. Style can leak where no scrubbing reaches; the classifier and guess test measure it.
- **Judge coverage is partial.** aider could not judge; kimi-code and others lost some turns to timeouts. The report says how many
  rankings and guesses each judge actually contributed.
- **Small samples.** Two benchmarks, 2 repeats, 5 to 6 harnesses, one model. The ranking illustrates the method.
- **Cost** is only what harnesses report; DeepSeek prices were not applied, and most harnesses report none.
- Deterministic checks run on the host, on model-written code, with a timeout.
- A stale directory, `results/defaults/todoapi/main`, from the first version is still in the git-ignored `results/` because
  deletion was blocked.
