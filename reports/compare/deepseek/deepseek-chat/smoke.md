# Compare · deepseek/deepseek-chat · smoke

Run `main` · 3 repeats · 165 graded submissions

| Harness | Tasks graded | Pass rate (repeat spread) | Deterministic | Median wall (s) | Total wall (s) | Cost (USD) | No cost reported |
|---|---|---|---|---|---|---|---|
| aider | 5 | 100% (100%–100%) | 1.00 | 17.0 | 250 | 0.0000 | 15 |
| cheetahclaws | 5 | 100% (100%–100%) | 1.00 | 15.5 | 260 | 0.0000 | 15 |
| claude-code | 5 | 100% (100%–100%) | 1.00 | 13.4 | 209 | 1.2509 | 0 |
| goose | 5 | 100% (100%–100%) | 1.00 | 8.9 | 142 | 0.0000 | 15 |
| grok-cli | 5 | 100% (100%–100%) | 1.00 | 8.8 | 159 | 0.0000 | 15 |
| hermes | 5 | 100% (100%–100%) | 1.00 | 59.2 | 1470 | 0.0000 | 15 |
| kimi-code | 5 | 100% (100%–100%) | 1.00 | 12.3 | 197 | 0.0000 | 15 |
| minimax-code | 5 | 100% (100%–100%) | 1.00 | 26.7 | 415 | 0.0000 | 15 |
| opensquilla | 5 | 100% (100%–100%) | 1.00 | 27.5 | 515 | 0.0349 | 0 |
| qwen-code | 5 | 100% (100%–100%) | 1.00 | 14.7 | 243 | 0.0000 | 15 |
| nanobot | 5 | 0% (0%–0%) | 0.00 | 18.7 | 1084 | 0.0000 | 15 |

## Unsupported harnesses

- **cline**: provider refused: authentication
- **codex**:  "message":"Reconnecting... waiting for network (Connection failed: error sending request)"} {"type":"error","message":"Reconnecting... waiting for network (Connection failed: error sending request)"}
- **gajae**: probe fail: Error: No API key for litellm/deepseek-chat
- **jcode**: probe fail: Error: Failed to select model 'deepseek-chat': Model deepseek-chat not supported by Anthropic provider
- **kilo**:  c/deepseek-chat. {"type":"error","timestamp":1792365369326,"sessionID":"ses_eaeb30055ffebTHgwHfqQX2R9n","error":{"name":"UnknownError","data":{"message":"Model not found: anthropic/deepseek-chat."}}}
- **mimo**: : s (native:7:39) {"type":"error","timestamp":1792365363982,"sessionID":"ses_ffe5eaeb2ffe1ffeeHHRv0OGro","error":{"name":"UnknownError","data":{"message":"Model not found: anthropic/deepseek-chat."}}}
- **omp**: probe fail: Model "anthropic/deepseek-chat" not found Run `omp models find <pattern>` to search, or `omp models` to list all.
- **opencode**:  imestamp":1792365390129,"sessionID":"ses_eaeb29ce7ffeYwJrMfE1WcTmi2","error":{"name":"UnknownError","data":{"message":"Unexpected server error. Check server logs for details.","ref":"err_5a67363f"}}}
- **openhands**:  ───────────────────────────────────────[0m Goodbye! 👋 Conversation ID: e6ead99aed59480099d53d6f7ba35323 Hint: run openhands --resume e6ead99a-ed59-4800-99d5-3d6f7ba35323 to resume this conversation.
- **pi**:  n error.","durationMs":21,"thinkingLevel":"medium"}],"willRetry":false} {"type":"auto_retry_end","success":false,"attempt":3,"finalError":"Connection error."} {"type":"agent_settled","aborted":false}

## Model not verified (run without the relay, which these harnesses can't use)

- goose
- grok-cli

## Findings (never scored)

- deepseek-harness: called deepseek-flash, not the named model deepseek-chat (15 runs)
- harness-engineering: called claude-sonnet-5-5, not the named model deepseek-chat (15 runs)

## Finished ok without writing a file in any run (check the harness's integration, not its skill)

- nanobot

## Runner errors (retried, not held against the harness)

None.

## Calibration agreement

None.

## Blindness check

None.

## Redactions

- 0 in total over 165 submissions, at most 0 in one
