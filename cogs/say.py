"""Talk through the bot. Type into any channel, from anywhere, as the bot."""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from core import ui
from core.checks import staff_only

COLORS = {
    "accent": ui.ACCENT,
    "green": ui.SUCCESS,
    "amber": ui.WARN,
    "red": ui.ERROR,
    "blank": ui.NEUTRAL,
}


class Say(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="say", description="make the bot post a message in any channel")
    @app_commands.describe(
        message="what to post - use \\n for a line break",
        channel="where to post it, defaults to right here",
        reply_to="message id to reply to",
    )
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.guild_only()
    @staff_only()
    async def say(
        self,
        interaction: discord.Interaction,
        message: str,
        channel: discord.TextChannel | None = None,
        reply_to: str | None = None,
    ) -> None:
        target = channel or interaction.channel
        guild = interaction.guild
        assert guild is not None
        if not isinstance(target, discord.TextChannel):
            await interaction.response.send_message(embed=ui.error("pick a text channel"), ephemeral=True)
            return
        if guild.me is None or not target.permissions_for(guild.me).send_messages:
            await interaction.response.send_message(
                embed=ui.error(f"i cant talk in {target.mention}"), ephemeral=True
            )
            return

        text = message.replace("\\n", "\n")
        reference = None
        if reply_to and reply_to.isdigit():
            try:
                reference = await target.fetch_message(int(reply_to))
            except discord.HTTPException:
                reference = None

        sent = await target.send(
            text,
            reference=reference,
            allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
        )
        await interaction.response.send_message(
            embed=ui.ok(f"posted in {target.mention} - [jump]({sent.jump_url})"), ephemeral=True
        )

    @app_commands.command(name="embed", description="post a tidy embed in any channel")
    @app_commands.describe(
        title="heading",
        body="the text - use \\n for line breaks",
        channel="where to post it",
        color="accent, green, amber, red or blank",
        small_caps="write the title in small caps like the rest of the server",
    )
    @app_commands.choices(
        color=[app_commands.Choice(name=name, value=name) for name in COLORS]
    )
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.guild_only()
    @staff_only()
    async def embed_command(
        self,
        interaction: discord.Interaction,
        title: str,
        body: str,
        channel: discord.TextChannel | None = None,
        color: app_commands.Choice[str] | None = None,
        small_caps: bool = True,
    ) -> None:
        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.response.send_message(embed=ui.error("pick a text channel"), ephemeral=True)
            return
        embed = ui.embed(
            title,
            body.replace("\\n", "\n"),
            color=COLORS[color.value if color else "accent"],
            caps=small_caps,
        )
        sent = await target.send(embed=embed)
        await interaction.response.send_message(
            embed=ui.ok(f"posted in {target.mention} - [jump]({sent.jump_url})"), ephemeral=True
        )

    @app_commands.command(name="edit", description="edit something the bot already posted")
    @app_commands.describe(
        message_id="id of the bot message",
        new_text="what it should say now",
        channel="which channel it is in",
    )
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.guild_only()
    @staff_only()
    async def edit(
        self,
        interaction: discord.Interaction,
        message_id: str,
        new_text: str,
        channel: discord.TextChannel | None = None,
    ) -> None:
        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel) or not message_id.isdigit():
            await interaction.response.send_message(embed=ui.error("bad channel or id"), ephemeral=True)
            return
        try:
            message = await target.fetch_message(int(message_id))
        except discord.HTTPException:
            await interaction.response.send_message(
                embed=ui.error("cant find that message in that channel"), ephemeral=True
            )
            return
        if message.author.id != interaction.client.user.id:  # type: ignore[union-attr]
            await interaction.response.send_message(
                embed=ui.error("i can only edit my own messages"), ephemeral=True
            )
            return
        await message.edit(content=new_text.replace("\\n", "\n"), embed=None)
        await interaction.response.send_message(embed=ui.ok("edited"), ephemeral=True)

    @app_commands.command(name="dm", description="send someone a dm from the bot")
    @app_commands.describe(user="who to message", message="what to say")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    @staff_only()
    async def dm(self, interaction: discord.Interaction, user: discord.Member, message: str) -> None:
        guild = interaction.guild
        assert guild is not None
        embed = ui.embed(f"message from {guild.name}", message.replace("\\n", "\n"))
        embed.set_footer(text="sent by the server staff")
        try:
            await user.send(embed=embed)
        except discord.HTTPException:
            await interaction.response.send_message(
                embed=ui.error(f"{user.mention} has dms closed"), ephemeral=True
            )
            return
        await interaction.response.send_message(embed=ui.ok(f"sent to {user.mention}"), ephemeral=True)

    @app_commands.command(name="announce", description="post an announcement and ping everyone in a role")
    @app_commands.describe(
        channel="where it goes",
        message="the announcement",
        ping="role to ping, leave blank for no ping",
        title="heading, defaults to announcement",
    )
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    @staff_only()
    async def announce(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        message: str,
        ping: discord.Role | None = None,
        title: str = "announcement",
    ) -> None:
        embed = ui.embed(title, message.replace("\\n", "\n"))
        embed.set_footer(text=f"posted by {interaction.user}")
        sent = await channel.send(
            content=ping.mention if ping else None,
            embed=embed,
            allowed_mentions=discord.AllowedMentions(roles=[ping] if ping else False, everyone=False),
        )
        await interaction.response.send_message(
            embed=ui.ok(f"announced in {channel.mention} - [jump]({sent.jump_url})"), ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Say(bot))
