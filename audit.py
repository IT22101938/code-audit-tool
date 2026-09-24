"""
Code audit tool - sends a source file to Claude and gets back a
structured JSON report (security issues, bugs, perf, maintainability).

Usage:
    python audit.py sample_vulnerable_code.py
    python audit.py sample_vulnerable_code.py --output report.json
"""

import os
import re
import sys
import json
import time
import argparse
from typing import List, Optional
from enum import Enum

from pydantic import BaseModel, Field, ValidationError
from dotenv import load_dotenv
import anthropic

load_dotenv()

MODEL = "claude-haiku-4-5"
MAX_RETRIES = 2
TIMEOUT_SECONDS = 30


class IssueType(str, Enum):
    SECURITY_RISK = "Security Risk"
    BUG = "Bug"
    PERFORMANCE = "Performance"
    MAINTAINABILITY = "Maintainability"


class Severity(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class Issue(BaseModel):
    issue_type: IssueType
    location: str = Field(..., description="Line number or code segment")
    description: str
    severity: Severity


class AuditReport(BaseModel):
    summary: str = Field(..., description="2-sentence overview of code health")
    issues: List[Issue]
    recommended_fixes: List[str]


# Schema is embedded directly in the system prompt so the model has no
# excuse to wander off-format. Still validated with pydantic afterward
# since LLMs don't always follow instructions perfectly.
SYSTEM_PROMPT = """You are a senior code auditor. Analyze the given source
code for security vulnerabilities, bugs, performance issues, and
maintainability problems. Respond with ONLY valid JSON in this exact shape,
no markdown fences and no extra text:

{
  "summary": "2-sentence executive overview of the code health",
  "issues": [
    {
      "issue_type": "Security Risk" | "Bug" | "Performance" | "Maintainability",
      "location": "line number or code segment reference",
      "description": "concise technical explanation of the issue",
      "severity": "Critical" | "High" | "Medium" | "Low"
    }
  ],
  "recommended_fixes": ["actionable code snippet or architectural remedy"]
}
"""


def build_user_prompt(code: str, filename: str) -> str:
    return (
        f"Audit the following file ({filename}). Return findings as JSON "
        f"matching the schema you were given.\n\n"
        f"--- FILE CONTENTS ---\n{code}\n--- END FILE ---"
    )


class AuditError(Exception):
    pass


# Simple pattern checks used when the LLM provider can't be reached.
# Not as thorough as a real review, but it keeps the tool useful instead
# of just failing outright, and it covers the flaw types this task cares
# about most (hardcoded secrets, SQL injection via string interpolation,
# a couple of common footguns).
SECRET_PATTERN = re.compile(r'(api[_-]?key|password|secret|token)\s*=\s*["\'][^"\']{6,}["\']', re.IGNORECASE)
SQL_FSTRING_PATTERN = re.compile(r'f["\'].*?(SELECT|INSERT|UPDATE|DELETE).*?\{.*?\}', re.IGNORECASE)
EVAL_PATTERN = re.compile(r'\beval\(|\bexec\(')
OS_SYSTEM_PATTERN = re.compile(r'os\.system\(')
BARE_EXCEPT_PATTERN = re.compile(r'except\s*:')


def local_fallback_audit(code: str, filename: str) -> AuditReport:
    issues = []

    for i, line in enumerate(code.split("\n"), start=1):
        if SECRET_PATTERN.search(line):
            issues.append(Issue(
                issue_type=IssueType.SECURITY_RISK,
                location=f"line {i}",
                description="Hardcoded secret/credential found in source code.",
                severity=Severity.CRITICAL,
            ))
        if SQL_FSTRING_PATTERN.search(line):
            issues.append(Issue(
                issue_type=IssueType.SECURITY_RISK,
                location=f"line {i}",
                description="SQL query built with f-string interpolation - likely SQL injection risk.",
                severity=Severity.CRITICAL,
            ))
        if EVAL_PATTERN.search(line):
            issues.append(Issue(
                issue_type=IssueType.SECURITY_RISK,
                location=f"line {i}",
                description="Use of eval()/exec() can allow arbitrary code execution.",
                severity=Severity.HIGH,
            ))
        if OS_SYSTEM_PATTERN.search(line):
            issues.append(Issue(
                issue_type=IssueType.SECURITY_RISK,
                location=f"line {i}",
                description="os.system() call - risk of command injection if input isn't sanitized.",
                severity=Severity.HIGH,
            ))
        if BARE_EXCEPT_PATTERN.search(line):
            issues.append(Issue(
                issue_type=IssueType.MAINTAINABILITY,
                location=f"line {i}",
                description="Bare except: clause swallows all errors, making bugs harder to trace.",
                severity=Severity.MEDIUM,
            ))

    if not issues:
        issues.append(Issue(
            issue_type=IssueType.MAINTAINABILITY,
            location="n/a",
            description="No issues matched by the local pattern checks. This fallback mode only "
                        "covers a small set of common flaws, so treat it as a first pass, not a full review.",
            severity=Severity.LOW,
        ))

    summary = (
        f"Local rule-based fallback scan of {filename} found {len(issues)} issue(s). "
        f"This ran without an LLM provider, so coverage is limited to common patterns only."
    )

    fixes = [
        "Move hardcoded secrets to environment variables and load them with os.getenv().",
        "Replace string-interpolated SQL with parameterized queries.",
        "Avoid eval()/exec() and os.system() on untrusted input.",
        "Replace bare except: clauses with specific exception types.",
    ]

    return AuditReport(summary=summary, issues=issues, recommended_fixes=fixes)


def run_audit(code: str, filename: str, api_key: Optional[str] = None, use_fallback: bool = True) -> AuditReport:
    key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not key:
        if use_fallback:
            print("No API key found - using local fallback analysis.")
            return local_fallback_audit(code, filename)
        raise AuditError("No API key found - set ANTHROPIC_API_KEY in your .env file.")

    client = anthropic.Anthropic(api_key=key, timeout=TIMEOUT_SECONDS)
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=2000,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": build_user_prompt(code, filename)}],
            )
            raw_text = "".join(
                block.text for block in response.content if block.type == "text"
            ).strip()

            # models sometimes wrap output in ```json fences anyway - strip if so
            if raw_text.startswith("```"):
                raw_text = raw_text.strip("`").split("\n", 1)[-1]
                if raw_text.startswith("json\n"):
                    raw_text = raw_text[5:]

            parsed = json.loads(raw_text)
            return AuditReport(**parsed)

        except anthropic.AuthenticationError as e:
            # bad key isn't going to fix itself on retry - stop immediately
            last_error = f"Invalid API key: {e}"
            break

        except anthropic.APITimeoutError:
            last_error = f"Request timed out (attempt {attempt}/{MAX_RETRIES})"
            time.sleep(1)

        except anthropic.APIConnectionError as e:
            last_error = f"Connection error (attempt {attempt}/{MAX_RETRIES}): {e}"
            time.sleep(1)

        except anthropic.RateLimitError:
            last_error = f"Rate limited (attempt {attempt}/{MAX_RETRIES})"
            time.sleep(2)

        except json.JSONDecodeError:
            last_error = f"Model returned malformed JSON (attempt {attempt}/{MAX_RETRIES})"

        except ValidationError as e:
            last_error = f"Response didn't match schema (attempt {attempt}/{MAX_RETRIES}): {e}"

    # Primary provider didn't come through - fall back rather than dead-end
    if use_fallback:
        print(f"Primary provider failed ({last_error}). Falling back to local static analysis.")
        return local_fallback_audit(code, filename)

    raise AuditError(f"Audit failed after {MAX_RETRIES} attempts. Last error: {last_error}")


def main():
    parser = argparse.ArgumentParser(description="AI-powered code audit tool")
    parser.add_argument("file", help="Path to the source file to audit")
    parser.add_argument("--output", help="Optional path to save the JSON report")
    parser.add_argument("--no-fallback", action="store_true",
                         help="Disable local fallback; fail instead if the API is unreachable")
    args = parser.parse_args()

    if not os.path.isfile(args.file):
        print(f"Error: file not found: {args.file}")
        sys.exit(1)

    with open(args.file, "r", encoding="utf-8") as f:
        code = f.read()

    print(f"Auditing {args.file} ...\n")

    try:
        report = run_audit(code, os.path.basename(args.file), use_fallback=not args.no_fallback)
    except AuditError as e:
        print(f"Audit failed: {e}")
        sys.exit(1)

    output_json = report.model_dump_json(indent=2)
    print(output_json)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_json)
        print(f"\nSaved report to {args.output}")


if __name__ == "__main__":
    main()