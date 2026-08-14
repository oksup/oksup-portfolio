"""
What the bot is costing you.

Reads data/costs.csv, which llm.py appends to on every model call. Estimates
only: they use the price table in config.py, not a billing API. Close enough
to catch a runaway loop, not close enough to reconcile an invoice.
"""

from __future__ import annotations

import costs
from tools.base import tool


@tool(
    name="spend_report",
    description=(
        "Estimated model spend, broken down by channel and model, with a monthly run "
        "rate. Use when asked what this is costing."
    ),
    parameters={
        "type": "object",
        "properties": {
            "days": {"type": "integer", "description": "Look back this many days. Default 30."}
        },
        "required": [],
    },
)
def spend_report(days: int = 30) -> str:
    return costs.summary(max(1, min(int(days or 30), 365)))
