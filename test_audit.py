"""
Unit tests for audit.py. Run with: pytest test_audit.py -v

Both API calls are mocked - no real network requests, no API key needed.
"""

import json
from unittest.mock import MagicMock, patch

import httpx
from anthropic import AuthenticationError

from audit import run_audit, AuditReport


def _mock_text_block(text):
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


@patch("audit.anthropic.Anthropic")
def test_successful_audit_returns_valid_report(mock_anthropic_cls):
    """A well-formed API response should parse into a valid AuditReport."""
    valid_json = json.dumps({
        "summary": "The code has a critical SQL injection flaw and one performance issue.",
        "issues": [
            {
                "issue_type": "Security Risk",
                "location": "line 6",
                "description": "SQL injection via unparameterized f-string query.",
                "severity": "Critical",
            }
        ],
        "recommended_fixes": ["Use parameterized queries instead of f-strings."],
    })

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [_mock_text_block(valid_json)]
    mock_client.messages.create.return_value = mock_response
    mock_anthropic_cls.return_value = mock_client

    report = run_audit("some code", "test.py", api_key="fake-key-for-test")

    assert isinstance(report, AuditReport)
    assert len(report.issues) == 1
    assert report.issues[0].severity == "Critical"
    assert "SQL injection" in report.issues[0].description
    assert "parameterized" in report.recommended_fixes[0]


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

    vulnerable_code = 'api_key = "sk-proj-998877665544332211"\n'
    report = run_audit(vulnerable_code, "sample.py", api_key="bad-key")

    # should not raise - should return a usable report from the local fallback
    assert isinstance(report, AuditReport)
    assert any(issue.issue_type == "Security Risk" for issue in report.issues)
    assert any("secret" in issue.description.lower() for issue in report.issues)
