# Task 2 - Path A: Technical Engineering & MLOps

## Fallback logic

`run_audit()` tries Claude first, and falls back to a local rule-based scanner if Claude can't be reached or returns something unusable. It returns the first valid, Pydantic-validated report:

| Order | Provider | Enabled when | Structured output method |
|---|---|---|---|
| 1 | Anthropic Claude (`claude-haiku-4-5`) | `ANTHROPIC_API_KEY` set | Forced tool use (`tool_choice`) |
| 2 | Local rule-based scanner | always (unless `--no-fallback`) | Regex checks, no network |

The local scanner builds its report from the same Pydantic `AuditReport` model as the Claude path, so both routes produce output that matches the exact same schema — there is one source of truth for the JSON shape either way.

### What counts as a failure (triggers the local fallback)
- Invalid API key: not retried, falls back immediately.
- Timeout, connection error, rate limit, 5xx/529: retried up to `MAX_RETRIES` (2) with a short backoff, then falls back.
- 4xx errors other than 429: not retried, falls back immediately.
- Response truncated (`max_tokens`), no tool call, malformed JSON, or Pydantic validation failure ("invalid response"): falls back.

The SDK's own retries are disabled (`max_retries=0`) so they don't stack with ours.

### Design notes
- Status messages go to **stderr**, so `python audit.py x.py > report.json` yields clean JSON.
- Line numbers are added to the code sent to the model so `location` values are reliable.
- The local scanner covers all three flaw types in the sample: hardcoded secret, SQL injection, and an append-only loop.
- `--no-fallback` makes the tool fail loudly (exit code 1) instead of degrading silently.

## Automated tests (`pytest`)

Run: `pytest -q` (no API key needed; network calls are mocked).

1. `test_successful_audit_returns_valid_report`: mocked Claude tool-use response yields a validated `AuditReport` with exactly the required keys.
2. `test_invalid_api_key_falls_back_to_local_analysis`: an invalid key falls back to the local scanner with no retry, and raises `AuditError` when fallback is disabled (`use_fallback=False`).
