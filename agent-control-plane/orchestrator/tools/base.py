"""
Tool plumbing: registration, JSON schema, the allowlist check, and the
confirm gate for destructive actions.

Design rule: the model never gets a shell. It gets these functions and
nothing else. Every new capability is a new function here, with an explicit
schema, so you always know the full surface area the model can reach.
"""

# Lets this file use modern type-hint syntax on older Pythons (3.7+).
from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass, field
from typing import Callable

from config import TOOL_TIMEOUT_SECONDS

log = logging.getLogger("tools")

REGISTRY: dict[str, "Tool"] = {}


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    fn: Callable
    high_impact: bool = False

    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


def tool(name: str, description: str, parameters: dict, high_impact: bool = False):
    """Decorator that registers a function as a callable tool."""

    def decorator(fn):
        REGISTRY[name] = Tool(name, description, parameters, fn, high_impact)
        return fn

    return decorator


def execute(name: str, raw_args: str, allowed: set[str]) -> str:
    """
    Run one tool call. Returns a string that gets fed back to the model.

    Never raises. A tool blowing up should become a message the model can
    read and react to, not a crashed bot.
    """
    if name not in allowed:
        return f"ERROR: tool '{name}' is not available in this channel."

    spec = REGISTRY.get(name)
    if spec is None:
        return f"ERROR: tool '{name}' does not exist."

    try:
        args = json.loads(raw_args) if raw_args else {}
    except json.JSONDecodeError as exc:
        return f"ERROR: could not parse arguments: {exc}"

    if spec.high_impact and not args.get("confirm"):
        return (
            f"BLOCKED: '{name}' is destructive and requires confirm=true. "
            "Ask the user to confirm in plain language first."
        )

    log.info("executing %s(%s)", name, args)
    try:
        result = spec.fn(**args)
    except TypeError as exc:
        return f"ERROR: bad arguments for '{name}': {exc}"
    except Exception as exc:  # noqa: BLE001 - deliberate catch-all
        log.exception("tool %s failed", name)
        return f"ERROR: '{name}' failed: {exc}"

    return result if isinstance(result, str) else json.dumps(result, default=str)


def run_cli(cmd: list[str]) -> str:
    """
    Helper for tools that shell out to a real CLI later (plane-cli, tea, etc).

    Always non-interactive, always time-limited. Not used by the stub tools,
    but it is here so that when you swap SQLite for real Plane you drop the
    command in and the guardrails already exist.
    """
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=TOOL_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError:
        return f"ERROR: command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return f"ERROR: '{cmd[0]}' timed out after {TOOL_TIMEOUT_SECONDS}s."

    if proc.returncode != 0:
        return f"ERROR (exit {proc.returncode}): {proc.stderr.strip() or proc.stdout.strip()}"
    return proc.stdout.strip() or "OK (no output)"
