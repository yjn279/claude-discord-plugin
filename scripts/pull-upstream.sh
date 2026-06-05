#!/usr/bin/env bash
#
# Refresh the discord/ subtree from the official monorepo.
#
# git subtree can only pull from a repo whose ROOT is the directory we track, so
# we first `git subtree split` the official monorepo's external_plugins/discord
# into a temporary branch, then `git subtree pull --squash` from it. Run from the
# repo root, on the machine that created the repo (splits are deterministic
# per-machine).
#
#   ./scripts/pull-upstream.sh
#
# A clean pull lands as one squashed merge commit. Conflicts (almost always in
# discord/server.ts, marked with `// discord-threads:`) surface as merge
# conflicts: resolve them, `git commit`, then `git push`.

set -euo pipefail

UPSTREAM_URL="https://github.com/anthropics/claude-plugins-official.git"
UPSTREAM_PREFIX="external_plugins/discord"
LOCAL_PREFIX="discord"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "→ Cloning upstream monorepo…"
git clone --quiet "$UPSTREAM_URL" "$TMP/mono"

echo "→ Splitting $UPSTREAM_PREFIX history…"
git -C "$TMP/mono" subtree split --prefix="$UPSTREAM_PREFIX" -b discord-base >/dev/null 2>&1

echo "→ Pulling into $LOCAL_PREFIX/ …"
git subtree pull --prefix="$LOCAL_PREFIX" "$TMP/mono" discord-base --squash \
  -m "Merge upstream external_plugins/discord"

echo "✓ Done. Review the diff, then: git push"
