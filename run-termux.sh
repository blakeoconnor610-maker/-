#!/data/data/com.termux/files/usr/bin/bash
# Starts the bot on a phone and stops Android putting it to sleep.
set -euo pipefail
cd "$(dirname "$0")"

# Without this Android suspends the process the moment the screen goes off.
termux-wake-lock 2>/dev/null || echo "note: install Termux:API for a reliable wake lock"

trap 'termux-wake-unlock 2>/dev/null || true' EXIT

exec python bot.py
