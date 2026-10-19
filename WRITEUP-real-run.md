# The real run: 11 harnesses compete on HumanEval+ and judge each other, blind

This is the second write-up. `WRITEUP.md` (kept as is) covers building the repo and what harness-interface got in the way of.
This one covers the real run that exercises the rebuilt loop on a public benchmark, with every key I had. Report:
`reports/compare/deepseek/deepseek-chat/humaneval.md`. Raw records: `results/compare/deepseek/deepseek-chat/humaneval/real1/`
(git-ignored).

## 1. The result

**Run `real1`:** 11 harnesses competed on 12 hard HumanEval+ problems, two repeats each, all on `deepseek/deepseek-chat`. All 11
then judged every group of results, blind (247 valid rankings), and then tried to guess who wrote what. **Blindness verified**,
so the ranking stands.

| Rank | Harness | Score (0 to 1) | Hidden-test pass rate | Median wall (s) |
|---|---|---|---|---|
| 1 | minimax-code | 0.68 | 50% | 28 |
| 2 | kimi-code | 0.57 | 42% | 18 |
| 3 | hermes | 0.54 | 38% | 59 |
| 4 | goose | 0.51 | 42% | 9 |
| 5 | grok-cli | 0.51 | 46% | 10 |
| 6 | claude-code | 0.49 | 33% | 19 |
| 7 | nanobot | 0.48 | 42% | 27 |
| 8 | opensquilla | 0.47 | 33% | 33 |
| 9 | qwen-code | 0.44 | 29% | 19 |
| 10 | cheetahclaws | 0.44 | 33% | 18 |
| 11 | aider | 0.38 | 21% | 25 |

Score is the mean Borda points a harness's results earned across all judges' rankings (1 = ranked best by everyone, 0 = worst by
everyone). The peers' ranking agrees moderately with each other (Kendall's W 0.62) and with the hidden tests (rank correlation
0.49), so the peers are measuring something real, not noise, and not exactly what the tests measure.

**What this does and doesn't show.** Each harness has 24 results, so a pass rate has a 95% margin of about plus or minus 20
points. Only the ends are separated: minimax-code at the top and aider at the bottom. Ranks 2 to 10 sit inside each other's
margins. The honest summary is "minimax-code looks strongest, aider weakest, the middle is a pack", on one model, one benchmark
subset, and one run. Rerun with more repeats before acting on the middle.

## 2. The eval, and how it was chosen

The goal was a real public benchmark where harnesses would actually differ. `smoke` and plain HumanEval saturate: on plain
HumanEval, `deepseek-chat` alone fails only 4 of 164 problems.

1. **Benchmark:** HumanEval+ (Liu et al., NeurIPS 2023, Apache-2.0), the same 164 problems as HumanEval with far more hidden tests.
   The data stays outside the repo (`HUMANEVAL_PATH`).
2. **Screen:** I asked `deepseek-chat` alone, with no harness, to complete all 164 problems once at temperature 0 and ran the hidden
   tests (`benchmarks/humaneval/screen.py`). 13 failed. Using no harness for the screen favours none of them; it does select
   problems that *this model* finds hard, which is the point and also a bias (see 6).
3. **Gate:** the intake gate checks every task's reference solution scores 1. It rejected **p032**: its HumanEval+ test is malformed
   in this dataset export, so even the canonical solution crashes inside it. 12 problems remained: p076, p091, p097, p099, p116,
   p130, p132, p141, p145, p151, p154, p163.
4. **Command** (one command, resumable):
   `HUMANEVAL_PATH=HumanEvalPlus.jsonl HUMANEVAL_IDS=p076,... uv run --extra evalplus harness-arena compare humaneval --model deepseek/deepseek-chat --harnesses all --repeat 2 --workers 8 --audit-groups 6 --run-id real1`

## 3. What happened, stage by stage

- **Probe.** 23 harnesses probed. 13 can run `deepseek-chat` (aider, claude-code, cheetahclaws, deepseek-harness, goose, grok-cli,
  harness-engineering, hermes, kimi-code, minimax-code, nanobot, opensquilla, qwen-code); goose and grok-cli only without the relay.
  10 cannot (cline, codex, gajae, jcode, kilo, mimo, omp, opencode, openhands, pi), with the same reasons as before.
- **Contest.** 312 runs (13 harnesses x 12 problems x 2 repeats), no runner errors.
  Two harnesses were flagged by the relay and never ranked: **deepseek-harness** called `deepseek-flash` and
  **harness-engineering** called `claude-sonnet-5-5` on all 24 of their runs. They therefore neither appear in the ranking nor judge.
- **Scrub.** One round; the classifier named the author of 0 of 264 results (nothing to feed back). Nothing needed redacting:
  code solutions carry no names.
- **Peer judging.** 11 judges x 24 groups = 264 judgments, 247 valid. All 17 failures: 16 were aider (it only edits files it is
  told about, and sometimes cannot write `ranking.json`; twice it wrote an invalid ranking), and 1 was nanobot (a timeout). The
  tally uses the valid rankings.
- **Blindness test.** The harnesses were shown 6 groups and the names of the harnesses that wrote them, and attributed each.
  All judges together: 66 right of 627 guesses (p=0.12 by luck). Recognising their own work: 6 of 57 (p=0.42). Each judge alone
  against alpha divided by the number of judges: nobody beat chance. Two judges came close:
  **hermes and qwen-code each got 12 of 66** (p=0.015). That is below 0.05 on its own and would count as a leak without the
  correction for testing ten judges (the bar is 0.005), so the run passes, but it is the thing to watch. aider could not take the
  test (no usable guess).

## 4. Self-votes

Self-votes were allowed because blindness is verified. Each harness's self-bias (what it gave its own results minus what the others
gave them) ranges from about -0.05 to +0.09 on a 0 to 1 scale; the largest is opensquilla at +0.09, the smallest hermes at -0.05.
None is large, and a harness that cannot recognise its own work (6 of 57) has no way to favour it.

## 5. Cost and time

Only claude-code ($2.96, its own price table) and opensquilla ($0.06) report cost; the other nine report none, so the cost column
is not comparable. DeepSeek token prices were not applied. Wall time per task is measured: goose and grok-cli are fastest
(about 9 to 10 s), hermes slowest (59 s).

## 6. Limits

- **One run, one model.** Judges and contestants share `deepseek-chat`, so they share its blind spots. The hidden-test anchor is the
  independent check, and the peers agree with it only moderately (0.49).
- **Small and selected.** 12 problems chosen because `deepseek-chat` fails them; 2 repeats. A harness that helps a model recover
  on hard problems is favoured; one that helps on easy problems is not measured.
- **Two harnesses excluded by integrity findings**, so the ranking is of 11, not 13, and those two did not judge.
- **aider and nanobot as judges.** aider could not judge reliably; its own ranking in the table is as a contestant only.
- **Blindness is statistical.** hermes and qwen-code came close to the threshold. A run with more guesses would settle whether
  that is chance.
- **Costs** are mostly unreported.
- Deterministic checks run on the host, on model-written code, with a timeout.

## 7. To reproduce

```bash
git clone https://github.com/mrcloudchase/harness-arena && cd harness-arena && git checkout harness-arena
uv sync --extra evalplus
curl -L -o HumanEvalPlus.jsonl https://huggingface.co/datasets/evalplus/humanevalplus/resolve/main/test.jsonl
# the default sandbox image must exist (see WRITEUP.md, section 4)
HUMANEVAL_PATH=$PWD/HumanEvalPlus.jsonl uv run --extra evalplus python benchmarks/humaneval/screen.py deepseek-chat   # prints HUMANEVAL_IDS
```
then the command in section 2, minus any problem the gate rejects.
