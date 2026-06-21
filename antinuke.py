import re
import discord
from discord.ext import commands


def parse_duration(text: str):
    """Parses '10m', '2h', '1d' etc into seconds. Returns None if invalid."""
    match = re.fullmatch(r"(\d+)\s*([smhd])", text.strip().lower())
    if not match:
        return None
    amount, unit = match.groups()
    amount = int(amount)
    multiplier = {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]
    return amount * multiplier


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        await member.ban(reason=reason)
        embed = discord.Embed(
            title="🔨 Member Banned",
            description=f"{member.mention} was banned.\n**Reason:** {reason}",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)

    @commands.command(name="unban")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unban(self, ctx, user_id: int):
        try:
            user = await self.bot.fetch_user(user_id)
            await ctx.guild.unban(user)
            await ctx.send(f"✅ Unbanned **{user}**.")
        except discord.NotFound:
            await ctx.send("❌ That user isn't banned or doesn't exist.")

    @commands.command(name="mute", aliases=["timeout"])
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def mute(self, ctx, member: discord.Member, duration: str = "10m", *, reason: str = "No reason provided"):
        seconds = parse_duration(duration)
        if seconds is None:
            await ctx.send("❌ Invalid duration. Use formats like `10m`, `2h`, `1d`.")
            return
        seconds = min(seconds, 28 * 86400)  # discord max timeout is 28 days
        until = discord.utils.utcnow() + discord.utils.timedelta(seconds=seconds)
        await member.timeout(until, reason=reason)
        embed = discord.Embed(
            title="🔇 Member Muted",
            description=f"{member.mention} was muted for **{duration}**.\n**Reason:** {reason}",
            color=discord.Color.orange(),
        )
        await ctx.send(embed=embed)

    @commands.command(name="unmute")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def unmute(self, ctx, member: discord.Member):
        await member.timeout(None, reason=f"Unmuted by {ctx.author}")
        await ctx.send(f"✅ {member.mention} has been unmuted.")

    @commands.group(name="role", invoke_without_command=True)
    async def role(self, ctx):
        await ctx.send(f"Use `{ctx.prefix}role add @user @role` or `{ctx.prefix}role remove @user @role`.")

    @role.command(name="add")
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def role_add(self, ctx, member: discord.Member, role: discord.Role):
        await member.add_roles(role, reason=f"Added by {ctx.author}")
        await ctx.send(f"✅ Gave {role.mention} to {member.mention}.")

    @role.command(name="remove")
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def role_remove(self, ctx, member: discord.Member, role: discord.Role):
        await member.remove_roles(role, reason=f"Removed by {ctx.author}")
        await ctx.send(f"✅ Removed {role.mention} from {member.mention}.")

    @commands.command(name="promote")
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def promote(self, ctx, member: discord.Member, role: discord.Role):
        await member.add_roles(role, reason=f"Promoted by {ctx.author}")
        embed = discord.Embed(
            description=f"⬆️ {member.mention} has been promoted to {role.mention}!",
            color=discord.Color.green(),
        )
        await ctx.send(embed=embed)

    @commands.command(name="demote")
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def demote(self, ctx, member: discord.Member, role: discord.Role):
        await member.remove_roles(role, reason=f"Demoted by {ctx.author}")
        embed = discord.Embed(
            description=f"⬇️ {member.mention} has been demoted from {role.mention}.",
            color=discord.Color.dark_orange(),
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Moderation(bot))
