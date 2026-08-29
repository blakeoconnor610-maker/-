"""Private support tickets: a button panel, one channel per person, transcripts."""

from __future__ import annotations

import asyncio
import io
import logging
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from core import ui
from core.checks import is_staff_member
from core.smallcaps import small

log = logging.getLogger("bot.tickets")

STAFF_ROLE_NAMES = {small(name) for name in ("owner", "admin", "mod", "helper")}


async def staff_roles(bot: commands.Bot, guild: discord.Guild) -> list[discord.Role]:
    """Every role that should be able to see tickets and staff-only output."""
    config = await bot.db.config(guild.id)  # type: ignore[attr-defined]
    roles: list[discord.Role] = []
    staff_role_id = config.get("staff_role")
    if staff_role_id:
        role = guild.get_role(staff_role_id)
        if role is not None:
            roles.append(role)
    for role in guild.roles:
        if role.name in STAFF_ROLE_NAMES and role not in roles:
            roles.append(role)
    return roles


async def build_transcript(channel: discord.TextChannel) -> discord.File:
    lines = [
        f"transcript for #{channel.name}",
        f"channel id: {channel.id}",
        f"saved: {datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S} utc",
        "-" * 60,
        "",
    ]
    async for message in channel.history(limit=2000, oldest_first=True):
        stamp = f"{message.created_at:%Y-%m-%d %H:%M:%S}"
        body = message.clean_content or ""
        for embed in message.embeds:
            if embed.title:
                body += f"\n    [embed] {embed.title}"
            if embed.description:
                body += f"\n    {embed.description}"
        for attachment in message.attachments:
            body += f"\n    [file] {attachment.url}"
        lines.append(f"[{stamp}] {message.author} ({message.author.id}): {body}".rstrip())
    data = io.BytesIO("\n".join(lines).encode("utf-8"))
    return discord.File(data, filename=f"ticket-{channel.name}.txt")


class TicketPanelView(discord.ui.View):
    """The permanent button people press to open a ticket."""

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="open a ticket",
        style=discord.ButtonStyle.primary,
        custom_id="ticket:open",
    )
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(TicketModal(self.bot))


class TicketModal(discord.ui.Modal, title="open a ticket"):
    reason = discord.ui.TextInput(
        label="what do you need help with",
        style=discord.TextStyle.paragraph,
        placeholder="short version is fine",
        required=True,
        max_length=500,
    )

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await create_ticket(self.bot, interaction, str(self.reason))


async def create_ticket(bot: commands.Bot, interaction: discord.Interaction, topic: str) -> None:
    guild = interaction.guild
    if guild is None or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message(
            embed=ui.error("tickets only work inside a server"), ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True, thinking=True)

    existing = await bot.db.open_ticket_for(guild.id, interaction.user.id)  # type: ignore[attr-defined]
    if existing is not None:
        channel = guild.get_channel(existing["channel_id"])
        if channel is not None:
            await interaction.followup.send(
                embed=ui.warn(f"you already have one open: {channel.mention}"), ephemeral=True
            )
            return
        await bot.db.close_ticket(existing["channel_id"])  # type: ignore[attr-defined]

    config = await bot.db.config(guild.id)  # type: ignore[attr-defined]
    category = guild.get_channel(config.get("ticket_category") or 0)
    if not isinstance(category, discord.CategoryChannel):
        category = discord.utils.get(guild.categories, name=small("tickets"))
    if category is None:
        try:
            category = await guild.create_category(
                small("tickets"),
                overwrites={guild.default_role: discord.PermissionOverwrite(view_channel=False)},
                reason="ticket system",
            )
            await bot.db.set_config(guild.id, ticket_category=category.id)  # type: ignore[attr-defined]
        except discord.Forbidden:
            await interaction.followup.send(
                embed=ui.error("i cant make the tickets category - i need manage channels"),
                ephemeral=True,
            )
            return

    number = await bot.db.next_ticket_number(guild.id)  # type: ignore[attr-defined]
    overwrites: dict[discord.abc.Snowflake, discord.PermissionOverwrite] = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True,
            attach_files=True, embed_links=True,
        ),
    }
    if guild.me is not None:
        overwrites[guild.me] = discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True,
            manage_channels=True, manage_messages=True, attach_files=True, embed_links=True,
        )
    for role in await staff_roles(bot, guild):
        overwrites[role] = discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True,
            attach_files=True, embed_links=True, manage_messages=True,
        )

    try:
        channel = await guild.create_text_channel(
            name=f"{small('ticket')}-{number:04d}",
            category=category,
            overwrites=overwrites,
            topic=f"ticket {number} opened by {interaction.user} ({interaction.user.id})",
            reason=f"ticket opened by {interaction.user}",
        )
    except discord.Forbidden:
        await interaction.followup.send(
            embed=ui.error("i cant create the channel - check my manage channels permission"),
            ephemeral=True,
        )
        return

    await bot.db.create_ticket(channel.id, guild.id, interaction.user.id, number, topic)  # type: ignore[attr-defined]

    staff_mention = " ".join(role.mention for role in await staff_roles(bot, guild)) or "staff"
    embed = ui.embed(
        f"ticket {number:04d}",
        f"{interaction.user.mention} opened this.\n\n**what they said**\n{ui.trim(topic, 900)}\n\n"
        "someone will be with you shortly. add anything else you think helps.",
    )
    embed.set_footer(text=f"opened by {interaction.user}")
    await channel.send(
        content=f"{interaction.user.mention} {staff_mention}",
        embed=embed,
        view=TicketControlView(bot),
        allowed_mentions=discord.AllowedMentions(users=True, roles=True),
    )
    await interaction.followup.send(
        embed=ui.ok(f"opened {channel.mention}"), ephemeral=True
    )

    if isinstance(bot, commands.Bot) and hasattr(bot, "send_log"):
        log_embed = ui.embed(
            "ticket opened",
            f"**ticket** {channel.mention} ({number:04d})\n"
            f"**by** {ui.user_line(interaction.user)}\n"
            f"**about** {ui.trim(topic, 500)}",
            color=ui.ACCENT,
        )
        await bot.send_log(guild, log_embed)  # type: ignore[attr-defined]


class TicketControlView(discord.ui.View):
    """Buttons that live at the top of every ticket channel."""

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="claim", style=discord.ButtonStyle.secondary, custom_id="ticket:claim")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await is_staff_member(interaction):
            await interaction.response.send_message(
                embed=ui.error("staff only"), ephemeral=True
            )
            return
        await self.bot.db.claim_ticket(interaction.channel_id, interaction.user.id)  # type: ignore[attr-defined]
        await interaction.response.send_message(
            embed=ui.info(f"{interaction.user.mention} is handling this one.")
        )

    @discord.ui.button(label="close", style=discord.ButtonStyle.danger, custom_id="ticket:close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        ticket = await self.bot.db.get_ticket(interaction.channel_id)  # type: ignore[attr-defined]
        if ticket is None:
            await interaction.response.send_message(
                embed=ui.error("this isnt a ticket channel"), ephemeral=True
            )
            return
        is_owner = interaction.user.id == ticket["user_id"]
        if not is_owner and not await is_staff_member(interaction):
            await interaction.response.send_message(
                embed=ui.error("only staff or whoever opened it can close it"), ephemeral=True
            )
            return
        await close_ticket(self.bot, interaction, "closed with the button")


async def close_ticket(bot: commands.Bot, interaction: discord.Interaction, reason: str) -> None:
    channel = interaction.channel
    guild = interaction.guild
    if not isinstance(channel, discord.TextChannel) or guild is None:
        return

    ticket = await bot.db.get_ticket(channel.id)  # type: ignore[attr-defined]
    if ticket is None:
        await interaction.response.send_message(
            embed=ui.error("this isnt a ticket channel"), ephemeral=True
        )
        return

    await interaction.response.send_message(
        embed=ui.warn("saving the transcript then deleting this channel in a few seconds.")
    )
    await bot.db.close_ticket(channel.id)  # type: ignore[attr-defined]

    config = await bot.db.config(guild.id)  # type: ignore[attr-defined]
    log_channel = guild.get_channel(config.get("ticket_log") or 0)
    opener = guild.get_member(ticket["user_id"])

    if isinstance(log_channel, discord.TextChannel):
        try:
            transcript = await build_transcript(channel)
            embed = ui.embed(
                f"ticket {ticket['number']:04d} closed",
                f"**opened by** {opener.mention if opener else ticket['user_id']}\n"
                f"**closed by** {interaction.user.mention}\n"
                f"**reason** {ui.trim(reason, 500)}\n"
                f"**about** {ui.trim(ticket['topic'] or 'not given', 500)}",
                color=ui.WARN,
            )
            await log_channel.send(embed=embed, file=transcript)
        except discord.HTTPException:
            log.warning("could not save transcript for %s", channel.id)

    if opener is not None:
        try:
            await opener.send(
                embed=ui.info(
                    f"your ticket in **{guild.name}** was closed by {interaction.user}.\n"
                    "open another one any time if you still need help."
                )
            )
        except discord.HTTPException:
            pass

    await asyncio.sleep(5)
    try:
        await channel.delete(reason=f"ticket closed by {interaction.user}")
    except discord.HTTPException:
        pass


class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    ticket = app_commands.Group(
        name="ticket",
        description="support tickets",
        guild_only=True,
    )

    @ticket.command(name="open", description="open a ticket without hunting for the button")
    @app_commands.describe(about="what you need help with")
    async def ticket_open(self, interaction: discord.Interaction, about: str) -> None:
        await create_ticket(self.bot, interaction, about)

    @ticket.command(name="close", description="close the ticket you are in")
    @app_commands.describe(reason="why it is being closed")
    async def ticket_close(self, interaction: discord.Interaction, reason: str = "no reason given") -> None:
        ticket = await self.bot.db.get_ticket(interaction.channel_id)  # type: ignore[attr-defined]
        if ticket is None:
            await interaction.response.send_message(
                embed=ui.error("run this inside a ticket channel"), ephemeral=True
            )
            return
        if interaction.user.id != ticket["user_id"] and not await is_staff_member(interaction):
            await interaction.response.send_message(
                embed=ui.error("only staff or whoever opened it can close it"), ephemeral=True
            )
            return
        await close_ticket(self.bot, interaction, reason)

    @ticket.command(name="add", description="pull someone else into this ticket")
    @app_commands.describe(user="who to add")
    async def ticket_add(self, interaction: discord.Interaction, user: discord.Member) -> None:
        if not await is_staff_member(interaction):
            await interaction.response.send_message(embed=ui.error("staff only"), ephemeral=True)
            return
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(embed=ui.error("wrong channel type"), ephemeral=True)
            return
        await channel.set_permissions(
            user, view_channel=True, send_messages=True, read_message_history=True,
            reason=f"added to ticket by {interaction.user}",
        )
        await interaction.response.send_message(embed=ui.ok(f"{user.mention} can see this now"))

    @ticket.command(name="remove", description="remove someone from this ticket")
    @app_commands.describe(user="who to remove")
    async def ticket_remove(self, interaction: discord.Interaction, user: discord.Member) -> None:
        if not await is_staff_member(interaction):
            await interaction.response.send_message(embed=ui.error("staff only"), ephemeral=True)
            return
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(embed=ui.error("wrong channel type"), ephemeral=True)
            return
        await channel.set_permissions(user, overwrite=None, reason=f"removed by {interaction.user}")
        await interaction.response.send_message(embed=ui.ok(f"{user.mention} was removed"))

    @ticket.command(name="rename", description="rename this ticket channel")
    @app_commands.describe(name="the new name")
    async def ticket_rename(self, interaction: discord.Interaction, name: str) -> None:
        if not await is_staff_member(interaction):
            await interaction.response.send_message(embed=ui.error("staff only"), ephemeral=True)
            return
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(embed=ui.error("wrong channel type"), ephemeral=True)
            return
        await channel.edit(name=small(name.lower()).replace(" ", "-"))
        await interaction.response.send_message(embed=ui.ok("renamed"))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Tickets(bot))
