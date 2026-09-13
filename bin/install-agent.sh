#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$HOME/Library/LaunchAgents/com.sagar.ai-sme-map.plist"
PY="$(command -v python3)"
mkdir -p "$HOME/Library/LaunchAgents"
sed -e "s|__ROOT__|$ROOT|g" -e "s|__PYTHON__|$PY|g" \
  "$ROOT/launchd/com.sagar.ai-sme-map.plist" > "$DEST"
launchctl unload "$DEST" 2>/dev/null || true
launchctl load "$DEST"
echo "Loaded $DEST"
echo "Atlas: http://127.0.0.1:7432"
