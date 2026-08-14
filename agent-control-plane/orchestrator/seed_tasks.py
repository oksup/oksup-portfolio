"""
Loads a job queue written in markdown into the task tracker, in one go.

Reads headings like `### A1. Landing page` and the fenced code block under
each one, then creates a task per job. The heading becomes the title, the
code block becomes the job description the coding agent receives.

Usage:
    python seed_tasks.py                        # loads the Style Report queue
    python seed_tasks.py path/to/other.md
    python seed_tasks.py --list                 # show what is queued already
"""

from __future__ import annotations

import os
import re
import sys

from config import DB_PATH  # noqa: F401  (import triggers .env load)
from tools.tasks import _conn

DEFAULT_QUEUE = os.path.expanduser(
    "~/Documents/Cowork OS/Personal Projects/Style Report/Job_Queue.md"
)

# `### A1. Landing page` followed later by a ```fenced block```
JOB_RE = re.compile(
    r"^###\s+(?P<code>[A-Z]\d+)\.\s+(?P<title>.+?)\s*$.*?^```\s*$(?P<body>.*?)^```\s*$",
    re.MULTILINE | re.DOTALL,
)


def parse(path: str) -> list[tuple[str, str]]:
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    jobs = []
    for m in JOB_RE.finditer(text):
        title = f"{m.group('code')}. {m.group('title')}"
        body = m.group("body").strip()
        if body:
            jobs.append((title, body))
    return jobs


def show_queue() -> None:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, title, status, branch FROM tasks ORDER BY id"
        ).fetchall()
    if not rows:
        print("Queue is empty.")
        return
    for task_id, title, status, branch in rows:
        mark = "done" if status == "done" else ("building" if branch else "open")
        print(f"  #{task_id:<3} [{mark:^8}] {title}")


def main() -> int:
    args = [a for a in sys.argv[1:]]
    if "--list" in args:
        show_queue()
        return 0

    path = args[0] if args else DEFAULT_QUEUE
    if not os.path.exists(path):
        print(f"No file at {path}")
        return 1

    jobs = parse(path)
    if not jobs:
        print(f"Found no jobs in {path}. Expected '### A1. Title' headings with code blocks.")
        return 1

    with _conn() as conn:
        existing = {r[0] for r in conn.execute("SELECT title FROM tasks")}
        added = 0
        for title, body in jobs:
            if title in existing:
                print(f"  skip (already queued)  {title}")
                continue
            conn.execute(
                "INSERT INTO tasks (title, notes) VALUES (?, ?)", (title, body)
            )
            print(f"  added                  {title}")
            added += 1

    print(f"\n{added} task(s) added. In Discord #code, say: next\n")
    show_queue()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
