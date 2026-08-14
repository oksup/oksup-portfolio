"""
Turns a goal into a queue of correctly-sized jobs, so nobody has to write them.

This is the step that used to be done by hand. You say "plan phase B" and it
reads the product specs, breaks the goal into jobs the coding agent can
actually complete, and puts them in the tracker ready for autopilot.

The hard part is not generating text, it is SIZING. A job that is too big is
the single most common reason an agent produces something vague and wrong. All
the sizing rules live in the prompt below.
"""

from __future__ import annotations

import json
import logging
import os
import re

from config import MAX_PLAN_JOBS, SPEC_CHARS_PER_FILE, SPEC_DIR
from llm import chat
from tools import tasks as task_store
from tools.base import tool

log = logging.getLogger("plan")

PLANNER_PROMPT = """You break a goal into jobs for a coding agent that builds a
website. Each job you write is handed to that agent verbatim, unattended, with
no chance to ask questions.

SIZING IS THE WHOLE JOB. Get this wrong and everything downstream fails.
- One job = one screen, one section, or one specific change. Never more.
- If a job would take a human developer more than about an hour, split it.
- "Build the quiz" is wrong. "Add a page at /quiz with one question and four
  options" is right.
- 4 to {max_jobs} jobs. If the goal needs more, cover only the first part well
  and say so in your note.

WRITING THE JOBS:
- Plain language. Describe WHAT to build and what it should do, never HOW to
  code it. No file names, no framework instructions, no library choices.
- Include exact copy where copy is needed. If the product is in Bahasa
  Indonesia, write the Bahasa strings out in full. Never leave the agent to
  invent wording.
- Each job must be testable by a non-technical person looking at a web page.
- Order matters. Later jobs may rely on earlier ones being finished.
- Mention "phone first" where layout is involved.

NEVER WRITE A JOB THAT:
- sets or handles a price, or touches payment logic
- handles secrets, API keys, or environment files
- deletes user data
Those are done by a human. If the goal needs them, put them in your note instead.

Answer with JSON only, no other text:
{{"note": "<one sentence on what you covered and what you left out>",
  "jobs": [{{"title": "<5-8 word label>", "job": "<the full instruction>"}}]}}
"""


def _read_specs() -> str:
    """Product context, so the planner builds what was decided, not what it imagines."""
    if not os.path.isdir(SPEC_DIR):
        return "(no spec files found)"
    chunks = []
    for name in sorted(os.listdir(SPEC_DIR)):
        if not name.endswith(".md") or name == "MEMORY.md":
            continue
        try:
            with open(os.path.join(SPEC_DIR, name), encoding="utf-8") as fh:
                body = fh.read(SPEC_CHARS_PER_FILE)
        except OSError:
            continue
        chunks.append(f"### {name}\n{body}")
    return "\n\n".join(chunks) or "(no spec files found)"


# Telling the planner not to write these is not enough; models drift. Anything
# matching gets held back for Oka to do by hand, never queued for autopilot.
FORBIDDEN = re.compile(
    r"\b("
    r"price|pricing|harga|payment|pembayaran|checkout|xendit|stripe|invoice|"
    r"refund|api[ _-]?key|secret|credential|token|\.env|environment variable"
    r")\b",
    re.IGNORECASE,
)


def _forbidden_reason(title: str, body: str) -> str | None:
    match = FORBIDDEN.search(f"{title} {body}")
    return match.group(0) if match else None


def _parse(raw: str) -> dict | None:
    """Models like wrapping JSON in code fences. Strip and salvage."""
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None


@tool(
    name="plan_work",
    description=(
        "Break a goal into properly sized jobs and add them to the task queue, "
        "without anyone writing them by hand. Use when the user says 'plan the "
        "next phase', 'work out what needs doing for X', or describes something "
        "big they want built. For a single small change use assign_coding_task."
    ),
    parameters={
        "type": "object",
        "properties": {
            "goal": {
                "type": "string",
                "description": (
                    "What the user wants built, in their own words. Include any "
                    "detail they gave about scope."
                ),
            }
        },
        "required": ["goal"],
    },
)
def plan_work(goal: str) -> str:
    specs = _read_specs()

    messages = [
        {"role": "system", "content": PLANNER_PROMPT.format(max_jobs=MAX_PLAN_JOBS)},
        {
            "role": "user",
            "content": (
                f"Product specs for context:\n\n{specs}\n\n"
                f"---\n\nGoal: {goal}\n\nWrite the jobs."
            ),
        },
    ]

    try:
        # Always the strong model. A bad plan wastes every job that follows it,
        # so this is the wrong place to save money.
        response = chat("smart", messages, channel="plan")
        raw = response.choices[0].message.content or ""
    except Exception as exc:  # noqa: BLE001
        log.exception("planner call failed")
        return f"ERROR: could not plan that: {exc}"

    data = _parse(raw)
    if not data or not isinstance(data.get("jobs"), list) or not data["jobs"]:
        return (
            "ERROR: the planner did not return usable jobs. Try describing the "
            f"goal more concretely.\nIt said:\n{raw[:400]}"
        )

    jobs = data["jobs"][:MAX_PLAN_JOBS]

    with task_store._conn() as conn:
        existing = {r[0] for r in conn.execute("SELECT title FROM tasks")}
        added, held, skipped = [], [], 0
        for item in jobs:
            title = str(item.get("title", "")).strip()
            body = str(item.get("job", "")).strip()
            if not title or not body:
                continue
            if title in existing:
                skipped += 1
                continue
            reason = _forbidden_reason(title, body)
            if reason:
                held.append((title, reason))
                continue
            conn.execute("INSERT INTO tasks (title, notes) VALUES (?, ?)", (title, body))
            added.append(title)

    parts = []
    if added:
        lines = "\n".join(f"  {i}. {t}" for i, t in enumerate(added, 1))
        parts.append(f"Added {len(added)} job(s) to the queue:\n{lines}")
    elif skipped:
        parts.append(f"Nothing new to add; those {skipped} job(s) are already queued.")
    else:
        parts.append("Nothing was queued.")

    if held:
        held_lines = "\n".join(f"  {t}  (mentions '{r}')" for t, r in held)
        parts.append(
            f"\nHeld back for you to do by hand, not queued:\n{held_lines}\n"
            "Anything touching money or secrets is done by a person, not "
            "unattended. Set prices in the Xendit dashboard, never in code."
        )

    note = str(data.get("note", "")).strip()
    if note:
        parts.append(f"\n{note}")

    total = task_store.open_count()
    if added:
        parts.append(f"\n{total} task(s) queued. Say 'run everything' to build them.")
    return "\n".join(parts)
