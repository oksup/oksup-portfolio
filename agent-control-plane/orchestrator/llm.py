"""
The single door to any LLM.

Every model call goes through chat(). That is what makes a provider swap a
config edit instead of a rewrite.
"""

# Lets this file use modern type-hint syntax on older Pythons (3.7+).
from __future__ import annotations

import logging

import litellm

import costs
from config import FORCE_ROLE, MODELS, NUM_RETRIES

log = logging.getLogger("llm")

litellm.suppress_debug_info = True
litellm.drop_params = True  # silently drop params a given provider does not support


def chat(role: str, messages: list, tools: list | None = None, channel: str = "-"):
    """
    role    : "fast" or "smart" (see config.MODELS)
    messages: OpenAI-format message list
    tools   : OpenAI-format tool schema list, or None
    channel : only used to attribute cost. Never affects the call.

    LiteLLM normalises Anthropic's `tools` format and Gemini's
    `function_declarations` format into one shape, so nothing above this
    function ever knows which provider is active.
    """
    effective = FORCE_ROLE or role
    model = MODELS[effective]

    kwargs = {
        "model": model,
        "messages": messages,
        # Deterministic. Tool selection should not be a dice roll, and it makes
        # your evals reproducible.
        "temperature": 0,
        "num_retries": NUM_RETRIES,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    log.info("%s | %d msgs | %d tools", model, len(messages), len(tools or []))
    response = litellm.completion(**kwargs)

    # Cost accounting. Wrapped because a missing usage field on some provider
    # must never turn a working reply into an exception.
    try:
        usage = getattr(response, "usage", None)
        if usage is not None:
            usd = costs.record(
                channel,
                effective,
                model,
                int(getattr(usage, "prompt_tokens", 0) or 0),
                int(getattr(usage, "completion_tokens", 0) or 0),
            )
            log.info("cost $%.5f", usd)
    except Exception as exc:  # noqa: BLE001
        log.warning("cost accounting skipped: %s", exc)

    return response
