# Compare · deepseek/deepseek-chat · smoke

Run `live1` · 2 repeats · 30 results ranked by 5 judges · **BLIND VERIFIED**

| Rank | Harness | Score (0–1) | Mean place | 1st places | Groups | Self-bias | Hidden-check pass rate (repeat spread) | Median wall (s) | Total wall (s) | Cost (USD) | No cost reported |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | goose | 0.72 | 1.7 | 4 | 6 | 0.198 | 100% (100%–100%) | 8.2 | 50 | 0.0000 | 6 |
| 2 | kimi-code | 0.66 | 2.3 | 1 | 6 | 0.271 | 100% (100%–100%) | 14.9 | 96 | 0.0000 | 6 |
| 3 | grok-cli | 0.43 | 3.5 | 1 | 6 | 0.135 | 100% (100%–100%) | 10.5 | 66 | 0.0000 | 6 |
| 4 | qwen-code | 0.36 | 3.5 | 1 | 6 | -0.083 | 100% (100%–100%) | 18.6 | 114 | 0.0000 | 6 |
| 5 | claude-code | 0.33 | 4.0 | 0 | 6 | 0.000 | 100% (100%–100%) | 15.1 | 90 | 0.4860 | 0 |

Score is each harness's results' mean Borda points across every judge's ranking (1 = ranked best by everyone, 0 = worst by everyone). Judge agreement (Kendall's W): 0.48. Agreement with the hidden check where it varies: –.

## Blindness verification

- Scrub loop: **success** after 1 round(s). A classifier named the author of 1 of 30 results (p=0.999).
- All judges together guessed 11 of 100 authors right (p=0.994).
- Judges recognising their own work: 2 of 20 (p=0.931).
- Verdict: **blind**: nobody beat chance.

| Judge | Right | Guesses | p (by luck) |
|---|---|---|---|
| claude-code | 3 | 20 | 0.794 |
| goose | 2 | 20 | 0.931 |
| grok-cli | 2 | 20 | 0.931 |
| kimi-code | 3 | 20 | 0.794 |
| qwen-code | 1 | 20 | 0.988 |

## Judging coverage

- 30 valid rankings from 5 judges

## Unsupported harnesses (neither compete nor judge)

None.

## Model not verified (run without the relay, which these harnesses can't use)

- goose
- grok-cli

## Findings (never scored)

None.

## Finished ok without writing a file in any run (check the harness's integration, not its skill)

None.

## Runner errors (retried, not held against the harness)

None.

## Redactions

- 0 in total over 30 results, at most 0 in one
