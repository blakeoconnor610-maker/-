#!/usr/bin/env bash
# One command to get going: makes a virtualenv, installs everything, starts the bot.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "made a .env for you - open it and paste your bot token in, then run this again"
  exit 1
fi

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
exec python bot.py
