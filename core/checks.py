"""Permission checks used across the moderation and admin commands."""

from __future__ import annotations

import discord
from discord import app_commands


class NotStaff(app_commands.CheckFailure):
    """Raised when someone without staff access runs a staff command."""


async def is_staff_member(interaction: discord.Interaction) -> bool:
    """Staff = server owner, anyone with Manage Server, or the configured staff role."""
    member = interaction.user
    guild = interaction.guild
    if guild is None or not isinstance(member, discord.Member):
        return False
    if member.id == guild.owner_id:
        return True
    if member.guild_permissions.administrator or member.guild_permissions.manage_guild:
        return True
    config = await interaction.client.db.config(guild.id)  # type: ignore[attr-defined]
    staff_role_id = config.get("staff_role")
    return bool(staff_role_id and member.get_role(staff_role_id))


def staff_only():
    """Decorator form of :func:`is_staff_member`."""

    async def predicate(interaction: discord.Interaction) -> bool:
        if await is_staff_member(interaction):
            return True
        raise NotStaff("you need staff perms for that one")

    return app_commands.check(predicate)


def hierarchy_error(
    guild: discord.Guild,
    actor: discord.Member,
    target: discord.Member,
    action: str,
) -> str | None:
    """Return a human explanation if the action is not allowed, else None."""
    if target.id == actor.id:
        return f"you cant {action} yourself"
    if target.id == guild.me.id:
        return f"i am not going to {action} myself"
    if target.id == guild.owner_id:
        return f"cant {action} the server owner"
    if actor.id != guild.owner_id and target.top_role >= actor.top_role:
        return f"{target.mention} has a role at or above yours, so you cant {action} them"
    if target.top_role >= guild.me.top_role:
        return (
            f"my highest role is below {target.mention}'s - "
            "drag my role above theirs in server settings and try again"
        )
    return None
