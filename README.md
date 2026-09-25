# Code Audit Tool

An AI tool that checks code files for security problems, bugs, performance
issues and maintainability problems. It sends the code to Claude (Anthropic's
AI) and returns a clean, structured JSON report.

If Claude can't be reached, the tool switches to a local backup scanner
instead of failing.

**Task 2 choice: Path A** (fallback logic and automated tests).

---

## How it works

1. `audit.py` reads the file and adds line numbers.
2. It asks Claude for the audit. Claude is forced to answer through a tool
   whose schema comes from the Pydantic model, so the answer is structured data.
3. Pydantic checks the answer again before it is used.
4. If Claude fails (bad key, timeout, bad answer), the local scanner runs and
   still returns a report in the same format.

Progress messages go to stderr, so `python audit.py file.py > report.json`
gives clean JSON.

---

## Setup

### 1. Install Python
You need Python 3.9 or newer. Check with:
```
python --version
```

### 2. Create a virtual environment
```
python -m venv venv
```
Activate it:
- **Windows:** `venv\Scripts\Activate.ps1`
- **Mac/Linux:** `source venv/bin/activate`

You should see `(venv)` at the start of your terminal line.

### 3. Install packages
```
pip install -r requirements.txt
```

### 4. Add your API key
Copy `.env.example` to a new file named `.env` and paste in your key:
```
ANTHROPIC_API_KEY=your_real_key_here
```
Never share or upload `.env`. It is already in `.gitignore`.

### 5. Run the tool
```
python audit.py sample_vulnerable_code.py
```
Save the report to a file:
```
python audit.py sample_vulnerable_code.py --output report.json
```

### 6. Try the backup mode
Change the key in `.env` to something fake, like `ANTHROPIC_API_KEY=invalid`, then run the same command:
```
python audit.py sample_vulnerable_code.py
```
The API rejects the key, and you still get a report from the local scanner.

To see it fail on purpose instead, add `--no-fallback`:
```
python audit.py sample_vulnerable_code.py --no-fallback
```
This prints an error and exits with code 1. Put your real key back afterwards.

### 7. Run the tests
```
pytest test_audit.py -v
```
You should see `2 passed`. The tests use fake API responses, so they need no key or internet.

---

## Project files

| File | What it does |
|---|---|
| `audit.py` | Main tool. Sends code to Claude, checks the answer, falls back if needed |
| `sample_vulnerable_code.py` | Sample file with known flaws for testing |
| `test_audit.py` | The 2 automated tests |
| `requirements.txt` | Packages needed |
| `.env.example` | Template for your `.env` file |
| `TASK2_PATH_A.md` | Fallback logic and testing notes (chosen path) |
| `TASK3_user_stories_and_process_map.md` | User stories and the process diagram |
| `TASK4_aws_architecture.md` | How to host this on AWS |

---

## Task 5 – My Answers

### 1. AI Workflows & Daily Habits
I use Claude for most of my coding work, GitHub Copilot for quick suggestions
inside my editor, and NotebookLM to turn my study notes into visual summaries
that are easier to remember. For everyday research, quick questions and
writing emails, I switch between Claude, ChatGPT and Gemini depending on the
task. Before I submit anything AI helped with, I read it carefully, run and
test it myself, ask the AI to explain its own logic, ask follow-up questions
if something looks off, and sometimes check it against the official
documentation.

### 2. Role Alignment
I would prefer a split of 60% Dev / 40% BA over my first 6 months. I am
early in my career, so I want some time on the business side too, to find out
where my strengths fit before I narrow my focus. This case study showed me I
enjoy the technical side more, but I want to stay open to consulting.

### 3. Handling Ambiguity
During my internship, I built a chatbot to help with PeoTV error support. At
first it was not clear which error messages or types the bot needed to
handle. I first talked to my supervisor to understand what was expected, then
spoke with the PeoTV engineers to learn the technical details of the errors,
and then went back to my supervisor to confirm everything before I started
building. Checking in this way meant I was not guessing, and I built the right
thing the first time.

### 4. Remote Discipline & Communication
When I get stuck, I first try to solve it myself for a short time instead of
asking right away. But I do not let it drag on. If I am still stuck, I message
my team lead before it becomes urgent, and I explain what I tried, what I
think the problem is, and what help I need. While I wait for a reply, I move
on to another task instead of sitting idle.
