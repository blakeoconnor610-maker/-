"""Leveling. Talk in chat, earn xp, level up, unlock roles."""

from __future__ import annotations

import logging
import random
import time

import discord
from discord import app_commands
from discord.ext import commands

from core import ui
from core.checks import staff_only

log = logging.getLogger("bot.levels")


def xp_for_next(level: int) -> int:
    """XP needed to get from `level` to `level + 1`."""
    return 5 * (level ** 2) + 50 * level + 100


def total_xp_for(level: int) -> int:
    """Total XP needed to reach `level` from scratch."""
    return sum(xp_for_next(n) for n in range(level))


def level_from_xp(xp: int) -> int:
    level = 0
    while xp >= total_xp_for(level + 1):
        level += 1
        if level > 500:  # sanity stop
            break
    return level


class Levels(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._cooldowns: dict[tuple[int, int], float] = {}

    # ------------------------------------------------------------ xp ----

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None:
            return
        if not isinstance(message.author, discord.Member):
            return
        if message.is_system():
            return

        guild_id = message.guild.id
        config = await self.bot.db.config(guild_id)  # type: ignore[attr-defined]
        if not config.get("levels_enabled", 1):
            return
        if message.channel.id in await self.bot.db.no_xp_channels(guild_id):  # type: ignore[attr-defined]
            return

        key = (guild_id, message.author.id)
        now = time.monotonic()
        cooldown = int(config.get("xp_cooldown") or 60)
        if now - self._cooldowns.get(key, 0.0) < cooldown:
            return
        self._cooldowns[key] = now

        low = int(config.get("xp_min") or 15)
        high = max(low, int(config.get("xp_max") or 25))
        gained = random.randint(low, high)

        row = await self.bot.db.add_xp(guild_id, message.author.id, gained)  # type: ignore[attr-defined]
        new_level = level_from_xp(row["xp"])
        if new_level <= row["level"]:
            return

        await self.bot.db.set_level(guild_id, message.author.id, new_level, row["xp"])  # type: ignore[attr-defined]
        await self._announce(message, new_level, config)

    async def _announce(self, message: discord.Message, level: int, config: dict) -> None:
        guild = message.guild
        assert guild is not None
        member = message.author
        assert isinstance(member, discord.Member)

        rewards = await self._sync_roles(member, level)

        channel_id = config.get("level_channel")
        channel = guild.get_channel(channel_id) if channel_id else None
        if not isinstance(channel, discord.TextChannel):
            channel = message.channel if isinstance(message.channel, discord.TextChannel) else None
        if channel is None:
            return

        text = f"{member.mention} just hit **level {level}**"
        if rewards:
            text += "\n\nunlocked " + ", ".join(role.mention for role in rewards)

        embed = ui.embed("level up", text, color=ui.SUCCESS)
        embed.set_thumbnail(url=member.display_avatar.url)

        me = guild.me
        if me is None or not channel.permissions_for(me).send_messages:
            return
        ping = bool(config.get("level_ping", 1))
        try:
            await channel.send(
                content=member.mention if ping else None,
                embed=embed,
                allowed_mentions=discord.AllowedMentions(users=True),
            )
        except discord.HTTPException:
            pass

    async def _sync_roles(self, member: discord.Member, level: int) -> list[discord.Role]:
        """Give every level role the member has now earned, take back lower ones."""
        rows = await self.bot.db.level_roles(member.guild.id)  # type: ignore[attr-defined]
        if not rows:
            return []
        me = member.guild.me
        if me is None or not me.guild_permissions.manage_roles:
            return []

        earned: list[discord.Role] = []
        newly: list[discord.Role] = []
        stale: list[discord.Role] = []
        for row in rows:
            role = member.guild.get_role(row["role_id"])
            if role is None or role >= me.top_role:
                continue
            if level >= row["level"]:
                earned.append(role)
                if role not in member.roles:
                    newly.append(role)
            elif role in member.roles:
                stale.append(role)

        # Only the highest level role is worth keeping hoisted, but stacking is
        # friendlier - keep them all, just drop ones above the member's level.
        try:
            if newly:
                await member.add_roles(*newly, reason=f"reached level {level}")
            if stale:
                await member.remove_roles(*stale, reason="level roles resynced")
        except discord.HTTPException:
            return []
        return newly

    # ------------------------------------------------------ commands ----

    @app_commands.command(name="rank", description="see your level and xp")
    @app_commands.describe(user="check someone else instead")
    @app_commands.guild_only()
    async def rank(self, interaction: discord.Interaction, user: discord.Member | None = None) -> None:
        member = user or interaction.user
        assert interaction.guild is not None
        row = await self.bot.db.get_level(interaction.guild.id, member.id)  # type: ignore[attr-defined]

        level = row["level"]
        xp = row["xp"]
        floor = total_xp_for(level)
        needed = xp_for_next(level)
        into = xp - floor
        place = await self.bot.db.rank_of(interaction.guild.id, member.id)  # type: ignore[attr-defined]

        embed = ui.embed(member.display_name, color=ui.ACCENT, caps=False)
        embed.add_field(name="level", value=str(level), inline=True)
        embed.add_field(name="rank", value=f"#{place}" if xp else "unranked", inline=True)
        embed.add_field(name="messages", value=str(row["messages"]), inline=True)
        embed.add_field(
            name="progress",
            value=f"`{ui.bar(into, needed)}`\n{into} / {needed} xp  ({xp} total)",
            inline=False,
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard", description="top chatters in the server")
    @app_commands.describe(page="which page, 10 per page")
    @app_commands.guild_only()
    async def leaderboard(self, interaction: discord.Interaction, page: int = 1) -> None:
        assert interaction.guild is not None
        page = max(1, page)
        rows = await self.bot.db.leaderboard(interaction.guild.id, 10, (page - 1) * 10)  # type: ignore[attr-defined]
        if not rows:
            await interaction.response.send_message(
                embed=ui.info("nobody has any xp yet. go talk to someone.")
            )
            return

        lines = []
        for index, row in enumerate(rows, start=(page - 1) * 10 + 1):
            member = interaction.guild.get_member(row["user_id"])
            name = member.display_name if member else f"user {row['user_id']}"
            lines.append(f"`{index:>2}.` **{name}** - level {row['level']} - {row['xp']} xp")

        embed = ui.embed("leaderboard", "\n".join(lines))
        embed.set_footer(text=f"page {page}")
        await interaction.response.send_message(embed=embed)

    levels_group = app_commands.Group(
        name="levels",
        description="leveling settings",
        guild_only=True,
        default_permissions=discord.Permissions(manage_guild=True),
    )

    @levels_group.command(name="toggle", description="turn leveling on or off")
    @staff_only()
    async def levels_toggle(self, interaction: discord.Interaction, enabled: bool) -> None:
        assert interaction.guild is not None
        await self.bot.db.set_config(interaction.guild.id, levels_enabled=int(enabled))  # type: ignore[attr-defined]
        await interaction.response.send_message(
            embed=ui.ok("leveling is on" if enabled else "leveling is off"), ephemeral=True
        )

    @levels_group.command(name="give", description="hand someone xp")
    @staff_only()
    async def levels_give(self, interaction: discord.Interaction, user: discord.Member, amount: int) -> None:
        assert interaction.guild is not None
        row = await self.bot.db.add_xp(interaction.guild.id, user.id, amount)  # type: ignore[attr-defined]
        new_level = level_from_xp(row["xp"])
        await self.bot.db.set_level(interaction.guild.id, user.id, new_level, row["xp"])  # type: ignore[attr-defined]
        await self._sync_roles(user, new_level)
        await interaction.response.send_message(
            embed=ui.ok(f"{user.mention} now has {row['xp']} xp (level {new_level})")
        )

    @levels_group.command(name="set", description="set someone to an exact level")
    @staff_only()
    async def levels_set(self, interaction: discord.Interaction, user: discord.Member, level: int) -> None:
        assert interaction.guild is not None
        level = max(0, min(level, 500))
        xp = total_xp_for(level)
        await self.bot.db.set_level(interaction.guild.id, user.id, level, xp)  # type: ignore[attr-defined]
        await self._sync_roles(user, level)
        await interaction.response.send_message(
            embed=ui.ok(f"{user.mention} is now level {level}")
        )

    @levels_group.command(name="reset", description="wipe one persons xp, or the whole server")
    @app_commands.describe(user="leave blank to wipe everyone")
    @staff_only()
    async def levels_reset(self, interaction: discord.Interaction, user: discord.Member | None = None) -> None:
        assert interaction.guild is not None
        if user is not None:
            await self.bot.db.execute(  # type: ignore[attr-defined]
                "DELETE FROM levels WHERE guild_id = ? AND user_id = ?",
                interaction.guild.id, user.id,
            )
            await interaction.response.send_message(embed=ui.ok(f"wiped {user.mention}"), ephemeral=True)
            return
        await self.bot.db.execute("DELETE FROM levels WHERE guild_id = ?", interaction.guild.id)  # type: ignore[attr-defined]
        await interaction.response.send_message(
            embed=ui.ok("every level in this server has been reset"), ephemeral=True
        )

    @levels_group.command(name="noxp", description="toggle whether a channel gives xp")
    @staff_only()
    async def levels_noxp(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        assert interaction.guild is not None
        blocked = await self.bot.db.toggle_no_xp(interaction.guild.id, channel.id)  # type: ignore[attr-defined]
        await interaction.response.send_message(
            embed=ui.ok(
                f"{channel.mention} no longer gives xp" if blocked
                else f"{channel.mention} gives xp again"
            ),
            ephemeral=True,
        )

    @levels_group.command(name="reward", description="give a role at a certain level")
    @app_commands.describe(level="the level that unlocks it", role="the role to hand out")
    @staff_only()
    async def levels_reward(self, interaction: discord.Interaction, level: int, role: discord.Role) -> None:
        assert interaction.guild is not None
        await self.bot.db.set_level_role(interaction.guild.id, level, role.id)  # type: ignore[attr-defined]
        await interaction.response.send_message(
            embed=ui.ok(f"{role.mention} unlocks at level {level}"), ephemeral=True
        )

    @levels_group.command(name="rewards", description="list every level role")
    @staff_only()
    async def levels_rewards(self, interaction: discord.Interaction) -> None:
        assert interaction.guild is not None
        rows = await self.bot.db.level_roles(interaction.guild.id)  # type: ignore[attr-defined]
        if not rows:
            await interaction.response.send_message(embed=ui.info("no level roles set"), ephemeral=True)
            return
        lines = []
        for row in rows:
            role = interaction.guild.get_role(row["role_id"])
            lines.append(f"level {row['level']} - {role.mention if role else 'deleted role'}")
        await interaction.response.send_message(
            embed=ui.embed("level rewards", "\n".join(lines)), ephemeral=True
        )

    @levels_group.command(name="unreward", description="stop giving a role at a level")
    @staff_only()
    async def levels_unreward(self, interaction: discord.Interaction, level: int) -> None:
        assert interaction.guild is not None
        await self.bot.db.remove_level_role(interaction.guild.id, level)  # type: ignore[attr-defined]
        await interaction.response.send_message(embed=ui.ok(f"cleared level {level}"), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Levels(bot))
