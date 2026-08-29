"""Turn things like `10m`, `1h30m`, `7d` into seconds."""

from __future__ import annotations

import re

_UNITS = {
    "s": 1, "sec": 1, "secs": 1, "second": 1, "seconds": 1,
    "m": 60, "min": 60, "mins": 60, "minute": 60, "minutes": 60,
    "h": 3600, "hr": 3600, "hrs": 3600, "hour": 3600, "hours": 3600,
    "d": 86400, "day": 86400, "days": 86400,
    "w": 604800, "week": 604800, "weeks": 604800,
}

_PATTERN = re.compile(r"(\d+)\s*([a-z]+)")


def parse_duration(text: str) -> int | None:
    """Seconds, or None if it does not look like a duration at all."""
    if not text:
        return None
    text = text.strip().lower().replace(" ", "")
    if text.isdigit():  # bare number means minutes
        return int(text) * 60
    total = 0
    matched = False
    for amount, unit in _PATTERN.findall(text):
        if unit not in _UNITS:
            return None
        total += int(amount) * _UNITS[unit]
        matched = True
    return total if matched and total > 0 else None


def human_duration(seconds: int) -> str:
    if seconds <= 0:
        return "0s"
    parts: list[str] = []
    for label, size in (("w", 604800), ("d", 86400), ("h", 3600), ("m", 60), ("s", 1)):
        if seconds >= size:
            count, seconds = divmod(seconds, size)
            parts.append(f"{count}{label}")
    return " ".join(parts[:3])
