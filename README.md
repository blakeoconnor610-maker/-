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
mobile app — or from the Android app in `android/`, which gives you a channel
picker, a chat box, and switches for the bot's settings.

---

## The app

There is a real Android app in `android/`, and a built, signed apk sitting at
**`android/dist/chillbot-panel.apk`** — copy that to your phone and open it.

### Installing it
1. Get `android/dist/chillbot-panel.apk` onto your phone (usb, google drive,
   emailing it to yourself, whatever is easiest).
2. Open it. Android will say the app came from an unknown source — that is just
   what sideloading looks like. Allow it for your file manager or browser and
   carry on.
3. Open **server panel** from your app drawer and long-press it onto your home
   screen.

### First run
Open it. That is the whole step.

The bot announces itself on your wifi over mdns, and the app listens for it —
finds it, connects, done. No address to look up and nothing to type. It saves
what it found, so every launch after that goes straight to the panel.

If more than one panel turns up, they are listed and you tap the one you want.

Two fallbacks, if the announcement never arrives (some routers block mdns, and
guest networks usually do):

- Press **the bot is running on this phone** if the bot is in Termux on the
  same handset — loopback is not something mdns can announce on.
- Run **`/panel`** in Discord. The bot works out its own address and hands you
  the exact line to type, and tells you if the panel is switched off or the
  password is too short. Owner only, and only you see the reply.
- Or type it yourself in the box on the same screen — the bot machine's address
  plus your `PANEL_PORT`, e.g. `http://192.168.1.20:8080`.

**change address** in the menu gets you back to this screen if things move.

Then the panel password, once, and it stays logged in.

### What you can do from it

**chat tab** — pick any channel the bot can post in and type. It sends as the
bot, and shows the last 30 messages so you can see what you are replying to.

**controls tab** — a card per server with real switches:

- **leveling** on or off
- **ping on level up** on or off

plus the member count, how many tickets have been opened, and where logs, level
ups, welcomes and ticket logs are currently pointing. Flipping a switch writes
straight to the bot's database and takes effect on the next message — no restart.

### Turning the panel on

The app is a window onto the panel, so the panel has to be running for it to
have anything to talk to. In the bot's `.env`:

```
PANEL_ENABLED=true
PANEL_HOST=0.0.0.0
PANEL_PORT=8080
PANEL_PASSWORD=<paste a long random string>
```

Generate the password with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Restart the bot. It logs `control panel listening on ...` when it comes up. The
bot refuses to start the panel with a password under 12 characters.

`PANEL_HOST=0.0.0.0` means anything that can reach that machine on that port can
reach the login page, so:

- **On your own network** this is fine. The phone and the bot machine just need
  to be on the same wifi.
- **On a public server, put it behind https** — Caddy, nginx or a Cloudflare
  tunnel. Over plain http the password crosses the network in the clear, and the
  password is the only thing guarding it.
- **Not exposing it at all** is the safest option: leave `PANEL_HOST=127.0.0.1`
  and reach it through a tunnel or a vpn like Tailscale.

The app allows plain http so the local-network case works out of the box.

### What is not in the app

Your bot token. It never leaves the machine running the bot — the app only ever
holds the panel address and a session cookie. That is deliberate: an apk that
talked to Discord directly would need the token baked inside it, and anyone who
pulled the file apart would own your bot.

### Rebuilding it

You do not need to — the apk is already built and committed. If you change the
app:

```bash
cd android
./gradlew :app:apk          # writes dist/chillbot-panel.apk
```

You need a jdk (17 or newer) and the Android sdk; point `ANDROID_HOME` at it, or
just open `android/` in Android Studio. Pushing a change under `android/` also
builds it on GitHub Actions and attaches the apk to the run.

It is signed with the key in `android/keystore/`, which is committed on purpose
so that a rebuild installs over the top as an update rather than making you
uninstall first. That key signs nothing but this one sideloaded app and guards
no secrets. Swap it for your own before you first install if you would rather.

## Where the bot actually runs

Worth being clear about, because it trips people up: **the app is not the bot.**
The bot is a python program that has to be running somewhere, logged into
Discord, for anything to work. The app is a remote control for it.

Three places to run it, best first:

**A cheap vps** — a few dollars a month gets you a box that never sleeps, never
loses wifi, and is not your phone battery. This is what a server bot wants.

**A pc at home** — free, and fine. The bot is offline whenever the machine is
off or asleep.

**Your phone, in Termux** — free, and it does genuinely work, but Android will
fight you: it kills background apps, and the bot is offline any time the phone
is. Fine for trying it out, poor for a server people actually use.

### Running it on your phone

1. Install **Termux** from [F-Droid](https://f-droid.org/packages/com.termux/).
   The Play Store copy is abandoned and too old to work.
2. In Termux:

   ```bash
   pkg install git -y
   git clone <this repo> bot && cd bot
   bash termux-setup.sh
   ```

   That installs python, installs the dependencies, and writes you a `.env`
   with the panel already switched on. **It prints a panel password — write it
   down**, you type it into the app once.
3. Paste your bot token in: `nano .env`, fill in `DISCORD_TOKEN`, then ctrl+o,
   enter, ctrl+x.
4. Start it:

   ```bash
   bash run-termux.sh
   ```

   That takes a wake lock so Android does not suspend it the second the screen
   goes off. For a reliable one, install **Termux:API** too. Leave the Termux
   notification alone — swiping it away kills the bot.
5. Open the panel app and press **the bot is running on this phone**. That is
   the loopback address; mdns discovery cannot find a bot on the same device,
   so there is a button for it.

Then run `/setup` in your server and you are going.

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
run.sh              one command setup and start, on a pc or server
termux-setup.sh     the same thing for a phone, plus run-termux.sh to start it
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
  static/index.html the panel itself - chat and controls tabs
android/
  app/src/main/     the android app, three small java files
  dist/             the built apk lives here
  keystore/         the signing key, committed on purpose
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
| do not know the panel address | run `/panel` in discord |
| app says it cant reach the panel | the bot is not running, `PANEL_ENABLED` is not true, or the phone is on a different network |
