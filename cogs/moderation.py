"""Every moderation command: ban, kick, mute, warn, purge, lock, and the rest.

Each action tries to DM the person first, then writes to the log channel.
"""

from __future__ import annotations

import datetime as dt
import logging

import discord
from discord import app_commands
from discord.ext import commands

from core import ui
from core.checks import hierarchy_error, staff_only
from core.timeparse import human_duration, parse_duration

log = logging.getLogger("bot.moderation")

MAX_TIMEOUT = 28 * 86400  # discord's hard ceiling


async def dm_notice(user: discord.abc.User, guild: discord.Guild, action: str,
                    reason: str, extra: str = "") -> bool:
    """Best effort DM. Returns False if their dms are shut."""
    embed = ui.embed(
        action,
        f"you were **{action}** in **{guild.name}**.\n\n**reason**\n{reason or 'none given'}"
        + (f"\n\n{extra}" if extra else ""),
        color=ui.WARN,
    )
    try:
        await user.send(embed=embed)
        return True
    except (discord.Forbidden, discord.HTTPException):
        return False


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _log_action(
        self,
        guild: discord.Guild,
        action: str,
        target: discord.abc.User,
        moderator: discord.abc.User,
        reason: str,
        extra: str = "",
        color: int = ui.WARN,
    ) -> None:
        embed = ui.embed(action, color=color)
        embed.add_field(name="user", value=f"{target.mention}\n{ui.user_line(target)}", inline=True)
        embed.add_field(name="moderator", value=moderator.mention, inline=True)
        if extra:
            embed.add_field(name="details", value=extra, inline=False)
        embed.add_field(name="reason", value=ui.trim(reason or "none given", 900), inline=False)
        embed.timestamp = dt.datetime.now(dt.timezone.utc)
        await self.bot.send_log(guild, embed)  # type: ignore[attr-defined]

    # ------------------------------------------------------------ ban ----

    @app_commands.command(name="ban", description="ban someone from the server")
    @app_commands.describe(
        user="who to ban",
        reason="why",
        delete_days="how many days of their messages to wipe, 0 to 7",
    )
    @app_commands.default_permissions(ban_members=True)
    @app_commands.checks.bot_has_permissions(ban_members=True)
    @app_commands.guild_only()
    @staff_only()
    async def ban(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        reason: str = "no reason given",
        delete_days: app_commands.Range[int, 0, 7] = 0,
    ) -> None:
        guild = interaction.guild
        assert guild is not None and isinstance(interaction.user, discord.Member)

        member = guild.get_member(user.id)
        if member is not None:
            problem = hierarchy_error(guild, interaction.user, member, "ban")
            if problem:
                await interaction.response.send_message(embed=ui.error(problem), ephemeral=True)
                return

        await interaction.response.defer()
        dmed = await dm_notice(user, guild, "banned", reason) if member else False
        try:
            await guild.ban(
                user,
                reason=f"{interaction.user} - {reason}",
                delete_message_seconds=delete_days * 86400,
            )
        except discord.Forbidden:
            await interaction.followup.send(
                embed=ui.error("discord said no. my role probably sits below theirs."), ephemeral=True
            )
            return

        await interaction.followup.send(
            embed=ui.ok(f"**{user}** is banned.\n**reason** {ui.trim(reason, 500)}", title="banned")
        )
        await self._log_action(
            guild, "banned", user, interaction.user, reason,
            extra=("could not dm them" if not dmed else "dm sent"), color=ui.ERROR,
        )

    @app_commands.command(name="unban", description="lift a ban")
    @app_commands.describe(user_id="their user id", reason="why")
    @app_commands.default_permissions(ban_members=True)
    @app_commands.checks.bot_has_permissions(ban_members=True)
    @app_commands.guild_only()
    @staff_only()
    async def unban(self, interaction: discord.Interaction, user_id: str,
                    reason: str = "no reason given") -> None:
        guild = interaction.guild
        assert guild is not None
        if not user_id.isdigit():
            await interaction.response.send_message(
                embed=ui.error("that is not a user id. turn on developer mode, right click, copy id."),
                ephemeral=True,
            )
            return
        try:
            user = await self.bot.fetch_user(int(user_id))
            await guild.unban(user, reason=f"{interaction.user} - {reason}")
        except discord.NotFound:
            await interaction.response.send_message(
                embed=ui.error("that person is not banned here"), ephemeral=True
            )
            return
        await interaction.response.send_message(embed=ui.ok(f"**{user}** is unbanned"))
        await self._log_action(guild, "unbanned", user, interaction.user, reason, color=ui.SUCCESS)

    @app_commands.command(name="softban", description="ban then instantly unban, to clear their messages")
    @app_commands.describe(user="who", reason="why")
    @app_commands.default_permissions(ban_members=True)
    @app_commands.checks.bot_has_permissions(ban_members=True)
    @app_commands.guild_only()
    @staff_only()
    async def softban(self, interaction: discord.Interaction, user: discord.Member,
                      reason: str = "no reason given") -> None:
        guild = interaction.guild
        assert guild is not None and isinstance(interaction.user, discord.Member)
        problem = hierarchy_error(guild, interaction.user, user, "softban")
        if problem:
            await interaction.response.send_message(embed=ui.error(problem), ephemeral=True)
            return
        await interaction.response.defer()
        await dm_notice(user, guild, "kicked", reason, "your recent messages were cleared.")
        await guild.ban(user, reason=f"softban by {interaction.user} - {reason}",
                        delete_message_seconds=86400)
        await guild.unban(user, reason="softban")
        await interaction.followup.send(embed=ui.ok(f"softbanned **{user}**"))
        await self._log_action(guild, "softbanned", user, interaction.user, reason, color=ui.ERROR)

    # ----------------------------------------------------------- kick ----

    @app_commands.command(name="kick", description="kick someone out")
    @app_commands.describe(user="who to kick", reason="why")
    @app_commands.default_permissions(kick_members=True)
    @app_commands.checks.bot_has_permissions(kick_members=True)
    @app_commands.guild_only()
    @staff_only()
    async def kick(self, interaction: discord.Interaction, user: discord.Member,
                   reason: str = "no reason given") -> None:
        guild = interaction.guild
        assert guild is not None and isinstance(interaction.user, discord.Member)
        problem = hierarchy_error(guild, interaction.user, user, "kick")
        if problem:
            await interaction.response.send_message(embed=ui.error(problem), ephemeral=True)
            return

        await interaction.response.defer()
        dmed = await dm_notice(user, guild, "kicked", reason)
        await user.kick(reason=f"{interaction.user} - {reason}")
        await interaction.followup.send(
            embed=ui.ok(f"**{user}** was kicked.\n**reason** {ui.trim(reason, 500)}", title="kicked")
        )
        await self._log_action(
            guild, "kicked", user, interaction.user, reason,
            extra=("could not dm them" if not dmed else "dm sent"), color=ui.ERROR,
        )

    # ----------------------------------------------------------- mute ----

    @app_commands.command(name="mute", description="time someone out so they cant talk")
    @app_commands.describe(
        user="who to mute",
        duration="like 10m, 2h, 1d, 7d - max 28d",
        reason="why",
    )
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.bot_has_permissions(moderate_members=True)
    @app_commands.guild_only()
    @staff_only()
    async def mute(self, interaction: discord.Interaction, user: discord.Member,
                   duration: str = "10m", reason: str = "no reason given") -> None:
        guild = interaction.guild
        assert guild is not None and isinstance(interaction.user, discord.Member)
        problem = hierarchy_error(guild, interaction.user, user, "mute")
        if problem:
            await interaction.response.send_message(embed=ui.error(problem), ephemeral=True)
            return

        seconds = parse_duration(duration)
        if seconds is None:
            await interaction.response.send_message(
                embed=ui.error("i cant read that duration. try `10m`, `2h`, `1d`, `7d`."),
                ephemeral=True,
            )
            return
        if seconds > MAX_TIMEOUT:
            await interaction.response.send_message(
                embed=ui.error("discord caps timeouts at 28 days. use `/ban` if you need longer."),
                ephemeral=True,
            )
            return

        await interaction.response.defer()
        pretty = human_duration(seconds)
        until = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=seconds)
        dmed = await dm_notice(user, guild, "muted", reason, f"it lifts on its own in {pretty}.")
        await user.timeout(until, reason=f"{interaction.user} - {reason}")

        await interaction.followup.send(
            embed=ui.ok(
                f"**{user}** is muted for **{pretty}**.\n**reason** {ui.trim(reason, 500)}",
                title="muted",
            )
        )
        await self._log_action(
            guild, "muted", user, interaction.user, reason,
            extra=f"lasts {pretty}, until <t:{int(until.timestamp())}:f>"
                  + ("" if dmed else "\ncould not dm them"),
        )

    @app_commands.command(name="unmute", description="lift a mute early")
    @app_commands.describe(user="who", reason="why")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.bot_has_permissions(moderate_members=True)
    @app_commands.guild_only()
    @staff_only()
    async def unmute(self, interaction: discord.Interaction, user: discord.Member,
                     reason: str = "no reason given") -> None:
        guild = interaction.guild
        assert guild is not None
        config = await self.bot.db.config(guild.id)  # type: ignore[attr-defined]
        muted_role = guild.get_role(config.get("muted_role") or 0)

        was_muted = user.is_timed_out() or (muted_role is not None and muted_role in user.roles)
        if not was_muted:
            await interaction.response.send_message(
                embed=ui.info(f"{user.mention} is not muted"), ephemeral=True
            )
            return

        await interaction.response.defer()
        if user.is_timed_out():
            await user.timeout(None, reason=f"{interaction.user} - {reason}")
        if muted_role is not None and muted_role in user.roles:
            await user.remove_roles(muted_role, reason=f"{interaction.user} - {reason}")

        await interaction.followup.send(embed=ui.ok(f"**{user}** can talk again"))
        await self._log_action(guild, "unmuted", user, interaction.user, reason, color=ui.SUCCESS)

    # ----------------------------------------------------------- warn ----

    @app_commands.command(name="warn", description="put a warning on someones record")
    @app_commands.describe(user="who", reason="what they did")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    @staff_only()
    async def warn(self, interaction: discord.Interaction, user: discord.Member, reason: str) -> None:
        guild = interaction.guild
        assert guild is not None and isinstance(interaction.user, discord.Member)
        problem = hierarchy_error(guild, interaction.user, user, "warn")
        if problem:
            await interaction.response.send_message(embed=ui.error(problem), ephemeral=True)
            return

        await interaction.response.defer()
        warn_id = await self.bot.db.add_warning(guild.id, user.id, interaction.user.id, reason)  # type: ignore[attr-defined]
        total = len(list(await self.bot.db.warnings_for(guild.id, user.id)))  # type: ignore[attr-defined]
        await dm_notice(user, guild, "warned", reason, f"that is warning number {total}.")

        await interaction.followup.send(
            embed=ui.ok(
                f"warned **{user}**. that is **{total}** total.\n**reason** {ui.trim(reason, 500)}",
                title="warned",
            )
        )
        await self._log_action(
            guild, "warned", user, interaction.user, reason, extra=f"warning #{warn_id}, {total} total"
        )

    @app_commands.command(name="warnings", description="see someones warnings")
    @app_commands.describe(user="who")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    @staff_only()
    async def warnings(self, interaction: discord.Interaction, user: discord.Member) -> None:
        assert interaction.guild is not None
        rows = list(await self.bot.db.warnings_for(interaction.guild.id, user.id))  # type: ignore[attr-defined]
        if not rows:
            await interaction.response.send_message(
                embed=ui.info(f"{user.mention} has a clean record"), ephemeral=True
            )
            return
        lines = []
        for row in rows[:15]:
            mod = interaction.guild.get_member(row["mod_id"])
            lines.append(
                f"`#{row['id']}` <t:{row['created_at']}:R> by {mod.mention if mod else 'someone who left'}\n"
                f"> {ui.trim(row['reason'] or 'no reason given', 200)}"
            )
        embed = ui.embed(f"warnings for {user.display_name}", "\n\n".join(lines))
        embed.set_footer(text=f"{len(rows)} total")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="delwarn", description="delete one warning by its number")
    @app_commands.describe(warn_id="the number shown in /warnings")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    @staff_only()
    async def delwarn(self, interaction: discord.Interaction, warn_id: int) -> None:
        assert interaction.guild is not None
        removed = await self.bot.db.delete_warning(interaction.guild.id, warn_id)  # type: ignore[attr-defined]
        await interaction.response.send_message(
            embed=ui.ok(f"deleted warning #{warn_id}") if removed
            else ui.error("no warning with that number here"),
            ephemeral=True,
        )

    @app_commands.command(name="clearwarns", description="wipe someones whole record")
    @app_commands.describe(user="who")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    @staff_only()
    async def clearwarns(self, interaction: discord.Interaction, user: discord.Member) -> None:
        guild = interaction.guild
        assert guild is not None
        count = await self.bot.db.clear_warnings(guild.id, user.id)  # type: ignore[attr-defined]
        await interaction.response.send_message(
            embed=ui.ok(f"cleared {count} warning(s) from {user.mention}"), ephemeral=True
        )
        await self._log_action(guild, "warnings cleared", user, interaction.user,
                               f"{count} removed", color=ui.SUCCESS)

    # ------------------------------------------------------- channels ----

    @app_commands.command(name="purge", description="bulk delete recent messages")
    @app_commands.describe(
        amount="how many to look at, 1 to 200",
        user="only delete messages from this person",
        contains="only delete messages containing this text",
    )
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.checks.bot_has_permissions(manage_messages=True)
    @app_commands.guild_only()
    @staff_only()
    async def purge(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[int, 1, 200],
        user: discord.Member | None = None,
        contains: str | None = None,
    ) -> None:
        channel = interaction.channel
        if not isinstance(channel, (discord.TextChannel, discord.Thread)):
            await interaction.response.send_message(embed=ui.error("wrong channel type"), ephemeral=True)
            return

        def matches(message: discord.Message) -> bool:
            if user is not None and message.author.id != user.id:
                return False
            if contains is not None and contains.lower() not in message.content.lower():
                return False
            return True

        await interaction.response.defer(ephemeral=True, thinking=True)
        deleted = await channel.purge(limit=amount, check=matches, reason=f"purge by {interaction.user}")
        await interaction.followup.send(
            embed=ui.ok(f"deleted {len(deleted)} message(s)"), ephemeral=True
        )
        assert interaction.guild is not None
        embed = ui.embed("messages purged", color=ui.WARN)
        embed.add_field(name="channel", value=channel.mention, inline=True)
        embed.add_field(name="moderator", value=interaction.user.mention, inline=True)
        embed.add_field(name="count", value=str(len(deleted)), inline=True)
        await self.bot.send_log(interaction.guild, embed)  # type: ignore[attr-defined]

    @app_commands.command(name="slowmode", description="set slowmode on this channel")
    @app_commands.describe(seconds="0 turns it off, max 21600")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    @app_commands.guild_only()
    @staff_only()
    async def slowmode(self, interaction: discord.Interaction,
                       seconds: app_commands.Range[int, 0, 21600]) -> None:
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(embed=ui.error("wrong channel type"), ephemeral=True)
            return
        await channel.edit(slowmode_delay=seconds, reason=f"slowmode by {interaction.user}")
        await interaction.response.send_message(
            embed=ui.ok("slowmode off" if seconds == 0 else f"slowmode set to {seconds}s")
        )

    @app_commands.command(name="lock", description="stop everyone talking in a channel")
    @app_commands.describe(channel="which channel, defaults to this one", reason="why")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    @app_commands.guild_only()
    @staff_only()
    async def lock(self, interaction: discord.Interaction,
                   channel: discord.TextChannel | None = None,
                   reason: str = "no reason given") -> None:
        guild = interaction.guild
        assert guild is not None
        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.response.send_message(embed=ui.error("wrong channel type"), ephemeral=True)
            return
        overwrite = target.overwrites_for(guild.default_role)
        overwrite.send_messages = False
        await target.set_permissions(guild.default_role, overwrite=overwrite,
                                     reason=f"{interaction.user} - {reason}")
        await interaction.response.send_message(
            embed=ui.warn(f"{target.mention} is locked.\n**reason** {ui.trim(reason, 400)}", title="locked")
        )

    @app_commands.command(name="unlock", description="let everyone talk again")
    @app_commands.describe(channel="which channel, defaults to this one")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    @app_commands.guild_only()
    @staff_only()
    async def unlock(self, interaction: discord.Interaction,
                     channel: discord.TextChannel | None = None) -> None:
        guild = interaction.guild
        assert guild is not None
        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.response.send_message(embed=ui.error("wrong channel type"), ephemeral=True)
            return
        overwrite = target.overwrites_for(guild.default_role)
        overwrite.send_messages = None
        await target.set_permissions(guild.default_role, overwrite=overwrite,
                                     reason=f"unlocked by {interaction.user}")
        await interaction.response.send_message(embed=ui.ok(f"{target.mention} is open again"))

    # --------------------------------------------------------- people ----

    @app_commands.command(name="nick", description="change someones nickname")
    @app_commands.describe(user="who", nickname="leave blank to reset it")
    @app_commands.default_permissions(manage_nicknames=True)
    @app_commands.checks.bot_has_permissions(manage_nicknames=True)
    @app_commands.guild_only()
    @staff_only()
    async def nick(self, interaction: discord.Interaction, user: discord.Member,
                   nickname: str | None = None) -> None:
        try:
            await user.edit(nick=nickname, reason=f"nick change by {interaction.user}")
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=ui.error("my role sits below theirs, i cant rename them"), ephemeral=True
            )
            return
        await interaction.response.send_message(
            embed=ui.ok(f"{user.mention} is now **{nickname}**" if nickname
                        else f"reset {user.mention}'s nickname")
        )

    role_group = app_commands.Group(
        name="role",
        description="hand out or take away roles",
        guild_only=True,
        default_permissions=discord.Permissions(manage_roles=True),
    )

    @role_group.command(name="add", description="give someone a role")
    @staff_only()
    async def role_add(self, interaction: discord.Interaction,
                       user: discord.Member, role: discord.Role) -> None:
        guild = interaction.guild
        assert guild is not None and guild.me is not None
        if role >= guild.me.top_role:
            await interaction.response.send_message(
                embed=ui.error(f"{role.mention} is above my highest role, i cant touch it"),
                ephemeral=True,
            )
            return
        await user.add_roles(role, reason=f"added by {interaction.user}")
        await interaction.response.send_message(embed=ui.ok(f"gave {role.mention} to {user.mention}"))

    @role_group.command(name="remove", description="take a role away")
    @staff_only()
    async def role_remove(self, interaction: discord.Interaction,
                          user: discord.Member, role: discord.Role) -> None:
        guild = interaction.guild
        assert guild is not None and guild.me is not None
        if role >= guild.me.top_role:
            await interaction.response.send_message(
                embed=ui.error(f"{role.mention} is above my highest role, i cant touch it"),
                ephemeral=True,
            )
            return
        await user.remove_roles(role, reason=f"removed by {interaction.user}")
        await interaction.response.send_message(embed=ui.ok(f"took {role.mention} off {user.mention}"))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(bot))
