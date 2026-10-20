# Compare · deepseek/deepseek-flash · humaneval

Run `flash1` · 3 repeats · 252 results ranked by 12 judges · **BLIND VERIFIED**

| Rank | Harness | Score (0–1) | Mean place | 1st places | Groups | Self-bias | Hidden-check pass rate (repeat spread) | Median wall (s) | Total wall (s) | Cost (USD) | No cost reported |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | claude-code | 0.57 | 5.7 | 4 | 21 | 0.020 | 29% (14%–43%) | 18.4 | 407 | 2.2713 | 0 |
| 2 | hermes | 0.56 | 5.5 | 5 | 21 | -0.009 | 33% (14%–43%) | 67.5 | 1476 | 0.0000 | 21 |
| 3 | aider | 0.55 | 6.3 | 2 | 21 | -0.248 | 29% (29%–29%) | 24.6 | 712 | 0.0000 | 21 |
| 4 | grok-cli | 0.54 | 5.9 | 2 | 21 | 0.047 | 33% (29%–43%) | 13.3 | 328 | 0.0000 | 21 |
| 5 | goose | 0.53 | 5.8 | 1 | 21 | -0.021 | 14% (14%–14%) | 15.8 | 322 | 0.0283 | 0 |
| 6 | cheetahclaws | 0.53 | 5.9 | 4 | 21 | -0.016 | 19% (14%–29%) | 18.7 | 411 | 0.0000 | 21 |
| 7 | kimi-code | 0.50 | 6.3 | 0 | 21 | 0.022 | 19% (14%–29%) | 17.4 | 485 | 0.0000 | 21 |
| 8 | deepseek-harness | 0.49 | 6.9 | 0 | 21 | 0.110 | 29% (14%–43%) | 18.1 | 489 | 0.0000 | 21 |
| 9 | opensquilla | 0.48 | 7.1 | 1 | 21 | 0.022 | 24% (14%–29%) | 37.7 | 814 | 5.3288 | 0 |
| 10 | minimax-code | 0.47 | 7.0 | 0 | 21 | 0.040 | 24% (14%–29%) | 23.9 | 528 | 0.0000 | 21 |
| 11 | qwen-code | 0.41 | 7.5 | 2 | 21 | -0.058 | 33% (14%–43%) | 21.9 | 495 | 0.0000 | 21 |
| 12 | nanobot | 0.38 | 8.1 | 0 | 21 | 0.006 | 14% (14%–14%) | 35.5 | 757 | 0.0000 | 21 |

Score is each harness's results' mean Borda points across every judge's ranking (1 = ranked best by everyone, 0 = worst by everyone). Judge agreement (Kendall's W): 0.70. Agreement with the hidden check where it varies: 0.16.

## Blindness verification

- Scrub loop: **success** after 1 round(s). A classifier named the author of 0 of 252 results (p=1.000).
- Asked in the conversation where they ranked: 233 guess sets; in a fresh turn: 0.
- All judges together guessed 236 of 2796 authors right (p=0.428).
- Judges recognising their own work: 25 of 233 (p=0.116).
- Verdict: **blind**: nobody beat chance.

| Judge | Right | Guesses | p (by luck) |
|---|---|---|---|
| aider | 2 | 60 | 0.965 |
| cheetahclaws | 15 | 228 | 0.861 |
| claude-code | 26 | 252 | 0.153 |
| deepseek-harness | 22 | 252 | 0.442 |
| goose | 17 | 252 | 0.848 |
| grok-cli | 21 | 240 | 0.441 |
| hermes | 21 | 252 | 0.533 |
| kimi-code | 22 | 252 | 0.442 |
| minimax-code | 21 | 252 | 0.533 |
| nanobot | 25 | 252 | 0.209 |
| opensquilla | 25 | 252 | 0.209 |
| qwen-code | 19 | 252 | 0.708 |

## Judging coverage

- 236 valid rankings from 12 judges; 16 judgments failed or were excluded
- aider · p075 #2: 2 rounds without success: no usable ranking.json: [Errno 2] No such file or directory: '/tmp/judge-5l3diwsx/ranking.json'
- aider · p075 #3: 2 rounds without success: no usable ranking.json: [Errno 2] No such file or directory: '/tmp/judge-x370z809/ranking.json'
- aider · p091 #1: 2 rounds without success: no usable ranking.json: [Errno 2] No such file or directory: '/tmp/judge-3go0y5fg/ranking.json'
- aider · p099 #1: 2 rounds without success: no usable ranking.json: [Errno 2] No such file or directory: '/tmp/judge-fr6m7_de/ranking.json'
- aider · p099 #2: 2 rounds without success: no usable ranking.json: [Errno 2] No such file or directory: '/tmp/judge-717vcigs/ranking.json'
- aider · p099 #3: 2 rounds without success: no usable ranking.json: [Errno 2] No such file or directory: '/tmp/judge-mk4qamj7/ranking.json'
- aider · p132 #1: 2 rounds without success: no usable ranking.json: [Errno 2] No such file or directory: '/tmp/judge-tieo8bt7/ranking.json'
- aider · p132 #2: 2 rounds without success: no usable ranking.json: [Errno 2] No such file or directory: '/tmp/judge-xy_yotq7/ranking.json'
- aider · p132 #3: 2 rounds without success: no usable ranking.json: [Errno 2] No such file or directory: '/tmp/judge-wrlkjcsu/ranking.json'
- aider · p141 #1: 2 rounds without success: no usable ranking.json: [Errno 2] No such file or directory: '/tmp/judge-q8xby55y/ranking.json'
- aider · p141 #2: 2 rounds without success: no usable ranking.json: [Errno 2] No such file or directory: '/tmp/judge-k5gr57dc/ranking.json'
- aider · p141 #3: 2 rounds without success: no usable ranking.json: [Errno 2] No such file or directory: '/tmp/judge-9eqruxxp/ranking.json'
- aider · p151 #1: 2 rounds without success: no usable ranking.json: [Errno 2] No such file or directory: '/tmp/judge-7762ptua/ranking.json'
- aider · p151 #3: 2 rounds without success: no usable ranking.json: [Errno 2] No such file or directory: '/tmp/judge-njfm18w5/ranking.json'
- aider · p163 #1: 2 rounds without success: no usable ranking.json: [Errno 2] No such file or directory: '/tmp/judge-w8e2kq32/ranking.json'
- aider · p163 #3: 2 rounds without success: no usable ranking.json: [Errno 2] No such file or directory: '/tmp/judge-f3mxksaz/ranking.json'

## Unsupported harnesses (neither compete nor judge)

- **cline**: provider refused: authentication
- **codex**:  "message":"Reconnecting... waiting for network (Connection failed: error sending request)"} {"type":"error","message":"Reconnecting... waiting for network (Connection failed: error sending request)"}
- **gajae**: probe fail: Error: No API key for kilo/~deepseek/deepseek-flash-latest
- **jcode**: probe fail: Error: Failed to select model 'deepseek-flash': Model deepseek-flash not supported by Anthropic provider
- **kilo**:  deepseek-flash. {"type":"error","timestamp":1792442380682,"sessionID":"ses_eaa1be98cffeHdOGWe8K6I416K","error":{"name":"UnknownError","data":{"message":"Model not found: anthropic/deepseek-flash."}}}
- **mimo**: l: (native:7:39) {"type":"error","timestamp":1792442368748,"sessionID":"ses_ffe5eaa1c00d3ffeUriAN6AgBI","error":{"name":"UnknownError","data":{"message":"Model not found: anthropic/deepseek-flash."}}}
- **omp**: probe fail: Model "anthropic/deepseek-flash" not found Run `omp models find <pattern>` to search, or `omp models` to list all.
- **opencode**:  imestamp":1792442383827,"sessionID":"ses_eaa1bc7fdffe8klbhUMfHxgpgv","error":{"name":"UnknownError","data":{"message":"Unexpected server error. Check server logs for details.","ref":"err_668db5e7"}}}
- **openhands**:  ───────────────────────────────────────[0m Goodbye! 👋 Conversation ID: 879c85a4c6954d5f86de4c3837718231 Hint: run openhands --resume 879c85a4-c695-4d5f-86de-4c3837718231 to resume this conversation.
- **pi**:  on error.","durationMs":7,"thinkingLevel":"medium"}],"willRetry":false} {"type":"auto_retry_end","success":false,"attempt":3,"finalError":"Connection error."} {"type":"agent_settled","aborted":false}

## Model not verified (run without the relay, which these harnesses can't use)

- goose
- grok-cli

## Findings (never scored)

- harness-engineering: called claude-sonnet-5-5, not the named model deepseek-flash (21 runs)

## Finished ok without writing a file in any run (check the harness's integration, not its skill)

None.

## Runner errors (retried, not held against the harness)

None.

## Redactions

- 0 in total over 252 results, at most 0 in one
