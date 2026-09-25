import os
import re
import sys
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
MAX_TOKENS = 4096
MAX_FILE_BYTES = 200_000  # skip huge files
TOOL_NAME = "submit_audit_report"


def log(msg: str) -> None:
    """Print to stderr so stdout stays clean JSON."""
    print(msg, file=sys.stderr)


# schema
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
    location: str = Field(..., description="Line number or code segment reference")
    description: str = Field(..., description="Concise technical explanation of the issue")
    severity: Severity


class AuditReport(BaseModel):
    summary: str = Field(..., description="Exactly 2-sentence executive overview of the code health")
    issues: List[Issue]
    recommended_fixes: List[str] = Field(
        ..., description="Actionable code snippets or architectural remedies"
    )


# schema comes from the Pydantic model, so it lives in one place
AUDIT_REPORT_TOOL = {
    "name": TOOL_NAME,
    "description": "Submit the structured results of a source code audit.",
    "input_schema": AuditReport.model_json_schema(),
}

SYSTEM_PROMPT = (
    "You are a senior code auditor. Analyze the given source code for security "
    "vulnerabilities, bugs, performance issues, and maintainability problems. "
    "Each line of the file is prefixed with its line number and a colon; use those "
    f"numbers in the location field. Call the {TOOL_NAME} tool exactly once with your findings."
)


def build_user_prompt(code: str, filename: str) -> str:
    # add line numbers, models miscount lines otherwise
    numbered = "\n".join(f"{i}: {line}" for i, line in enumerate(code.split("\n"), start=1))
    return f"Audit the following file ({filename}).\n\n--- FILE CONTENTS ---\n{numbered}\n--- END FILE ---"


class AuditError(Exception):
    pass


class BadModelOutput(Exception):
    """Claude replied, but the answer is unusable."""


# local fallback
# Basic pattern checks for when Claude is down. Not a full review.
SECRET_PATTERN = re.compile(r'(api[_-]?key|password|secret|token)\s*=\s*["\'][^"\']{6,}["\']', re.IGNORECASE)
SQL_FSTRING_PATTERN = re.compile(r'f["\'].*?(SELECT|INSERT|UPDATE|DELETE).*?\{.*?\}', re.IGNORECASE)
EVAL_PATTERN = re.compile(r'\beval\(|\bexec\(')
OS_SYSTEM_PATTERN = re.compile(r'os\.system\(')
BARE_EXCEPT_PATTERN = re.compile(r'except\s*:')
FOR_LOOP_PATTERN = re.compile(r'^\s*for\s+\w+\s+in\s+.+:\s*$')
APPEND_PATTERN = re.compile(r'\.append\(')


def local_fallback_audit(code: str, filename: str) -> AuditReport:
    issues: List[Issue] = []
    lines = code.split("\n")

    def add(kind: IssueType, line_no: int, text: str, sev: Severity) -> None:
        issues.append(Issue(issue_type=kind, location=f"line {line_no}", description=text, severity=sev))

    for i, line in enumerate(lines, start=1):
        if SECRET_PATTERN.search(line):
            add(IssueType.SECURITY_RISK, i, "Hardcoded secret/credential found in source code.", Severity.CRITICAL)
        if SQL_FSTRING_PATTERN.search(line):
            add(IssueType.SECURITY_RISK, i,
                "SQL query built with f-string interpolation - likely SQL injection risk.", Severity.CRITICAL)
        if EVAL_PATTERN.search(line):
            add(IssueType.SECURITY_RISK, i, "Use of eval()/exec() can allow arbitrary code execution.", Severity.HIGH)
        if OS_SYSTEM_PATTERN.search(line):
            add(IssueType.SECURITY_RISK, i,
                "os.system() call - risk of command injection if input isn't sanitized.", Severity.HIGH)
        if BARE_EXCEPT_PATTERN.search(line):
            add(IssueType.MAINTAINABILITY, i,
                "Bare except: clause swallows all errors, making bugs harder to trace.", Severity.MEDIUM)
        # loop that only appends to a list
        if FOR_LOOP_PATTERN.match(line) and i < len(lines) and APPEND_PATTERN.search(lines[i]):
            add(IssueType.PERFORMANCE, i,
                "Loop that only appends each item to a list; use list(results) or a list comprehension.",
                Severity.LOW)

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
        "Replace string-interpolated SQL with parameterized queries, e.g. db.execute('SELECT * FROM users WHERE id = %s', (uid,)).",
        "Avoid eval()/exec() and os.system() on untrusted input.",
        "Replace bare except: clauses with specific exception types.",
        "Replace append-only loops with list(results) or a list comprehension.",
    ]
    return AuditReport(summary=summary, issues=issues, recommended_fixes=fixes)


# main flow
def run_audit(code: str, filename: str, api_key: Optional[str] = None, use_fallback: bool = True) -> AuditReport:
    key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not key:
        if use_fallback:
            log("No API key found - using local fallback analysis.")
            return local_fallback_audit(code, filename)
        raise AuditError("No API key found - set ANTHROPIC_API_KEY in your .env file.")

    # SDK retries off, we retry ourselves below
    client = anthropic.Anthropic(api_key=key, timeout=TIMEOUT_SECONDS, max_retries=0)
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": build_user_prompt(code, filename)}],
                tools=[AUDIT_REPORT_TOOL],
                tool_choice={"type": "tool", "name": TOOL_NAME},
            )

            if response.stop_reason == "max_tokens":
                raise BadModelOutput("response was truncated by max_tokens")

            parsed = next(
                (b.input for b in response.content
                 if b.type == "tool_use" and b.name == TOOL_NAME),
                None,
            )
            if parsed is None:
                raise BadModelOutput("model did not call the expected tool")

            return AuditReport(**parsed)

        except anthropic.AuthenticationError as e:
            # bad key won't fix itself, stop here
            last_error = f"Invalid API key: {e}"
            break

        except anthropic.APITimeoutError:
            last_error = f"Request timed out (attempt {attempt}/{MAX_RETRIES})"
            delay = 1

        except anthropic.APIConnectionError as e:
            last_error = f"Connection error (attempt {attempt}/{MAX_RETRIES}): {e}"
            delay = 1

        except anthropic.RateLimitError:
            last_error = f"Rate limited (attempt {attempt}/{MAX_RETRIES})"
            delay = 2

        except anthropic.APIStatusError as e:
            # 5xx may recover, other 4xx won't
            last_error = f"API error {e.status_code} (attempt {attempt}/{MAX_RETRIES})"
            if e.status_code < 500:
                break
            delay = 1

        except BadModelOutput as e:
            last_error = f"Bad model output: {e} (attempt {attempt}/{MAX_RETRIES})"
            delay = 0

        except ValidationError as e:
            last_error = f"Response didn't match schema (attempt {attempt}/{MAX_RETRIES}): {e}"
            delay = 0

        log(last_error)
        if attempt < MAX_RETRIES and delay:
            time.sleep(delay)

    # Claude failed, use the local scanner
    if use_fallback:
        log(f"Primary provider failed ({last_error}). Falling back to local static analysis.")
        return local_fallback_audit(code, filename)

    raise AuditError(f"All attempts failed. Last error: {last_error}")


def main():
    parser = argparse.ArgumentParser(description="AI-powered code audit tool")
    parser.add_argument("file", help="Path to the source file to audit")
    parser.add_argument("--output", help="Optional path to save the JSON report")
    parser.add_argument("--no-fallback", action="store_true",
                        help="Disable local fallback; fail instead if the API is unreachable")
    args = parser.parse_args()

    if not os.path.isfile(args.file):
        log(f"Error: file not found: {args.file}")
        sys.exit(1)
    if os.path.getsize(args.file) > MAX_FILE_BYTES:
        log(f"Error: file is larger than {MAX_FILE_BYTES // 1000} KB; refusing to send it to the API.")
        sys.exit(1)

    with open(args.file, "r", encoding="utf-8") as f:
        code = f.read()

    log(f"Auditing {args.file} ...")

    try:
        report = run_audit(code, os.path.basename(args.file), use_fallback=not args.no_fallback)
    except AuditError as e:
        log(f"Audit failed: {e}")
        sys.exit(1)

    output_json = report.model_dump_json(indent=2)
    print(output_json)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_json)
        log(f"Saved report to {args.output}")


if __name__ == "__main__":
    main()
