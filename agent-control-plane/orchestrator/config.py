"""
Central config. This is the ONLY file that names a model.

Swapping providers or models is an edit here and nothing else.
Never import google.genai or anthropic anywhere in this project.
"""

import os

from dotenv import load_dotenv

# Load .env HERE, before anything below reads a setting.
#
# This module is imported by bot.py, agent.py and the tools, and Python runs
# imports before the rest of a file. If .env is only loaded further down in
# bot.py, every os.getenv() call below has already run and returned nothing.
# Settings with defaults hide the problem; settings without one come back empty.
#
# Absolute path so it works no matter which folder you run from.
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

# ---------------------------------------------------------------------------
# Provider and model roles.
#
# "fast"  = high-frequency work: parsing, classifying, simple tool calls.
# "smart" = anything that writes code, spends money, or is annoying to undo.
#
# LiteLLM model-string format is "<provider>/<model>".
# ---------------------------------------------------------------------------

PROVIDER = os.getenv("LLM_PROVIDER", "gemini")

MODELS_BY_PROVIDER = {
    # Verified 2026-07-25. Google retires old model IDs for new API keys with
    # no warning, so if you get a 404 saying a model "is no longer available
    # to new users", run: python list_models.py
    "gemini": {
        # $0.30 / $2.50 per million tokens in / out
        "fast": "gemini/gemini-3.5-flash-lite",
        # $1.50 / $7.50 per million tokens in / out
        "smart": "gemini/gemini-3.6-flash",
    },
    "anthropic": {
        "fast": "anthropic/claude-haiku-4-5-20251001",
        "smart": "anthropic/claude-sonnet-5",
    },
}

MODELS = MODELS_BY_PROVIDER[PROVIDER]

# ---------------------------------------------------------------------------
# PHASE 1 DEBUG SWITCH.
#
# Set FORCE_ROLE=smart in .env while you are still building. Every channel then
# uses the strong model, so any misbehaviour is your schema or your prompt,
# never the model being too weak. Once your evals pass, unset it and let the
# per-channel routing in registry.py take over.
# ---------------------------------------------------------------------------
FORCE_ROLE = os.getenv("FORCE_ROLE") or None

# Max tool-call rounds per user message. Stops runaway loops burning tokens.
MAX_STEPS = 6

# Retries for transient provider errors (rate limits, 5xx). LiteLLM backs off.
NUM_RETRIES = 3

# Hard timeout for any tool that shells out to a subprocess.
TOOL_TIMEOUT_SECONDS = 30

# How many previous channel messages to feed as context.
HISTORY_LIMIT = 8

# Where the stub backends write. Override with DATA_DIR in .env if you ever run
# from a network drive or cloud-synced folder, where SQLite cannot take a lock.
DATA_DIR = os.getenv("DATA_DIR") or os.path.join(os.path.dirname(__file__), "data")

# ---------------------------------------------------------------------------
# Coding agent (#code channel)
# ---------------------------------------------------------------------------

# The repo the agent is allowed to touch. It gets write access here and
# nowhere else, so this folder should contain that project and nothing more.
PROJECT_REPO = os.path.expanduser(os.getenv("PROJECT_REPO", "~/dev/style-report"))

# How to invoke the coding agent. {prompt_file} is replaced with a path to a
# file holding the job description, which avoids all shell-quoting problems.
# Run `python check_agent.py` to find the form that works on your machine.
CODING_AGENT_CMD = os.getenv("CODING_AGENT_CMD", "")

# How to tell the agent which folder to work in. `agy` has no flag for this,
# and with no workspace set it silently writes into its own scratch folder, so
# the instruction has to carry the path. check_agent.py finds which phrasing
# works and prints the value to put here.
AGENT_PROMPT_STYLE = os.getenv("AGENT_PROMPT_STYLE", "path")

PROMPT_STYLES = {
    "plain": "{job}",
    "path": (
        "Work inside the git repository at {repo}.\n"
        "Every file you create or edit must be inside that folder.\n\n{job}"
    ),
    "adddir": "/add-dir {repo}\n\n{job}",
    "abspath": (
        "Work in {repo}. Use absolute paths starting with {repo} for every "
        "file you create or edit. Do not use a scratch folder.\n\n{job}"
    ),
}

# Coding runs take minutes, not seconds. Separate from TOOL_TIMEOUT_SECONDS.
CODING_TIMEOUT_SECONDS = int(os.getenv("CODING_TIMEOUT_SECONDS", "900"))

# Command that proves the code still works. Must exit non-zero on failure.
# For Next.js, `npm run build` also runs the TypeScript check.
BUILD_CMD = os.getenv("BUILD_CMD", "npm run build")

# How many times the agent may try to fix its own broken build before giving
# up and telling you. Past three it is guessing, not reasoning.
MAX_FIX_ATTEMPTS = int(os.getenv("MAX_FIX_ATTEMPTS", "3"))

# The branch the agent must never commit to directly.
MAIN_BRANCH = os.getenv("MAIN_BRANCH", "main")

# ---------------------------------------------------------------------------
# Cost tracking.
#
# USD per MILLION tokens, input / output. Update when Google changes pricing.
# Only used for the running spend estimate: nothing here affects a model call.
# ---------------------------------------------------------------------------
PRICES_PER_MTOK = {
    "gemini/gemini-3.5-flash-lite": (0.30, 2.50),
    "gemini/gemini-3.6-flash": (1.50, 7.50),
    "anthropic/claude-haiku-4-5-20251001": (1.00, 5.00),
    "anthropic/claude-sonnet-5": (3.00, 15.00),
}

# Append-only CSV. One row per model call.
COST_LOG_PATH = os.path.join(DATA_DIR, "costs.csv")
COST_LOG_ENABLED = os.getenv("COST_LOG_ENABLED", "1") != "0"

# ---------------------------------------------------------------------------
# Protected paths.
#
# Autopilot merges passing builds into main without review. These path
# patterns are the exception: a job that touched one of them is pushed and a
# PR is opened, but the merge waits for Oka.
#
# This is a second, independent layer from the FORBIDDEN regex in plan.py.
# That one stops such jobs being WRITTEN. This one stops them being MERGED,
# including jobs typed by hand that never went through the planner.
# ---------------------------------------------------------------------------
PROTECTED_PATHS = [
    "*.env*",
    "**/payment*",
    "**/payments/**",
    "**/checkout*",
    "**/qris*",
    "**/xendit*",
    "**/stripe*",
    "**/billing*",
    "**/auth*",
    "**/middleware.*",
    "**/api/webhook*/**",
    "**/pricing*",
    "**/price*",
    "next.config.*",
    "vercel.json",
    "package.json",
]

# ---------------------------------------------------------------------------
# Email delivery (Brevo). Personal account, never the Nakula one.
# Free tier is 300 emails/day, which covers launch.
# ---------------------------------------------------------------------------
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", "")
BREVO_SENDER_NAME = os.getenv("BREVO_SENDER_NAME", "Style Report")

# ---------------------------------------------------------------------------
# Payments. QRIS with manual confirmation, no payment gateway.
#
# Bank Indonesia sets MDR for Usaha Mikro Individu at 0% on transactions of
# Rp 500.000 or less, so a Rp 39.000 ticket costs nothing to collect. A static
# QRIS code cannot notify anything, so payment confirmation is a human step
# until a provider with callbacks is worth the fee.
# ---------------------------------------------------------------------------
PRODUCT_PRICE_IDR = int(os.getenv("PRODUCT_PRICE_IDR", "39000"))
PAYMENTS_DB_PATH = os.path.join(DATA_DIR, "payments.db")

# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------

# Where the product specs live. The planner reads these for context so the
# jobs it writes match what you actually decided, instead of inventing a
# product from the goal sentence alone.
SPEC_DIR = os.path.expanduser(
    os.getenv("SPEC_DIR", "~/Documents/Cowork OS/Personal Projects/Style Report")
)

# Per spec file, to keep the planning prompt a sane size.
SPEC_CHARS_PER_FILE = 6000

# A plan longer than this is a sign the goal was too broad.
MAX_PLAN_JOBS = 10
NOTES_DIR = os.path.join(DATA_DIR, "notes")
DB_PATH = os.path.join(DATA_DIR, "tasks.db")

# ---------------------------------------------------------------------------
# System prompt.
#
# Written for a weaker model on purpose: short, concrete, and it tells the
# model what NOT to do. Vague prompts are where Flash falls apart.
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are the orchestrator for a small autonomous build team.
You are operating in the #{channel} channel.

Today is {today}.
When the user says something like "friday", "besok", "next week" or "end of
month", work out the actual calendar date yourself and pass it to the tool in
YYYY-MM-DD form. Tools never accept vague dates.

How to behave:
- Call a tool rather than describing what you would do.
- You only have this channel's tools. If a request needs a tool you do not
  have, say which channel it belongs in. Never invent a tool.
- Call at most one tool unless the user clearly asked for several things.
- If a tool returns a line starting with ERROR or BLOCKED, read it and either
  fix the arguments or tell the user plainly. Never retry the same call twice.
- Answer in one or two lines. No preamble, no filler, no emojis, no em-dashes.
- For destructive tools you must pass confirm=true, and only when the user
  explicitly asked for the deletion in their latest message.
{hints}"""
