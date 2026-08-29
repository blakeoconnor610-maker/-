#!/data/data/com.termux/files/usr/bin/bash
# Sets the bot up to run on an Android phone, inside Termux.
#
#   pkg install git -y
#   git clone <this repo> bot && cd bot
#   bash termux-setup.sh
#
# A phone is not a great place to run a bot 24/7 - see the readme - but this
# works, and it is free.
set -euo pipefail

echo "installing python and the build tools aiohttp needs..."
pkg update -y
pkg install -y python build-essential libffi openssl rust

echo "installing the bot's dependencies..."
pip install --upgrade pip wheel
pip install -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  PANEL_PASSWORD="$(python -c 'import secrets; print(secrets.token_urlsafe(24))')"
  # The bot and the panel are on the same phone, so the panel only needs to
  # listen on loopback - nothing else can reach it, which is exactly what we want.
  sed -i "s|^PANEL_ENABLED=.*|PANEL_ENABLED=true|" .env
  sed -i "s|^PANEL_HOST=.*|PANEL_HOST=127.0.0.1|" .env
  sed -i "s|^PANEL_PASSWORD=.*|PANEL_PASSWORD=$PANEL_PASSWORD|" .env

  echo
  echo "made you a .env with the panel already switched on."
  echo "your panel password is:  $PANEL_PASSWORD"
  echo "write that down, you type it into the app once."
  echo
  echo "now open .env and paste your bot token into DISCORD_TOKEN:"
  echo "  nano .env"
  echo
  echo "then start the bot with:"
  echo "  bash run-termux.sh"
  exit 0
fi

echo "all set. start the bot with: bash run-termux.sh"
