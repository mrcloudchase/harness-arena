# Defaults · each harness on its own default model · readme

Run `blind` · 2 repeats · 30 graded submissions

| Harness | Tasks graded | Pass rate (repeat spread) | Deterministic | deepseek/deepseek-chat | openai/gpt-4.1-mini | Panel median | Pairwise wins | Median wall (s) | Total wall (s) | Cost (USD) | No cost reported |
|---|---|---|---|---|---|---|---|---|---|---|---|
| cheetahclaws | 3 | 100% (100%–100%) | 1.00 | 0.82 | 0.96 | 0.89 | 0.06 | 12.5 | 77 | 0.0000 | 6 |
| deepseek-harness | 3 | 100% (100%–100%) | 1.00 | 1.00 | 1.00 | 1.00 | 0.79 | 36.7 | 239 | 0.0000 | 6 |
| kimi-code | 3 | 100% (100%–100%) | 1.00 | 1.00 | 1.00 | 1.00 | 0.38 | 22.7 | 140 | 0.0000 | 6 |
| minimax-code | 3 | 100% (100%–100%) | 1.00 | 1.00 | 1.00 | 1.00 | 0.77 | 39.4 | 252 | 0.0000 | 6 |
| qwen-code | 3 | 100% (100%–100%) | 1.00 | 1.00 | 1.00 | 1.00 | 0.51 | 23.1 | 141 | 0.0000 | 6 |

## Unsupported harnesses

None.

## Model not verified (run without the relay, which these harnesses can't use)

None.

## Findings (never scored)

None.

## Finished ok without writing a file in any run (check the harness's integration, not its skill)

None.

## Runner errors (retried, not held against the harness)

None.

## Calibration agreement

- llm: deepseek/deepseek-chat 0.92 (n=8); openai/gpt-4.1-mini 0.70 (n=8), threshold 0.6

## Blindness check

- deepseek/deepseek-chat: 9/30 guessed, chance 20%, p=0.129
- openai/gpt-4.1-mini: 5/30 guessed, chance 20%, p=0.745

## Redactions

- 8 in total over 30 submissions, at most 1 in one
