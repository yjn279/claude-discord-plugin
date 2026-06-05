#!/usr/bin/env bash
#
# run-channel.sh — run this forked Discord channel as a resident bot.
#
# Claude Code gates the plain `--channels` flag to an Anthropic-approved
# allowlist; a self-forked channel is rejected ("not on the approved channels
# allowlist"). The supported path for your own channel is
# `--dangerously-load-development-channels`. We pass the *installed* plugin id
# (`plugin:discord@claude-discord-plugin`) so the marketplace build runs, not a
# local working copy.
#
# Prerequisites:
#   - The plugin is installed:
#       claude plugin marketplace add yjn279/claude-discord-plugin
#       claude plugin install discord@claude-discord-plugin
#   - bun on PATH (https://bun.sh); python3 (for confirm-loop.py).
#   - DISCORD_BOT_TOKEN in ~/.claude/channels/discord/.env, and access policy in
#     ~/.claude/channels/discord/access.json (managed by /discord:access).
#
# Persistent launch (recommended):
#   screen -dmS discord /path/to/scripts/run-channel.sh
# Foreground:
#   ./scripts/run-channel.sh
# Attach / stop:
#   screen -r discord    /    screen -S discord -X quit
#
# claude needs a TTY or it falls back to --print and exits immediately; the
# bundled confirm-loop.py supplies a PTY and answers the startup prompts.

set -uo pipefail

PLUGIN_ID="discord@claude-discord-plugin"
HERE="$(cd "$(dirname "$0")" && pwd)"
export PATH="$HOME/.bun/bin:$HOME/.local/bin:$PATH"

for bin in claude bun python3; do
  command -v "$bin" >/dev/null 2>&1 || { echo "run-channel: '$bin' not found on PATH" >&2; exit 1; }
done

if [ ! -f "$HOME/.claude/channels/discord/.env" ]; then
  echo "run-channel: token missing — set it via /discord:configure or /discord:access first." >&2
  exit 1
fi

# Auto-restart loop: claude exits on crash; come back after a short pause.
while true; do
  echo "run-channel: start $(date)"
  python3 "$HERE/confirm-loop.py" claude --dangerously-load-development-channels "plugin:$PLUGIN_ID"
  echo "run-channel: exited ($?), restarting in 5s"
  sleep 5
done
