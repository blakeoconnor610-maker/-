"""/config - point the bot at the channels and roles it should use."""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from core import ui
from core.checks import staff_only

CHANNEL_KEYS = {
    "logs": ("log_channel", "everything gets logged here"),
    "joins": ("join_channel", "joins and leaves"),
    "welcome": ("welcome_channel", "greeting for new members"),
    "levels": ("level_channel", "level up announcements"),
    "ticketlogs": ("ticket_log", "closed ticket transcripts"),
}


class Config(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    config_group = app_commands.Group(
        name="config",
        description="tell the bot which channels and roles to use",
        guild_only=True,
        default_permissions=discord.Permissions(manage_guild=True),
    )

    @config_group.command(name="view", description="see the current setup")
    @staff_only()
    async def view(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        assert guild is not None
        config = await self.bot.db.config(guild.id)  # type: ignore[attr-defined]

        def channel(column: str) -> str:
            channel_id = config.get(column)
            found = guild.get_channel(channel_id) if channel_id else None
            return found.mention if found else "not set"

        def role(column: str) -> str:
            role_id = config.get(column)
            found = guild.get_role(role_id) if role_id else None
            return found.mention if found else "not set"

        embed = ui.embed("config", f"everything **{guild.name}** is wired up to right now")
        embed.add_field(
            name="channels",
            value=(
                f"logs {channel('log_channel')}\n"
                f"joins and leaves {channel('join_channel')}\n"
                f"welcome {channel('welcome_channel')}\n"
                f"level ups {channel('level_channel')}\n"
                f"ticket logs {channel('ticket_log')}"
            ),
            inline=False,
        )
        embed.add_field(
            name="roles",
            value=(
                f"staff {role('staff_role')}\n"
                f"member {role('member_role')}\n"
                f"muted {role('muted_role')}\n"
                f"autorole {role('autorole')}"
            ),
            inline=False,
        )
        embed.add_field(
            name="leveling",
            value=(
                f"{'on' if config.get('levels_enabled') else 'off'} - "
                f"{config.get('xp_min')} to {config.get('xp_max')} xp every "
                f"{config.get('xp_cooldown')}s, "
                f"ping on level up {'yes' if config.get('level_ping') else 'no'}"
            ),
            inline=False,
        )
        tickets_cat = guild.get_channel(config.get("ticket_category") or 0)
        embed.add_field(
            name="tickets",
            value=f"open under **{tickets_cat.name if tickets_cat else 'not set'}**, "
                  f"{config.get('ticket_counter', 0)} opened so far",
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @config_group.command(name="channel", description="point one of the bot channels somewhere")
    @app_commands.describe(which="which one", channel="the channel to use")
    @app_commands.choices(
        which=[app_commands.Choice(name=name, value=name) for name in CHANNEL_KEYS]
    )
    @staff_only()
    async def set_channel(
        self,
        interaction: discord.Interaction,
        which: app_commands.Choice[str],
        channel: discord.TextChannel,
    ) -> None:
        assert interaction.guild is not None
        column, label = CHANNEL_KEYS[which.value]
        await self.bot.db.set_config(interaction.guild.id, **{column: channel.id})  # type: ignore[attr-defined]
        await interaction.response.send_message(
            embed=ui.ok(f"{label} now go to {channel.mention}"), ephemeral=True
        )

    @config_group.command(name="staffrole", description="which role counts as staff")
    @staff_only()
    async def staff_role(self, interaction: discord.Interaction, role: discord.Role) -> None:
        assert interaction.guild is not None
        await self.bot.db.set_config(interaction.guild.id, staff_role=role.id)  # type: ignore[attr-defined]
        await interaction.response.send_message(
            embed=ui.ok(f"{role.mention} is the staff role"), ephemeral=True
        )

    @config_group.command(name="mutedrole", description="role used for long mutes")
    @staff_only()
    async def muted_role(self, interaction: discord.Interaction, role: discord.Role) -> None:
        assert interaction.guild is not None
        await self.bot.db.set_config(interaction.guild.id, muted_role=role.id)  # type: ignore[attr-defined]
        await interaction.response.send_message(
            embed=ui.ok(f"{role.mention} is the muted role"), ephemeral=True
        )

    @config_group.command(name="ticketcategory", description="where ticket channels get made")
    @staff_only()
    async def ticket_category(self, interaction: discord.Interaction,
                              category: discord.CategoryChannel) -> None:
        assert interaction.guild is not None
        await self.bot.db.set_config(interaction.guild.id, ticket_category=category.id)  # type: ignore[attr-defined]
        await interaction.response.send_message(
            embed=ui.ok(f"tickets open under **{category.name}**"), ephemeral=True
        )

    @config_group.command(name="xp", description="tune how fast people level")
    @app_commands.describe(
        minimum="lowest xp per message",
        maximum="highest xp per message",
        cooldown="seconds between xp gains",
        ping="ping people when they level up",
    )
    @staff_only()
    async def xp(
        self,
        interaction: discord.Interaction,
        minimum: app_commands.Range[int, 1, 500] | None = None,
        maximum: app_commands.Range[int, 1, 500] | None = None,
        cooldown: app_commands.Range[int, 0, 3600] | None = None,
        ping: bool | None = None,
    ) -> None:
        assert interaction.guild is not None
        updates: dict[str, int] = {}
        if minimum is not None:
            updates["xp_min"] = minimum
        if maximum is not None:
            updates["xp_max"] = maximum
        if cooldown is not None:
            updates["xp_cooldown"] = cooldown
        if ping is not None:
            updates["level_ping"] = int(ping)
        if not updates:
            await interaction.response.send_message(
                embed=ui.info("give me at least one thing to change"), ephemeral=True
            )
            return
        if "xp_min" in updates and "xp_max" in updates and updates["xp_min"] > updates["xp_max"]:
            await interaction.response.send_message(
                embed=ui.error("minimum cant be bigger than maximum"), ephemeral=True
            )
            return
        await self.bot.db.set_config(interaction.guild.id, **updates)  # type: ignore[attr-defined]
        await interaction.response.send_message(embed=ui.ok("xp settings updated"), ephemeral=True)

    @config_group.command(name="reset", description="forget every setting for this server")
    @staff_only()
    async def reset(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        assert guild is not None
        await self.bot.db.execute("DELETE FROM guild_config WHERE guild_id = ?", guild.id)  # type: ignore[attr-defined]
        self.bot.db._config_cache.pop(guild.id, None)  # type: ignore[attr-defined]
        await interaction.response.send_message(
            embed=ui.ok("settings wiped. channels and roles are untouched - run `/setup` to rewire."),
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Config(bot))
