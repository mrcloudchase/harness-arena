# The deepseek-flash run: 12 harnesses compete on HumanEval+ and judge each other, blind

Third write-up. `WRITEUP.md` covers building the repo; `WRITEUP-real-run.md` covers the first real run on `deepseek-chat`. This covers
the rerun on `deepseek/deepseek-flash` (DeepSeek-V4.1-Flash), on harness-interface v1.0.5, with the blindness test now merged into
the judging pass. Report: `reports/compare/deepseek/deepseek-flash/humaneval.md`. Raw records:
`results/compare/deepseek/deepseek-flash/humaneval/flash1/` (git-ignored).

## 1. The result

12 harnesses competed on 7 HumanEval+ problems, three repeats each, all on `deepseek-flash`. All 12 then judged every group of
results, blind (236 valid rankings), and attributed who wrote what. **Blindness verified.**

| Rank | Harness | Score | Hidden-test pass rate | Median wall (s) |
|---|---|---|---|---|
| 1 | claude-code | 0.57 | 29% | 18 |
| 2 | hermes | 0.56 | 33% | 68 |
| 3 | aider | 0.55 | 29% | 25 |
| 4 | grok-cli | 0.54 | 33% | 13 |
| 5 | goose | 0.53 | 14% | 16 |
| 6 | cheetahclaws | 0.53 | 19% | 19 |
| 7 | kimi-code | 0.50 | 19% | 17 |
| 8 | deepseek-harness | 0.49 | 29% | 18 |
| 9 | opensquilla | 0.48 | 24% | 38 |
| 10 | minimax-code | 0.47 | 24% | 24 |
| 11 | qwen-code | 0.41 | 33% | 22 |
| 12 | nanobot | 0.38 | 14% | 36 |

**This run does not separate the harnesses, and I would not act on its order.** The scores run from 0.38 to 0.57, and ranks 1 to 8
are within 0.08 of each other. Each pass rate is over 21 results (a 95% margin of about plus or minus 20 points), and they run
14% to 33%. The judges agree with each other well (Kendall's W 0.70) but only weakly with the hidden tests (rank correlation
0.16, against 0.49 on the `deepseek-chat` run): on this set they are agreeing about something other than correctness.

**The two runs disagree with each other.** minimax-code was first on `deepseek-chat` and tenth here; aider was last and is third;
claude-code went from sixth to first; qwen-code has the second-lowest score here and the joint-highest pass rate. Different model
and a different, smaller problem set, so they are not strictly comparable, but a ranking that reorders this much is mostly noise.
The only thing both runs agree on is that nobody is far ahead.

## 2. How the run was set up

- **harness-interface v1.0.5** (was v1.0.2): same 23 harnesses. The sandbox image has a new tag; v1.0.5 publishes it, so I pulled
  `ghcr.io/mrcloudchase/harness-interface/default:d9da17aa9835` instead of building, and added one layer so containers trust this
  environment's TLS-intercepting proxy. I removed the old image to make room for it.
- **Which harnesses run `deepseek-flash`.** I probed all 23. 13 run it as shipped (aider, claude-code, cheetahclaws,
  deepseek-harness, goose, grok-cli, harness-engineering, hermes, kimi-code, minimax-code, nanobot, opensquilla, qwen-code; goose
  and grok-cli only without the relay). 10 do not (cline, codex, gajae, jcode, kilo, mimo, omp, opencode, openhands, pi). Causes:
  openhands sends a tool format (`"type": "custom"`) that DeepSeek's Anthropic endpoint rejects; cline and pi are hard-wired to
  Anthropic's endpoint; kilo, mimo, opencode and omp do not know the model; jcode rejects it; gajae routes it through a gateway and
  wants a key; codex never sends a request (it loops on a models-list call to chatgpt.com, which the sandbox blocks), although
  DeepSeek does serve the Responses API codex needs. DeepSeek serves `deepseek-flash` over OpenAI chat, Anthropic messages and
  OpenAI Responses.
- **The problem set.** I screened all 164 HumanEval+ problems with `deepseek-flash` alone, no harness, at temperature 0 and kept
  the ones it fails: p032, p075, p091, p099, p132, p141, p151, p163. p032's test is malformed in this dataset export (its own
  canonical solution crashes in it), so the intake gate rejects it, leaving 7. Six of the 7 were also in the earlier run's set.
- **Command:** `HUMANEVAL_PATH=HumanEvalPlus.jsonl HUMANEVAL_IDS=p075,p091,p099,p132,p141,p151,p163 uv run --extra evalplus harness-arena compare humaneval --model deepseek/deepseek-flash --harnesses all --repeat 3 --workers 8 --run-id flash1`

## 3. What happened

- **Contest:** 273 runs (13 harnesses x 7 problems x 3 repeats), 271 ok and 2 failed, no runner errors. The relay flagged
  **harness-engineering** (it calls `claude-sonnet-5-5` whatever it is told, on all 21 runs), so it is not ranked and did not judge.
  deepseek-harness, which called `deepseek-flash` while told `deepseek-chat` last time, is no longer flagged, as expected: the model it
  prefers is now the model named. 12 harnesses remain.
- **Scrub:** one round; a classifier named the author of 0 of 252 results.
- **Peer judging:** 12 judges x 21 groups = 252 judgments, 236 valid. All 16 failures are aider (it only edits files it is told
  about and often cannot write `ranking.json`).
- **Blindness test, now inside the judging pass.** After saving its ranking, each judge was told who took part and attributed each
  result, in the same conversation: 233 guess sets, all resumed, none needing a fresh turn. All judges together guessed 236 of 2,796
  right (p=0.43); harnesses recognising their own work 25 of 233 (p=0.12); no judge alone beat chance. The smallest p is claude-code's
  at 0.15. Compared with `deepseek-chat`, nobody was close to the line this time (hermes and qwen-code had been at p=0.015). aider
  made only 60 guesses.
- **Self-bias** (own results minus what others gave them): from -0.25 (aider, on few judgments) to +0.11 (deepseek-harness). Most
  are within a few hundredths of zero.
- **Cost:** only claude-code ($2.27), opensquilla ($5.33) and goose ($0.03) reported any. opensquilla's $5.33 over 21 results is the
  one notable number, and it is the harness's own accounting.

## 4. The merged blindness test: what it bought and cost

The test now runs in the judging pass, after each ranking is saved and in the same conversation. Gains: it covers every group a judge
ranked (2,796 guesses, not the 627 sampled before), so "nobody beat chance" is a much stronger statement, and the names are shown
only after the ranking is saved. I said it would also be faster, and **that was wrong**: the whole run took about 3 hours, against
2h12m for the earlier one, because the follow-up happens for every ranking rather than for a sample, and it is not as short as I
assumed. The stronger test is the reason to keep it; time is not.

## 5. Limits

- **Seven problems and 21 results per harness**: too few to separate harnesses whose true difference is small. More problems would
  help far more than more repeats, but the screen finds only 7 that this model fails, so a harder benchmark is the real fix.
- **Selected for being hard for one model**; judges and contestants share that model's blind spots.
- **The peers do not track the hidden tests here** (0.16), so the peer score here is not a proxy for correctness.
- **aider could not judge**; harness-engineering was excluded; 10 harnesses cannot run the model at all.
- **Costs are mostly unreported**, and the figures that exist use each harness's own accounting.
- A model alias (`deepseek-flash`) is one version of the model at the time of the run.
- Deterministic checks run on the host, on model-written code, with a timeout.

## 6. What I would do next

A benchmark where harnesses differ more than model noise does (the problem is not the harnesses' ability to judge or the blindness, both
of which held up, but that these problems are too easy to rank anyone on). Agentic bug-fixing tasks in real repositories are the obvious
candidate; the loop, the gate, the blind peer ranking and the verified blindness are the parts that are ready for it.
