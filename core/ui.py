"""Shared look and feel. Soft colours, small-caps titles, no emoji anywhere."""

from __future__ import annotations

import discord

from .smallcaps import small

ACCENT = 0xA9B7E0   # soft periwinkle
SUCCESS = 0x9ED8A6  # sage
WARN = 0xEFC97E     # muted amber
ERROR = 0xE59A9A    # dusty red
NEUTRAL = 0x2B2D31  # blends into dark theme


def embed(
    title: str | None = None,
    description: str | None = None,
    *,
    color: int = ACCENT,
    caps: bool = True,
) -> discord.Embed:
    """Build an embed with a small-caps title."""
    return discord.Embed(
        title=small(title) if (title and caps) else title,
        description=description,
        color=color,
    )


def ok(description: str, title: str = "done") -> discord.Embed:
    return embed(title, description, color=SUCCESS)


def warn(description: str, title: str = "heads up") -> discord.Embed:
    return embed(title, description, color=WARN)


def error(description: str, title: str = "cant do that") -> discord.Embed:
    return embed(title, description, color=ERROR)


def info(description: str, title: str | None = None) -> discord.Embed:
    return embed(title, description, color=ACCENT)


def bar(current: int, total: int, length: int = 18) -> str:
    """Text progress bar - no emoji, just block characters."""
    total = max(total, 1)
    filled = max(0, min(length, round(length * current / total)))
    return "".join(("█" if i < filled else "░") for i in range(length))


def user_line(user: discord.abc.User | discord.Member) -> str:
    """`name (id)` - safe for logs even after the user leaves."""
    return f"{user} (`{user.id}`)"


def trim(text: str, limit: int = 1000) -> str:
    text = text or ""
    return text if len(text) <= limit else text[: limit - 3] + "..."
