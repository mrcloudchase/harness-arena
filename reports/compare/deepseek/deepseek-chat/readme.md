# Compare · deepseek/deepseek-chat · readme

Run `live1` · 2 repeats · 36 results ranked by 5 judges · **BLIND VERIFIED**

| Rank | Harness | Score (0–1) | Mean place | 1st places | Groups | Self-bias | Hidden-check pass rate (repeat spread) | Median wall (s) | Total wall (s) | Cost (USD) | No cost reported |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | kimi-code | 0.73 | 1.7 | 4 | 6 | 0.125 | – | 32.2 | 222 | 0.0000 | 6 |
| 2 | goose | 0.61 | 2.7 | 1 | 6 | 0.025 | – | 18.1 | 133 | 0.0000 | 6 |
| 3 | qwen-code | 0.55 | 2.8 | 1 | 6 | -0.067 | – | 31.9 | 195 | 0.0000 | 6 |
| 4 | claude-code | 0.53 | 4.2 | 0 | 6 | -0.033 | – | 25.2 | 163 | 0.7786 | 0 |
| 5 | grok-cli | 0.53 | 3.7 | 1 | 6 | 0.092 | – | 18.9 | 394 | 0.0000 | 6 |
| 6 | aider | 0.05 | 6.0 | 0 | 6 | – | – | 31.3 | 189 | 0.0000 | 6 |

Score is each harness's results' mean Borda points across every judge's ranking (1 = ranked best by everyone, 0 = worst by everyone). Judge agreement (Kendall's W): 0.50. Agreement with the hidden check where it varies: –.

## Blindness verification

- Scrub loop: **success** after 1 round(s). A classifier named the author of 1 of 36 results (p=0.999).
- All judges together guessed 32 of 174 authors right (p=0.300).
- Judges recognising their own work: 7 of 29 (p=0.198).
- Verdict: **blind**: nobody beat chance.

- Could not take the test (no usable guess): aider.
| Judge | Right | Guesses | p (by luck) |
|---|---|---|---|
| claude-code | 7 | 36 | 0.393 |
| goose | 4 | 36 | 0.872 |
| grok-cli | 6 | 36 | 0.569 |
| kimi-code | 7 | 30 | 0.223 |
| qwen-code | 8 | 36 | 0.243 |

## Judging coverage

- 30 valid rankings from 6 judges; 6 judgments failed or were excluded
- aider · bucket #1: 2 rounds without success: no usable ranking.json: [Errno 2] No such file or directory: '/tmp/judge-rnlxm4xz/ranking.json'
- aider · bucket #2: 2 rounds without success: no usable ranking.json: [Errno 2] No such file or directory: '/tmp/judge-dkmmj5ak/ranking.json'
- aider · csvstat #1: 2 rounds without success: no usable ranking.json: [Errno 2] No such file or directory: '/tmp/judge-sk5wqvnp/ranking.json'
- aider · csvstat #2: 2 rounds without success: no usable ranking.json: [Errno 2] No such file or directory: '/tmp/judge-w_g7h8vp/ranking.json'
- aider · slugify #1: 2 rounds without success: no usable ranking.json: [Errno 2] No such file or directory: '/tmp/judge-uzun974p/ranking.json'
- aider · slugify #2: 2 rounds without success: no usable ranking.json: [Errno 2] No such file or directory: '/tmp/judge-cpy82s01/ranking.json'

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

- 5 in total over 36 results, at most 1 in one
