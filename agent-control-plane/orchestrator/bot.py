"""
Discord front end. Thin on purpose: read a message, hand it to the agent,
post the reply. All the thinking lives in agent.py.

Run with:  python bot.py
"""

# Lets this file use modern type-hint syntax on older Pythons (3.7+).
from __future__ import annotations

import asyncio
import logging
import os

import discord
from dotenv import load_dotenv

from agent import run_agent
from config import HISTORY_LIMIT, MODELS, PROVIDER
from tools import code as code_tools

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)-8s %(levelname)-5s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("bot")

DISCORD_CHAR_LIMIT = 2000

intents = discord.Intents.default()
intents.message_content = True  # requires the Message Content Intent in the dev portal
client = discord.Client(intents=intents)


async def recent_history(channel, exclude_id: int) -> list:
    """Last few messages in the channel, oldest first, as OpenAI-format turns."""
    turns = []
    async for m in channel.history(limit=HISTORY_LIMIT + 1):
        if m.id == exclude_id or not m.content:
            continue
        turns.append(
            {"role": "assistant" if m.author == client.user else "user", "content": m.content}
        )
    return list(reversed(turns))


def chunk(text: str) -> list[str]:
    """Discord rejects messages over 2000 characters."""
    return [text[i : i + DISCORD_CHAR_LIMIT] for i in range(0, len(text), DISCORD_CHAR_LIMIT)] or [
        "(empty)"
    ]


@client.event
async def on_ready():
    log.info("connected as %s | provider=%s | models=%s", client.user, PROVIDER, MODELS)

    # Coding jobs run in a background thread for several minutes. This lets
    # them post their result back into the channel when they finish.
    loop = asyncio.get_running_loop()

    def reporter(channel_name: str, text: str) -> None:
        channel = discord.utils.get(client.get_all_channels(), name=channel_name)
        if channel is None:
            log.warning("no #%s channel to report into", channel_name)
            return
        for part in chunk(text):
            asyncio.run_coroutine_threadsafe(channel.send(part), loop)

    code_tools.set_reporter(reporter)


@client.event
async def on_message(message: discord.Message):
    if message.author == client.user or message.author.bot:
        return
    if not message.content.strip():
        return

    channel_name = getattr(message.channel, "name", "direct")
    log.info("#%s <%s> %s", channel_name, message.author, message.content[:120])

    async with message.channel.typing():
        try:
            history = await recent_history(message.channel, message.id)
            # to_thread keeps the bot responsive: without it, one slow model
            # call freezes every other channel until it finishes.
            reply, calls = await asyncio.to_thread(
                run_agent, channel_name, message.content, history
            )
            if calls:
                log.info("tools used: %s", ", ".join(name for name, _ in calls))
        except Exception as exc:  # noqa: BLE001
            log.exception("agent failed")
            reply = f"Agent error: {exc}"

    for part in chunk(reply):
        await message.channel.send(part)


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise SystemExit("DISCORD_TOKEN missing. Copy .env.example to .env and fill it in.")
    client.run(token, log_handler=None)
