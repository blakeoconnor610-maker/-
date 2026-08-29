"""Server logging.

The headline feature: when a message gets deleted the log says who deleted it,
shows their username, and pings them.
"""

from __future__ import annotations

import datetime as dt
import logging

import discord
from discord.ext import commands

from core import ui

log = logging.getLogger("bot.logs")

# How recent an audit log entry has to be for us to trust it belongs to
# the delete we just saw.
AUDIT_WINDOW = dt.timedelta(seconds=12)


class Logs(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        # Remembers the last audit log entry we matched, so repeated deletes by
        # the same moderator (discord bundles those into one entry) still resolve.
        self._audit_seen: dict[int, tuple[int, int]] = {}

    # ---------------------------------------------------------- helper ----

    async def _channel(self, guild: discord.Guild, column: str) -> discord.TextChannel | None:
        config = await self.bot.db.config(guild.id)  # type: ignore[attr-defined]
        channel = guild.get_channel(config.get(column) or 0)
        if isinstance(channel, discord.TextChannel):
            return channel
        if column != "log_channel":
            return await self._channel(guild, "log_channel")
        return None

    async def _send(
        self,
        guild: discord.Guild,
        embed: discord.Embed,
        column: str = "log_channel",
        content: str | None = None,
    ) -> None:
        channel = await self._channel(guild, column)
        if channel is None or guild.me is None:
            return
        if not channel.permissions_for(guild.me).send_messages:
            return
        embed.timestamp = embed.timestamp or dt.datetime.now(dt.timezone.utc)
        try:
            await channel.send(
                content=content,
                embed=embed,
                allowed_mentions=discord.AllowedMentions(users=True),
            )
        except discord.HTTPException:
            log.warning("log write failed in guild %s", guild.id)

    async def _find_deleter(
        self, message: discord.Message
    ) -> tuple[discord.abc.User | None, bool]:
        """Work out who deleted a message.

        Returns (user, certain). Discord only tells us through the audit log,
        and it never logs a person deleting their own message - so no entry
        means the author did it themselves.
        """
        guild = message.guild
        if guild is None or guild.me is None or not guild.me.guild_permissions.view_audit_log:
            return None, False

        try:
            async for entry in guild.audit_logs(limit=6, action=discord.AuditLogAction.message_delete):
                if entry.target is None or entry.target.id != message.author.id:
                    continue
                extra_channel = getattr(entry.extra, "channel", None)
                if extra_channel is not None and extra_channel.id != message.channel.id:
                    continue

                count = getattr(entry.extra, "count", 1) or 1
                fresh = dt.datetime.now(dt.timezone.utc) - entry.created_at < AUDIT_WINDOW
                previous = self._audit_seen.get(entry.id)
                bumped = previous is not None and count > previous[1]

                if fresh or bumped:
                    self._audit_seen[entry.id] = (entry.user.id if entry.user else 0, count)
                    return entry.user, True
                break
        except discord.Forbidden:
            return None, False
        except discord.HTTPException:
            return None, False

        return message.author, True  # nobody else touched it, so they deleted it

    # -------------------------------------------------------- messages ----

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot:
            return

        deleter, certain = await self._find_deleter(message)
        self_delete = deleter is not None and deleter.id == message.author.id

        embed = ui.embed("message deleted", color=ui.ERROR)
        embed.add_field(
            name="author",
            value=f"{message.author.mention}\n**{message.author}**\n`{message.author.id}`",
            inline=True,
        )
        if deleter is not None:
            embed.add_field(
                name="deleted by",
                value=(
                    "themselves" if self_delete
                    else f"{deleter.mention}\n**{deleter}**\n`{deleter.id}`"
                ),
                inline=True,
            )
        else:
            embed.add_field(
                name="deleted by",
                value="unknown - give me **view audit log** to find out",
                inline=True,
            )
        embed.add_field(name="channel", value=message.channel.mention, inline=True)
        embed.add_field(
            name="content",
            value=ui.trim(message.content, 1000) or "*no text, probably just a file*",
            inline=False,
        )
        if message.attachments:
            embed.add_field(
                name="attachments",
                value="\n".join(a.filename for a in message.attachments[:8]),
                inline=False,
            )
        embed.set_thumbnail(url=message.author.display_avatar.url)
        embed.set_footer(text=f"message id {message.id}")

        # Ping whoever pulled the trigger, exactly as asked.
        ping_target = deleter if deleter is not None else message.author
        content = f"{ping_target.mention} deleted a message"
        if not certain:
            content = f"{message.author.mention} had a message deleted"

        await self._send(message.guild, embed, "log_channel", content=content)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages: list[discord.Message]) -> None:
        if not messages or messages[0].guild is None:
            return
        guild = messages[0].guild
        embed = ui.embed(
            "messages bulk deleted",
            f"**{len(messages)}** messages were cleared in {messages[0].channel.mention}",
            color=ui.ERROR,
        )
        preview = "\n".join(
            f"**{m.author}**: {ui.trim(m.content, 120)}" for m in messages[-10:] if m.content
        )
        if preview:
            embed.add_field(name="last few", value=ui.trim(preview, 1000), inline=False)
        await self._send(guild, embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if before.guild is None or before.author.bot or before.content == after.content:
            return
        embed = ui.embed("message edited", color=ui.WARN)
        embed.add_field(
            name="author",
            value=f"{after.author.mention}\n**{after.author}**\n`{after.author.id}`",
            inline=True,
        )
        embed.add_field(name="channel", value=after.channel.mention, inline=True)
        embed.add_field(name="jump", value=f"[go to it]({after.jump_url})", inline=True)
        embed.add_field(name="before", value=ui.trim(before.content, 1000) or "*empty*", inline=False)
        embed.add_field(name="after", value=ui.trim(after.content, 1000) or "*empty*", inline=False)
        embed.set_thumbnail(url=after.author.display_avatar.url)
        await self._send(before.guild, embed, content=f"{after.author.mention} edited a message")

    # --------------------------------------------------------- members ----

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        age = dt.datetime.now(dt.timezone.utc) - member.created_at
        embed = ui.embed("member joined", color=ui.SUCCESS)
        embed.add_field(name="who", value=f"{member.mention}\n**{member}**\n`{member.id}`", inline=True)
        embed.add_field(
            name="account made",
            value=f"<t:{int(member.created_at.timestamp())}:R>"
                  + ("\n**brand new account**" if age.days < 7 else ""),
            inline=True,
        )
        embed.add_field(name="member count", value=str(member.guild.member_count), inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)
        await self._send(member.guild, embed, "join_channel")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        roles = [r.mention for r in member.roles if r != member.guild.default_role]
        embed = ui.embed("member left", color=ui.ERROR)
        embed.add_field(name="who", value=f"**{member}**\n`{member.id}`", inline=True)
        embed.add_field(
            name="was here",
            value=f"<t:{int(member.joined_at.timestamp())}:R>" if member.joined_at else "unknown",
            inline=True,
        )
        embed.add_field(name="member count", value=str(member.guild.member_count), inline=True)
        if roles:
            embed.add_field(name="roles", value=ui.trim(" ".join(roles), 900), inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        await self._send(member.guild, embed, "join_channel")

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        if before.nick != after.nick:
            embed = ui.embed("nickname changed", color=ui.ACCENT)
            embed.add_field(name="who", value=f"{after.mention}\n`{after.id}`", inline=True)
            embed.add_field(name="before", value=before.nick or "*none*", inline=True)
            embed.add_field(name="after", value=after.nick or "*none*", inline=True)
            await self._send(after.guild, embed)

        gained = set(after.roles) - set(before.roles)
        lost = set(before.roles) - set(after.roles)
        if gained or lost:
            embed = ui.embed("roles changed", color=ui.ACCENT)
            embed.add_field(name="who", value=f"{after.mention}\n`{after.id}`", inline=False)
            if gained:
                embed.add_field(name="added", value=" ".join(r.mention for r in gained), inline=False)
            if lost:
                embed.add_field(name="removed", value=" ".join(r.mention for r in lost), inline=False)
            await self._send(after.guild, embed)

        if before.is_timed_out() != after.is_timed_out():
            if after.is_timed_out() and after.timed_out_until is not None:
                embed = ui.embed("timed out", color=ui.WARN)
                embed.add_field(name="who", value=f"{after.mention}\n`{after.id}`", inline=True)
                embed.add_field(
                    name="until",
                    value=f"<t:{int(after.timed_out_until.timestamp())}:f>",
                    inline=True,
                )
            else:
                embed = ui.embed("timeout ended", color=ui.SUCCESS)
                embed.add_field(name="who", value=f"{after.mention}\n`{after.id}`", inline=True)
            await self._send(after.guild, embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User) -> None:
        embed = ui.embed("user banned", color=ui.ERROR)
        embed.add_field(name="who", value=f"**{user}**\n`{user.id}`", inline=True)
        await self._send(guild, embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User) -> None:
        embed = ui.embed("user unbanned", color=ui.SUCCESS)
        embed.add_field(name="who", value=f"**{user}**\n`{user.id}`", inline=True)
        await self._send(guild, embed)

    # -------------------------------------------------- server changes ----

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel) -> None:
        embed = ui.embed("channel created", f"**{channel.name}**\n`{channel.id}`", color=ui.SUCCESS)
        await self._send(channel.guild, embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel) -> None:
        embed = ui.embed("channel deleted", f"**{channel.name}**\n`{channel.id}`", color=ui.ERROR)
        await self._send(channel.guild, embed)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role) -> None:
        embed = ui.embed("role created", f"**{role.name}**\n`{role.id}`", color=ui.SUCCESS)
        await self._send(role.guild, embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role) -> None:
        embed = ui.embed("role deleted", f"**{role.name}**\n`{role.id}`", color=ui.ERROR)
        await self._send(role.guild, embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Logs(bot))
