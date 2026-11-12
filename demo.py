"""Runs the test questions and saves the real logged steps to example_runs.md (for the README)."""
from agent import run, build_agent

CASES = [
    ("1. No tool needed", "What is an API? Answer in one sentence."),
    ("2. Calculator tool", "What is 48,372 x 9,184 + 2^20?"),
    ("3. Search tool", "What is the latest stable version of Python?"),
    ("4. Multi-step (search, then calculate)",
     "Find the height of Mount Everest and of the Burj Khalifa in metres, then calculate how many "
     "times taller Everest is, rounded to 2 decimals."),
    ("5. Tool failure (division by zero)", "Use the calculator to compute 100 / (5 - 5) and explain the result."),
]

if __name__ == "__main__":
    agent = build_agent()
    out = ["# Example runs", "", "Raw logs from `demo.py` (unedited).", ""]
    for title, q in CASES:
        print("\n" + "=" * 70 + "\n" + title)
        _, steps = run(q, agent=agent)
        out += [f"## {title}", "", "```", *steps, "```", ""]
    open("example_runs.md", "w", encoding="utf-8").write("\n".join(out))
    print("\nSaved example_runs.md")