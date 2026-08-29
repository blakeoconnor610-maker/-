"""A small phone-friendly web panel for typing into any channel as the bot.

Turn it on with PANEL_ENABLED=true and set a long PANEL_PASSWORD.
Open it on your phone and use "add to home screen" - it installs like an app.
"""

from __future__ import annotations

import hmac
import logging
import os
import secrets
from pathlib import Path

import discord
from aiohttp import web

from core.netinfo import local_ips

log = logging.getLogger("bot.panel")

# Advertised over mdns so the phone app can find the panel without anyone
# typing an ip address.
SERVICE_TYPE = "_chillpanel._tcp.local."

STATIC = Path(__file__).parent / "static"
COOKIE = "panel_session"
_sessions: set[str] = set()


def _authed(request: web.Request) -> bool:
    token = request.cookies.get(COOKIE)
    return bool(token and token in _sessions)


def _require(request: web.Request) -> None:
    if not _authed(request):
        raise web.HTTPUnauthorized(text='{"error":"log in first"}', content_type="application/json")


def _visible_channels(bot: discord.Client) -> list[dict]:
    out: list[dict] = []
    for guild in bot.guilds:
        me = guild.me
        if me is None:
            continue
        for channel in guild.text_channels:
            perms = channel.permissions_for(me)
            if perms.send_messages and perms.view_channel:
                out.append({
                    "id": str(channel.id),
                    "name": channel.name,
                    "guild": guild.name,
                    "category": channel.category.name if channel.category else "",
                })
    out.sort(key=lambda c: (c["guild"], c["category"], c["name"]))
    return out


TOGGLES = {
    "levels_enabled": "leveling",
    "level_ping": "ping on level up",
}


def _guild_summary(bot: discord.Client, guild: discord.Guild, config: dict) -> dict:
    def channel_name(column: str) -> str | None:
        channel = guild.get_channel(config.get(column) or 0)
        return channel.name if channel else None

    return {
        "id": str(guild.id),
        "name": guild.name,
        "members": guild.member_count or 0,
        "channels": len(guild.text_channels),
        "toggles": {key: bool(config.get(key)) for key in TOGGLES},
        "wiring": {
            "logs": channel_name("log_channel"),
            "level ups": channel_name("level_channel"),
            "welcome": channel_name("welcome_channel"),
            "ticket logs": channel_name("ticket_log"),
        },
        "tickets_opened": config.get("ticket_counter", 0),
    }


def build_app(bot: discord.Client, password: str) -> web.Application:
    app = web.Application()

    async def index(request: web.Request) -> web.StreamResponse:
        return web.FileResponse(STATIC / "index.html")

    async def manifest(request: web.Request) -> web.StreamResponse:
        return web.json_response({
            "name": "server panel",
            "short_name": "panel",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#1a1b1e",
            "theme_color": "#1a1b1e",
            "icons": [],
        })

    async def login(request: web.Request) -> web.StreamResponse:
        body = await request.json()
        given = str(body.get("password", ""))
        if not hmac.compare_digest(given, password):
            return web.json_response({"error": "wrong password"}, status=401)
        token = secrets.token_urlsafe(32)
        _sessions.add(token)
        response = web.json_response({"ok": True})
        response.set_cookie(COOKIE, token, httponly=True, samesite="Lax", max_age=60 * 60 * 24 * 7)
        return response

    async def whoami(request: web.Request) -> web.StreamResponse:
        return web.json_response({
            "authed": _authed(request),
            "bot": str(bot.user) if bot.user else None,
        })

    async def channels(request: web.Request) -> web.StreamResponse:
        _require(request)
        return web.json_response({"channels": _visible_channels(bot)})

    async def history(request: web.Request) -> web.StreamResponse:
        _require(request)
        channel_id = request.query.get("channel", "")
        channel = bot.get_channel(int(channel_id)) if channel_id.isdigit() else None
        if not isinstance(channel, discord.TextChannel):
            return web.json_response({"error": "unknown channel"}, status=404)
        messages = []
        try:
            async for message in channel.history(limit=30):
                messages.append({
                    "author": message.author.display_name,
                    "content": message.clean_content,
                    "mine": bool(bot.user and message.author.id == bot.user.id),
                    "at": message.created_at.strftime("%H:%M"),
                })
        except discord.HTTPException:
            return web.json_response({"error": "cant read that channel"}, status=403)
        messages.reverse()
        return web.json_response({"messages": messages})

    async def guilds(request: web.Request) -> web.StreamResponse:
        _require(request)
        db = getattr(bot, "db", None)
        if db is None:
            return web.json_response({"guilds": [], "toggles": TOGGLES})
        out = []
        for guild in bot.guilds:
            out.append(_guild_summary(bot, guild, await db.config(guild.id)))
        return web.json_response({"guilds": out, "toggles": TOGGLES})

    async def setting(request: web.Request) -> web.StreamResponse:
        _require(request)
        db = getattr(bot, "db", None)
        if db is None:
            return web.json_response({"error": "bot is still starting up"}, status=503)
        body = await request.json()
        guild_id = str(body.get("guild", ""))
        key = str(body.get("key", ""))
        if key not in TOGGLES:
            return web.json_response({"error": "not something you can toggle"}, status=400)
        if not guild_id.isdigit() or bot.get_guild(int(guild_id)) is None:
            return web.json_response({"error": "unknown server"}, status=404)
        await db.set_config(int(guild_id), **{key: int(bool(body.get("value")))})
        return web.json_response({"ok": True})

    async def send(request: web.Request) -> web.StreamResponse:
        _require(request)
        body = await request.json()
        channel_id = str(body.get("channel", ""))
        content = str(body.get("content", "")).strip()
        if not content:
            return web.json_response({"error": "nothing to send"}, status=400)
        if len(content) > 2000:
            return web.json_response({"error": "discord caps messages at 2000 characters"}, status=400)
        channel = bot.get_channel(int(channel_id)) if channel_id.isdigit() else None
        if not isinstance(channel, discord.TextChannel):
            return web.json_response({"error": "unknown channel"}, status=404)
        try:
            await channel.send(
                content,
                allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
            )
        except discord.HTTPException as err:
            return web.json_response({"error": str(err)}, status=502)
        return web.json_response({"ok": True})

    app.router.add_get("/", index)
    app.router.add_get("/manifest.json", manifest)
    app.router.add_post("/api/login", login)
    app.router.add_get("/api/whoami", whoami)
    app.router.add_get("/api/channels", channels)
    app.router.add_get("/api/guilds", guilds)
    app.router.add_post("/api/setting", setting)
    app.router.add_get("/api/history", history)
    app.router.add_post("/api/send", send)
    return app


async def _advertise(bot: discord.Client, port: int):
    """Announce the panel on the local network.

    Returns a coroutine function that takes the announcement back down, or None
    if we could not advertise. Never fatal - the app can always be pointed at an
    address by hand.
    """
    try:
        import socket

        from zeroconf import ServiceInfo
        from zeroconf.asyncio import AsyncZeroconf
    except ImportError:
        log.info("zeroconf is not installed, the app will need the address typed in")
        return None

    addresses = [socket.inet_aton(ip) for ip in local_ips()]
    if not addresses:
        log.info("no local address to advertise on")
        return None

    name = str(bot.user) if bot.user else "server panel"
    info = ServiceInfo(
        SERVICE_TYPE,
        f"{name[:40]}.{SERVICE_TYPE}",
        addresses=addresses,
        port=port,
        properties={"path": "/", "app": "chillbot-panel"},
        server=f"chillbot-panel-{port}.local.",
    )

    try:
        aiozc = AsyncZeroconf()
        await aiozc.async_register_service(info)
    except Exception:
        log.exception("could not advertise the panel on the network")
        return None

    log.info("advertising the panel on the local network as %s", name)

    async def stop() -> None:
        try:
            await aiozc.async_unregister_service(info)
            await aiozc.async_close()
        except Exception:
            pass

    return stop


async def start_panel(bot: discord.Client) -> web.AppRunner:
    password = (os.getenv("PANEL_PASSWORD") or "").strip()
    if len(password) < 12:
        raise RuntimeError(
            "PANEL_PASSWORD must be at least 12 characters before the panel will start"
        )
    host = os.getenv("PANEL_HOST", "0.0.0.0")
    port = int(os.getenv("PANEL_PORT", "8080"))

    runner = web.AppRunner(build_app(bot, password))
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()

    # Hung off the runner so the bot can take it down again on shutdown.
    runner.panel_zeroconf_stop = await _advertise(bot, port)  # type: ignore[attr-defined]
    log.info("control panel listening on http://%s:%s", host, port)
    return runner
