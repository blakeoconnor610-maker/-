"""Help, info commands, polls, and a couple of owner tools."""

from __future__ import annotations

import datetime as dt
import platform
import time

import discord
from discord import app_commands
from discord.ext import commands

from core import ui
from core.checks import staff_only
from core.netinfo import panel_state
from core.smallcaps import small

HELP_SECTIONS: dict[str, list[tuple[str, str]]] = {
    "getting started": [
        ("/setup", "build every channel and role in small caps, no emoji"),
        ("/config view", "see where logs, levels and tickets point"),
        ("/config channel", "move any of those somewhere else"),
        ("/ticketpanel", "post the open-a-ticket button anywhere"),
    ],
    "levels": [
        ("/rank", "your level, xp and place on the board"),
        ("/leaderboard", "top chatters"),
        ("/levels reward", "give a role at a level"),
        ("/levels give", "hand someone xp"),
        ("/levels set", "set someone to an exact level"),
        ("/levels noxp", "stop a channel giving xp"),
        ("/levels toggle", "turn leveling on or off"),
    ],
    "moderation": [
        ("/ban", "ban someone, optionally wiping their messages"),
        ("/unban", "lift a ban by user id"),
        ("/softban", "ban and instantly unban to clear messages"),
        ("/kick", "kick someone out"),
        ("/mute", "time someone out, like 10m or 7d"),
        ("/unmute", "lift it early"),
        ("/warn", "put a warning on their record"),
        ("/warnings", "read someones record"),
        ("/delwarn", "delete one warning"),
        ("/clearwarns", "wipe a whole record"),
        ("/purge", "bulk delete, filter by person or text"),
        ("/slowmode", "slow a channel down"),
        ("/lock", "stop everyone talking in a channel"),
        ("/unlock", "let them talk again"),
        ("/nick", "change a nickname"),
        ("/role add", "give someone a role"),
        ("/role remove", "take one away"),
    ],
    "tickets": [
        ("/ticket open", "open a private ticket with staff"),
        ("/ticket close", "close it and save a transcript"),
        ("/ticket add", "pull someone into a ticket"),
        ("/ticket remove", "take someone out"),
        ("/ticket rename", "rename the channel"),
    ],
    "talking as the bot": [
        ("/say", "post a message in any channel"),
        ("/embed", "post a tidy embed anywhere"),
        ("/edit", "edit something the bot posted"),
        ("/dm", "dm someone from the bot"),
        ("/announce", "announcement with an optional role ping"),
    ],
    "odds and ends": [
        ("/userinfo", "everything about a member"),
        ("/serverinfo", "everything about the server"),
        ("/avatar", "pull someones avatar"),
        ("/poll", "quick poll with buttons"),
        ("/smallcaps", "convert text to the small caps font"),
        ("/panel", "the address to put in the phone app"),
        ("/ping", "check the bot is alive"),
    ],
}


class HelpSelect(discord.ui.Select):
    def __init__(self) -> None:
        options = [
            discord.SelectOption(label=small(name), value=name, description=f"{len(cmds)} commands")
            for name, cmds in HELP_SECTIONS.items()
        ]
        super().__init__(placeholder=small("pick a section"), options=options)

    async def callback(self, interaction: discord.Interaction) -> None:
        section = self.values[0]
        body = "\n".join(f"`{name}` - {desc}" for name, desc in HELP_SECTIONS[section])
        await interaction.response.edit_message(embed=ui.embed(section, body))


class HelpView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=180)
        self.add_item(HelpSelect())


class PollView(discord.ui.View):
    def __init__(self, question: str, options: list[str], author: str) -> None:
        super().__init__(timeout=86400)
        self.question = question
        self.author = author
        self.options = options
        self.votes: dict[int, int] = {}
        for index, label in enumerate(options):
            self.add_item(PollButton(index, label))

    def tally(self) -> str:
        counts = [0] * len(self.options)
        for choice in self.votes.values():
            counts[choice] += 1
        total = sum(counts) or 1
        lines = []
        for index, label in enumerate(self.options):
            share = counts[index] / total
            lines.append(
                f"**{label}**\n`{ui.bar(counts[index], total)}` {counts[index]} "
                f"({share * 100:.0f}%)"
            )
        return "\n\n".join(lines) + f"\n\n{len(self.votes)} vote(s)"

    def render(self) -> discord.Embed:
        embed = ui.embed(
            "poll",
            f"**{self.question}**\n\npress a button to vote, you can change it.",
        )
        embed.add_field(name=small("results"), value=self.tally(), inline=False)
        embed.set_footer(text=f"started by {self.author}")
        return embed


class PollButton(discord.ui.Button):
    def __init__(self, index: int, label: str) -> None:
        super().__init__(label=label[:80], style=discord.ButtonStyle.secondary)
        self.index = index

    async def callback(self, interaction: discord.Interaction) -> None:
        view: PollView = self.view  # type: ignore[assignment]
        view.votes[interaction.user.id] = self.index
        await interaction.response.edit_message(embed=view.render(), view=view)


class Utility(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.started_at = time.time()

    @app_commands.command(name="help", description="every command the bot has")
    async def help_command(self, interaction: discord.Interaction) -> None:
        embed = ui.embed(
            "help",
            "pick a section below.\n\n"
            "brand new server? run `/setup` first - it builds every channel and role "
            "in the small caps font, sets up logging, levels and tickets, and tells you "
            "the one thing you have to do by hand afterwards.",
        )
        await interaction.response.send_message(embed=embed, view=HelpView(), ephemeral=True)

    @app_commands.command(name="ping", description="check the bot is alive")
    async def ping(self, interaction: discord.Interaction) -> None:
        uptime = int(time.time() - self.started_at)
        hours, remainder = divmod(uptime, 3600)
        minutes, seconds = divmod(remainder, 60)
        embed = ui.embed(
            "ping",
            f"**latency** {self.bot.latency * 1000:.0f}ms\n"
            f"**up for** {hours}h {minutes}m {seconds}s\n"
            f"**servers** {len(self.bot.guilds)}\n"
            f"**python** {platform.python_version()} / discord.py {discord.__version__}",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="userinfo", description="everything about a member")
    @app_commands.describe(user="who, defaults to you")
    @app_commands.guild_only()
    async def userinfo(self, interaction: discord.Interaction,
                       user: discord.Member | None = None) -> None:
        member = user or interaction.user
        assert isinstance(member, discord.Member) and interaction.guild is not None

        roles = [r.mention for r in reversed(member.roles) if r != interaction.guild.default_role]
        level_row = await self.bot.db.get_level(interaction.guild.id, member.id)  # type: ignore[attr-defined]
        warnings = list(await self.bot.db.warnings_for(interaction.guild.id, member.id))  # type: ignore[attr-defined]

        embed = ui.embed(str(member), color=member.colour.value or ui.ACCENT, caps=False)
        embed.add_field(name="id", value=f"`{member.id}`", inline=True)
        embed.add_field(name="nickname", value=member.nick or "none", inline=True)
        embed.add_field(name="bot", value="yes" if member.bot else "no", inline=True)
        embed.add_field(
            name="joined",
            value=f"<t:{int(member.joined_at.timestamp())}:R>" if member.joined_at else "unknown",
            inline=True,
        )
        embed.add_field(
            name="account made",
            value=f"<t:{int(member.created_at.timestamp())}:R>",
            inline=True,
        )
        embed.add_field(
            name="level",
            value=f"{level_row['level']} ({level_row['xp']} xp)",
            inline=True,
        )
        embed.add_field(name="warnings", value=str(len(warnings)), inline=True)
        if member.is_timed_out() and member.timed_out_until is not None:
            embed.add_field(
                name="muted until",
                value=f"<t:{int(member.timed_out_until.timestamp())}:f>",
                inline=True,
            )
        embed.add_field(
            name=f"roles ({len(roles)})",
            value=ui.trim(" ".join(roles), 1000) or "none",
            inline=False,
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="serverinfo", description="everything about this server")
    @app_commands.guild_only()
    async def serverinfo(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        assert guild is not None
        humans = sum(1 for m in guild.members if not m.bot)
        bots = guild.member_count - humans if guild.member_count else 0

        embed = ui.embed(guild.name)
        embed.add_field(name="id", value=f"`{guild.id}`", inline=True)
        embed.add_field(
            name="owner",
            value=guild.owner.mention if guild.owner else "unknown",
            inline=True,
        )
        embed.add_field(
            name="made",
            value=f"<t:{int(guild.created_at.timestamp())}:R>",
            inline=True,
        )
        embed.add_field(name="members", value=f"{humans} people, {bots} bots", inline=True)
        embed.add_field(
            name="channels",
            value=f"{len(guild.text_channels)} text, {len(guild.voice_channels)} voice",
            inline=True,
        )
        embed.add_field(name="roles", value=str(len(guild.roles)), inline=True)
        embed.add_field(
            name="boosts",
            value=f"level {guild.premium_tier}, {guild.premium_subscription_count} boosts",
            inline=True,
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="avatar", description="pull someones avatar")
    @app_commands.describe(user="who, defaults to you")
    @app_commands.guild_only()
    async def avatar(self, interaction: discord.Interaction,
                     user: discord.Member | None = None) -> None:
        member = user or interaction.user
        embed = ui.embed(str(member), caps=False)
        embed.set_image(url=member.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="smallcaps", description="convert text into the small caps font")
    @app_commands.describe(text="what to convert")
    async def smallcaps(self, interaction: discord.Interaction, text: str) -> None:
        converted = small(text)
        await interaction.response.send_message(
            embed=ui.embed("small caps", f"```\n{converted}\n```\n{converted}"),
            ephemeral=True,
        )

    @app_commands.command(name="poll", description="quick poll with buttons")
    @app_commands.describe(
        question="what you are asking",
        option1="first choice", option2="second choice",
        option3="third choice", option4="fourth choice", option5="fifth choice",
    )
    @app_commands.guild_only()
    async def poll(
        self,
        interaction: discord.Interaction,
        question: str,
        option1: str,
        option2: str,
        option3: str | None = None,
        option4: str | None = None,
        option5: str | None = None,
    ) -> None:
        options = [o for o in (option1, option2, option3, option4, option5) if o]
        view = PollView(question, options, str(interaction.user))
        await interaction.response.send_message(embed=view.render(), view=view)

    @app_commands.command(name="membercount", description="how many people are here")
    @app_commands.guild_only()
    async def membercount(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        assert guild is not None
        humans = sum(1 for m in guild.members if not m.bot)
        await interaction.response.send_message(
            embed=ui.embed(
                "member count",
                f"**{guild.member_count}** total\n**{humans}** people\n"
                f"**{(guild.member_count or 0) - humans}** bots",
            )
        )

    @app_commands.command(
        name="panel",
        description="the address to type into the phone app",
    )
    @app_commands.guild_only()
    async def panel(self, interaction: discord.Interaction) -> None:
        if not await self.bot.is_owner(interaction.user):
            await interaction.response.send_message(embed=ui.error("owner only"), ephemeral=True)
            return

        state = panel_state()

        if state["problem"]:
            body = (
                f"the panel is not running: **{state['problem']}**.\n\n"
                "open the bot's `.env`, set\n"
                "```\nPANEL_ENABLED=true\nPANEL_PORT=8080\n"
                "PANEL_PASSWORD=<a long random string>\n```\n"
                "then restart the bot and run this again."
            )
            await interaction.response.send_message(
                embed=ui.warn(body, title="panel is off"), ephemeral=True
            )
            return

        if state["addresses"]:
            addresses = "\n".join(f"`{address}`" for address in state["addresses"])
        else:
            addresses = (
                "i could not work out this machine's address. run `ip addr` "
                "(or `ipconfig` on windows) on the machine the bot is on and use "
                f"whatever starts with 192.168 or 10., with `:{state['port']}` on the end."
            )

        body = (
            "put one of these into the phone app, or any browser:\n\n"
            f"{addresses}\n\n"
            "your phone has to be on the same network as this machine. if there is "
            "more than one, try them in order - the first is usually right.\n\n"
            f"**listening on** `{state['host']}:{state['port']}`\n"
            f"**reachable by** {state['reach']}"
        )
        await interaction.response.send_message(
            embed=ui.embed("panel address", body), ephemeral=True
        )

    @app_commands.command(name="sync", description="owner only - refresh slash commands")
    @app_commands.guild_only()
    async def sync(self, interaction: discord.Interaction) -> None:
        if not await self.bot.is_owner(interaction.user):
            await interaction.response.send_message(
                embed=ui.error("owner only"), ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        assert interaction.guild is not None
        self.bot.tree.copy_global_to(guild=interaction.guild)
        synced = await self.bot.tree.sync(guild=interaction.guild)
        await interaction.followup.send(
            embed=ui.ok(f"synced {len(synced)} commands to this server"), ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Utility(bot))
