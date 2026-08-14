"""
The agent loop. Deliberately has no Discord in it, so the eval harness can
drive the exact same code path the bot uses.

Loop:
  1. build the message list
  2. ask the model
  3. if it asked for tools, run them and feed the results back
  4. repeat until it replies with text, or MAX_STEPS is hit
"""

# Lets this file use modern type-hint syntax on older Pythons (3.7+).
from __future__ import annotations

import logging
from datetime import date

from config import MAX_STEPS, SYSTEM_PROMPT
from llm import chat
from registry import allowed_names, hints_for_channel, model_for_channel, tools_for_channel
from tools.base import execute

log = logging.getLogger("agent")


def run_agent(channel: str, user_message: str, history: list | None = None) -> tuple[str, list]:
    """
    Returns (final_text, calls_made) where calls_made is a list of
    (tool_name, arguments_json) in the order they ran.
    """
    tool_specs = tools_for_channel(channel)
    schemas = [t.schema() for t in tool_specs]
    allowed = allowed_names(channel)
    role = model_for_channel(channel)

    # Computed per call, not at import. A bot left running for a week would
    # otherwise still think it is the day you started it.
    today = date.today().strftime("%A %Y-%m-%d")

    system = SYSTEM_PROMPT.format(
        channel=channel, hints=hints_for_channel(channel), today=today
    )
    messages = [{"role": "system", "content": system}]
    messages.extend(history or [])
    messages.append({"role": "user", "content": user_message})

    calls_made: list[tuple[str, str]] = []

    for step in range(MAX_STEPS):
        response = chat(role, messages, schemas or None, channel=channel)
        msg = response.choices[0].message
        calls = msg.tool_calls or []

        # Append the assistant turn explicitly rather than dumping the SDK
        # object, so the shape stays identical across providers.
        entry: dict = {"role": "assistant", "content": msg.content or ""}
        if calls:
            entry["tool_calls"] = [
                {
                    "id": c.id,
                    "type": "function",
                    "function": {"name": c.function.name, "arguments": c.function.arguments},
                }
                for c in calls
            ]
        messages.append(entry)

        if not calls:
            return (msg.content or "(no reply)"), calls_made

        for call in calls:
            name = call.function.name
            raw_args = call.function.arguments
            calls_made.append((name, raw_args))
            result = execute(name, raw_args, allowed)
            log.info("step %d: %s -> %s", step, name, result[:120])
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": name,
                    "content": result,
                }
            )

    return f"Stopped after {MAX_STEPS} tool rounds without a final answer.", calls_made
