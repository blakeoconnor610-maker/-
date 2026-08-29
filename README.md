# chill server bot

A full Discord bot for a casual server. One `/setup` command builds every channel
and role in the small caps font with no emoji anywhere, then leveling, tickets,
moderation and logging are already wired up and running.

---

## What you get

**`/setup`** builds the whole server in one go:

| category | channels |
| --- | --- |
| ɪɴꜰᴏ | ᴡᴇʟᴄᴏᴍᴇ, ʀᴜʟᴇꜱ, ᴀɴɴᴏᴜɴᴄᴇᴍᴇɴᴛꜱ, ʀᴏʟᴇꜱ |
| ᴄʜᴀᴛ | ɢᴇɴᴇʀᴀʟ, ᴍᴇᴅɪᴀ, ᴍᴜꜱɪᴄ, ᴠᴇɴᴛ, ᴄᴏᴜɴᴛɪɴɢ, ᴄᴏᴍᴍᴀɴᴅꜱ |
| ʟᴇᴠᴇʟꜱ | ʟᴇᴠᴇʟ-ᴜᴘ, ʟᴇᴀᴅᴇʀʙᴏᴀʀᴅ |
| ꜱᴜᴘᴘᴏʀᴛ | ᴄʀᴇᴀᴛᴇ-ᴀ-ᴛɪᴄᴋᴇᴛ |
| ᴛɪᴄᴋᴇᴛꜱ | (hidden, open tickets land here) |
| ᴠᴏɪᴄᴇ | ᴄʜɪʟʟ, ɢᴀᴍɪɴɢ, ᴍᴜꜱɪᴄ, ᴀꜰᴋ |
| ꜱᴛᴀꜰꜰ | ꜱᴛᴀꜰꜰ-ᴄʜᴀᴛ, ꜱᴇʀᴠᴇʀ-ʟᴏɢꜱ, ᴍᴏᴅ-ʟᴏɢꜱ, ᴊᴏɪɴ-ʟᴇᴀᴠᴇ, ᴛɪᴄᴋᴇᴛ-ʟᴏɢꜱ |

Roles, top to bottom: ᴏᴡɴᴇʀ, ᴀᴅᴍɪɴ, ᴍᴏᴅ, ʜᴇʟᴘᴇʀ, ʙᴏᴏꜱᴛᴇʀ, ᴠɪᴘ,
ʟᴠʟ 100 / 75 / 50 / 30 / 20 / 10 / 5, ᴍᴇᴍʙᴇʀ, ᴍᴜᴛᴇᴅ — with permissions,
colours and channel overwrites already set.

It also writes the rules, posts the ticket button, points logging at
ꜱᴇʀᴠᴇʀ-ʟᴏɢꜱ, points level ups at ʟᴇᴠᴇʟ-ᴜᴘ, sets ᴍᴇᴍʙᴇʀ as the autorole and
registers the level roles as rewards.

**Running `/setup` twice is safe.** Nothing is deleted, and anything already
named the same is reused instead of duplicated — so if it stops halfway
(usually a permissions problem) just fix the problem and run it again.

### Leveling
Talk in chat, earn xp, level up. The level-up message goes to ʟᴇᴠᴇʟ-ᴜᴘ and
**pings you**, and level roles hand themselves out at 5, 10, 20, 30, 50, 75
and 100. `/rank` shows a progress bar, `/leaderboard` shows the top chatters.
Tune everything with `/config xp` and `/levels`.

### Tickets
A button in ꜱᴜᴘᴘᴏʀᴛ opens a private channel with just that person and staff in
it. Staff can claim, add or remove people, rename it, and close it — closing
saves a full text transcript into ᴛɪᴄᴋᴇᴛ-ʟᴏɢꜱ and dms the person. The buttons
keep working after a restart.

### Moderation
`/ban` `/unban` `/softban` `/kick` `/mute` `/unmute` `/warn` `/warnings`
`/delwarn` `/clearwarns` `/purge` `/slowmode` `/lock` `/unlock` `/nick`
`/role add` `/role remove`

Every punishment dms the person first, then writes to the log channel. Mutes use
Discord's native timeout and take plain durations like `10m`, `2h`, `7d`.
If you try to action someone above you in the role list the bot explains why it
cannot, instead of silently failing.

### Logging
Goes to ꜱᴇʀᴠᴇʀ-ʟᴏɢꜱ: **message deletes (with who deleted it, their username, and
a ping)**, edits with before/after, bulk purges, joins and leaves, nickname and
role changes, timeouts, bans, unbans, channel and role creation and deletion.

> **On the delete ping:** Discord only reveals who deleted a message through the
> audit log, so the bot needs the **View Audit Log** permission — without it the
> log says "unknown". Discord never records someone deleting their *own*
> message, so when the audit log has nothing the bot correctly reports it as a
> self-delete. Also worth knowing: a ping in a staff-only channel shows up in
> the log, but Discord will not push a notification to someone who cannot see
> that channel. If you want them to actually get told, use `/dm`.

### Talking as the bot, from anywhere
`/say` posts into **any** channel from any channel, `/embed` posts a tidy embed,
`/edit` changes something the bot already said, `/dm` messages a person, and
`/announce` posts with an optional role ping. All of it works from the Discord
mobile app.

---

## About the apk

I did not build an Android apk, and I would push back on wanting one: an apk
that talks to Discord still needs your bot token shipped inside it, which means
anyone who pulls the file apart owns your bot. It also needs signing, a Play
Store listing or sideloading, and a rebuild every time you change something.

What is in here instead does the same job:

1. **`/say`** — from the Discord app on your phone, type `/say` in any channel,
   pick a target channel, and the bot posts there. That is the whole feature,
   with no extra app to install.
2. **The control panel** (`panel/`) — a phone-sized web page listing every
   channel the bot can post in, with a chat box. On Android, open it in Chrome
   and tap **Add to home screen**: you get an icon and a full-screen app, which
   is what an apk would have given you, without the token ever leaving your
   server.

Turn the panel on in `.env`:

```
PANEL_ENABLED=true
PANEL_PORT=8080
PANEL_PASSWORD=<paste a long random string>
```

Generate the password with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Then open `http://<your-server-ip>:8080`. **Only expose it over HTTPS** (put it
behind Caddy, nginx or a Cloudflare tunnel) — the password is the only thing
guarding it, and over plain http it travels in the clear. If the bot runs on
your own machine, keep `PANEL_HOST=127.0.0.1` and reach it through a tunnel
rather than opening a port.

---

## Setting it up

### 1. Make the bot account
1. Go to <https://discord.com/developers/applications> and hit **New Application**.
2. **Bot** tab → **Reset Token** → copy it. That token is a password; never paste
   it anywhere public.
3. Still on the **Bot** tab, scroll to **Privileged Gateway Intents** and turn on
   both **Server Members Intent** and **Message Content Intent**. Leveling and
   the delete logs do not work without them.

### 2. Invite it
**OAuth2 → URL Generator**, tick `bot` and `applications.commands`, then tick
**Administrator**. Administrator is genuinely the easy path here because `/setup`
creates roles and rewrites channel permissions.

If you would rather be precise, use this link instead and swap in your
application id — it is every permission the bot actually uses and nothing more:

```
https://discord.com/oauth2/authorize?client_id=YOUR_APP_ID&scope=bot+applications.commands&permissions=1428500376790
```

### 3. Run it

```bash
git clone <this repo>
cd <this repo>
cp .env.example .env      # then paste your token into DISCORD_TOKEN
./run.sh
```

`run.sh` makes a virtualenv, installs everything and starts the bot. Or by hand:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python bot.py
```

Docker works too:

```bash
docker build -t chillbot .
docker run -d --name chillbot --env-file .env -v "$PWD/data:/app/data" chillbot
```

### 4. In Discord

1. Put your own server's id in `DEV_GUILD_ID` in `.env` while you are setting
   up — slash commands then appear **instantly**. Leave it blank and Discord can
   take up to an hour to show them the first time.
2. **Drag the bot's role to the top of the role list** in Server Settings →
   Roles. Discord will not let it ban, mute, or hand out roles to anyone whose
   highest role sits above its own. This is the single most common reason a
   command comes back with "discord said no".
3. Run **`/setup`**, press **build it**, and give it a minute — Discord rate
   limits channel creation.
4. Run `/help` to see everything, or `/config view` to check where things point.

---

## Layout

```
bot.py              startup, extension loading, command sync, error handling
core/
  db.py             sqlite storage - config, levels, tickets, warnings
  smallcaps.py      the small caps font conversion
  ui.py             shared embed styling
  checks.py         staff check and role hierarchy rules
  timeparse.py      "1h30m" -> seconds
cogs/
  setup.py          /setup - the whole server build
  levels.py         xp, level ups, level roles, leaderboard
  moderation.py     ban, kick, mute, warn, purge, lock, roles
  tickets.py        button panel, ticket channels, transcripts
  logs.py           delete, edit, join, leave, role and ban logging
  welcome.py        greeting and autorole
  say.py            /say /embed /edit /dm /announce
  config.py         /config
  utility.py        /help, info commands, polls
panel/
  server.py         the phone control panel backend
  static/index.html the panel itself
```

Everything is stored in `data/bot.db`. Back that file up and you keep every
level, warning and setting.

## Changing the server layout

The channel and role lists are plain data at the top of `cogs/setup.py` —
`ROLES` and `LAYOUT`. Write names in ordinary lowercase english; the bot converts
them to small caps for you. Add a channel by adding one line to a category's
`channels` list, then run `/setup` again — existing channels are left alone and
only the new one gets made.

## If something is not working

| what you see | what it means |
| --- | --- |
| slash commands do not appear | set `DEV_GUILD_ID` in `.env` and restart, or wait out the global sync |
| "discord said no" on a mod command | the bot's role is below the target's — drag it higher |
| `/setup` stops partway | the bot is missing Manage Channels or Manage Roles; grant them and run it again |
| delete logs say "unknown" | the bot needs View Audit Log |
| nobody gains xp | Message Content Intent is off in the developer portal |
| level ups post nowhere | `/config channel levels #channel` |
