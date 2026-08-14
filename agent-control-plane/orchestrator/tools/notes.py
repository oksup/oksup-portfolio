"""
Note tools. Backed by plain markdown files on disk.

Stand-in for Outline. Swap the file I/O for outline-cli calls later; the
schemas do not change.
"""

import os
import re

from config import NOTES_DIR
from tools.base import tool


def _slug(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s or "untitled"


def _path(title: str) -> str:
    os.makedirs(NOTES_DIR, exist_ok=True)
    return os.path.join(NOTES_DIR, f"{_slug(title)}.md")


@tool(
    name="write_note",
    description="Create or overwrite a markdown note in the wiki.",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "body": {"type": "string", "description": "Full markdown body."},
        },
        "required": ["title", "body"],
    },
)
def write_note(title: str, body: str) -> str:
    path = _path(title)
    existed = os.path.exists(path)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(f"# {title}\n\n{body.strip()}\n")
    return f"{'Updated' if existed else 'Created'} note '{title}' ({len(body)} chars)."


@tool(
    name="list_notes",
    description="List every note in the wiki.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def list_notes() -> str:
    os.makedirs(NOTES_DIR, exist_ok=True)
    files = sorted(f for f in os.listdir(NOTES_DIR) if f.endswith(".md"))
    if not files:
        return "No notes yet."
    return "\n".join(f[:-3] for f in files)


@tool(
    name="read_note",
    description="Read the full contents of one note by title.",
    parameters={
        "type": "object",
        "properties": {"title": {"type": "string"}},
        "required": ["title"],
    },
)
def read_note(title: str) -> str:
    path = _path(title)
    if not os.path.exists(path):
        return f"No note called '{title}'. Use list_notes to see what exists."
    with open(path, encoding="utf-8") as fh:
        return fh.read()
