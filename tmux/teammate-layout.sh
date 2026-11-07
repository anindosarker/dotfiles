#!/bin/sh
# $1 = window id. If the window has a Claude Code teammate pane and the main
# (first) pane is under 60% of the width, apply main-vertical (main-pane-width).
# $2 = "settle": also re-check over the next 2s. Claude Code rearranges the
# panes after opening the first teammate with a command that has no tmux hook.
w="$1"

check() {
  tmux list-panes -t "$w" -F '#{pane_start_command}' 2>/dev/null | grep -q -- --agent-id || return 0
  ww=$(tmux display -p -t "$w" '#{window_width}')
  mw=$(tmux list-panes -t "$w" -F '#{pane_index} #{pane_width}' | awk '$1==0{print $2}')
  [ -n "$mw" ] && [ "$mw" -lt $((ww * 60 / 100)) ] && tmux select-layout -t "$w" main-vertical
  return 0
}

check
if [ "$2" = settle ]; then
  for d in 0.2 0.3 0.5 1; do sleep $d; check; done
fi
exit 0
