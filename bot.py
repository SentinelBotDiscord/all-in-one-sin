import asyncio
import json
import logging
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from utils import storage  # noqa: F401 — ensure utils/storage is importable for cogs

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("bot")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

with open(CONFIG_PATH, "r") as _f:
    config: dict = json.load(_f)

PREFIX = config.get("prefix", ".")

# ---------------------------------------------------------------------------
# Cogs to load (file name without .py extension)
# ---------------------------------------------------------------------------

COGS = [
    "antimod",
    "antinuke",
    "application",
    "moderation",
    "sin",
]

# ---------------------------------------------------------------------------
# Bot setup
# ---------------------------------------------------------------------------

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)
bot.config = config  # expose config to all cogs via bot.config


@bot.event
async def on_ready():
    log.info("Logged in as %s (ID: %s)", bot.user, bot.user.id)
    log.info("Connected to %d guild(s)", len(bot.guilds))
    log.info("Prefix: %s", PREFIX)


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        await bot.process_commands(message)
        return

    # Track per-guild message counts for the application eligibility cog.
    counts = storage.load("message_counts", {})
    gid = str(message.guild.id)
    uid = str(message.author.id)
    counts.setdefault(gid, {})
    counts[gid][uid] = counts[gid].get(uid, 0) + 1
    storage.save("message_counts", counts)

    await bot.process_commands(message)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    token = os.environ.get("DISCORD_TOKEN") or os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "No bot token found. Set the DISCORD_TOKEN environment variable."
        )

    async with bot:
        for cog in COGS:
            try:
                await bot.load_extension(cog)
                log.info("Loaded cog: %s", cog)
            except Exception as exc:
                log.error("Failed to load cog %s: %s", cog, exc)

        await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
