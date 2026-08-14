"""
Task tools. Backed by a local SQLite file for now.

This is the stand-in for Plane. When you are ready to self-host Plane, the
only thing that changes is the body of these functions: swap the SQL for
run_cli(["plane-cli", ...]). The schemas, the channel scoping, and everything
in bot.py stay identical. That is the whole point of the wrapper pattern.

Note on dates: these tools only ever accept YYYY-MM-DD. Working out that
"friday" means 2026-07-31 is the model's job, not the tool's. Keep the fuzzy
part in the prompt and the exact part in the code, never the other way round.
"""

# Lets this file use modern type-hint syntax on older Pythons (3.7+).
from __future__ import annotations

import os
import sqlite3
from datetime import date, datetime

from config import DATA_DIR, DB_PATH
from tools.base import tool


def _conn():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS tasks (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               title TEXT NOT NULL,
               notes TEXT DEFAULT '',
               status TEXT NOT NULL DEFAULT 'open',
               created_at TEXT NOT NULL DEFAULT (datetime('now'))
           )"""
    )
    # Add the due_date column to databases created before this feature existed.
    # Safe to run every time: we check first, so your existing tasks survive.
    existing = {row[1] for row in conn.execute("PRAGMA table_info(tasks)")}
    if "due_date" not in existing:
        conn.execute("ALTER TABLE tasks ADD COLUMN due_date TEXT")
    # Links a task to the branch the coding agent built for it.
    if "branch" not in existing:
        conn.execute("ALTER TABLE tasks ADD COLUMN branch TEXT")
    return conn


# ---------------------------------------------------------------------------
# Plain helpers (not tools). Used by the #code channel to pull work from the
# tracker, so a task can go from written down to built without retyping it.
# ---------------------------------------------------------------------------


def next_open_task():
    """Oldest open task that has not already been built. Returns (id, title, notes) or None."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT id, title, notes FROM tasks "
            "WHERE status = 'open' AND (branch IS NULL OR branch = '') "
            "ORDER BY id LIMIT 1"
        ).fetchone()
    return row


def attach_branch(task_id: int, branch: str) -> None:
    with _conn() as conn:
        conn.execute("UPDATE tasks SET branch = ? WHERE id = ?", (branch, task_id))


def clear_branch(task_id: int) -> None:
    """Called when a job fails, so the task goes back in the queue."""
    with _conn() as conn:
        conn.execute("UPDATE tasks SET branch = NULL WHERE id = ?", (task_id,))


def complete_by_branch(branch: str):
    """Marks the task done once its branch is shipped. Returns the task id or None."""
    with _conn() as conn:
        row = conn.execute("SELECT id FROM tasks WHERE branch = ?", (branch,)).fetchone()
        if not row:
            return None
        conn.execute("UPDATE tasks SET status = 'done' WHERE id = ?", (row[0],))
        return row[0]


def open_count() -> int:
    with _conn() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE status = 'open'"
        ).fetchone()[0]


def find_by_title(title: str):
    """Task id for an exact title, or None. Keeps queueing tools idempotent."""
    with _conn() as conn:
        row = conn.execute("SELECT id FROM tasks WHERE title = ? LIMIT 1", (title,)).fetchone()
    return row[0] if row else None


def add(title: str, notes: str = "") -> int:
    """Insert a task and return its id. For tools that queue work programmatically."""
    with _conn() as conn:
        cursor = conn.execute(
            "INSERT INTO tasks (title, notes) VALUES (?, ?)", (title, notes)
        )
        return cursor.lastrowid


def _check_date(value: str) -> str | None:
    """Returns an error message if the date is not a real YYYY-MM-DD date."""
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return (
            f"ERROR: '{value}' is not a valid date. "
            "Use YYYY-MM-DD, for example 2026-07-31."
        )
    return None


def _format(row) -> str:
    task_id, title, status, due = row
    line = f"#{task_id} [{status}] {title}"
    if due:
        if status == "open" and due < date.today().isoformat():
            line += f"  (OVERDUE, was due {due})"
        else:
            line += f"  (due {due})"
    return line


@tool(
    name="create_task",
    description="Create a new task in the tracker. Returns the new task id.",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Short imperative title."},
            "notes": {"type": "string", "description": "Optional detail or acceptance criteria."},
            "due_date": {
                "type": "string",
                "description": (
                    "Optional deadline in YYYY-MM-DD form only. Work out the real "
                    "calendar date from what the user said before calling this. "
                    "Omit entirely if no deadline was mentioned."
                ),
            },
        },
        "required": ["title"],
    },
)
def create_task(title: str, notes: str = "", due_date: str = "") -> str:
    if due_date:
        problem = _check_date(due_date)
        if problem:
            return problem

    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO tasks (title, notes, due_date) VALUES (?, ?, ?)",
            (title.strip(), notes.strip(), due_date or None),
        )
    suffix = f", due {due_date}" if due_date else ""
    return f"Created task #{cur.lastrowid}: {title.strip()}{suffix}"


@tool(
    name="list_tasks",
    description=(
        "List tasks in the tracker. Use status='overdue' to show only open tasks "
        "whose deadline has already passed."
    ),
    parameters={
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["open", "done", "overdue", "all"],
                "description": "Defaults to open.",
            }
        },
        "required": [],
    },
)
def list_tasks(status: str = "open") -> str:
    today = date.today().isoformat()
    base = "SELECT id, title, status, due_date FROM tasks"

    with _conn() as conn:
        if status == "all":
            rows = conn.execute(f"{base} ORDER BY id").fetchall()
        elif status == "overdue":
            rows = conn.execute(
                f"{base} WHERE status = 'open' AND due_date IS NOT NULL "
                "AND due_date < ? ORDER BY due_date",
                (today,),
            ).fetchall()
        else:
            rows = conn.execute(
                f"{base} WHERE status = ? ORDER BY COALESCE(due_date, '9999'), id", (status,)
            ).fetchall()

    if not rows:
        return "Nothing overdue." if status == "overdue" else f"No tasks with status '{status}'."
    return "\n".join(_format(r) for r in rows)


@tool(
    name="set_due_date",
    description=(
        "Set, change or clear the deadline on a task that already exists. "
        "To clear a deadline, pass an empty due_date."
    ),
    parameters={
        "type": "object",
        "properties": {
            "task_id": {"type": "integer"},
            "due_date": {
                "type": "string",
                "description": (
                    "Deadline in YYYY-MM-DD form only, or empty string to remove "
                    "the deadline. Work out the real calendar date first."
                ),
            },
        },
        "required": ["task_id", "due_date"],
    },
)
def set_due_date(task_id: int, due_date: str = "") -> str:
    if due_date:
        problem = _check_date(due_date)
        if problem:
            return problem

    with _conn() as conn:
        cur = conn.execute(
            "UPDATE tasks SET due_date = ? WHERE id = ?", (due_date or None, task_id)
        )
        if cur.rowcount == 0:
            return f"No task #{task_id}."
    return (
        f"Task #{task_id} is now due {due_date}."
        if due_date
        else f"Deadline removed from task #{task_id}."
    )


@tool(
    name="complete_task",
    description="Mark a task as done.",
    parameters={
        "type": "object",
        "properties": {"task_id": {"type": "integer", "description": "The task id."}},
        "required": ["task_id"],
    },
)
def complete_task(task_id: int) -> str:
    with _conn() as conn:
        cur = conn.execute("UPDATE tasks SET status = 'done' WHERE id = ?", (task_id,))
        if cur.rowcount == 0:
            return f"No task #{task_id}."
    return f"Task #{task_id} marked done."


@tool(
    name="delete_task",
    description=(
        "Permanently delete a task. Destructive. Requires confirm=true, and you may "
        "only set confirm=true when the user explicitly asked to delete it."
    ),
    parameters={
        "type": "object",
        "properties": {
            "task_id": {"type": "integer"},
            "confirm": {"type": "boolean", "description": "Must be true to proceed."},
        },
        "required": ["task_id", "confirm"],
    },
    high_impact=True,
)
def delete_task(task_id: int, confirm: bool = False) -> str:
    with _conn() as conn:
        cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        if cur.rowcount == 0:
            return f"No task #{task_id}."
    return f"Task #{task_id} deleted."
