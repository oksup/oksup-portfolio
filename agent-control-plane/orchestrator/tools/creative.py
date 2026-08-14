"""
Marketing copy generation for the #creatives channel.

Output is written to data/creatives/ as well as returned, because Discord
scrollback is not a filing system and you will want the good version later.

These tools produce copy, never spend. Nothing here can create an ad, set a
budget, or touch an ad account. That stays manual on purpose.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime

from config import DATA_DIR
from llm import chat
from tools.base import tool
from tools.plan import _read_specs

log = logging.getLogger("creative")

CREATIVE_DIR = os.path.join(DATA_DIR, "creatives")

VOICE = """You write marketing copy for an Indonesian consumer product.

Rules, all hard:
- Bahasa Indonesia unless told otherwise. Natural, spoken Indonesian, the way
  someone actually talks. Not translated English, not formal press-release
  Indonesian.
- No emojis. No em-dashes.
- Concrete over clever. Say what the thing does for the reader.
- Never promise a result you cannot deliver. No "pasti", no "dijamin".
- Never mention a price, a discount, or a payment method. Those are set by a
  human elsewhere and copy that names a price goes stale the day it changes.
"""


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "untitled"


def _save(kind: str, label: str, body: str) -> str:
    """Returns the path written, or an empty string. Never raises."""
    try:
        os.makedirs(CREATIVE_DIR, exist_ok=True)
        name = f"{datetime.now():%m%d-%H%M}-{kind}-{_slug(label)}.md"
        path = os.path.join(CREATIVE_DIR, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(f"# {kind}: {label}\n\n{body}\n")
        return path
    except OSError as exc:
        log.warning("could not save creative: %s", exc)
        return ""


def _generate(role: str, instruction: str, label: str, kind: str) -> str:
    messages = [
        {"role": "system", "content": VOICE},
        {
            "role": "user",
            "content": (
                f"Product context:\n{_read_specs()[:12000]}\n\n"
                f"---\n\nTask:\n{instruction}"
            ),
        },
    ]
    response = chat(role, messages, channel="creatives")
    body = (response.choices[0].message.content or "").strip()
    if not body:
        return "ERROR: the model returned nothing. Try describing the audience more specifically."
    path = _save(kind, label, body)
    footer = f"\n\nSaved: {os.path.basename(path)}" if path else ""
    return body + footer


@tool(
    name="write_ad_copy",
    description=(
        "Write ad copy variations for a campaign. Returns several options to choose from. "
        "Does not create or spend on any ad."
    ),
    parameters={
        "type": "object",
        "properties": {
            "audience": {
                "type": "string",
                "description": "Who this is aimed at, in the user's own words.",
            },
            "angle": {
                "type": "string",
                "description": "Optional: the hook or benefit to lead with.",
            },
            "count": {"type": "integer", "description": "How many variations. Default 5, max 10."},
        },
        "required": ["audience"],
    },
)
def write_ad_copy(audience: str, angle: str = "", count: int = 5) -> str:
    n = max(1, min(int(count or 5), 10))
    instruction = (
        f"Write {n} ad copy variations aimed at: {audience}.\n"
        + (f"Lead with this angle: {angle}.\n" if angle else "")
        + "For each: a headline of at most 40 characters, a body of at most 90 "
        "characters, and a 2 to 4 word call to action. Number them. Make them "
        "genuinely different from each other, not the same sentence reworded."
    )
    return _generate("smart", instruction, audience, "ad")


@tool(
    name="write_social_post",
    description="Write a social post for one platform. Does not publish anything.",
    parameters={
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "What the post is about."},
            "platform": {
                "type": "string",
                "description": "instagram, tiktok, twitter, or linkedin.",
            },
        },
        "required": ["topic"],
    },
)
def write_social_post(topic: str, platform: str = "instagram") -> str:
    shape = {
        "instagram": "A caption of 3 to 5 short lines, then 5 hashtags on their own line.",
        "tiktok": "A spoken script of about 20 seconds, written as it would be said out loud, with a hook in the first 3 seconds.",
        "twitter": "One post under 280 characters. No hashtags.",
        "linkedin": "4 to 6 short paragraphs, first line as the hook, no hashtags.",
    }.get(platform.lower(), "A caption of 3 to 5 short lines.")
    instruction = f"Write one {platform} post about: {topic}.\nFormat: {shape}"
    return _generate("smart", instruction, f"{platform}-{topic}", "social")


@tool(
    name="image_prompt",
    description=(
        "Write prompts for an image generator, for a visual you describe. Returns text "
        "prompts only. Generates no image and spends nothing."
    ),
    parameters={
        "type": "object",
        "properties": {
            "subject": {"type": "string", "description": "What the image should show."},
            "count": {"type": "integer", "description": "How many prompts. Default 3, max 6."},
        },
        "required": ["subject"],
    },
)
def image_prompt(subject: str, count: int = 3) -> str:
    n = max(1, min(int(count or 3), 6))
    instruction = (
        f"Write {n} image generation prompts for: {subject}.\n"
        "Write the prompts in English, they go to an image model. Each one must "
        "specify subject, setting, lighting, camera framing and mood. Indonesian "
        "context where people appear: real Indonesian faces and clothing, not a "
        "generic stock look. Never name a living artist or a brand."
    )
    return _generate("smart", instruction, subject, "imgprompt")
