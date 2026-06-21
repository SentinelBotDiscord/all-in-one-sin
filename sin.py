import time
import discord
from discord.ext import commands
from utils import storage

THRESHOLD = 3       # number of actions
WINDOW_SECONDS = 10  # within this many seconds triggers punishment


def get_settings():
    return storage.load("guild_settings", {})


def save_settings(data):
    storage.save("guild_settings", data)


def get_guild(data, guild_id):
    gid = str(guild_id)
    if gid not in data:
        data[gid] = {}
    return data[gid]


class Antinuke(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # in-memory action tracker: {guild_id: {actor_id: [timestamps]}}
        self.actions = {}

    def is_enabled(self, guild_id):
        data = get_settings()
        g = get_guild(data, guild_id)
        return g.get("antinuke_enabled", False)

    async def get_log_channel(self, guild):
        data = get_settings()
        g = get_guild(data, guild.id)
        channel_id = g.get("antinuke_log_channel")
        if channel_id:
            return guild.get_channel(int(channel_id))
        return None

    async def log_event(self, guild, description, color=discord.Color.red()):
        channel = await self.get_log_channel(guild)
        if channel:
            embed = discord.Embed(title="🛡️ Antinuke Alert", description=description, color=color)
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                pass

    async def record_and_check(self, guild, actor, action_label):
        """Returns True if this actor crossed the threshold and was punished."""
        if not self.is_enabled(guild.id):
            return False
        if actor is None or actor.bot and actor.id == self.bot.user.id:
            return False
        now = time.time()
        g_acts = self.actions.setdefault(guild.id, {})
        timestamps = g_acts.setdefault(actor.id, [])
        timestamps.append(now)
        # keep only timestamps within the window
        timestamps[:] = [t for t in timestamps if now - t <= WINDOW_SECONDS]
        if len(timestamps) >= THRESHOLD:
            timestamps.clear()
            await self.punish(guild, actor, action_label)
            return True
        return False

    async def punish(self, guild, actor, action_label):
        member = guild.get_member(actor.id) if hasattr(actor, "id") else None
        try:
            if member:
                # strip all roles to neutralize permissions, then ban as a hard stop
                await member.ban(reason=f"Antinuke: mass {action_label} detected")
        except discord.Forbidden:
            pass
        except Exception:
            pass
        await self.log_event(
            guild,
            f"🚨 **{actor}** triggered antinuke for mass **{action_label}** "
            f"(≥{THRESHOLD} actions in {WINDOW_SECONDS}s) and has been banned.",
        )

    # ---------- Event listeners ----------

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        guild = channel.guild
        if not self.is_enabled(guild.id):
            return
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
            await self.record_and_check(guild, entry.user, "channel deletion")
            break

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        guild = role.guild
        if not self.is_enabled(guild.id):
            return
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
            await self.record_and_check(guild, entry.user, "role deletion")
            break

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        if not self.is_enabled(guild.id):
            return
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
            await self.record_and_check(guild, entry.user, "member bans")
            break

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        guild = member.guild
        if not self.is_enabled(guild.id):
            return
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
            if entry.target and entry.target.id == member.id:
                await self.record_and_check(guild, entry.user, "member kicks")
            break

    # ---------- Mass mention / role ping protection ----------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if not self.is_enabled(message.guild.id):
            return
        # Admins are exempt so staff can't accidentally lock themselves out
        # with a legitimate @everyone announcement.
        if message.author.guild_permissions.administrator:
            return

        has_mass_mention = (
            message.mention_everyone
            or len(message.role_mentions) > 0
            or len(message.mentions) >= 5
        )
        if not has_mass_mention:
            return

        try:
            await message.delete()
        except (discord.Forbidden, discord.NotFound):
            pass

        member = message.guild.get_member(message.author.id)
        if member:
            try:
                until = discord.utils.utcnow() + discord.utils.timedelta(minutes=10)
                await member.timeout(until, reason="Antinuke: role/mass mention blocked")
            except (discord.Forbidden, discord.HTTPException):
                pass

        embed = discord.Embed(
            title="⚠️ Warning — Role / Mass Mention Blocked",
            description=(
                f"Your message in **{message.guild.name}** was deleted because it contained "
                f"a `@everyone`, `@here`, or role ping.\n\n"
                f"Role and mass mentions are **disabled for all users** in this server.\n"
                f"You have been **timed out for 10 minutes**."
            ),
            color=discord.Color.gold(),
        )
        embed.timestamp = discord.utils.utcnow()
        try:
            await message.author.send(embed=embed)
        except discord.Forbidden:
            pass

        await self.log_event(
            message.guild,
            f"⚠️ **{message.author}** triggered mass-mention protection in {message.channel.mention} "
            f"and was timed out for 10 minutes.",
            color=discord.Color.gold(),
        )

    # Commands for `.sin antinuke ...` live in cogs/sin.py to avoid duplicate
    # `.sin` group registration across cogs. This cog only handles detection.


async def setup(bot):
    await bot.add_cog(Antinuke(bot))
