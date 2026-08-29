"""Entry point. Run with:  python bot.py"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import traceback

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from core import ui
from core.checks import NotStaff
from core.db import Database

load_dotenv()

log = logging.getLogger("bot")

EXTENSIONS = (
    "cogs.setup",
    "cogs.config",
    "cogs.levels",
    "cogs.moderation",
    "cogs.tickets",
    "cogs.logs",
    "cogs.welcome",
    "cogs.say",
    "cogs.utility",
)


def _int_env(name: str) -> int | None:
    raw = (os.getenv(name) or "").strip()
    return int(raw) if raw.isdigit() else None


class ChillBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.members = True          # joins, leaves, role changes
        intents.message_content = True  # leveling + delete/edit logs
        intents.guilds = True

        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            help_command=None,
            allowed_mentions=discord.AllowedMentions(
                everyone=False, roles=False, users=True, replied_user=True
            ),
            activity=discord.Activity(
                type=discord.ActivityType.listening, name="/help"
            ),
        )
        self.db = Database(os.getenv("DATABASE_PATH", "data/bot.db"))
        self.owner_id_override = _int_env("OWNER_ID")
        self.dev_guild_id = _int_env("DEV_GUILD_ID")
        self.panel_runner = None

    # ---------- lifecycle ----------

    async def setup_hook(self) -> None:
        await self.db.connect()
        log.info("database ready at %s", self.db.path)

        for extension in EXTENSIONS:
            try:
                await self.load_extension(extension)
                log.info("loaded %s", extension)
            except Exception:
                log.exception("failed to load %s", extension)

        # Ticket buttons have to survive restarts, so register the views up front.
        from cogs.tickets import TicketPanelView, TicketControlView

        self.add_view(TicketPanelView(self))
        self.add_view(TicketControlView(self))

        if self.dev_guild_id:
            guild = discord.Object(id=self.dev_guild_id)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            log.info("synced %d commands to dev guild %s", len(synced), self.dev_guild_id)
        else:
            synced = await self.tree.sync()
            log.info("synced %d commands globally (can take up to an hour to show up)", len(synced))

        if os.getenv("PANEL_ENABLED", "false").lower() in ("1", "true", "yes"):
            from panel.server import start_panel

            try:
                self.panel_runner = await start_panel(self)
            except Exception:
                log.exception("control panel failed to start")

    async def close(self) -> None:
        if self.panel_runner is not None:
            await self.panel_runner.cleanup()
        await self.db.close()
        await super().close()

    async def on_ready(self) -> None:
        assert self.user is not None
        log.info("logged in as %s (%s)", self.user, self.user.id)
        log.info("serving %d guild(s)", len(self.guilds))

    async def is_owner(self, user: discord.abc.User) -> bool:  # type: ignore[override]
        if self.owner_id_override and user.id == self.owner_id_override:
            return True
        return await super().is_owner(user)

    # ---------- helpers used by the cogs ----------

    async def log_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        config = await self.db.config(guild.id)
        channel_id = config.get("log_channel")
        if not channel_id:
            return None
        channel = guild.get_channel(channel_id)
        return channel if isinstance(channel, discord.TextChannel) else None

    async def send_log(self, guild: discord.Guild, embed: discord.Embed, content: str | None = None) -> None:
        channel = await self.log_channel(guild)
        if channel is None:
            return
        me = guild.me
        if me is None or not channel.permissions_for(me).send_messages:
            return
        try:
            await channel.send(content=content, embed=embed)
        except discord.HTTPException:
            log.warning("could not write to the log channel in %s", guild.id)


bot = ChillBot()


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, err: app_commands.AppCommandError) -> None:
    """One place to turn every command failure into a readable reply."""
    if isinstance(err, app_commands.CommandInvokeError):
        err = err.original  # type: ignore[assignment]

    if isinstance(err, NotStaff):
        message = str(err)
    elif isinstance(err, app_commands.MissingPermissions):
        missing = ", ".join(p.replace("_", " ") for p in err.missing_permissions)
        message = f"you need these perms: {missing}"
    elif isinstance(err, app_commands.BotMissingPermissions):
        missing = ", ".join(p.replace("_", " ") for p in err.missing_permissions)
        message = f"i am missing these perms: {missing}"
    elif isinstance(err, app_commands.CommandOnCooldown):
        message = f"slow down, try again in {err.retry_after:.0f}s"
    elif isinstance(err, app_commands.CheckFailure):
        message = "you cant use that command"
    elif isinstance(err, discord.Forbidden):
        message = "discord blocked that - check my role position and permissions"
    else:
        message = "something broke on my end, it got logged"
        log.error("unhandled command error", exc_info=err)
        traceback.print_exception(type(err), err, err.__traceback__, file=sys.stderr)

    embed = ui.error(message)
    try:
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)
    except discord.HTTPException:
        pass


def main() -> None:
    token = (os.getenv("DISCORD_TOKEN") or "").strip()
    if not token:
        sys.exit(
            "DISCORD_TOKEN is not set.\n"
            "Copy .env.example to .env and paste your bot token into it."
        )
    discord.utils.setup_logging(level=logging.INFO, root=False)
    logging.getLogger("bot").setLevel(logging.INFO)
    try:
        bot.run(token, log_handler=None)
    except discord.LoginFailure:
        sys.exit("Discord rejected that token. Reset it in the developer portal and update .env.")


if __name__ == "__main__":
    main()
