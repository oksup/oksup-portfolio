"""
SEO tooling for the #seo channel.

Honest limit, stated up front: there is no keyword volume API wired in here,
and a model does not know search volume. It will happily invent a number that
looks plausible. So these tools produce keyword MAPS, page BRIEFS and
METADATA, with volume left blank for you to fill from a real tool.

That split is deliberate. The judgement half is where the model helps. The
data half is where it lies.

`page_brief` writes output in the same shape the coding agent expects, so an
SEO page can go straight into the build queue from here.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime

from config import DATA_DIR
from llm import chat
from tools import tasks as task_store
from tools.base import tool
from tools.plan import FORBIDDEN, _read_specs

log = logging.getLogger("seo")

SEO_DIR = os.path.join(DATA_DIR, "seo")

SEO_SYSTEM = """You are an SEO strategist working on an Indonesian consumer
website. The site is in Bahasa Indonesia and competes against English-first
products that do not serve this market in-language. That language gap is the
whole opportunity.

Rules:
- Never state a search volume, difficulty score or traffic estimate. You do
  not know them. Write "?" and let a human fill it in from a real tool.
- Every page must have exactly one primary keyword. Two pages competing for
  the same keyword is cannibalisation and it costs rankings.
- Bahasa Indonesia keywords as people actually type them, including the
  informal spellings.
- Content must be server-rendered and indexable. Never propose anything that
  only appears after a click or a script runs.
- No emojis. No em-dashes.
"""


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:50] or "untitled"


def _save(kind: str, label: str, body: str) -> str:
    try:
        os.makedirs(SEO_DIR, exist_ok=True)
        path = os.path.join(SEO_DIR, f"{datetime.now():%m%d-%H%M}-{kind}-{_slug(label)}.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(f"# {kind}: {label}\n\n{body}\n")
        return path
    except OSError as exc:
        log.warning("could not save: %s", exc)
        return ""


def _ask(role: str, instruction: str, with_specs: bool = True) -> str:
    content = instruction
    if with_specs:
        content = f"Product context:\n{_read_specs()[:12000]}\n\n---\n\n{instruction}"
    response = chat(role, [{"role": "system", "content": SEO_SYSTEM},
                           {"role": "user", "content": content}], channel="seo")
    return (response.choices[0].message.content or "").strip()


@tool(
    name="keyword_map",
    description=(
        "Build a keyword map for a topic: primary keyword per page, supporting terms, "
        "and search intent. Volume columns are left blank on purpose."
    ),
    parameters={
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "The topic or product area."},
            "pages": {"type": "integer", "description": "How many pages to map. Default 6, max 15."},
        },
        "required": ["topic"],
    },
)
def keyword_map(topic: str, pages: int = 6) -> str:
    n = max(1, min(int(pages or 6), 15))
    body = _ask(
        "fast",
        f"Build a keyword map for: {topic}.\n"
        f"Cover {n} pages. Output a markdown table with columns: "
        "Page | Primary keyword | Intent | Supporting terms | Volume | Difficulty.\n"
        "Put ? in Volume and Difficulty for every row. Below the table, flag in one "
        "line any two rows at risk of competing for the same query.",
    )
    if not body:
        return "ERROR: the model returned nothing."
    path = _save("keywords", topic, body)
    return body + (f"\n\nSaved: {os.path.basename(path)}" if path else "")


@tool(
    name="write_metadata",
    description="Write title tag, meta description and URL slug for one page.",
    parameters={
        "type": "object",
        "properties": {
            "page": {"type": "string", "description": "What the page is about."},
            "keyword": {"type": "string", "description": "The primary keyword for this page."},
        },
        "required": ["page", "keyword"],
    },
)
def write_metadata(page: str, keyword: str) -> str:
    body = _ask(
        "fast",
        f"Page: {page}\nPrimary keyword: {keyword}\n\n"
        "Give exactly these four lines and nothing else:\n"
        "Title: (max 60 characters, keyword near the front)\n"
        "Description: (max 155 characters, one clear reason to click)\n"
        "Slug: (lowercase, hyphens, no stop words)\n"
        "H1: (different wording from the title, same intent)",
    )
    return body or "ERROR: the model returned nothing."


@tool(
    name="queue_seo_page",
    description=(
        "Write a build job for one SEO landing page and put it in the queue for the "
        "coding agent. Use after you have a keyword for the page."
    ),
    parameters={
        "type": "object",
        "properties": {
            "keyword": {"type": "string", "description": "The primary keyword this page targets."},
            "page": {"type": "string", "description": "What the page should cover."},
        },
        "required": ["keyword", "page"],
    },
)
def queue_seo_page(keyword: str, page: str) -> str:
    body = _ask(
        "smart",
        f"Write ONE build job for a coding agent to create a landing page.\n"
        f"Primary keyword: {keyword}\nPage covers: {page}\n\n"
        "Rules for the job text:\n"
        "- Plain language. Say WHAT to build, never HOW to code it. No file names, "
        "no framework or library instructions.\n"
        "- Write out every piece of Bahasa Indonesia copy in full: the H1, each "
        "section heading, and the body text. The agent must never invent wording.\n"
        "- Include the title tag and meta description verbatim.\n"
        "- Phone first.\n"
        "- One page only. Nothing about payment, pricing or accounts.\n"
        "Reply with the job text alone, no preamble and no headings.",
    )
    if not body:
        return "ERROR: the model returned nothing."

    # Same safety layer the planner uses. An SEO page has no business touching
    # money or secrets, and a prompt saying so is not a guarantee.
    match = FORBIDDEN.search(f"{keyword} {page} {body}")
    if match:
        path = _save("held-page", keyword, body)
        return (
            f"HELD: this job mentions '{match.group(0)}', so it is not going in the queue.\n"
            f"Written to {os.path.basename(path)} for you to handle by hand."
        )

    title = f"SEO page: {keyword}"[:60]
    existing = task_store.find_by_title(title)
    if existing:
        return f"Already queued as task #{existing}. Nothing added."

    task_id = task_store.add(title, body)
    _save("page", keyword, body)
    return (
        f"Queued as task #{task_id}: {title}\n"
        f"It will build next time you say `next` or `run everything` in #code."
    )
