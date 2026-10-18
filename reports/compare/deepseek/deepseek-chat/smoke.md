# Compare · deepseek/deepseek-chat · smoke

Run `shake2` · 1 repeats · 11 graded submissions

| Harness | Tasks graded | Pass rate (repeat spread) | Deterministic | Median wall (s) | Total wall (s) | Cost (USD) | No cost reported |
|---|---|---|---|---|---|---|---|
| aider | 1 | 100% (100%–100%) | 1.00 | 16.7 | 17 | 0.0000 | 1 |
| cheetahclaws | 1 | 100% (100%–100%) | 1.00 | 17.3 | 17 | 0.0000 | 1 |
| claude-code | 1 | 100% (100%–100%) | 1.00 | 15.3 | 15 | 0.0866 | 0 |
| goose | 1 | 100% (100%–100%) | 1.00 | 10.7 | 11 | 0.0000 | 1 |
| grok-cli | 1 | 100% (100%–100%) | 1.00 | 9.5 | 9 | 0.0000 | 1 |
| hermes | 1 | 100% (100%–100%) | 1.00 | 58.1 | 58 | 0.0000 | 1 |
| kimi-code | 1 | 100% (100%–100%) | 1.00 | 17.7 | 18 | 0.0000 | 1 |
| minimax-code | 1 | 100% (100%–100%) | 1.00 | 33.4 | 33 | 0.0000 | 1 |
| opensquilla | 1 | 100% (100%–100%) | 1.00 | 30.2 | 30 | 0.0020 | 0 |
| qwen-code | 1 | 100% (100%–100%) | 1.00 | 16.5 | 16 | 0.0000 | 1 |
| nanobot | 1 | 0% (0%–0%) | 0.00 | 20.7 | 21 | 0.0000 | 1 |

## Unsupported harnesses

- **cline**: provider refused: authentication
- **codex**: probe timeout: "message":"Reconnecting... waiting for network (Connection failed: error sending request)"}
{"type":"error","message":"Reconnecting... waiting for network (Connection failed: error sending request)"}

- **gajae**: probe fail: Error: No API key for litellm/deepseek-chat

- **jcode**: probe fail: Error: Failed to select model 'deepseek-chat': Model deepseek-chat not supported by Anthropic provider

- **kilo**: probe fail: c/deepseek-chat.
{"type":"error","timestamp":1792364782159,"sessionID":"ses_eaebbf1b3ffexKWRSzbuoZ2KaN","error":{"name":"UnknownError","data":{"message":"Model not found: anthropic/deepseek-chat."}}}

- **mimo**: probe fail: s (native:7:39)

{"type":"error","timestamp":1792364779222,"sessionID":"ses_ffe5eaebbec12fferTqvXWGxgV","error":{"name":"UnknownError","data":{"message":"Model not found: anthropic/deepseek-chat."}}}

- **omp**: probe fail: Model "anthropic/deepseek-chat" not found

Run `omp models find <pattern>` to search, or `omp models` to list all.

- **opencode**: probe fail: imestamp":1792364804101,"sessionID":"ses_eaebb8c51ffeHExTy1aRe5z81W","error":{"name":"UnknownError","data":{"message":"Unexpected server error. Check server logs for details.","ref":"err_02c22695"}}}

- **openhands**: probe fail: ───────────────────────────────────────[0m
Goodbye! 👋
Conversation ID: 9a61db10f66c412288f134738ad99def
Hint: run openhands --resume 9a61db10-f66c-4122-88f1-34738ad99def to resume this
conversation.

- **pi**: probe fail: on error.","durationMs":7,"thinkingLevel":"medium"}],"willRetry":false}
{"type":"auto_retry_end","success":false,"attempt":3,"finalError":"Connection error."}
{"type":"agent_settled","aborted":false}


## Model not verified (run without the relay, which these harnesses can't use)

- goose
- grok-cli

## Findings (never scored)

- harness-engineering · roman #1: called claude-sonnet-5-5, not the named model deepseek-chat
- deepseek-harness · roman #1: called deepseek-flash, not the named model deepseek-chat

## Runner errors (retried, not held against the harness)

None.

## Calibration agreement

None.

## Blindness check

None.

## Redactions

- 0 in total over 11 submissions, at most 0 in one
