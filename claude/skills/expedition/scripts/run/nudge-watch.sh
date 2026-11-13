#!/usr/bin/env bash
# Nudge watcher for the expedition flow. The built-in "You Should Know" plugin shows a
# "Heads up" note only in the window of the session it came from, so notes for unattended
# windows (runners, spec forks) never reach the owner. This loop polls the plugin's store
# every 5 s and types each note whose source is not the lead into the lead's tmux window as
# one line: "NUDGE <name or unknown>: <text>" (same typing method as runner.sh send).
#
# Store: key "seen" is a flat list of note texts, appended as shown; key "sessions" is a list
# of {id, askedTurn, offeredTurn?, tag?}, where an entry gaining offeredTurn (or a new value of
# it) means that session was just shown a note. Names come from ~/.claude/expedition-runners.json
# (runner or fork uuid); the lead pane and session id from its key "lead", written by runner.sh.
#
# Usage: nudge-watch.sh          run the loop (runner.sh start and runner.sh watch start detach it)
# Env overrides (tests): NUDGE_STORE, NUDGE_STATE, NUDGE_LOG, NUDGE_REGISTRY, NUDGE_INTERVAL.
# State keeps the seen count and the offered (id, turn) pairs, so a restart replays nothing;
# a first run initialises from the current store without sending. Exits when the registry has
# no "lead" or the lead window is gone (logged).
set -euo pipefail

STATE_DIR="$HOME/.claude/expedition-runners"
STORE="${NUDGE_STORE:-$HOME/.claude/plugins/store/cc-plugin-you-should-know_builtin-19776595df2c.json}"
STATE="${NUDGE_STATE:-$STATE_DIR/nudge-watch.state}"
LOG="${NUDGE_LOG:-$STATE_DIR/nudge-watch.log}"
REGISTRY="${NUDGE_REGISTRY:-$HOME/.claude/expedition-runners.json}"
PIDFILE="$STATE_DIR/nudge-watch.pid"
INTERVAL="${NUDGE_INTERVAL:-5}"

mkdir -p "$STATE_DIR" "$(dirname "$STATE")" "$(dirname "$LOG")"

log() { printf '%s %s\n' "$(date '+%Y-%m-%dT%H:%M:%S')" "$*" >> "$LOG"; }

cleanup() {
  # Remove the pid file only when it names this process (a test instance leaves it alone).
  if [ -f "$PIDFILE" ] && [ "$(cat "$PIDFILE" 2>/dev/null)" = "$$" ]; then rm -f "$PIDFILE"; fi
}
trap cleanup EXIT
trap 'log "stopped by signal"; exit 0' INT TERM

window_alive() {
  local target="$1"
  [ -n "$target" ] || return 1
  tmux list-windows -a -F '#{session_name}:#{window_id}' 2>/dev/null | grep -qxF "$target"
}

# Same method as runner.sh cmd_send: literal text, pause, Enter, re-Enter if still in the box.
type_line() {
  local target="$1" line="$2"
  tmux send-keys -t "$target" -l "$line"
  sleep 0.3
  tmux send-keys -t "$target" Enter
  sleep 1
  if tmux capture-pane -p -t "$target" \
      | awk '/^[[:space:]]*─/ { n++; box[n] = buf; buf = ""; next } { buf = buf $0 } END { print box[n] }' \
      | grep -qF -- "${line:0:40}"; then
    tmux send-keys -t "$target" Enter
  fi
}

# lead_field <key>: field of the registry key "lead", empty if missing.
lead_field() {
  python3 -I - "$REGISTRY" "$1" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
try:
    d = json.loads(p.read_text()) if p.is_file() else {}
except ValueError:
    d = {}
print((d.get("lead") or {}).get(sys.argv[2], "") or "")
PY
}

# poll: compares the store with the state file, updates the state, prints one line per note to
# forward as "NUDGE <source>: <text>". First run (no state file) initialises and prints nothing.
poll() {
  python3 -I - "$STORE" "$STATE" "$REGISTRY" "$1" <<'PY'
import json, sys
from pathlib import Path
store, state, registry, lead = (Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4])

def load(p):
    try:
        return json.loads(p.read_text()) if p.is_file() else None
    except ValueError:
        return None

data = load(store) or {}
seen = [s if isinstance(s, str) else json.dumps(s) for s in data.get("seen") or []]
offered = {f"{s.get('id')}:{s.get('offeredTurn')}": s.get("id")
           for s in data.get("sessions") or [] if isinstance(s, dict) and s.get("offeredTurn")}
old = load(state)
state.write_text(json.dumps({"seen": len(seen), "offered": sorted(offered)}) + "\n")
if old is None:
    sys.exit(0)
start = old.get("seen", 0)
if start > len(seen):  # store pruned or reset: nothing new to forward
    sys.exit(0)
texts = seen[start:]
if not texts:
    sys.exit(0)
new_ids = [i for k, i in offered.items() if k not in set(old.get("offered") or [])]
reg = load(registry) or {}
names = {e.get("uuid"): name for name, e in reg.items()
         if name != "lead" and isinstance(e, dict) and e.get("uuid")}
others = [i for i in new_ids if i != lead]
if new_ids and not others:
    sys.exit(0)  # only the lead was shown a note: the lead sees its own notes
source = ", ".join(dict.fromkeys(names.get(i, "unknown") for i in others)) or "unknown"
for t in texts:
    print(f"NUDGE {source}: " + " ".join(t.split()))
PY
}

lead_tmux="$(lead_field tmux)"
lead_session="$(lead_field session)"
if [ -z "$lead_tmux" ]; then
  log "exit: registry $REGISTRY has no lead"
  exit 0
fi
log "start pid $$ lead $lead_tmux session ${lead_session:-?} store $STORE"

while true; do
  # The lead can move (a new lead session records itself): re-read it each poll.
  lead_tmux="$(lead_field tmux)"
  lead_session="$(lead_field session)"
  if [ -z "$lead_tmux" ]; then log "exit: registry has no lead"; exit 0; fi
  if ! window_alive "$lead_tmux"; then log "exit: lead window $lead_tmux is gone"; exit 0; fi
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    type_line "$lead_tmux" "$line"
    log "forwarded to $lead_tmux: $line"
  done < <(poll "$lead_session")
  sleep "$INTERVAL"
done
