#!/bin/sh
# $1 = window id. If the window has a Claude Code teammate pane and the main
# (first) pane is under 60% of the width, apply main-vertical (main-pane-width).
w="$1"
tmux list-panes -t "$w" -F '#{pane_start_command}' | grep -q -- --agent-id || exit 0
set -- $(tmux display -p -t "$w" '#{window_width}')
ww=$1
mw=$(tmux list-panes -t "$w" -F '#{pane_index} #{pane_width}' | awk '$1==0{print $2}')
[ "$mw" -lt $((ww * 60 / 100)) ] && tmux select-layout -t "$w" main-vertical
exit 0
