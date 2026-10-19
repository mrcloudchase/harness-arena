# Building harness-arena on harness-interface: what I did, step by step

For the author of [harness-interface](https://github.com/mrcloudchase/harness-interface). Everything below was done
against v1.0.2 used as a Python library (no server), without modifying it. Where it got in the way I say exactly what
was missing and how harness-arena works around it (section 4).

## 1. Result in one paragraph

`harness-arena` is ~1,300 lines of Python in 17 small modules (`harness_arena/`), 4 benchmark folders (`benchmarks/`) and 37
tests that run without Docker or keys. `harness-arena compare <benchmark> --model p/m` and `harness-arena defaults <benchmark>`
each run the whole pipeline (probe, run, blind, judge, report) and resume on the same `--run-id`. All five phases were run
live in Docker; their reports are committed under `reports/`.

| Phase | Run live | Report |
|---|---|---|
| 1 loop + deterministic judging | `compare smoke --model deepseek/deepseek-chat` on all 23 harnesses (13 supported, 11 scored, 3 repeats); `defaults smoke` on 6 harnesses | `reports/compare/deepseek/deepseek-chat/smoke.md`, `reports/defaults/smoke.md` |
| 2 blinding + model judges | `defaults readme` on 5 harnesses, panel `openai/gpt-4.1-mini` + `deepseek/deepseek-chat`, pairwise both orders, calibration (0.70 / 0.92), blindcheck (9/30 and 5/30 correct vs 20% chance, p=0.13 and 0.75, not leaking) | `reports/defaults/readme.md` |
| 3 harness judges | `defaults todoapi` on 3 harnesses, held-out judge `qwen-code` on two models, calibration 0.91 and 0.20 (n=4): the 0.20 judge is below the 0.6 threshold, so the report withholds the judged scores | `reports/defaults/todoapi.md` |
| 4 model-verification relay | on by default in `compare`; found harnesses calling other models (section 5) | in the compare report |
| 5 more benchmarks | `readme`, `todoapi`, `humaneval` (HumanEval, MIT, read from `HUMANEVAL_PATH`, 20 problems x 5 harnesses) | `reports/compare/deepseek/deepseek-chat/humaneval.md` |

Read the numbers with these caveats (details in section 6): the smoke and HumanEval slices are saturated (everything that
ran scores 100%), so they discriminate on integrity and speed, not on skill; compare-mode *judged* benchmarks could not be
run live because I only had OpenAI and DeepSeek keys (the rules need two judge families that are not the compared model's);
and the "human" calibration scores are ones I wrote, not human raters'.

## 2. Procedure

### 2.1 Read harness-interface first
I read the README, `how-it-works`, `library`, `harness-contract`, `providers`, `sandboxes`, `security`, `conventions`,
`harnesses/README.md`, `examples/library/run_a_harness.py`, and the library source (`harness/contract.py`, `harness/turn.py`,
`runtimes/docker.py`, `runtimes/local.py`). The facts the design rests on:
- A turn is `Turn.start(runtime, harness, provider, Request(task, model, files), workspace, scripts)`, then `events()` and
  `result()`. `Result` has status, exit code, answer, usage, cost, `files`, but not wall time (I time it).
- A harness's provider is just a name in `harness.json`; `Provider(name, url, key)` is what a run is given. So "run harness H on
  model M" = same harness, different `Provider`, `Request.model = M`.
- `DockerRuntime(engine, sandbox, egress=[provider.host], mounts=[...])` is the sandbox; `LocalRuntime()` is a plain process,
  which is what the tests use with fake harness folders.
- Each shipped harness speaks one API shape (anthropic or openai), which fixes which vendor endpoints it can be pointed at.

### 2.2 Set up
`uv add "harness-interface @ git+https://github.com/mrcloudchase/harness-interface@v1.0.2"`; the harness folders come from the
installed package (`hi_cli/harnesses`). Keys come from the environment; none are in the repo.

### 2.3 Build the loop (phase 1)
1. `catalog.py`: harness folders, a vendor -> API shape -> endpoint table, and `Catalog.target(harness, "vendor/model")`, which
   keeps the harness's shape, swaps the provider for the vendor's endpoint of that shape, and passes the model. No key or no
   endpoint of that shape means the harness is *unavailable*, not broken.
2. `turns.py`: one timed turn on a chosen runtime. A turn that never ran, or whose output shows a provider refusal (401/403/429,
   quota, rate limit), is retried with backoff and, if it keeps failing, recorded as a runner error, not held against the harness.
3. `arena.py`: the probe (one trivial turn per harness on the model; failures are unsupported and listed), then every
   harness x task x repeat, `--workers` at a time, one JSON line per run in `runs.jsonl`. Rerunning a run id skips what is recorded.
4. `benchmark.py` / `benchmarks/smoke/`: a benchmark is a folder; `tasks()`, `deliverables(task)`, `judges(task)`. `smoke` has five
   Python tasks graded by hidden pytest tests (`checks.pytest_check`, run on the host).
5. `store.py` keeps the two modes in separate trees (`results/compare/<provider>/<model>/...`, `results/defaults/...`).
6. `report.py` renders the table and the sections under it; `cli.py` ties it together.

### 2.4 Blinding and judges (phase 2)
7. `submission.py`: after a turn only files matching `deliverables(task)` are copied, scrubbed, into a fresh directory under a
   random id (`S-7f3a9c`). Dotfiles, `.home/`, `AGENTS.md`/`CLAUDE.md`/`QWEN.md`, `.aider*`, binaries and symlinks out of the
   workspace are never copied. Workspaces live at neutral temp paths so no harness, model or benchmark name is in a path.
8. `scrub.py`: terms are built from the harness folders (folder name, `name`, the display name and CLI names in the description),
   the provider catalog and the models in use; co-author trailers and "generated by" lines are redacted; counts are recorded.
9. The id -> (harness, model, task, repeat) map is written to `sealed/map.json`. `RunDir.sealed()` raises until judging is marked
   finished, and `judging.py` never opens the run records. Submissions are judged in random order.
10. `models.py`: a plain `httpx` model judge at temperature 0 (OpenAI-chat and Anthropic-messages shapes), a prompt containing only
    the rubric and the scrubbed submission (not even the task, so a judge scores the work alone), JSON out (score and reason per rubric item). `Panel` enforces at least two
    families and none from the compared model's family; the median is the score. `prefer()` judges a pair in both orders.
11. `calibrate.py`: correlation of each judge with the human scores in `calibration/`; the report withholds judged scores unless
    every judge reaches the benchmark's threshold. `blindcheck.py`: each model judge guesses the harness; a one-sided binomial test
    flags a leak and the report flags the judged columns.

### 2.5 Harness judges (phase 3)
12. `exercise.py`: a held-out harness (refused if it is a contestant) runs in a fresh workspace containing only
    `submission/` and `RUBRIC.md`, once per judge model, and writes `verdict.json`.

### 2.6 Relay (phase 4)
13. `relay.py`: a recording HTTPS reverse proxy on the host. Each run is pointed at `https://<docker-gateway>:<port>/<tag>`, its
    sandbox may reach only that, and it is told to trust the relay's self-signed certificate (mounted read-only). Every request's
    `model` is recorded; a run that called another model is a finding and never scored. A harness that cannot use the relay is
    re-probed without it, run without it, and listed as "model not verified".

### 2.7 Benchmarks (phase 5)
14. `readme` (judged, calibrated), `todoapi` (harness-judged, calibrated), `humaneval` (public; data stays outside the repo).
    I checked the HumanEval grader without any harness: all 164 reference solutions pass and all 164 empty bodies fail.

### 2.8 Tests
`tests/` uses `LocalRuntime` and fake harness folders written from a shell body. They prove, among others: a judge's prompt never
contains a harness, vendor or model name, a transcript or a non-deliverable file; the sealed map is unreadable until judging ends and
is never read during it; pairwise runs both orders and cancels a first-picker; the modes never share a path; the probe excludes
unsupported harnesses; resume skips what is recorded; the report's numbers match hand-computed records; refusals are retried and not
scored; timeouts are graded; hidden material in a task's files is a leak.

## 3. Running it live

- The default sandbox image would not build here: the environment's proxy re-terminates TLS, and the Dockerfile has no way to trust
  its CA. I built a local base image tagged `node:22-bookworm-slim` that adds the CA, then built the *unmodified* default Dockerfile
  on it under its own tag, so `Docker.image()` found it and skipped the build (3.3 GB).
- Order of work: single harness, no relay; with relay; all 23 probes; full runs; judged runs; HumanEval.

## 4. What harness-interface was missing, and what I did instead

| # | What blocked or hurt | Workaround in harness-arena | Suggested change |
|---|---|---|---|
| 1 | No declared API shape per harness. To retarget a harness at another vendor I hard-code `SHIPPED = {provider-name: (vendor, shape)}` in `catalog.py`. | the table | a `shape` field (`anthropic`/`openai`) in `harness.json` |
| 2 | `Result` has no wall time, and no way to tell a provider refusal from a harness failure. | time it myself; regex the last 4 KB of output for 401/403/429/quota | a `wall_s` field, and `report.py` writing `error_kind: "provider"` into `HI_OUTPUT` |
| 3 | `cost_usd` is reported by only 2 of 11 harnesses I ran (claude-code, opensquilla); claude-code's is its own Claude price table, not the provider's, so it is not comparable. | the report shows "no cost reported" counts | say in the harness docs which cost is real; consider token-based cost in the library |
| 4 | claude-code's `run.sh` does not pin its other model slots, so on a named model it still calls `claude-haiku-4-5-...` in the background (the relay caught this on its first run). | `catalog.PIN` sets `ANTHROPIC_SMALL_FAST_MODEL` and `ANTHROPIC_DEFAULT_{HAIKU,SONNET,OPUS}_MODEL` to the named model in compare mode | set them from `HI_MODEL` in `claude-code/run.sh` |
| 5 | Two harnesses ignore `HI_MODEL` for some calls: `harness-engineering` called `claude-sonnet-5-5` on every run; `deepseek-harness` called `deepseek-flash`. | none: they are listed as findings and not scored in compare mode | honour `HI_MODEL` everywhere |
| 6 | `nanobot` writes its output into `.home/.nanobot/workspace/`, not the task workspace, so it "finishes ok" with no files and scores 0%. That is the integration, not nanobot. | none (copying out of `.home` would defeat blinding); the report flags any harness that finishes ok but never writes a file | run nanobot with its workspace set to `HI_WORKSPACE` |
| 7 | The sandbox image cannot be customised (build args, CA, mirrors): its tag is a hash of the Dockerfile, and `Docker.image()` writes its build log only at the end, so a hung build is silent for as long as it hangs. | pre-built the same tag by hand, behind a CA-trusting base image | accept build args or extra CA files; stream the build log |
| 8 | The 15-minute `run.timeout_s` also applies to a one-word probe, so a harness that cannot reach the model stalls the probe for 15 minutes. | `Run.timeout_s` replaced with 240 s for probes (`dataclasses.replace`) | none needed, but a per-turn timeout override on `Turn.start` would be cleaner |
| 9 | A harness cannot say "I need an API shape the provider does not serve". `codex` on DeepSeek spins on "Reconnecting..." until the timeout (DeepSeek's `/v1` has no Responses API); `pi`, `omp`, `cline`, `kilo`, `mimo`, `opencode`, `jcode`, `gajae`, `openhands` also fail the probe on DeepSeek, mostly because their run scripts only know Anthropic model catalogs or keys (`Model "anthropic/deepseek-chat" not found`, `No API key for litellm/deepseek-chat`, `Model deepseek-chat not supported by Anthropic provider`). | the probe lists each as unsupported with the tail of its output | fail fast with a clear error when the model is unknown to the CLI |
| 10 | `goose` and `grok-cli` could not use a TLS relay (probably their CA handling), though they work direct. | probe falls back to no relay and lists them as "model not verified" | document how each CLI trusts a CA |
| 11 | Nothing stops a caller choosing a workspace path that names the harness, model or benchmark, and the CLI sees it as its cwd. | harness-arena uses neutral temp paths | a note in `library.md` |

None of these needed a change to harness-interface to get a working benchmark; 1, 2, 4, 5, 6 and 7 are the ones that would make
the next benchmark smaller and its results more trustworthy.

## 5. Findings the benchmark itself produced (compare, `deepseek/deepseek-chat`)

- Probe: supported through the relay or direct: aider, cheetahclaws, claude-code, deepseek-harness, goose, grok-cli,
  harness-engineering, hermes, kimi-code, minimax-code, nanobot, opensquilla, qwen-code. Unsupported: cline (auth), codex, gajae,
  jcode, kilo, mimo, omp, opencode, openhands, pi (reasons in the report).
- Never scored (integrity): deepseek-harness (all 15 runs: called `deepseek-flash`), harness-engineering (all 15: called
  `claude-sonnet-5-5`).
- Scored: aider, cheetahclaws, claude-code, goose, grok-cli, hermes, kimi-code, minimax-code, opensquilla, qwen-code at 100%
  on `smoke` (3 repeats); nanobot 0% for the integration reason in row 6. goose and grok-cli are not model-verified. Fastest
  median wall: grok-cli 8.8 s, goose 8.9 s; slowest: hermes 59 s.
- Blindness: scrubbing redacted a handful of identifying strings across the 30 `readme` submissions; neither judge beat chance.
- Hiding the task from judges cost agreement: with the task, the harness judge on `gpt-4.1-mini` agreed 0.74 with the calibration scores; without it, 0.20. The gate then withheld the todoapi judged scores, which is the gate working as designed. The rubric items would need to be written to stand alone (they currently lean on the task).

## 6. Limits and things to know

- **Calibration scores are mine.** `benchmarks/*/calibration/examples.json` hold the "human" scores; I wrote them. Agreement
  numbers show the judges track a sensible ordering, not that they match real raters. Replace them before trusting a judged report.
- **Judged benchmarks ran in `defaults` mode only** (panel of two families, no compared model). `compare` of a judged benchmark
  needs two judge families other than the compared one; with only OpenAI and DeepSeek keys that was impossible for a DeepSeek run.
  The rule is enforced and tested; set `ANTHROPIC_API_KEY` or `GEMINI_API_KEY` to use it.
- **Harness judges need a harness that speaks every judge model's API shape.** codex cannot judge on DeepSeek, so qwen-code was the
  held-out judge. In compare mode with `--harnesses all` no harness is held out; pass a subset.
- **Saturated benchmarks.** `smoke` and the first 20 HumanEval problems are easy: 100% for every harness that ran.
- **Deterministic checks run on the host**, as specified, on model-written code (with a timeout). Treat a benchmark you do not trust
  accordingly.
- **Scrubbing is textual.** Names under 3 characters (such as the harness `pi`) are not redacted, since that would also redact
  "pi"; the blindness check is the backstop. Binary deliverables are not judged.
- **Relay limits.** It records only requests with a JSON `model` field; Gemini-style models in the URL are not checked. It trusts
  the harness to use the provider URL it was given, which the sandbox enforces (the relay is the only reachable host).
- **Cost and wall time** include only what the harness reports and what was measured; DeepSeek token prices were not applied.
- A stale run directory (`results/defaults/todoapi/main`) was left in the git-ignored `results/` because deletion was blocked;
  the committed todoapi report is from run `judged`.
