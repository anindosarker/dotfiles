#!/bin/sh
# $1 = session id, or "all". Tint the session's status bar with 10% of its
# current window's color (blended into colour237 by name2color.py --alpha).
ALPHA=0.1
if [ "$1" = all ]; then
  for s in $(tmux ls -F '#{session_id}'); do "$0" "$s"; done
  exit 0
fi
s="$1"
set -- $(tmux display -p -t "$s" '#S #I')
c=$(~/.tmux/plugins/tmux-colortag/name2color.py "$1" "$2" "$(tmux display -p -t "$s" '#W')" --alpha $ALPHA)
[ -n "$c" ] && tmux set -t "$s" status-style "bg=$c,fg=colour250"
exit 0
