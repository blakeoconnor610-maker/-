"""SQLite storage. One file, no external database to run."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Iterable, Optional

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS guild_config (
    guild_id          INTEGER PRIMARY KEY,
    log_channel       INTEGER,
    join_channel      INTEGER,
    welcome_channel   INTEGER,
    level_channel     INTEGER,
    ticket_category   INTEGER,
    ticket_log        INTEGER,
    staff_role        INTEGER,
    member_role       INTEGER,
    muted_role        INTEGER,
    autorole          INTEGER,
    levels_enabled    INTEGER NOT NULL DEFAULT 1,
    xp_min            INTEGER NOT NULL DEFAULT 15,
    xp_max            INTEGER NOT NULL DEFAULT 25,
    xp_cooldown       INTEGER NOT NULL DEFAULT 60,
    level_ping        INTEGER NOT NULL DEFAULT 1,
    welcome_message   TEXT,
    ticket_counter    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS levels (
    guild_id   INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    xp         INTEGER NOT NULL DEFAULT 0,
    level      INTEGER NOT NULL DEFAULT 0,
    messages   INTEGER NOT NULL DEFAULT 0,
    last_gain  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS level_roles (
    guild_id INTEGER NOT NULL,
    level    INTEGER NOT NULL,
    role_id  INTEGER NOT NULL,
    PRIMARY KEY (guild_id, level)
);

CREATE TABLE IF NOT EXISTS no_xp_channels (
    guild_id   INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    PRIMARY KEY (guild_id, channel_id)
);

CREATE TABLE IF NOT EXISTS tickets (
    channel_id INTEGER PRIMARY KEY,
    guild_id   INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    number     INTEGER NOT NULL,
    topic      TEXT,
    open       INTEGER NOT NULL DEFAULT 1,
    claimed_by INTEGER,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS warnings (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id   INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    mod_id     INTEGER NOT NULL,
    reason     TEXT,
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_warnings_user ON warnings (guild_id, user_id);
CREATE INDEX IF NOT EXISTS idx_levels_xp ON levels (guild_id, xp DESC);
"""

CONFIG_COLUMNS = (
    "log_channel", "join_channel", "welcome_channel", "level_channel",
    "ticket_category", "ticket_log", "staff_role", "member_role",
    "muted_role", "autorole", "levels_enabled", "xp_min", "xp_max",
    "xp_cooldown", "level_ping", "welcome_message", "ticket_counter",
)


class Database:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self._conn: Optional[aiosqlite.Connection] = None
        self._config_cache: dict[int, dict[str, Any]] = {}

    async def connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")
        await self._conn.executescript(SCHEMA)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database.connect() was never awaited")
        return self._conn

    # ---------- tiny query helpers ----------

    async def execute(self, query: str, *args: Any) -> None:
        await self.conn.execute(query, args)
        await self.conn.commit()

    async def fetchone(self, query: str, *args: Any) -> Optional[aiosqlite.Row]:
        async with self.conn.execute(query, args) as cur:
            return await cur.fetchone()

    async def fetchall(self, query: str, *args: Any) -> Iterable[aiosqlite.Row]:
        async with self.conn.execute(query, args) as cur:
            return await cur.fetchall()

    async def fetchval(self, query: str, *args: Any, default: Any = None) -> Any:
        row = await self.fetchone(query, *args)
        return row[0] if row is not None else default

    # ---------- guild config ----------

    async def config(self, guild_id: int) -> dict[str, Any]:
        cached = self._config_cache.get(guild_id)
        if cached is not None:
            return cached
        row = await self.fetchone("SELECT * FROM guild_config WHERE guild_id = ?", guild_id)
        if row is None:
            await self.execute("INSERT OR IGNORE INTO guild_config (guild_id) VALUES (?)", guild_id)
            row = await self.fetchone("SELECT * FROM guild_config WHERE guild_id = ?", guild_id)
        data = dict(row)  # type: ignore[arg-type]
        self._config_cache[guild_id] = data
        return data

    async def set_config(self, guild_id: int, **values: Any) -> None:
        bad = set(values) - set(CONFIG_COLUMNS)
        if bad:
            raise ValueError(f"unknown config keys: {', '.join(sorted(bad))}")
        if not values:
            return
        await self.config(guild_id)  # make sure the row exists
        assignments = ", ".join(f"{key} = ?" for key in values)
        await self.execute(
            f"UPDATE guild_config SET {assignments} WHERE guild_id = ?",
            *values.values(), guild_id,
        )
        self._config_cache.pop(guild_id, None)

    # ---------- levels ----------

    async def get_level(self, guild_id: int, user_id: int) -> dict[str, Any]:
        row = await self.fetchone(
            "SELECT * FROM levels WHERE guild_id = ? AND user_id = ?", guild_id, user_id
        )
        if row is None:
            return {"guild_id": guild_id, "user_id": user_id, "xp": 0,
                    "level": 0, "messages": 0, "last_gain": 0}
        return dict(row)

    async def add_xp(self, guild_id: int, user_id: int, amount: int) -> dict[str, Any]:
        now = int(time.time())
        await self.execute(
            """INSERT INTO levels (guild_id, user_id, xp, messages, last_gain)
               VALUES (?, ?, ?, 1, ?)
               ON CONFLICT (guild_id, user_id) DO UPDATE SET
                   xp = xp + excluded.xp,
                   messages = messages + 1,
                   last_gain = excluded.last_gain""",
            guild_id, user_id, amount, now,
        )
        return await self.get_level(guild_id, user_id)

    async def set_level(self, guild_id: int, user_id: int, level: int, xp: int) -> None:
        await self.execute(
            """INSERT INTO levels (guild_id, user_id, xp, level)
               VALUES (?, ?, ?, ?)
               ON CONFLICT (guild_id, user_id) DO UPDATE SET
                   xp = excluded.xp, level = excluded.level""",
            guild_id, user_id, xp, level,
        )

    async def leaderboard(self, guild_id: int, limit: int = 10, offset: int = 0):
        return await self.fetchall(
            """SELECT user_id, xp, level, messages FROM levels
               WHERE guild_id = ? ORDER BY xp DESC LIMIT ? OFFSET ?""",
            guild_id, limit, offset,
        )

    async def rank_of(self, guild_id: int, user_id: int) -> int:
        return await self.fetchval(
            """SELECT COUNT(*) + 1 FROM levels
               WHERE guild_id = ? AND xp > (
                   SELECT xp FROM levels WHERE guild_id = ? AND user_id = ?
               )""",
            guild_id, guild_id, user_id, default=0,
        )

    # ---------- tickets ----------

    async def next_ticket_number(self, guild_id: int) -> int:
        await self.config(guild_id)
        await self.execute(
            "UPDATE guild_config SET ticket_counter = ticket_counter + 1 WHERE guild_id = ?",
            guild_id,
        )
        self._config_cache.pop(guild_id, None)
        return await self.fetchval(
            "SELECT ticket_counter FROM guild_config WHERE guild_id = ?", guild_id, default=1
        )

    async def open_ticket_for(self, guild_id: int, user_id: int):
        return await self.fetchone(
            "SELECT * FROM tickets WHERE guild_id = ? AND user_id = ? AND open = 1",
            guild_id, user_id,
        )

    async def create_ticket(self, channel_id: int, guild_id: int, user_id: int,
                            number: int, topic: str) -> None:
        await self.execute(
            """INSERT OR REPLACE INTO tickets
               (channel_id, guild_id, user_id, number, topic, open, created_at)
               VALUES (?, ?, ?, ?, ?, 1, ?)""",
            channel_id, guild_id, user_id, number, topic, int(time.time()),
        )

    async def get_ticket(self, channel_id: int):
        return await self.fetchone("SELECT * FROM tickets WHERE channel_id = ?", channel_id)

    async def close_ticket(self, channel_id: int) -> None:
        await self.execute("UPDATE tickets SET open = 0 WHERE channel_id = ?", channel_id)

    async def claim_ticket(self, channel_id: int, mod_id: int) -> None:
        await self.execute("UPDATE tickets SET claimed_by = ? WHERE channel_id = ?", mod_id, channel_id)

    # ---------- warnings ----------

    async def add_warning(self, guild_id: int, user_id: int, mod_id: int, reason: str) -> int:
        await self.execute(
            """INSERT INTO warnings (guild_id, user_id, mod_id, reason, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            guild_id, user_id, mod_id, reason, int(time.time()),
        )
        return await self.fetchval("SELECT last_insert_rowid()", default=0)

    async def warnings_for(self, guild_id: int, user_id: int):
        return await self.fetchall(
            "SELECT * FROM warnings WHERE guild_id = ? AND user_id = ? ORDER BY id DESC",
            guild_id, user_id,
        )

    async def delete_warning(self, guild_id: int, warn_id: int) -> bool:
        row = await self.fetchone(
            "SELECT id FROM warnings WHERE guild_id = ? AND id = ?", guild_id, warn_id
        )
        if row is None:
            return False
        await self.execute("DELETE FROM warnings WHERE id = ?", warn_id)
        return True

    async def clear_warnings(self, guild_id: int, user_id: int) -> int:
        count = await self.fetchval(
            "SELECT COUNT(*) FROM warnings WHERE guild_id = ? AND user_id = ?",
            guild_id, user_id, default=0,
        )
        await self.execute("DELETE FROM warnings WHERE guild_id = ? AND user_id = ?", guild_id, user_id)
        return count

    # ---------- misc ----------

    async def no_xp_channels(self, guild_id: int) -> set[int]:
        rows = await self.fetchall("SELECT channel_id FROM no_xp_channels WHERE guild_id = ?", guild_id)
        return {row["channel_id"] for row in rows}

    async def toggle_no_xp(self, guild_id: int, channel_id: int) -> bool:
        """Returns True if XP is now blocked in the channel."""
        existing = await self.fetchone(
            "SELECT 1 FROM no_xp_channels WHERE guild_id = ? AND channel_id = ?",
            guild_id, channel_id,
        )
        if existing:
            await self.execute(
                "DELETE FROM no_xp_channels WHERE guild_id = ? AND channel_id = ?",
                guild_id, channel_id,
            )
            return False
        await self.execute(
            "INSERT INTO no_xp_channels (guild_id, channel_id) VALUES (?, ?)", guild_id, channel_id
        )
        return True

    async def set_level_role(self, guild_id: int, level: int, role_id: int) -> None:
        await self.execute(
            """INSERT INTO level_roles (guild_id, level, role_id) VALUES (?, ?, ?)
               ON CONFLICT (guild_id, level) DO UPDATE SET role_id = excluded.role_id""",
            guild_id, level, role_id,
        )

    async def level_roles(self, guild_id: int):
        return await self.fetchall(
            "SELECT level, role_id FROM level_roles WHERE guild_id = ? ORDER BY level", guild_id
        )

    async def remove_level_role(self, guild_id: int, level: int) -> None:
        await self.execute("DELETE FROM level_roles WHERE guild_id = ? AND level = ?", guild_id, level)
