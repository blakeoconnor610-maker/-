"""Greets new people and hands them the starter role."""

from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from core import ui
from core.checks import staff_only

log = logging.getLogger("bot.welcome")

DEFAULT_WELCOME = (
    "{user} just showed up. make yourself at home.\n\n"
    "have a look at the rules, grab a role, talk whenever you feel like it. "
    "you are member **{count}**."
)


def render(template: str, member: discord.Member) -> str:
    return (
        template.replace("{user}", member.mention)
        .replace("{username}", member.display_name)
        .replace("{server}", member.guild.name)
        .replace("{count}", str(member.guild.member_count or 0))
    )


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if member.bot:
            return
        guild = member.guild
        config = await self.bot.db.config(guild.id)  # type: ignore[attr-defined]

        role_id = config.get("autorole")
        if role_id and guild.me is not None and guild.me.guild_permissions.manage_roles:
            role = guild.get_role(role_id)
            if role is not None and role < guild.me.top_role:
                try:
                    await member.add_roles(role, reason="autorole on join")
                except discord.HTTPException:
                    pass

        channel = guild.get_channel(config.get("welcome_channel") or 0)
        if not isinstance(channel, discord.TextChannel):
            return
        if guild.me is None or not channel.permissions_for(guild.me).send_messages:
            return

        template = config.get("welcome_message") or DEFAULT_WELCOME
        embed = ui.embed(f"welcome to {guild.name}", render(template, member))
        embed.set_thumbnail(url=member.display_avatar.url)
        try:
            await channel.send(
                content=member.mention,
                embed=embed,
                allowed_mentions=discord.AllowedMentions(users=True),
            )
        except discord.HTTPException:
            pass

    welcome_group = app_commands.Group(
        name="welcome",
        description="welcome message settings",
        guild_only=True,
        default_permissions=discord.Permissions(manage_guild=True),
    )

    @welcome_group.command(name="channel", description="where new people get greeted")
    @staff_only()
    async def welcome_channel(self, interaction: discord.Interaction,
                              channel: discord.TextChannel) -> None:
        assert interaction.guild is not None
        await self.bot.db.set_config(interaction.guild.id, welcome_channel=channel.id)  # type: ignore[attr-defined]
        await interaction.response.send_message(
            embed=ui.ok(f"greetings go to {channel.mention}"), ephemeral=True
        )

    @welcome_group.command(name="message", description="set the greeting text")
    @app_commands.describe(
        text="use {user} {username} {server} {count} as placeholders, or 'reset'"
    )
    @staff_only()
    async def welcome_message(self, interaction: discord.Interaction, text: str) -> None:
        assert interaction.guild is not None
        value = None if text.strip().lower() == "reset" else text
        await self.bot.db.set_config(interaction.guild.id, welcome_message=value)  # type: ignore[attr-defined]
        await interaction.response.send_message(
            embed=ui.ok("back to the default greeting" if value is None else "greeting updated"),
            ephemeral=True,
        )

    @welcome_group.command(name="test", description="see what the greeting looks like")
    @staff_only()
    async def welcome_test(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        assert guild is not None and isinstance(interaction.user, discord.Member)
        config = await self.bot.db.config(guild.id)  # type: ignore[attr-defined]
        template = config.get("welcome_message") or DEFAULT_WELCOME
        embed = ui.embed(f"welcome to {guild.name}", render(template, interaction.user))
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @welcome_group.command(name="autorole", description="role every new member gets")
    @app_commands.describe(role="leave blank to turn autorole off")
    @staff_only()
    async def welcome_autorole(self, interaction: discord.Interaction,
                               role: discord.Role | None = None) -> None:
        assert interaction.guild is not None
        await self.bot.db.set_config(interaction.guild.id, autorole=role.id if role else None)  # type: ignore[attr-defined]
        await interaction.response.send_message(
            embed=ui.ok(f"new members get {role.mention}" if role else "autorole is off"),
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Welcome(bot))
