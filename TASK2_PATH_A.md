# Task 2 - Path A: Technical Engineering & MLOps

## Multi-provider fallback

`run_audit()` walks a provider chain and returns the first valid, Pydantic-validated report:

| Order | Provider | Enabled when | Structured output method |
|---|---|---|---|
| 1 | Anthropic Claude (`claude-haiku-4-5`) | `ANTHROPIC_API_KEY` set | Forced tool use (`tool_choice`) |
| 2 | OpenAI (`gpt-4o-mini`) | `OPENAI_API_KEY` set | Forced function calling |
| 3 | Local rule-based scanner | always (unless `--no-fallback`) | Regex checks, no network |

Both LLM providers receive the **same JSON Schema, generated from the Pydantic `AuditReport` model**, so there is one source of truth.

### What counts as a failure (triggers the next provider)
- Invalid API key: not retried, moves on immediately.
- Timeout, connection error, rate limit, 5xx/529: retried up to `MAX_RETRIES` (2) with a short backoff.
- 4xx errors other than 429: not retried.
- Response truncated (`max_tokens`), no tool call, malformed JSON, or Pydantic validation failure ("invalid response").

The SDK's own retries are disabled (`max_retries=0`) so they don't stack with ours.

### Design notes
- Status messages go to **stderr**, so `python audit.py x.py > report.json` yields clean JSON.
- Line numbers are added to the code sent to the model so `location` values are reliable.
- The local scanner covers all three flaw types in the sample: hardcoded secret, SQL injection, and an append-only loop.
- `--no-fallback` makes the tool fail loudly (exit code 1) instead of degrading silently.

## Automated tests (`pytest`)

Run: `pytest -q` (no API key needed; network calls are mocked).

1. `test_successful_audit_returns_valid_json`: mocked Claude tool call yields a validated `AuditReport` with exactly the required keys.
2. `test_invalid_api_key_triggers_fallback_and_no_fallback_raises`: an invalid key falls back to the local scanner (with no retry), and raises `AuditError` when fallback is disabled.
3. Bonus: `test_secondary_provider_used_when_primary_fails`: OpenAI answers when Anthropic fails.
