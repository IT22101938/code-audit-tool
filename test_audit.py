"""
Unit tests for audit.py. Run with: pytest test_audit.py -v

Both API calls are mocked - no real network requests, no API key needed.
"""

import os
from unittest.mock import MagicMock, patch

import httpx
import pytest
from anthropic import AuthenticationError

from audit import run_audit, AuditReport, AuditError, TOOL_NAME

# load the sample next to this file, so tests work from any folder
SAMPLE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_vulnerable_code.py")
with open(SAMPLE_PATH, encoding="utf-8") as f:
    SAMPLE_CODE = f.read()


def _tool_use_block(payload):
    block = MagicMock()
    block.type = "tool_use"
    block.name = TOOL_NAME
    block.input = payload
    return block


@patch("audit.anthropic.Anthropic")
def test_successful_audit_returns_valid_report(mock_anthropic_cls):
    """A well-formed tool-use response should parse into a valid AuditReport."""
    payload = {
        "summary": "The code has a critical SQL injection flaw and one performance issue.",
        "issues": [
            {
                "issue_type": "Security Risk",
                "location": "line 5",
                "description": "SQL injection via unparameterized f-string query.",
                "severity": "Critical",
            }
        ],
        "recommended_fixes": ["Use parameterized queries instead of f-strings."],
    }

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.stop_reason = "tool_use"
    mock_response.content = [_tool_use_block(payload)]
    mock_client.messages.create.return_value = mock_response
    mock_anthropic_cls.return_value = mock_client

    report = run_audit(SAMPLE_CODE, "test.py", api_key="fake-key-for-test")

    assert isinstance(report, AuditReport)
    assert len(report.issues) == 1
    assert report.issues[0].severity == "Critical"
    assert "SQL injection" in report.issues[0].description
    assert "parameterized" in report.recommended_fixes[0]
    # the model was forced to call the schema tool
    kwargs = mock_client.messages.create.call_args.kwargs
    assert kwargs["tool_choice"] == {"type": "tool", "name": TOOL_NAME}


@patch("audit.anthropic.Anthropic")
def test_invalid_api_key_falls_back_to_local_analysis(mock_anthropic_cls):
    """An invalid key should trigger the local fallback rather than crash."""
    fake_response = httpx.Response(
        status_code=401,
        request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"),
    )
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = AuthenticationError(
        message="invalid api key", response=fake_response, body=None
    )
    mock_anthropic_cls.return_value = mock_client

    report = run_audit(SAMPLE_CODE, "sample.py", api_key="bad-key")

    # should not raise - should return a usable report from the local fallback
    assert isinstance(report, AuditReport)
    assert "fallback" in report.summary.lower()
    types = {issue.issue_type for issue in report.issues}
    assert "Security Risk" in types and "Performance" in types
    assert any("secret" in issue.description.lower() for issue in report.issues)
    # an invalid key must not be retried
    assert mock_client.messages.create.call_count == 1

    # with fallback disabled, the same failure must raise instead
    with pytest.raises(AuditError):
        run_audit(SAMPLE_CODE, "sample.py", api_key="bad-key", use_fallback=False)
