import re
import discord
from discord.ext import commands
from utils import storage


def get_message_counts():
    return storage.load("message_counts", {})


def save_message_counts(data):
    storage.save("message_counts", data)


def build_word_pattern(words):
    escaped = [re.escape(w) for w in words if w.strip()]
    if not escaped:
        return None
    return re.compile(r"\b(" + "|".join(escaped) + r")\b", re.IGNORECASE)


class Antimod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        words = bot.config.get("swear_words", [])
        self.pattern = build_word_pattern(words)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # ---- message counting (used by .application role set) ----
        counts = get_message_counts()
        gid = str(message.guild.id)
        uid = str(message.author.id)
        counts.setdefault(gid, {})
        counts[gid][uid] = counts[gid].get(uid, 0) + 1
        save_message_counts(counts)

        # ---- swear filter ----
        if self.pattern and self.pattern.search(message.content):
            matched = self.pattern.search(message.content).group(0)
            try:
                await message.delete()
            except (discord.Forbidden, discord.NotFound):
                pass

            owner = message.guild.owner
            if owner is None:
                try:
                    owner = await message.guild.fetch_member(message.guild.owner_id)
                except Exception:
                    owner = None

            if owner:
                embed = discord.Embed(
                    title="🤬 Swear Word Deleted",
                    description=(
                        f"**Server:** {message.guild.name}\n"
                        f"**Channel:** {message.channel.mention}\n"
                        f"**User:** {message.author} ({message.author.id})\n"
                        f"**Flagged word:** `{matched}`\n"
                        f"**Original message:** {message.content}"
                    ),
                    color=discord.Color.red(),
                )
                try:
                    await owner.send(embed=embed)
                except discord.Forbidden:
                    pass


async def setup(bot):
    await bot.add_cog(Antimod(bot))
