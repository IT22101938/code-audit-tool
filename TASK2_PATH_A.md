# Task 2 – Specialization Path A: Technical Engineering & MLOps

## Why I chose Path A

I chose Path A because I wanted to show I can make an AI tool that keeps working
even when something goes wrong — not just when everything is perfect. In a real
company, an AI audit tool that stops working the moment the API has a bad day
isn't very useful. I wanted to build something closer to what a production
tool actually needs: it should still give the team *something* useful, even
during an outage.

## What "fallback logic" means here

The original script (Task 1) sends code to Claude (Anthropic's AI) and asks it
to return a structured report of security issues, bugs, performance problems,
and maintainability issues.

But what happens if:
- The API key is wrong?
- The internet drops?
- Anthropic's servers are having issues?
- The AI sends back a broken/incomplete response?

Without a fallback, the script would just fail and give the user nothing.
That's not good enough for a real business tool.

So I added a **second layer** that kicks in automatically if the first layer
(the AI) fails for any reason. This is the "fallback" part.

## How my fallback works

Instead of using a second paid AI service (which needs its own subscription
and API key), I built a **local, rule-based fallback checker**. This means it
doesn't call any external AI at all — it just reads through the code file
directly and looks for well-known danger patterns using simple text matching
(called "regex", short for regular expressions).

It currently checks for:
- **Hardcoded secrets** — things like `api_key = "..."` or `password = "..."`
  written directly into the code instead of being kept private.
- **SQL injection risk** — code that builds a database query by directly
  inserting user input into a text string (an f-string), instead of using
  a safe, parameterized query.
- **Dangerous functions** — use of `eval()`, `exec()`, or `os.system()`,
  which can let attackers run their own code if misused.
- **Bare `except:` blocks** — a common bad habit where errors get silently
  ignored instead of properly handled, which makes bugs much harder to find.

If it doesn't find anything, it says so honestly instead of pretending
everything is perfect.

## Why I chose a local fallback instead of a second AI provider

The original brief suggested two options: fall back to a *second AI provider*,
or a *structured local fallback parser*. I went with the local parser because:

1. **No extra cost** — a second AI provider means paying for two subscriptions
   instead of one. A local fallback costs nothing to run.
2. **No extra dependency** — if Anthropic *and* a second AI company both have
   issues at the same time (rare, but possible), a local fallback still works,
   because it doesn't depend on the internet or any outside company at all.
3. **It's honest about its limits** — I made sure the local fallback's summary
   message clearly says it's running in a limited fallback mode, so nobody
   mistakes a quick pattern-match for a full AI review.

## What this fallback does *not* do

I want to be upfront about the tradeoffs, since this matters for how the tool
should actually be used:

- It can only catch the specific patterns I coded it to look for. It will
  **never** be as thorough as a full AI review, because it doesn't actually
  "understand" the code — it's just matching text patterns.
- It won't catch subtle logic bugs, bad architecture decisions, or anything
  that isn't one of the specific red flags I explicitly told it to look for.
- It's meant as a **safety net for outages**, not a replacement for the real
  AI-powered audit. The tool should always try Claude first, and only use the
  fallback when Claude genuinely can't be reached.

## How I tested it

I wrote two automated tests using `pytest` (in `test_audit.py`):

1. **Successful run test** — simulates a normal, working API response and
   checks that the script correctly turns it into a valid, structured report.
2. **Fallback test** — simulates an invalid API key and checks that instead of
   crashing, the script automatically switches to the local fallback and still
   returns a usable report that correctly flags a hardcoded secret.

Both tests use "mocking," which means they don't make any real API calls —
they simulate what the API would say, so the tests run instantly and don't
cost any money or need internet access to run.

I also tested this manually, live, by temporarily putting a fake API key in
my `.env` file and running the script for real. It correctly detected the
failure, printed a clear message explaining what happened, and still produced
a proper JSON report using the local checks — exactly as intended.
