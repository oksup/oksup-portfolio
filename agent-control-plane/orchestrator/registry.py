"""
Channel scoping. This is the security boundary AND the single biggest lever
on tool-calling accuracy with a cheap model.

A model choosing between 4 tools is far more reliable than one choosing
between 30. Keep each channel's list short. If a channel needs more than about
8 tools, that is a sign it should be split into two channels.

Two enforcement layers on purpose:
  1. Tools not listed here are never put in the model's schema list.
  2. tools.base.execute() rejects them again at call time, in case the model
     hallucinates a name it saw earlier in the conversation.
"""

# Lets this file use modern type-hint syntax on older Pythons (3.7+).
from __future__ import annotations

import tools  # noqa: F401 - side effect: populates the registry
from tools.base import REGISTRY

# channel name (without the #) -> tool names available there
CHANNEL_TOOLS: dict[str, list[str]] = {
    "tasks": [
        "plan_work",
        "create_task",
        "list_tasks",
        "set_due_date",
        "complete_task",
        "delete_task",
        "spend_report",
    ],
    "wiki": ["write_note", "list_notes", "read_note"],
    "creatives": ["write_ad_copy", "write_social_post", "image_prompt"],
    "seo": ["keyword_map", "write_metadata", "queue_seo_page"],
    "payments": [
        "record_payment",
        "list_payments",
        "revenue_summary",
        "deliver_report",
        "email_status",
    ],
    "code": [
        "plan_work",
        "run_queue",
        "stop_queue",
        "work_next_task",
        "assign_coding_task",
        "list_jobs",
        "ship_job",
        "rewind",
    ],
    # Add channels as you build them. A channel not listed gets zero tools and
    # the agent is a plain chat assistant there.
}

# Which model role each channel uses.
# Anything that writes code or spends money belongs on "smart".
CHANNEL_MODEL: dict[str, str] = {
    "tasks": "fast",
    "wiki": "fast",
    "code": "smart",
    # Customer-facing wording. Flash-Lite writes stiff, translated-sounding
    # Bahasa, and this copy is the product's first impression.
    "creatives": "smart",
    # Structural output against a fixed format. Cheap model is fine.
    "seo": "fast",
    # Touches money and sends email to real people.
    "payments": "smart",
}

# Channels that exist as notification sinks only. They get no tools: alerts
# arrive by webhook from Vercel or Sentry, and a channel with no tools cannot
# be used to reach anything. Listed here so it is clear the omission is
# deliberate rather than forgotten.
NOTIFICATION_ONLY = ["deployments", "alerts"]

# Per-channel worked examples appended to the system prompt.
#
# One or two concrete examples is the cheapest accuracy win available on a
# small model. Show the ambiguous cases, not the obvious ones.
CHANNEL_HINTS: dict[str, str] = {
    "tasks": """
Examples for this channel (assume today is Saturday 2026-07-25):
- "plan phase B" / "work out what's needed for the payment flow" -> plan_work(goal="<their words>")
- "add a task to fix the signup bug" -> create_task(title="Fix the signup bug")
- "add a task to send the invoice by friday" -> create_task(title="Send the invoice", due_date="2026-07-31")
- "add a task to call the bank besok" -> create_task(title="Call the bank", due_date="2026-07-26")
- "what's left?" -> list_tasks(status="open")
- "show finished ones too" -> list_tasks(status="all")
- "what's late?" -> list_tasks(status="overdue")
- "push task 3 to next monday" -> set_due_date(task_id=3, due_date="2026-08-03")
- "task 3 has no deadline anymore" -> set_due_date(task_id=3, due_date="")
- "2 is done" -> complete_task(task_id=2)
- "delete task 2 for good" -> delete_task(task_id=2, confirm=true)
- "remind me what a good task looks like" -> no tool, just answer.
Never pass a word like "friday" as a date. Always convert it to YYYY-MM-DD.
""",
    "wiki": """
Examples for this channel:
- "save a note called Pricing with the tiers we agreed" -> write_note(title="Pricing", body="...")
- "what do we have written down?" -> list_notes()
- "pull up the pricing note" -> read_note(title="Pricing")
- "add a task for this" -> no tool. Tell them that belongs in #tasks.
""",
    "creatives": """
Examples for this channel:
- "write me some ads for brides" -> write_ad_copy(audience="brides")
- "5 ad options, lead with speed" -> write_ad_copy(audience="<their words>", angle="speed", count=5)
- "caption for instagram about kondangan outfits" -> write_social_post(topic="kondangan outfits", platform="instagram")
- "tiktok script for the quiz" -> write_social_post(topic="the quiz", platform="tiktok")
- "image ideas for the landing page hero" -> image_prompt(subject="landing page hero")
- "run this ad" / "set the budget" -> no tool. Say that spending is done by hand in the ad account.
Never put a price in copy. If they ask for one, say prices are set elsewhere.
""",
    "seo": """
Examples for this channel:
- "keywords for wedding guest outfits" -> keyword_map(topic="wedding guest outfits")
- "map out 10 pages for kondangan" -> keyword_map(topic="kondangan", pages=10)
- "title and description for the quiz page" -> write_metadata(page="the quiz page", keyword="<their keyword>")
- "build a page for baju kondangan wanita" -> queue_seo_page(keyword="baju kondangan wanita", page="<what it covers>")
- "how much traffic does that get?" -> no tool. Say you cannot know volume and it needs a real keyword tool.
Never state a search volume or difficulty score. You do not know them.
""",
    "payments": """
Examples for this channel:
- "budi@gmail.com paid" -> record_payment(email="budi@gmail.com")
- "got 39000 from sari@mail.com ref BCA1234" -> record_payment(email="sari@mail.com", amount_idr=39000, reference="BCA1234")
- "who is waiting?" -> list_payments(undelivered_only=true)
- "how much this month?" -> revenue_summary(days=30)
- "send budi his report" -> deliver_report(...) only if you have the report content. If you do not, ask for it first.
- "is email working?" -> email_status()
Never deliver a report to an address with no payment on record.
""",
    "code": """
Examples for this channel:
- "plan phase B then build it" -> plan_work(goal="phase B"), then run_queue(confirm=true)
- "run everything" / "do the whole queue" / "build it all automatically" -> run_queue(confirm=true)
- "next" / "do the next one" -> work_next_task()
- "stop" -> stop_queue()
- "rewind autopilot-0725-2130" / "undo that run" -> rewind(tag="autopilot-0725-2130", confirm=true)
- "the quiz should be 8 separate screens instead of one long page" -> assign_coding_task(job="<their exact words>")
- "on my phone the Next button does nothing after uploading" -> assign_coding_task(job="<their exact words>")
- "what's waiting?" -> list_jobs()
- "ship agent/add-quiz-0725-1430" -> ship_job(branch="agent/add-quiz-0725-1430", confirm=true)
- "how long will this take?" -> no tool, just answer.

Pass the user's own description of the problem into `job` almost unchanged.
Do not translate it into technical instructions; the coding agent reads the
codebase itself and will do better with the symptom than with your guess at
the cause. Only ever ship a branch when the user has clearly said to.
""",
}


def tools_for_channel(channel: str) -> list:
    names = CHANNEL_TOOLS.get(channel, [])
    return [REGISTRY[n] for n in names if n in REGISTRY]


def allowed_names(channel: str) -> set[str]:
    return set(CHANNEL_TOOLS.get(channel, []))


def model_for_channel(channel: str) -> str:
    return CHANNEL_MODEL.get(channel, "fast")


def hints_for_channel(channel: str) -> str:
    return CHANNEL_HINTS.get(channel, "")
