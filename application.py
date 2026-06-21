import discord
from discord.ext import commands
from utils import storage

COMMAND_INFO = {
    "ban": "Bans a member from the server.",
    "unban": "Unbans a user by ID.",
    "mute": "Times out (mutes) a member for a given duration (e.g. 10m, 2h, 1d).",
    "timeout": "Alias of mute — times out a member.",
    "unmute": "Removes an active timeout from a member.",
    "role add": "Gives a role to a member.",
    "role remove": "Removes a role from a member.",
    "promote": "Promotes a member by giving them a role.",
    "demote": "Demotes a member by removing a role.",
    "antinuke": "Shows current antinuke status.",
    "antinuke enable": "Turns antinuke protection ON for this server.",
    "antinuke disable": "Turns antinuke protection OFF for this server.",
    "antinuke logs": "Sets the channel where antinuke logs are sent.",
    "boostchannel": "Sets the channel where boost announcement embeds are posted.",
    "boostlogs": "Sets the channel where boost keys get logged.",
    "assetrole": "Sets the role given to members who redeem a boost key.",
    "serverboost test": "Sends a test boost embed + DM to you.",
    "redeem": "Redeems a boost key for asset-request access (key has multiple uses).",
    "check key": "Checks if a key is valid and how many uses it has left.",
    "application role set": "Sets the role auto-given to members who are 30+ days old and have 500+ messages.",
}


def get_settings():
    return storage.load("guild_settings", {})


def save_settings(data):
    storage.save("guild_settings", data)


def get_guild(data, guild_id):
    gid = str(guild_id)
    if gid not in data:
        data[gid] = {}
    return data[gid]


class Sin(commands.Cog):
    """Owns the entire `.sin` command tree (help, credits, antinuke settings, boost settings)."""

    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="sin", invoke_without_command=True)
    async def sin(self, ctx, *, command_name: str = None):
        """`.sin` -> full command list. `.sin <command>` -> credit info for that command."""
        if command_name:
            key = command_name.lower().strip()
            if key in COMMAND_INFO:
                creator = self.bot.config.get("creator_name", "Unknown")
                embed = discord.Embed(
                    title=f"ℹ️ Command: {self.bot.config.get('prefix', '.')}{key}",
                    description=COMMAND_INFO[key],
                    color=discord.Color.blurple(),
                )
                embed.add_field(name="Credit", value=f"This command was created by **{creator}**.")
                await ctx.send(embed=embed)
            else:
                await ctx.send(
                    f"❌ No command called `{command_name}` found. Use `{self.bot.config.get('prefix','.')}sin` "
                    f"to see all commands."
                )
            return

        prefix = self.bot.config.get("prefix", ".")
        embed = discord.Embed(
            title="📜 All Commands",
            description=f"Prefix: `{prefix}`\nUse `{prefix}sin <command name>` to see who created a command and what it does.",
            color=discord.Color.gold(),
        )
        embed.add_field(
            name="🔨 Moderation",
            value=(
                f"`{prefix}ban @user [reason]`\n"
                f"`{prefix}unban <user_id>`\n"
                f"`{prefix}mute @user <duration> [reason]`\n"
                f"`{prefix}unmute @user`\n"
                f"`{prefix}role add @user @role`\n"
                f"`{prefix}role remove @user @role`\n"
                f"`{prefix}promote @user @role`\n"
                f"`{prefix}demote @user @role`"
            ),
            inline=False,
        )
        embed.add_field(
            name="🛡️ Antinuke",
            value=(
                f"`{prefix}sin antinuke` - check status\n"
                f"`{prefix}sin antinuke enable`\n"
                f"`{prefix}sin antinuke disable`\n"
                f"`{prefix}sin antinuke logs #channel`\n"
                f"Also blocks @everyone/@here/mass mentions automatically (delete + 10 min timeout) when enabled."
            ),
            inline=False,
        )
        embed.add_field(
            name="🤬 Antimod (Swear Filter)",
            value="Auto-deletes messages with blocked words and DMs the server owner. Edit `config.json` -> `swear_words` to customize.",
            inline=False,
        )
        embed.add_field(
            name="🚀 Boosts",
            value=(
                f"`{prefix}sin boostchannel #channel` - where the boost embed is posted\n"
                f"`{prefix}sin boostlogs #channel` - where boost keys get logged\n"
                f"`{prefix}sin assetrole @role` - role given on redeem\n"
                f"`{prefix}sin check key <key>` - check if a key is valid + uses left\n"
                f"`{prefix}serverboost test` - test the boost flow\n"
                f"`{prefix}redeem <key>` - redeem your boost key (multi-use)"
            ),
            inline=False,
        )
        embed.add_field(
            name="📋 Applications / Auto-role",
            value=f"`{prefix}application role set @role` - auto-gives this role to members 30+ days old with 500+ messages",
            inline=False,
        )
        embed.set_footer(text=f"Credits via {prefix}sin <command>")
        await ctx.send(embed=embed)

    # ---------------- antinuke settings ----------------

    @sin.group(name="antinuke", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def antinuke(self, ctx):
        data = get_settings()
        g = get_guild(data, ctx.guild.id)
        enabled = g.get("antinuke_enabled", False)
        await ctx.send(
            f"🛡️ Antinuke is currently **{'ENABLED' if enabled else 'DISABLED'}**.\n"
            f"Use `{ctx.prefix}sin antinuke enable`, `{ctx.prefix}sin antinuke disable`, "
            f"or `{ctx.prefix}sin antinuke logs #channel`."
        )

    @antinuke.command(name="enable")
    @commands.has_permissions(administrator=True)
    async def antinuke_enable(self, ctx):
        data = get_settings()
        g = get_guild(data, ctx.guild.id)
        g["antinuke_enabled"] = True
        save_settings(data)
        await ctx.send("✅ Antinuke protection has been **enabled**.")

    @antinuke.command(name="disable")
    @commands.has_permissions(administrator=True)
    async def antinuke_disable(self, ctx):
        data = get_settings()
        g = get_guild(data, ctx.guild.id)
        g["antinuke_enabled"] = False
        save_settings(data)
        await ctx.send("✅ Antinuke protection has been **disabled**.")

    @antinuke.command(name="logs")
    @commands.has_permissions(administrator=True)
    async def antinuke_logs(self, ctx, channel: discord.TextChannel):
        data = get_settings()
        g = get_guild(data, ctx.guild.id)
        g["antinuke_log_channel"] = channel.id
        save_settings(data)
        await ctx.send(f"✅ Antinuke logs will now be sent to {channel.mention}.")

    # ---------------- boost settings ----------------

    @sin.command(name="boostchannel")
    @commands.has_permissions(administrator=True)
    async def boostchannel(self, ctx, channel: discord.TextChannel):
        data = get_settings()
        g = get_guild(data, ctx.guild.id)
        g["boost_channel"] = channel.id
        save_settings(data)
        await ctx.send(f"✅ Boost announcements will be posted in {channel.mention}.")

    @sin.command(name="boostlogs")
    @commands.has_permissions(administrator=True)
    async def boostlogs(self, ctx, channel: discord.TextChannel):
        data = get_settings()
        g = get_guild(data, ctx.guild.id)
        g["boost_log_channel"] = channel.id
        save_settings(data)
        await ctx.send(f"✅ Boost keys will be logged in {channel.mention}.")

    @sin.command(name="assetrole")
    @commands.has_permissions(administrator=True)
    async def assetrole(self, ctx, role: discord.Role):
        data = get_settings()
        g = get_guild(data, ctx.guild.id)
        g["asset_role"] = role.id
        save_settings(data)
        await ctx.send(f"✅ Members who redeem a boost key will now receive {role.mention}.")

    # ---------------- key check ----------------

    @sin.group(name="check", invoke_without_command=True)
    async def check(self, ctx):
        await ctx.send(f"Use `{ctx.prefix}sin check key <key>`.")

    @check.command(name="key")
    async def check_key(self, ctx, key: str):
        boost_cog = self.bot.get_cog("Boost")
        if not boost_cog:
            await ctx.send("⚠️ Boost system isn't loaded.")
            return
        await boost_cog._check_key(ctx, key)


async def setup(bot):
    await bot.add_cog(Sin(bot))
