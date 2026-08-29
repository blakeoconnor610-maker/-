"""/setup - builds the whole server in one go.

Every name is written in small capitals and there is not a single emoji
anywhere. Running it twice is safe: anything that already exists is reused
instead of duplicated.
"""

from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from core import ui
from core.smallcaps import channel_name, small

log = logging.getLogger("bot.setup")

# ---------------------------------------------------------------- roles ----
# Highest first. Discord drops each new role at the bottom of the list, so
# creating them in this order leaves the stack in the right shape.
ROLES: list[dict] = [
    {"key": "owner",   "name": "owner",   "color": 0xE8A0A0, "hoist": True,
     "perms": {"administrator": True}},
    {"key": "admin",   "name": "admin",   "color": 0xE0B88A, "hoist": True,
     "perms": {"administrator": True}},
    {"key": "mod",     "name": "mod",     "color": 0xA9B7E0, "hoist": True,
     "perms": {
         "kick_members": True, "ban_members": True, "moderate_members": True,
         "manage_messages": True, "manage_nicknames": True, "manage_threads": True,
         "mute_members": True, "deafen_members": True, "move_members": True,
         "view_audit_log": True, "manage_channels": False,
     }},
    {"key": "helper",  "name": "helper",  "color": 0x9ED8A6, "hoist": True,
     "perms": {"manage_messages": True, "moderate_members": True, "manage_threads": True}},
    {"key": "booster", "name": "booster", "color": 0xE2A9E0, "hoist": True, "perms": {}},
    {"key": "vip",     "name": "vip",     "color": 0xEFC97E, "hoist": True, "perms": {}},
    {"key": "lvl100",  "name": "lvl 100", "color": 0xC7A0E8, "hoist": False, "perms": {}, "level": 100},
    {"key": "lvl75",   "name": "lvl 75",  "color": 0xB6A6E4, "hoist": False, "perms": {}, "level": 75},
    {"key": "lvl50",   "name": "lvl 50",  "color": 0xA6ACE0, "hoist": False, "perms": {}, "level": 50},
    {"key": "lvl30",   "name": "lvl 30",  "color": 0x9DBBDD, "hoist": False, "perms": {}, "level": 30},
    {"key": "lvl20",   "name": "lvl 20",  "color": 0x97C9D6, "hoist": False, "perms": {}, "level": 20},
    {"key": "lvl10",   "name": "lvl 10",  "color": 0x95D3C4, "hoist": False, "perms": {}, "level": 10},
    {"key": "lvl5",    "name": "lvl 5",   "color": 0x9AD7AE, "hoist": False, "perms": {}, "level": 5},
    {"key": "member",  "name": "member",  "color": 0xB5BAC1, "hoist": False, "perms": {}},
    {"key": "muted",   "name": "muted",   "color": 0x5C5F66, "hoist": False, "perms": {}},
]

STAFF_KEYS = ("owner", "admin", "mod", "helper")

# ------------------------------------------------------------- channels ----
# access:
#   "open"      - everyone can read and talk
#   "read"      - everyone can read, only staff can talk
#   "staff"     - staff only, hidden from everyone else
#   "tickets"   - hidden holding pen for open ticket channels
LAYOUT: list[dict] = [
    {
        "category": "info",
        "access": "read",
        "channels": [
            {"name": "welcome", "key": "welcome",
             "topic": "new people land here"},
            {"name": "rules", "key": "rules",
             "topic": "the short version: be normal"},
            {"name": "announcements", "key": "announcements",
             "topic": "server news"},
            {"name": "roles", "key": "roles",
             "topic": "grab your roles"},
        ],
    },
    {
        "category": "chat",
        "access": "open",
        "channels": [
            {"name": "general", "key": "general", "topic": "main chat, keep it chill"},
            {"name": "media", "key": "media", "topic": "pics, clips, memes"},
            {"name": "music", "key": "music_chat", "topic": "what are you listening to"},
            {"name": "vent", "key": "vent", "topic": "bad day? drop it here"},
            {"name": "counting", "key": "counting", "topic": "count up, dont break the chain"},
            {"name": "commands", "key": "commands", "topic": "spam bot commands in here"},
        ],
    },
    {
        "category": "levels",
        "access": "read",
        "channels": [
            {"name": "level up", "key": "level_up", "topic": "level ups get posted here"},
            {"name": "leaderboard", "key": "leaderboard", "topic": "top chatters"},
        ],
    },
    {
        "category": "support",
        "access": "read",
        "channels": [
            {"name": "create a ticket", "key": "ticket_panel",
             "topic": "press the button to open a private ticket with staff"},
        ],
    },
    {
        "category": "tickets",
        "access": "tickets",
        "channels": [],
    },
    {
        "category": "voice",
        "access": "open",
        "channels": [
            {"name": "chill", "key": "vc_chill", "voice": True},
            {"name": "gaming", "key": "vc_gaming", "voice": True},
            {"name": "music", "key": "vc_music", "voice": True},
            {"name": "afk", "key": "vc_afk", "voice": True},
        ],
    },
    {
        "category": "staff",
        "access": "staff",
        "channels": [
            {"name": "staff chat", "key": "staff_chat", "topic": "staff only"},
            {"name": "server logs", "key": "server_logs",
             "topic": "deletes, edits, joins, bans, everything"},
            {"name": "mod logs", "key": "mod_logs", "topic": "punishments"},
            {"name": "join leave", "key": "join_leave", "topic": "who came and who left"},
            {"name": "ticket logs", "key": "ticket_logs", "topic": "closed ticket transcripts"},
        ],
    },
]

RULES_TEXT = (
    "**1.** be decent to people. no harassment, slurs, or targeting anyone.\n"
    "**2.** no nsfw, gore, or anything you would not want on your screen at work.\n"
    "**3.** keep drama in dms. do not drag it into chat.\n"
    "**4.** no spam, no mass pings, no self promo without asking.\n"
    "**5.** use channels for what they say on the tin.\n"
    "**6.** do not ping staff for nothing, open a ticket instead.\n"
    "**7.** discord terms of service and community guidelines apply on top of all this.\n\n"
    "staff have the final call. if something feels off, open a ticket."
)


class ConfirmSetup(discord.ui.View):
    def __init__(self, author_id: int) -> None:
        super().__init__(timeout=90)
        self.author_id = author_id
        self.value: bool | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                embed=ui.error("this isnt your setup prompt"), ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="build it", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.value = True
        for child in self.children:
            child.disabled = True  # type: ignore[attr-defined]
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.value = False
        for child in self.children:
            child.disabled = True  # type: ignore[attr-defined]
        await interaction.response.edit_message(view=self)
        self.stop()


class Setup(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ---------------------------------------------------------- helpers ----

    @staticmethod
    def _find_role(guild: discord.Guild, name: str) -> discord.Role | None:
        return discord.utils.get(guild.roles, name=name)

    @staticmethod
    def _find_channel(guild: discord.Guild, name: str):
        return discord.utils.get(guild.channels, name=name)

    async def _ensure_roles(self, guild: discord.Guild, created: list[str]) -> dict[str, discord.Role]:
        roles: dict[str, discord.Role] = {}
        for spec in ROLES:
            name = small(spec["name"])
            existing = self._find_role(guild, name)
            if existing is not None:
                roles[spec["key"]] = existing
                continue
            perms = discord.Permissions(**spec["perms"]) if spec["perms"] else discord.Permissions.none()
            role = await guild.create_role(
                name=name,
                colour=discord.Colour(spec["color"]),
                hoist=spec["hoist"],
                mentionable=False,
                permissions=perms,
                reason="server setup",
            )
            roles[spec["key"]] = role
            created.append(f"role {name}")
        return roles

    def _overwrites(
        self,
        guild: discord.Guild,
        roles: dict[str, discord.Role],
        access: str,
    ) -> dict[discord.abc.Snowflake, discord.PermissionOverwrite]:
        everyone = guild.default_role
        muted = roles.get("muted")
        staff_roles = [roles[key] for key in STAFF_KEYS if key in roles]

        overwrites: dict[discord.abc.Snowflake, discord.PermissionOverwrite] = {}

        if access == "open":
            overwrites[everyone] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True,
                add_reactions=True, connect=True, speak=True,
            )
        elif access == "read":
            overwrites[everyone] = discord.PermissionOverwrite(
                view_channel=True, send_messages=False, read_message_history=True,
                add_reactions=False, create_public_threads=False, create_private_threads=False,
            )
            for role in staff_roles:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, manage_messages=True
                )
        else:  # staff / tickets
            overwrites[everyone] = discord.PermissionOverwrite(view_channel=False)
            for role in staff_roles:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True,
                    manage_messages=True, attach_files=True, embed_links=True,
                )

        if muted is not None:
            overwrites[muted] = discord.PermissionOverwrite(
                send_messages=False, add_reactions=False, speak=False,
                create_public_threads=False, create_private_threads=False,
                send_messages_in_threads=False,
            )

        me = guild.me
        if me is not None:
            overwrites[me] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, embed_links=True,
                attach_files=True, manage_messages=True, read_message_history=True,
            )
        return overwrites

    async def _ensure_layout(
        self,
        guild: discord.Guild,
        roles: dict[str, discord.Role],
        created: list[str],
    ) -> dict[str, discord.abc.GuildChannel]:
        found: dict[str, discord.abc.GuildChannel] = {}

        for block in LAYOUT:
            cat_name = small(block["category"])
            overwrites = self._overwrites(guild, roles, block["access"])

            category = discord.utils.get(guild.categories, name=cat_name)
            if category is None:
                category = await guild.create_category(
                    name=cat_name, overwrites=overwrites, reason="server setup"
                )
                created.append(f"category {cat_name}")
            else:
                try:
                    await category.edit(overwrites=overwrites, reason="server setup")
                except discord.Forbidden:
                    pass
            found[f"cat_{block['category'].replace(' ', '_')}"] = category

            for channel_spec in block["channels"]:
                name = channel_name(channel_spec["name"])
                existing = self._find_channel(guild, name)
                if existing is not None:
                    found[channel_spec["key"]] = existing
                    continue
                if channel_spec.get("voice"):
                    channel = await guild.create_voice_channel(
                        name=name, category=category, reason="server setup"
                    )
                else:
                    channel = await guild.create_text_channel(
                        name=name,
                        category=category,
                        topic=channel_spec.get("topic"),
                        reason="server setup",
                    )
                found[channel_spec["key"]] = channel
                created.append(f"channel {name}")

        return found

    async def _seed_content(
        self,
        guild: discord.Guild,
        channels: dict[str, discord.abc.GuildChannel],
        roles: dict[str, discord.Role],
    ) -> None:
        """Drop the starter embeds in, but only if the channel is still empty."""
        from cogs.tickets import TicketPanelView

        async def empty(channel: discord.abc.GuildChannel) -> bool:
            if not isinstance(channel, discord.TextChannel):
                return False
            me = guild.me
            if me is None or not channel.permissions_for(me).read_message_history:
                return False
            async for _ in channel.history(limit=1):
                return False
            return True

        welcome = channels.get("welcome")
        if isinstance(welcome, discord.TextChannel) and await empty(welcome):
            embed = ui.embed(
                f"welcome to {guild.name}",
                "chill server, no pressure. say hi in "
                f"{channels['general'].mention if 'general' in channels else 'general'} "
                "whenever you feel like it.\n\n"
                "read the rules, grab a role, talk when you want. thats it.",
            )
            await welcome.send(embed=embed)

        rules = channels.get("rules")
        if isinstance(rules, discord.TextChannel) and await empty(rules):
            await rules.send(embed=ui.embed("rules", RULES_TEXT))

        leaderboard = channels.get("leaderboard")
        if isinstance(leaderboard, discord.TextChannel) and await empty(leaderboard):
            await leaderboard.send(
                embed=ui.embed(
                    "leaderboard",
                    "run `/leaderboard` to see the top chatters, or `/rank` for your own.",
                )
            )

        roles_channel = channels.get("roles")
        if isinstance(roles_channel, discord.TextChannel) and await empty(roles_channel):
            level_lines = "\n".join(
                f"{roles[spec['key']].mention} at level {spec['level']}"
                for spec in ROLES
                if spec.get("level") and spec["key"] in roles
            )
            await roles_channel.send(
                embed=ui.embed(
                    "roles",
                    "level roles unlock on their own as you talk:\n\n" + level_lines,
                )
            )

        panel = channels.get("ticket_panel")
        if isinstance(panel, discord.TextChannel) and await empty(panel):
            await panel.send(
                embed=ui.embed(
                    "support",
                    "need staff? press the button and a private channel opens "
                    "with just you and the team in it.\n\n"
                    "one ticket at a time per person.",
                ),
                view=TicketPanelView(self.bot),
            )

    # --------------------------------------------------------- commands ----

    @app_commands.command(
        name="setup",
        description="build every channel and role for a chill server, in small caps",
    )
    @app_commands.describe(
        assign_me="give you the top staff role when it is done",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def setup_command(self, interaction: discord.Interaction, assign_me: bool = True) -> None:
        guild = interaction.guild
        assert guild is not None

        me = guild.me
        if me is None or not me.guild_permissions.manage_channels or not me.guild_permissions.manage_roles:
            await interaction.response.send_message(
                embed=ui.error(
                    "i need **manage channels** and **manage roles** before i can build anything.\n"
                    "give me those in server settings, then run `/setup` again."
                ),
                ephemeral=True,
            )
            return

        preview = (
            f"about to build **{len(ROLES)} roles** and "
            f"**{sum(len(b['channels']) for b in LAYOUT)} channels** across "
            f"**{len(LAYOUT)} categories**, all in small caps, no emoji.\n\n"
            "nothing gets deleted. anything already named the same is left alone, "
            "so you can run this again later without making duplicates."
        )
        view = ConfirmSetup(interaction.user.id)
        await interaction.response.send_message(embed=ui.embed("setup", preview), view=view)
        await view.wait()

        if not view.value:
            await interaction.edit_original_response(
                embed=ui.info("cancelled, nothing was changed."), view=None
            )
            return

        await interaction.edit_original_response(
            embed=ui.info("building. this takes a minute, discord rate limits me."), view=None
        )

        created: list[str] = []
        try:
            roles = await self._ensure_roles(guild, created)
            channels = await self._ensure_layout(guild, roles, created)
        except discord.Forbidden:
            await interaction.edit_original_response(
                embed=ui.error(
                    "discord blocked me partway through. drag my role to the top of the "
                    "role list in server settings and run `/setup` again - it will pick up "
                    "where it stopped."
                )
            )
            return

        # Save everything the other features need to know about.
        config: dict[str, int] = {}
        mapping = {
            "log_channel": "server_logs",
            "join_channel": "join_leave",
            "welcome_channel": "welcome",
            "level_channel": "level_up",
            "ticket_log": "ticket_logs",
        }
        for column, key in mapping.items():
            channel = channels.get(key)
            if channel is not None:
                config[column] = channel.id
        tickets_cat = channels.get("cat_tickets")
        if tickets_cat is not None:
            config["ticket_category"] = tickets_cat.id
        for column, key in (("staff_role", "mod"), ("member_role", "member"), ("muted_role", "muted")):
            if key in roles:
                config[column] = roles[key].id
        if "member" in roles:
            config["autorole"] = roles["member"].id
        await self.bot.db.set_config(guild.id, **config)

        for spec in ROLES:
            if spec.get("level") and spec["key"] in roles:
                await self.bot.db.set_level_role(guild.id, spec["level"], roles[spec["key"]].id)

        # Bot spam should not earn xp. Guarded so re-running setup does not toggle it back on.
        commands_channel = channels.get("commands")
        if commands_channel is not None:
            blocked = await self.bot.db.no_xp_channels(guild.id)
            if commands_channel.id not in blocked:
                await self.bot.db.toggle_no_xp(guild.id, commands_channel.id)

        try:
            await self._seed_content(guild, channels, roles)
        except discord.Forbidden:
            pass

        if assign_me and isinstance(interaction.user, discord.Member) and "owner" in roles:
            try:
                await interaction.user.add_roles(roles["owner"], reason="server setup")
            except discord.Forbidden:
                pass

        summary = (
            f"made **{len(created)}** new things"
            + (" (everything else was already there)" if len(created) < 10 else "")
            + ".\n\n"
            "**wired up for you**\n"
            f"logs go to {channels['server_logs'].mention if 'server_logs' in channels else 'nowhere yet'}\n"
            f"joins and leaves go to {channels['join_leave'].mention if 'join_leave' in channels else 'nowhere yet'}\n"
            f"level ups go to {channels['level_up'].mention if 'level_up' in channels else 'nowhere yet'}\n"
            f"tickets open under {small('tickets')}\n\n"
            "**one thing left**\n"
            "drag my role above every role you want me to be able to moderate, "
            "otherwise discord will not let me ban or mute those people.\n\n"
            "run `/config view` any time to see or change where things point."
        )
        await interaction.edit_original_response(embed=ui.ok(summary, title="server is ready"))
        log.info("setup finished in %s, created %d objects", guild.id, len(created))

    @app_commands.command(
        name="ticketpanel",
        description="post the open-a-ticket button in a channel",
    )
    @app_commands.describe(channel="where to put it, defaults to right here")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def ticket_panel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel | None = None,
    ) -> None:
        from cogs.tickets import TicketPanelView

        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.response.send_message(
                embed=ui.error("pick a normal text channel"), ephemeral=True
            )
            return
        await target.send(
            embed=ui.embed(
                "support",
                "need staff? press the button and a private channel opens "
                "with just you and the team in it.",
            ),
            view=TicketPanelView(self.bot),
        )
        await interaction.response.send_message(
            embed=ui.ok(f"panel posted in {target.mention}"), ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Setup(bot))
