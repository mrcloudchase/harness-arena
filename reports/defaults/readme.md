# Defaults · each harness on its own default model · readme

Run `main` · 2 repeats · 30 graded submissions

| Harness | Tasks graded | Pass rate (repeat spread) | Deterministic | deepseek/deepseek-chat | openai/gpt-4.1-mini | Panel median | Pairwise wins | Median wall (s) | Total wall (s) | Cost (USD) | No cost reported |
|---|---|---|---|---|---|---|---|---|---|---|---|
| deepseek-harness | 3 | 100% (100%–100%) | 1.00 | 1.00 | 1.00 | 1.00 | 0.78 | 31.5 | 203 | 0.0000 | 6 |
| kimi-code | 3 | 100% (100%–100%) | 1.00 | 1.00 | 1.00 | 1.00 | 0.48 | 25.2 | 158 | 0.0000 | 6 |
| minimax-code | 3 | 100% (100%–100%) | 1.00 | 1.00 | 1.00 | 1.00 | 0.75 | 48.2 | 278 | 0.0000 | 6 |
| qwen-code | 3 | 100% (100%–100%) | 1.00 | 1.00 | 1.00 | 1.00 | 0.44 | 18.6 | 115 | 0.0000 | 6 |
| cheetahclaws | 3 | 83% (67%–100%) | 0.83 | 0.64 | 0.82 | 0.73 | 0.06 | 13.9 | 82 | 0.0000 | 6 |

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

- llm: deepseek/deepseek-chat 0.94 (n=8); openai/gpt-4.1-mini 0.83 (n=8), threshold 0.6

## Blindness check

- deepseek/deepseek-chat: 7/30 guessed, chance 20%, p=0.393
- openai/gpt-4.1-mini: 7/30 guessed, chance 20%, p=0.393

## Redactions

- 4 in total over 30 submissions, at most 1 in one
