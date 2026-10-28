#!/usr/bin/env bash
# Autopilot setup: resolve the ATTENTION file path, warn on settings that break unattended runs.
set -u

root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo nobranch)
if [ -d "$root/.ai/plans" ]; then dir="$root/.ai/plans/handoff"; else dir="$root/plans/handoff"; fi
echo "ATTENTION=$dir/ATTENTION-$(date +%F)-${branch//\//-}.md"

settings="$HOME/.claude/settings.json"
if grep -Eq '"autoContinueAtUsageLimit"[[:space:]]*:[[:space:]]*false' "$settings" 2>/dev/null; then
  echo "WARN: auto-continue at usage limit is off; enable it in /config"
fi
if ! grep -Eqs '"remoteControlAtStartup"[[:space:]]*:[[:space:]]*true' "$settings" "$HOME/.claude.json"; then
  echo "WARN: Remote Control is off; type /rc now to monitor remotely"
fi
