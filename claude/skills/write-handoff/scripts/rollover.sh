#!/usr/bin/env bash
# Roll over: open the next Claude Code session in a new window of the current tmux session,
# detached (focus stays where it is), told to read the handoff.
#
# Usage: rollover.sh --cwd <dir> --name "<next name>" --handoff <abs path> [--model <alias>] [--prompt-prefix "<text>"]
#
# The window is named <next name>, opens in <dir> and runs
#   claude -n "<next name>" [--model <alias>] "<prefix>Read <handoff> and continue. Reply with one line: what you picked up and what is next."
# Prints the window target (session:index). Not inside tmux: one line, exit 3.
# Test overrides: EXPEDITION_CLAUDE (the claude command), EXPEDITION_TMUX_SOCKET (tmux -L <socket>).
set -euo pipefail

CLAUDE_BIN="${EXPEDITION_CLAUDE:-claude}"

tmux() {
  if [ -n "${EXPEDITION_TMUX_SOCKET:-}" ]; then command tmux -L "$EXPEDITION_TMUX_SOCKET" "$@"; else command tmux "$@"; fi
}

usage() {
  echo 'usage: rollover.sh --cwd <dir> --name "<next name>" --handoff <abs path> [--model <alias>] [--prompt-prefix "<text>"]' >&2
  exit 2
}

cwd="" name="" handoff="" model="" prefix=""
while [ $# -gt 0 ]; do
  case "$1" in
    --cwd) [ $# -ge 2 ] || usage; cwd="$2"; shift 2 ;;
    --name) [ $# -ge 2 ] || usage; name="$2"; shift 2 ;;
    --handoff) [ $# -ge 2 ] || usage; handoff="$2"; shift 2 ;;
    --model) [ $# -ge 2 ] || usage; model="$2"; shift 2 ;;
    --prompt-prefix) [ $# -ge 2 ] || usage; prefix="$2"; shift 2 ;;
    *) usage ;;
  esac
done
[ -n "$cwd" ] && [ -n "$name" ] && [ -n "$handoff" ] || usage
[ -d "$cwd" ] || { echo "error: --cwd not a folder: $cwd" >&2; exit 1; }
[ -f "$handoff" ] || { echo "error: --handoff not a file: $handoff" >&2; exit 1; }
cwd="$(cd "$cwd" && pwd)"

if [ -z "${TMUX:-}" ]; then
  echo "Not inside tmux: no window opened."
  exit 3
fi

cmd=("$CLAUDE_BIN" -n "$name")
[ -z "$model" ] || cmd+=(--model "$model")
cmd+=("${prefix}Read $handoff and continue. Reply with one line: what you picked up and what is next.")
line="cd $(printf '%q' "$cwd") && exec$(printf ' %q' "${cmd[@]}")"

session="$(tmux display-message -p ${TMUX_PANE:+-t "$TMUX_PANE"} '#{session_name}')"
tmux new-window -d -P -F '#{session_name}:#{window_index}' -t "$session:" -n "$name" -c "$cwd" "$line"
