#!/usr/bin/env bash
# Roll over in place: clear this Claude Code session in its own tmux window, rename it and start
# it again from a handoff file. Role-blind: everything specific is in the handoff.
#
# Usage: rollover.sh --handoff <abs path> [--name "<next name>"] [--dry-run]
#
# Called by the session as the last action of its turn. It returns at once and prints one line.
# A detached worker waits for the turn to end (the transcript stays quiet and the pane shows no
# running turn), then types into this session's pane:
#   /clear
#   /rename <next name>   (a single-pane tmux window with a fixed name gets automatic-rename on)
#   <starter prompt>      (each line as its own message, after the input box shows)
# Next name: --name as given, else the first line under "## Session name" in the handoff, else
# the session's own name (the last "custom-title" record of its
# transcript, set by /rename or claude -n) with its version bumped: a trailing V3 or v3 goes up by
# one, so does a trailing " 3"; no version: " v2" is appended. No name found: exit 4.
# Starter prompt: every non-empty line under "## Starter prompt" in the handoff, in order (for
# example a slash command such as /caveman:ultracave, then the line that starts the work), else
# "Read <handoff> and continue." When no starter line names the handoff, the last line gets that
# sentence appended. The pane is $TMUX_PANE, else the pane this process descends from, else the one
# pane whose title is this session's name. Not in a tmux pane: prints the starter prompt and exits 3.
# --dry-run: print the name and the starter prompt (one "prompt:" line per line), type nothing.
# Log of the worker: ~/.cache/roll-over/last.log
set -euo pipefail

QUIET_SECONDS=6      # transcript untouched this long means the turn's last message is written
MAX_WAIT_SECONDS=180 # give up waiting for the turn to end after this
BOX_WAIT_SECONDS=30  # a cleared session draws its input box in seconds; after this, type anyway

mtime() { stat -f %m "$1" 2>/dev/null || stat -c %Y "$1"; }

if [ "${1:-}" = "--worker" ]; then
  pane="$2" transcript="$3" name="$4" prompt="$5" current="${6:-}"
  # box_shown: the pane shows the input box, the text between two rule lines.
  box_shown() { [ "$(tmux capture-pane -p -t "$pane" 2>/dev/null | grep -c '^[[:space:]]*─')" -ge 2 ]; }
  echo "$(date '+%F %T') worker: pane=$pane name=$name"
  sleep 4
  waited=4
  while [ "$waited" -lt "$MAX_WAIT_SECONDS" ]; do
    age=$(( $(date +%s) - $(mtime "$transcript") ))
    if [ "$age" -ge "$QUIET_SECONDS" ] && ! tmux capture-pane -p -t "$pane" | grep -q 'esc to interrupt'; then break; fi
    sleep 2; waited=$((waited + 2))
  done
  echo "$(date '+%F %T') turn ended after ${waited}s, typing"
  tmux send-keys -t "$pane" -l '/clear'; tmux send-keys -t "$pane" Enter; sleep 3
  tmux send-keys -t "$pane" -l "/rename $name"; tmux send-keys -t "$pane" Enter; sleep 2
  # tmux names a window from the pane title (the session name) when automatic-rename is on. A
  # window opened with a fixed name has it off: switch it back on so the window follows the name.
  if [ "$(tmux display-message -p -t "$pane" '#{automatic-rename}')" = 0 ] && [ "$(tmux display-message -p -t "$pane" '#{window_panes}')" = 1 ]; then
    tmux set-window-option -t "$pane" automatic-rename on
  fi
  # One starter line per message, in order; each waits for the input box.
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    waited=0
    while ! box_shown && [ "$waited" -lt "$BOX_WAIT_SECONDS" ]; do sleep 1; waited=$((waited + 1)); done
    box_shown || echo "$(date '+%F %T') no input box after ${BOX_WAIT_SECONDS}s, typing anyway"
    tmux send-keys -t "$pane" -l "$line"; tmux send-keys -t "$pane" Enter; sleep 2
  done <<<"$prompt"
  echo "$(date '+%F %T') done"
  exit 0
fi

usage() { echo 'usage: rollover.sh --handoff <abs path> [--name "<next name>"] [--dry-run]' >&2; exit 2; }
handoff="" name="" dry=""
while [ $# -gt 0 ]; do
  case "$1" in
    --handoff) [ $# -ge 2 ] || usage; handoff="$2"; shift 2 ;;
    --name) [ $# -ge 2 ] || usage; name="$2"; shift 2 ;;
    --dry-run) dry=1; shift ;;
    *) usage ;;
  esac
done
[ -n "$handoff" ] || usage
[ -f "$handoff" ] || { echo "error: --handoff not a file: $handoff" >&2; exit 1; }
handoff="$(cd "$(dirname "$handoff")" && pwd)/$(basename "$handoff")"

sid="${CLAUDE_CODE_SESSION_ID:-}"
transcript=""
[ -z "$sid" ] || transcript="$(ls "${ROLLOVER_PROJECTS:-$HOME/.claude/projects}"/*/"$sid".jsonl 2>/dev/null | head -1)"

current="" bumped=""
if [ -n "$transcript" ]; then
  titles="$(python3 -I - "$transcript" <<'PY' 2>/dev/null || true
import json, re, sys
title = ""
for line in open(sys.argv[1], encoding="utf-8", errors="replace"):
    if '"custom-title"' not in line:
        continue
    try:
        t = json.loads(line).get("customTitle", "")
    except Exception:
        continue
    if t.strip():
        title = t.strip()
print(title)
if title:
    m = re.search(r"([vV])(\d+)$", title) or re.search(r"(?<=\S)( )(\d+)$", title)
    print(title[: m.start(2)] + str(int(m.group(2)) + 1) if m else title + " v2")
PY
)"
  current="$(sed -n 1p <<<"$titles")"
  bumped="$(sed -n 2p <<<"$titles")"
fi
# section <title> [all]: the first non-empty line under "## <title>" in the handoff, list marker
# and backticks stripped; with "all", every such line of the section, one per line (code fence
# lines skipped); empty when the handoff has no such section.
section() {
  python3 -I - "$handoff" "$1" "${2:-}" <<'PY'
import re, sys
want, every, lines, inside = sys.argv[2].lower(), sys.argv[3] == "all", [], False
for raw in open(sys.argv[1], encoding="utf-8", errors="replace"):
    m = re.match(r"^#{1,6}\s+(.*?)\s*$", raw)
    if m:
        if inside and lines:
            break
        inside = m.group(1).lower() == want
        continue
    if inside and raw.strip() and not (every and raw.strip().startswith(chr(96) * 3)):
        lines.append(re.sub(r"^[-*]\s+", "", raw.strip()).strip(chr(96)).strip())
        if not every:
            break
print("\n".join(lines))
PY
}

[ -n "$name" ] || name="$(section "session name")"
[ -n "$name" ] || name="$bumped"
if [ -z "$name" ]; then
  echo "error: this session has no name in its transcript; pass --name" >&2
  exit 4
fi

default_prompt="Read $handoff and continue."
prompt="$(section "starter prompt" all)"
if [ -z "$prompt" ]; then
  prompt="$default_prompt"
elif [[ "$prompt" != *"$handoff"* ]]; then
  prompt="$prompt $default_prompt"
fi

own_pane() {
  if [ -n "${TMUX_PANE:-}" ]; then echo "$TMUX_PANE"; return; fi
  command -v tmux >/dev/null 2>&1 || return 0
  local pid=$$ panes m
  panes="$(tmux list-panes -a -F '#{pane_pid} #{pane_id}' 2>/dev/null)" || return 0
  while [ -n "$pid" ] && [ "$pid" -gt 1 ]; do
    m="$(awk -v p="$pid" '$1 == p { print $2 }' <<<"$panes")"
    if [ -n "$m" ]; then echo "$m"; return; fi
    pid="$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ')"
  done
  # A session attached from a pane (claude --resume of a background session) is not a child of
  # that pane: take the one pane whose title is this session's name.
  [ -n "$current" ] || return 0
  m="$(tmux list-panes -a -F '#{pane_id}	#{pane_title}' | awk -F '\t' -v t="$current" '{ x = $2; sub(/^[^A-Za-z0-9]+/, "", x); if (x == t) print $1 }')"
  [ "$(wc -l <<<"$m" | tr -d ' ')" = 1 ] && echo "$m"
  return 0
}
pane="$(own_pane)"

if [ -n "$dry" ]; then
  echo "name: $name"; echo "pane: ${pane:-none}"; sed 's/^/prompt: /' <<<"$prompt"; exit 0
fi
if [ -z "$pane" ] || [ -z "$transcript" ]; then
  echo "Not inside a tmux pane: nothing typed. Type /clear, then paste: $(sed -n 1p <<<"$prompt")"
  sed -n '2,$s/^/Then paste: /p' <<<"$prompt"
  exit 3
fi

mkdir -p "$HOME/.cache/roll-over"
nohup "$0" --worker "$pane" "$transcript" "$name" "$prompt" "$current" </dev/null >"$HOME/.cache/roll-over/last.log" 2>&1 &
disown || true
echo "Rolling over to \"$name\": this window clears when this turn ends."
