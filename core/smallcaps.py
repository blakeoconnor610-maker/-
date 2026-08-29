"""Small-caps text conversion.

Discord force-lowercases channel names, but only for real ASCII letters.
Unicode small capitals are not ASCII letters, so they survive untouched -
that is how servers get the "small font capital" look.
"""

from __future__ import annotations

_MAP = {
    "a": "ᴀ", "b": "ʙ", "c": "ᴄ", "d": "ᴅ", "e": "ᴇ",
    "f": "ꜰ", "g": "ɢ", "h": "ʜ", "i": "ɪ", "j": "ᴊ",
    "k": "ᴋ", "l": "ʟ", "m": "ᴍ", "n": "ɴ", "o": "ᴏ",
    "p": "ᴘ", "q": "ǫ", "r": "ʀ", "s": "ꜱ", "t": "ᴛ",
    "u": "ᴜ", "v": "ᴠ", "w": "ᴡ", "x": "x",      "y": "ʏ",
    "z": "ᴢ",
}

_REVERSE = {v: k for k, v in _MAP.items()}


def small(text: str) -> str:
    """Convert text to small caps, leaving anything unmappable alone."""
    return "".join(_MAP.get(ch, _MAP.get(ch.lower(), ch)) if ch.isalpha() else ch for ch in text)


def unsmall(text: str) -> str:
    """Turn small caps back into plain lowercase ascii."""
    return "".join(_REVERSE.get(ch, ch) for ch in text)


def channel_name(text: str) -> str:
    """Small-caps a channel name and swap spaces for dashes, like Discord does."""
    return small(text.strip().lower()).replace(" ", "-")
