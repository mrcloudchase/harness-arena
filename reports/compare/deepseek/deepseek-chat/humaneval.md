# Compare · deepseek/deepseek-chat · humaneval

Run `real1` · 2 repeats · 264 results ranked by 11 judges · **BLIND VERIFIED**

| Rank | Harness | Score (0–1) | Mean place | 1st places | Groups | Self-bias | Hidden-check pass rate (repeat spread) | Median wall (s) | Total wall (s) | Cost (USD) | No cost reported |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | minimax-code | 0.68 | 3.8 | 10 | 24 | 0.015 | 50% (50%–50%) | 28.4 | 1346 | 0.0000 | 24 |
| 2 | kimi-code | 0.57 | 5.5 | 2 | 24 | 0.040 | 42% (33%–50%) | 18.1 | 974 | 0.0000 | 24 |
| 3 | hermes | 0.54 | 5.5 | 1 | 24 | -0.049 | 38% (25%–50%) | 59.4 | 2016 | 0.0000 | 24 |
| 4 | goose | 0.51 | 5.8 | 1 | 24 | 0.065 | 42% (42%–42%) | 8.9 | 346 | 0.0000 | 24 |
| 5 | grok-cli | 0.51 | 6.1 | 2 | 24 | 0.005 | 46% (42%–50%) | 10.0 | 453 | 0.0000 | 24 |
| 6 | claude-code | 0.49 | 6.2 | 3 | 24 | 0.020 | 33% (33%–33%) | 18.6 | 586 | 2.9567 | 0 |
| 7 | nanobot | 0.48 | 6.0 | 2 | 24 | 0.011 | 42% (42%–42%) | 26.6 | 1905 | 0.0000 | 24 |
| 8 | opensquilla | 0.47 | 6.7 | 1 | 24 | 0.093 | 33% (25%–42%) | 32.8 | 1033 | 0.0600 | 0 |
| 9 | qwen-code | 0.44 | 6.6 | 0 | 24 | -0.001 | 29% (17%–42%) | 19.4 | 768 | 0.0000 | 24 |
| 10 | cheetahclaws | 0.44 | 6.7 | 1 | 24 | -0.021 | 33% (33%–33%) | 17.5 | 674 | 0.0000 | 24 |
| 11 | aider | 0.38 | 7.0 | 3 | 24 | 0.006 | 21% (17%–25%) | 25.0 | 597 | 0.0000 | 24 |

Score is each harness's results' mean Borda points across every judge's ranking (1 = ranked best by everyone, 0 = worst by everyone). Judge agreement (Kendall's W): 0.62. Agreement with the hidden check where it varies: 0.49.

## Blindness verification

- Scrub loop: **success** after 1 round(s). A classifier named the author of 0 of 264 results (p=1.000).
- All judges together guessed 66 of 627 authors right (p=0.120).
- Judges recognising their own work: 6 of 57 (p=0.417).
- Verdict: **blind**: nobody beat chance.

- Could not take the test (no usable guess): aider.
| Judge | Right | Guesses | p (by luck) |
|---|---|---|---|
| cheetahclaws | 6 | 66 | 0.562 |
| claude-code | 5 | 66 | 0.728 |
| goose | 7 | 66 | 0.394 |
| grok-cli | 4 | 66 | 0.861 |
| hermes | 12 | 66 | 0.015 |
| kimi-code | 2 | 44 | 0.919 |
| minimax-code | 4 | 55 | 0.748 |
| nanobot | 10 | 66 | 0.074 |
| opensquilla | 4 | 66 | 0.861 |
| qwen-code | 12 | 66 | 0.015 |

## Judging coverage

- 247 valid rankings from 11 judges; 17 judgments failed or were excluded
- aider · p076 #1: 2 rounds without success: no usable ranking.json: [Errno 2] No such file or directory: '/tmp/judge-9fw3pz34/ranking.json'
- aider · p097 #1: 2 rounds without success: no usable ranking.json: [Errno 2] No such file or directory: '/tmp/judge-wdhzawhs/ranking.json'
- aider · p097 #2: ithout success: no usable ranking.json: the ranking must list exactly these ids, once each: S-398677, S-3c642c, S-437c16, S-4ed5ba, S-4fdd14, S-602e3f, S-65392d, S-6ca06b, S-6ff2dd, S-708a58, S-cf3200
- aider · p099 #1: 2 rounds without success: no usable ranking.json: [Errno 2] No such file or directory: '/tmp/judge-z1dbpa2n/ranking.json'
- aider · p099 #2: 2 rounds without success: no usable ranking.json: [Errno 2] No such file or directory: '/tmp/judge-wwdkcnme/ranking.json'
- aider · p116 #1: 2 rounds without success: no usable ranking.json: [Errno 2] No such file or directory: '/tmp/judge-t6m5cy8k/ranking.json'
- aider · p116 #2: ithout success: no usable ranking.json: the ranking must list exactly these ids, once each: S-2f122a, S-496828, S-5549b8, S-770dd2, S-90f14c, S-a89cd0, S-a9de0f, S-cc30e9, S-d4b551, S-e21000, S-f615ad
- aider · p130 #1: 2 rounds without success: no usable ranking.json: [Errno 2] No such file or directory: '/tmp/judge-5kqlm673/ranking.json'
- aider · p132 #2: 2 rounds without success: no usable ranking.json: [Errno 2] No such file or directory: '/tmp/judge-smg3w5xo/ranking.json'
- aider · p141 #1: 2 rounds without success: no usable ranking.json: [Errno 2] No such file or directory: '/tmp/judge-op9z1zr4/ranking.json'
- aider · p141 #2: 2 rounds without success: no usable ranking.json: [Errno 2] No such file or directory: '/tmp/judge-9jly2vsp/ranking.json'
- aider · p145 #1: 2 rounds without success: no usable ranking.json: [Errno 2] No such file or directory: '/tmp/judge-5_lwgeex/ranking.json'
- nanobot · p141 #2: 2 rounds without success: no usable ranking.json: [Errno 2] No such file or directory: '/tmp/judge-qcftcr49/ranking.json'
- aider · p151 #1: 2 rounds without success: no usable ranking.json: [Errno 2] No such file or directory: '/tmp/judge-f25qvzwz/ranking.json'
- aider · p151 #2: 2 rounds without success: no usable ranking.json: [Errno 2] No such file or directory: '/tmp/judge-dxmopoao/ranking.json'
- aider · p154 #1: 2 rounds without success: no usable ranking.json: [Errno 2] No such file or directory: '/tmp/judge-upeld_8y/ranking.json'
- aider · p154 #2: ithout success: no usable ranking.json: the ranking must list exactly these ids, once each: S-04b9ab, S-11c82d, S-19f8ab, S-304ad8, S-74b502, S-7f382b, S-887787, S-bf08e3, S-c4a89d, S-e846fc, S-ed43b9

## Unsupported harnesses (neither compete nor judge)

- **cline**: provider refused: authentication
- **codex**:  "message":"Reconnecting... waiting for network (Connection failed: error sending request)"} {"type":"error","message":"Reconnecting... waiting for network (Connection failed: error sending request)"}
- **gajae**: probe fail: Error: No API key for litellm/deepseek-chat
- **jcode**: probe fail: Error: Failed to select model 'deepseek-chat': Model deepseek-chat not supported by Anthropic provider
- **kilo**:  c/deepseek-chat. {"type":"error","timestamp":1792431944447,"sessionID":"ses_eaabb264fffeRGlNptpEecREZq","error":{"name":"UnknownError","data":{"message":"Model not found: anthropic/deepseek-chat."}}}
- **mimo**: : s (native:7:39) {"type":"error","timestamp":1792431932655,"sessionID":"ses_ffe5eaabb3f71ffePlM6wYp1J1","error":{"name":"UnknownError","data":{"message":"Model not found: anthropic/deepseek-chat."}}}
- **omp**: probe fail: Model "anthropic/deepseek-chat" not found Run `omp models find <pattern>` to search, or `omp models` to list all.
- **opencode**:  imestamp":1792431947106,"sessionID":"ses_eaabb07d7ffeqhNLFXu18E4hPs","error":{"name":"UnknownError","data":{"message":"Unexpected server error. Check server logs for details.","ref":"err_722a88a7"}}}
- **openhands**:  ───────────────────────────────────────[0m Goodbye! 👋 Conversation ID: 5679b53c67724dd691dd09d5e6f6ed48 Hint: run openhands --resume 5679b53c-6772-4dd6-91dd-09d5e6f6ed48 to resume this conversation.
- **pi**:  on error.","durationMs":9,"thinkingLevel":"medium"}],"willRetry":false} {"type":"auto_retry_end","success":false,"attempt":3,"finalError":"Connection error."} {"type":"agent_settled","aborted":false}

## Model not verified (run without the relay, which these harnesses can't use)

- goose
- grok-cli

## Findings (never scored)

- deepseek-harness: called deepseek-flash, not the named model deepseek-chat (24 runs)
- harness-engineering: called claude-sonnet-5-5, not the named model deepseek-chat (24 runs)

## Finished ok without writing a file in any run (check the harness's integration, not its skill)

None.

## Runner errors (retried, not held against the harness)

None.

## Redactions

- 0 in total over 264 results, at most 0 in one
