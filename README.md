# Code Audit Tool

An AI-powered tool that checks code files for security problems, bugs,
performance issues, and maintainability problems. It sends the code to
Claude (Anthropic's AI), and returns a clean, structured report.

If the AI can't be reached for any reason, the tool automatically switches
to a backup local checker instead of failing completely.

---

## Setup Instructions

### 1. Install Python
Make sure you have Python 3.9 or newer installed. Check with:
```
python --version
```

### 2. Create a virtual environment
This keeps this project's packages separate from everything else on your
computer.
```
python -m venv venv
```

Activate it:
- **Windows:** `venv\Scripts\Activate.ps1`
- **Mac/Linux:** `source venv/bin/activate`

You'll know it worked when you see `(venv)` at the start of your terminal line.

### 3. Install the required packages
```
pip install -r requirements.txt
```

### 4. Add your API key
Copy `.env.example` and rename the copy to `.env`. Open it and paste in your
real Anthropic API key:
```
ANTHROPIC_API_KEY=your_real_key_here
```
Never share this file or upload it anywhere — it's already excluded from
git through `.gitignore`.

### 5. Run the tool
```
python audit.py sample_vulnerable_code.py
```

To also save the result to a file:
```
python audit.py sample_vulnerable_code.py --output report.json
```

To test the backup mode without using a real API key:
```
python audit.py sample_vulnerable_code.py --no-fallback
```

### 6. Run the tests
```
pytest test_audit.py -v
```
You should see `2 passed`.

---

## Project Files

| File | What it does |
|---|---|
| `audit.py` | The main tool. Reads a file, sends it to Claude, checks the response matches the expected format |
| `sample_vulnerable_code.py` | A file with known problems, used to test the tool |
| `test_audit.py` | Automated tests that check the tool works correctly |
| `requirements.txt` | List of packages needed to run the tool |
| `.env.example` | A template showing what your `.env` file should look like |
| `TASK2_PATH_A.md` | Notes on the backup/fallback system |
| `TASK2_PATH_B_change_plan.md` | A plan for how a team could start using this tool |
| `TASK3_user_stories_and_process_map.md` | User stories and a diagram of how data flows through the system |
| `TASK4_aws_architecture.md` | How this tool could be hosted on AWS |
| `executive_summary.pdf` | A simple, one-page summary of the audit results, written for a non-technical reader |

---

## Task 5 – My Answers

### 1. AI Workflows & Daily Habits
I use Claude for most of my coding work, GitHub Copilot for quick suggestions
inside my editor, and NotebookLM to turn my study notes into visual summaries
that are easier to remember. For everyday research, quick questions, and
writing emails, I switch between Claude, ChatGPT, and Gemini depending on
what feels best for the task. Before I submit anything AI helped with, I
re-read it carefully, run and test it myself, ask the AI to explain its own
logic, ask follow-up questions if something looks off, and sometimes check
it against the official documentation.

### 2. Role Alignment
I'd prefer a 60/40 split, leaning more toward hands-on coding and cloud work
over my first 6 months. Since I'm still early in my career, I'd like a bit
more time on the business side too, so I can figure out where my strengths
really fit before narrowing my focus. Working on this case study showed me
I enjoy the technical side more, but I still want to stay open to the
consulting side.

### 3. Handling Ambiguity
During my internship, I built a chatbot to help with PeoTV error support.
At first, it wasn't clear which error messages or types the bot needed to
handle. To sort this out, I first talked to my supervisor to understand
what was expected, then spoke with the PeoTV engineers to learn the actual
technical details of the errors, and finally went back to my supervisor to
confirm everything before starting the build. Going back and forth like this
meant I wasn't just guessing — I built the right thing the first time.

### 4. Remote Discipline & Communication
When I get stuck on something, I first try to solve it myself for a short
amount of time rather than asking right away. But I don't let it drag on
too long either — if I'm still stuck, I message my team lead before it
becomes urgent, explaining what I already tried, what I think the problem
might be, and what I need help with. If I can, I keep working on something
else while I wait for a reply, instead of just sitting idle.
