import random
import string
import discord
from discord.ext import commands
from utils import storage


def get_settings():
    return storage.load("guild_settings", {})


def save_settings(data):
    storage.save("guild_settings", data)


def get_guild(data, guild_id):
    gid = str(guild_id)
    if gid not in data:
        data[gid] = {}
    return data[gid]


def get_boost_counts():
    return storage.load("boost_counts", {})


def save_boost_counts(data):
    storage.save("boost_counts", data)


def get_keys():
    return storage.load("boost_keys", {})


def save_keys(data):
    storage.save("boost_keys", data)


def generate_key():
    return "-".join(
        "".join(random.choices(string.ascii_uppercase + string.digits, k=4)) for _ in range(3)
    )


def perk_for_count(perks: dict, count: int):
    """Given perk tiers like {'1':5,'2':12,'3':15,'5':100}, return reward for
    the highest tier the user's boost count satisfies."""
    best = 0
    for tier_str, reward in perks.items():
        try:
            tier = int(tier_str)
        except ValueError:
            continue
        if count >= tier and reward > best:
            best = reward
    return best


class Boost(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_channel(self, guild, key):
        data = get_settings()
        g = get_guild(data, guild.id)
        cid = g.get(key)
        return guild.get_channel(int(cid)) if cid else None

    async def handle_boost(self, member: discord.Member):
        guild = member.guild
        counts = get_boost_counts()
        gid = str(guild.id)
        uid = str(member.id)
        counts.setdefault(gid, {})
        counts[gid][uid] = counts[gid].get(uid, 0) + 1
        save_boost_counts(counts)
        total_boosts = counts[gid][uid]

        perks = self.bot.config.get("boost_perks", {})
        reward = perk_for_count(perks, total_boosts)

        key = generate_key()
        keys = get_keys()
        total_uses = self.bot.config.get("key_uses", 5)
        keys[key] = {
            "guild_id": guild.id,
            "user_id": member.id,
            "boost_count": total_boosts,
            "assets": reward,
            "total_uses": total_uses,
            "uses_left": total_uses,
        }
        save_keys(keys)

        # Announcement embed in the boost channel
        boost_channel = await self.get_channel(guild, "boost_channel")
        if boost_channel:
            embed = discord.Embed(
                description=f"Hey {member.mention} we left you a little surprise! check the dm!!",
                color=discord.Color.fuchsia(),
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            try:
                await boost_channel.send(embed=embed)
            except discord.Forbidden:
                pass

        # Log the key
        boost_log_channel = await self.get_channel(guild, "boost_log_channel")
        if boost_log_channel:
            log_embed = discord.Embed(
                title="🔑 New Boost Key Issued",
                description=(
                    f"**User:** {member} ({member.id})\n"
                    f"**Total boosts:** {total_boosts}\n"
                    f"**Assets earned:** {reward}\n"
                    f"**Key:** `{key}`"
                ),
                color=discord.Color.purple(),
            )
            try:
                await boost_log_channel.send(embed=log_embed)
            except discord.Forbidden:
                pass

        # DM the booster
        dm_embed = discord.Embed(
            title="🎉 Thank You For Boosting!",
            description=(
                f"Thank you so much for boosting **{guild.name}**! 💜\n\n"
                f"Here is your personal key:\n```{key}```\n"
                f"You can redeem it with `.redeem {key}` to unlock access to channels "
                f"where you can request free assets. This key has **{total_uses} uses** — "
                f"check remaining uses anytime with `.sin check key {key}`.\n\n"
                f"**Your boost perks:**\n"
                f"You currently have **{total_boosts}** total boost(s) and have earned "
                f"**{reward} free assets**.\n\n"
                f"**Boost perk tiers:**\n"
                f"1 boost = 5 free assets\n"
                f"2 boosts = 12 free assets\n"
                f"3 boosts = 15 free assets\n"
                f"5 boosts = 100 free assets"
            ),
            color=discord.Color.fuchsia(),
        )
        try:
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        # Detect a new boost: member went from not-boosting to boosting.
        if before.premium_since is None and after.premium_since is not None:
            await self.handle_boost(after)

    @commands.command(name="serverboost")
    @commands.has_permissions(administrator=True)
    async def serverboost(self, ctx, action: str = None, boost_count: int = 1):
        if action != "test":
            await ctx.send(f"Usage: `{ctx.prefix}serverboost test [boost_count]`")
            return
        # Simulate the boost flow for the command invoker without requiring a real boost.
        member = ctx.author
        guild = ctx.guild
        perks = self.bot.config.get("boost_perks", {})
        reward = perk_for_count(perks, boost_count)
        key = generate_key()
        keys = get_keys()
        total_uses = self.bot.config.get("key_uses", 5)
        keys[key] = {
            "guild_id": guild.id,
            "user_id": member.id,
            "boost_count": boost_count,
            "assets": reward,
            "total_uses": total_uses,
            "uses_left": total_uses,
        }
        save_keys(keys)

        boost_channel = await self.get_channel(guild, "boost_channel") or ctx.channel
        embed = discord.Embed(
            description=f"Hey {member.mention} we left you a little surprise! check the dm!!",
            color=discord.Color.fuchsia(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await boost_channel.send(embed=embed)

        dm_embed = discord.Embed(
            title="🎉 Thank You For Boosting! (TEST)",
            description=(
                f"Thank you so much for boosting **{guild.name}**! 💜\n\n"
                f"Here is your personal key:\n```{key}```\n"
                f"You can redeem it with `.redeem {key}` to unlock access to channels "
                f"where you can request free assets. This key has **{total_uses} uses** — "
                f"check remaining uses anytime with `.sin check key {key}`.\n\n"
                f"**Simulated boost count:** {boost_count}\n"
                f"**Assets earned:** {reward}\n\n"
                f"**Boost perk tiers:**\n"
                f"1 boost = 5 free assets\n"
                f"2 boosts = 12 free assets\n"
                f"3 boosts = 15 free assets\n"
                f"5 boosts = 100 free assets"
            ),
            color=discord.Color.fuchsia(),
        )
        try:
            await member.send(embed=dm_embed)
            await ctx.send("✅ Test complete — check your DMs and the boost channel.")
        except discord.Forbidden:
            await ctx.send("⚠️ Test embed sent in channel, but I couldn't DM you (check your privacy settings).")

    @commands.command(name="redeem")
    async def redeem(self, ctx, key: str):
        keys = get_keys()
        key = key.strip().upper()
        entry = keys.get(key)

        if not entry:
            embed = discord.Embed(
                title="❌ Invalid Key",
                description="That key doesn't exist or has expired.",
                color=discord.Color.red(),
            )
            embed.timestamp = discord.utils.utcnow()
            await ctx.send(embed=embed)
            return

        if entry["guild_id"] != ctx.guild.id:
            embed = discord.Embed(
                title="❌ Invalid Key",
                description="This key isn't valid in this server.",
                color=discord.Color.red(),
            )
            embed.timestamp = discord.utils.utcnow()
            await ctx.send(embed=embed)
            return

        if entry["user_id"] != ctx.author.id:
            embed = discord.Embed(
                title="❌ Invalid Key",
                description="This key doesn't belong to you.",
                color=discord.Color.red(),
            )
            embed.timestamp = discord.utils.utcnow()
            await ctx.send(embed=embed)
            return

        if entry.get("uses_left", 0) <= 0:
            embed = discord.Embed(
                title="❌ Key Exhausted",
                description=f"`{key}` has no uses left. It was redeemable {entry.get('total_uses', 0)} time(s).",
                color=discord.Color.red(),
            )
            embed.timestamp = discord.utils.utcnow()
            await ctx.send(embed=embed)
            return

        data = get_settings()
        g = get_guild(data, ctx.guild.id)
        role_id = g.get("asset_role")
        if not role_id:
            await ctx.send(f"⚠️ No asset role has been configured yet. Ask an admin to run `{ctx.prefix}sin assetrole @role`.")
            return
        role = ctx.guild.get_role(int(role_id))
        if not role:
            await ctx.send("⚠️ The configured asset role no longer exists. Contact an admin.")
            return

        if role not in ctx.author.roles:
            try:
                await ctx.author.add_roles(role, reason="Redeemed boost key")
            except discord.Forbidden:
                await ctx.send("❌ I don't have permission to give you that role.")
                return

        entry["uses_left"] -= 1
        keys[key] = entry
        save_keys(keys)

        embed = discord.Embed(
            title="✅ Key Redeemed",
            description=(
                f"Your key `{key}` has been redeemed successfully.\n\n"
                f"You now have {role.mention} and can request your "
                f"**{entry['assets']}** free assets.\n\n"
                f"**Remaining uses on this key:** {entry['uses_left']}"
            ),
            color=discord.Color.green(),
        )
        embed.set_footer(text=f"Requested by {ctx.author}")
        embed.timestamp = discord.utils.utcnow()
        await ctx.send(embed=embed)

    async def _check_key(self, ctx, key: str):
        """Shared logic for `.sin check key <key>`."""
        keys = get_keys()
        key = key.strip().upper()
        entry = keys.get(key)
        if not entry or entry["guild_id"] != ctx.guild.id:
            await ctx.send("❌ Not a valid key.")
            return
        uses_left = entry.get("uses_left", 0)
        if uses_left <= 0:
            await ctx.send(f"❌ Key `{key}` is valid but has **0 uses left** (exhausted).")
            return
        await ctx.send(f"✅ Key valid — remaining uses: **{uses_left}**")


async def setup(bot):
    await bot.add_cog(Boost(bot))
