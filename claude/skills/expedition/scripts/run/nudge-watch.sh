#!/usr/bin/env bash
# Nudge watcher for the expedition flow. The built-in "You Should Know" plugin shows a
# "Heads up" note only in the window of the session it came from, so notes for unattended
# windows (runners, spec forks) never reach the owner. This loop polls the plugin's store
# every 5 s and types each note whose source is not the lead into the lead's tmux pane as
# one line: "NUDGE <name or unknown>: <text>" (same typing method as runner.sh send).
#
# Store: key "seen" is a flat list of note texts, appended as shown; key "sessions" is a list
# of {id, askedTurn, offeredTurn?, tag?}, where an entry gaining offeredTurn (or a new value of
# it) means that session was just shown a note. Names come from ~/.claude/expedition-runners.json
# (runner or fork uuid); the lead pane and session id from its key "lead", written by runner.sh
# (an older "lead" entry with only the window resolves to that window's pane running claude).
#
# Safety: a line is typed only into the lead's pane, and only while that pane runs a program
# that is not a shell (zsh, bash, sh, fish, dash, ksh, tcsh); otherwise the note is held in the
# state file and retried on the next poll, never marked delivered. Note text loses every control
# and non-printable character, whitespace is collapsed, and it is cut at 500 characters ("...").
#
# Dead loop: every NUDGE_RESUME_EVERY seconds (default 60) it runs run/check.py --tsv for the
# release of each runner entry that is not stopped, in that entry's folder. A runner gets the line
# "ultracode resume" typed into its pane (the same line as runner.sh resume, so the turn may use
# the Workflow tool) when it owns a row that is silent, finished or no run, and its own transcript
# (<projects>/*/<uuid>.jsonl) has not changed for the stale threshold (NUDGE_STALE_MINUTES,
# default 20): its loop wakeup died, as it does on a usage limit. A row whose owner is no live
# runner (no run id, a stopped or unregistered session) counts for the release's runner when it
# has exactly one. At most one typed line per runner per threshold period (state
# resume-watch.json), repeated each period while such a row remains; never into the lead, never
# into a fork, never while the runner's transcript is fresh. Each typed line is logged. A check.py
# failure is logged and skipped; the watcher goes on.
#
# Usage: nudge-watch.sh          run the loop (runner.sh start and runner.sh watch start detach it)
# Env overrides (tests): NUDGE_STORE, NUDGE_STATE, NUDGE_LOG, NUDGE_REGISTRY (else
# EXPEDITION_REGISTRY), NUDGE_INTERVAL, NUDGE_RESUME_EVERY, NUDGE_STALE_MINUTES,
# NUDGE_RESUME_STATE, EXPEDITION_STATE_DIR, EXPEDITION_PROJECTS (default ~/.claude/projects),
# EXPEDITION_TMUX_SOCKET (tmux -L <socket>).
# State keeps the seen count, the offered (id, turn) pairs and the held notes, so a restart
# replays nothing; a first run initialises from the current store without sending. Exits when
# the registry has no "lead" or the lead window is gone (logged); a registry it cannot parse
# is skipped for that poll.
set -euo pipefail

STATE_DIR="${EXPEDITION_STATE_DIR:-$HOME/.claude/expedition-runners}"
STORE="${NUDGE_STORE:-$HOME/.claude/plugins/store/cc-plugin-you-should-know_builtin-19776595df2c.json}"
STATE="${NUDGE_STATE:-$STATE_DIR/nudge-watch.state}"
LOG="${NUDGE_LOG:-$STATE_DIR/nudge-watch.log}"
REGISTRY="${NUDGE_REGISTRY:-${EXPEDITION_REGISTRY:-$HOME/.claude/expedition-runners.json}}"
PIDFILE="$STATE_DIR/nudge-watch.pid"
INTERVAL="${NUDGE_INTERVAL:-5}"
RESUME_EVERY="${NUDGE_RESUME_EVERY:-60}"
STALE_MINUTES="${NUDGE_STALE_MINUTES:-20}"
RESUME_STATE="${NUDGE_RESUME_STATE:-$STATE_DIR/resume-watch.json}"
CHECK="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/check.py"
export EXPEDITION_REGISTRY="$REGISTRY"

# Every tmux call goes to the default server, or to "tmux -L $EXPEDITION_TMUX_SOCKET" in tests.
tmux() {
  if [ -n "${EXPEDITION_TMUX_SOCKET:-}" ]; then command tmux -L "$EXPEDITION_TMUX_SOCKET" "$@"; else command tmux "$@"; fi
}

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

# pane_typable <pane id>: the pane exists, is not dead, and its foreground program is not a shell.
pane_typable() {
  local info
  info="$(tmux display-message -p -t "$1" '#{pane_dead} #{pane_current_command}' 2>/dev/null)" || return 1
  case "$info" in
    "0 "*) ;;
    *) return 1 ;;
  esac
  case "${info#0 }" in
    ""|zsh|-zsh|bash|-bash|sh|-sh|fish|-fish|dash|-dash|ksh|-ksh|tcsh|-tcsh) return 1 ;;
  esac
  return 0
}

# lead_pane <recorded pane> <window>: the recorded pane when it still exists; for an older entry
# without one, the window's pane running claude (claude, node, or the version-named binary).
lead_pane() {
  if [ -n "$1" ]; then
    tmux display-message -p -t "$1" '#{pane_id}' 2>/dev/null || true
    return 0
  fi
  tmux list-panes -t "$2" -F '#{pane_id} #{pane_current_command}' 2>/dev/null \
    | awk '$2 == "claude" || $2 == "node" || $2 ~ /^[0-9]+\.[0-9]+\.[0-9]+$/ { print $1; exit }'
}

# Same method as runner.sh cmd_send: literal text, pause, Enter, re-Enter if still in the box.
type_line() {
  local target="$1" line="$2"
  tmux send-keys -t "$target" -l -- "$line"
  sleep 0.3
  tmux send-keys -t "$target" Enter
  sleep 1
  if tmux capture-pane -p -t "$target" \
      | awk '/^[[:space:]]*─/ { n++; box[n] = buf; buf = ""; next } { buf = buf $0 } END { print box[n] }' \
      | grep -qF -- "${line:0:40}"; then
    tmux send-keys -t "$target" Enter
  fi
}

# lead_info: "<window>|<pane>|<session>" of the registry key "lead"; empty when there is no
# lead; exit 3 when the registry cannot be parsed.
lead_info() {
  python3 -I - "$REGISTRY" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
try:
    d = json.loads(p.read_text()) if p.is_file() else {}
    if not isinstance(d, dict):
        raise ValueError("not an object")
except (ValueError, OSError):
    sys.exit(3)
e = d.get("lead") or {}
if not isinstance(e, dict) or not e.get("tmux"):
    sys.exit(0)
print("|".join(str(e.get(k, "") or "").replace("|", "") for k in ("tmux", "pane", "session")))
PY
}

# poll: compares the store with the state file, adds each new note as a cleaned line
# "NUDGE <source>: <text>" to the held list in the state, and prints every held line as
# "new\t<line>" or "held\t<line>". First run (no state file) initialises and prints nothing.
poll() {
  python3 -I - "$STORE" "$STATE" "$REGISTRY" "$1" <<'PY'
import json, sys, unicodedata
from pathlib import Path
store, state, registry, lead = (Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4])

def load(p):
    try:
        return json.loads(p.read_text()) if p.is_file() else None
    except (ValueError, OSError):
        return None

def clean(s, cap=500):
    s = "".join(" " if ch.isspace() else ch for ch in s)
    s = "".join(ch for ch in s if unicodedata.category(ch)[0] != "C")
    s = " ".join(s.split())
    return s if len(s) <= cap else s[:cap - 3].rstrip() + "..."

data = load(store) or {}
seen = [s if isinstance(s, str) else json.dumps(s) for s in data.get("seen") or []]
offered = {f"{s.get('id')}:{s.get('offeredTurn')}": s.get("id")
           for s in data.get("sessions") or [] if isinstance(s, dict) and s.get("offeredTurn")}
old = load(state)
held = [h for h in (old or {}).get("pending") or [] if isinstance(h, str)]
new = []
if old is not None:
    start = old.get("seen", 0)
    texts = seen[start:] if start <= len(seen) else []  # store pruned or reset: nothing new
    new_ids = [i for k, i in offered.items() if k not in set(old.get("offered") or [])]
    reg = load(registry)
    reg = reg if isinstance(reg, dict) else {}
    names = {e.get("uuid"): name for name, e in reg.items()
             if name != "lead" and isinstance(e, dict) and e.get("uuid")}
    others = [i for i in new_ids if i != lead]
    if texts and not (new_ids and not others):  # only the lead was shown a note: it sees its own
        source = ", ".join(dict.fromkeys(names.get(i, "unknown") for i in others)) or "unknown"
        new = [f"NUDGE {clean(source, 100)}: {clean(t)}" for t in texts]
state.write_text(json.dumps({"seen": len(seen), "offered": sorted(offered), "pending": held + new}) + "\n")
for line in held:
    print("held\t" + line)
for line in new:
    print("new\t" + line)
PY
}

# ack <line>: drop the first held copy of a delivered line from the state.
ack() {
  python3 -I - "$STATE" "$1" <<'PY'
import json, sys
from pathlib import Path
p, line = Path(sys.argv[1]), sys.argv[2]
d = json.loads(p.read_text())
pending = d.get("pending") or []
if line in pending:
    pending.remove(line)
d["pending"] = pending
p.write_text(json.dumps(d) + "\n")
PY
}

# resume_targets: one line "<name>\t<pane>\t<window>\t<rows>" per runner to wake (see the header);
# nothing on any failure, which goes to the log.
resume_targets() {
  python3 -I - "$REGISTRY" "$CHECK" "$RESUME_STATE" "$STALE_MINUTES" "${EXPEDITION_PROJECTS:-$HOME/.claude/projects}" <<'PY' 2>>"$LOG" || true
import glob, json, os, subprocess, sys, time
from pathlib import Path
registry, check, state, stale, projects = sys.argv[1], sys.argv[2], Path(sys.argv[3]), float(sys.argv[4]) * 60, sys.argv[5]
now = time.time()

def log(msg):
    print(time.strftime("%Y-%m-%dT%H:%M:%S") + " resume check: " + msg, file=sys.stderr)

try:
    reg = json.loads(Path(registry).read_text())
    assert isinstance(reg, dict)
except Exception:
    sys.exit(0)
runners = {n: e for n, e in reg.items() if n != "lead" and isinstance(e, dict) and e.get("kind", "runner") != "fork"
           and e.get("state") != "stopped" and e.get("uuid") and e.get("release")}
try:
    typed = json.loads(state.read_text())
    typed = typed if isinstance(typed, dict) else {}
except Exception:
    typed = {}
due = {}
for release, cwd in sorted({(e["release"], e.get("cwd") or "") for e in runners.values()}):
    try:
        out = subprocess.run(["python3", "-I", check, release, "--tsv", "--stale", str(stale / 60)],
                             cwd=cwd if os.path.isdir(cwd) else None, capture_output=True, text=True, timeout=120)
    except Exception as exc:
        log(f"{release}: check.py did not run ({exc})")
        continue
    if out.returncode != 0:
        log(f"{release}: check.py exit {out.returncode}: {(out.stderr.strip().splitlines() or [''])[-1]}")
        continue
    mine = [n for n, e in runners.items() if e["release"] == release]
    for line in out.stdout.splitlines():
        f = line.split("\t")
        if len(f) < 6 or f[1] not in ("silent", "finished", "no run"):
            continue
        owner = f[3] if f[3] in mine else (mine[0] if len(mine) == 1 else None)
        if owner and f"{f[0]} {f[1]}" not in due.get(owner, []):
            due.setdefault(owner, []).append(f"{f[0]} {f[1]}")
for name, rows in sorted(due.items()):
    e = runners[name]
    seen = [os.path.getmtime(p) for p in glob.glob(os.path.join(projects, "*", e["uuid"] + ".jsonl"))]
    if seen and now - max(seen) < stale:
        continue  # the runner is active
    if now - float(typed.get(name, 0) or 0) < stale:
        continue  # typed once this period already
    print("\t".join([name, e.get("pane") or "", e.get("tmux") or "", ", ".join(rows)]))
PY
}

# resume_typed <name>: record the time of a typed resume, for the once-per-period rule.
resume_typed() {
  python3 -I - "$RESUME_STATE" "$1" <<'PY' || true
import json, sys, time
from pathlib import Path
p = Path(sys.argv[1])
try:
    d = json.loads(p.read_text())
    d = d if isinstance(d, dict) else {}
except Exception:
    d = {}
d[sys.argv[2]] = time.time()
p.write_text(json.dumps(d) + "\n")
PY
}

# resume_check: type "ultracode resume" into each runner resume_targets names, when its pane runs
# claude (never a shell).
resume_check() {
  local name rpane rtmux rows pane
  while IFS=$'\t' read -r name rpane rtmux rows; do
    [ -n "$name" ] || continue
    pane="$(lead_pane "$rpane" "$rtmux")"
    if [ -n "$pane" ] && pane_typable "$pane"; then
      type_line "$pane" "ultracode resume"
      resume_typed "$name"
      log "resume typed into $name ($pane): $rows"
    fi
  done < <(resume_targets)
}

info="$(lead_info)" || info=""
if [ -z "$info" ]; then
  log "exit: registry $REGISTRY has no lead"
  exit 0
fi
log "start pid $$ lead $(cut -d"|" -f1,2 <<< "$info" | tr "|" " ") store $STORE"

unreadable=0
last_resume=0
while true; do
  # The lead can move (a new lead session records itself): re-read it each poll.
  rc=0
  info="$(lead_info)" || rc=$?
  if [ "$rc" = 3 ]; then
    [ "$unreadable" = 1 ] || log "registry $REGISTRY unreadable: skipped this poll"
    unreadable=1
    sleep "$INTERVAL"
    continue
  fi
  unreadable=0
  if [ -z "$info" ]; then log "exit: registry has no lead"; exit 0; fi
  IFS="|" read -r lead_tmux lead_pane_id lead_session <<< "$info"
  if ! window_alive "$lead_tmux"; then log "exit: lead window $lead_tmux is gone"; exit 0; fi
  pane="$(lead_pane "$lead_pane_id" "$lead_tmux")"
  while IFS=$'\t' read -r kind line; do
    [ -n "$line" ] || continue
    if [ -n "$pane" ] && pane_typable "$pane"; then
      type_line "$pane" "$line"
      ack "$line"
      log "forwarded to $pane: $line"
    elif [ "$kind" = new ]; then
      log "held (lead pane ${pane:-unknown} is not a claude session): $line"
    fi
  done < <(poll "$lead_session")
  if [ $(( $(date +%s) - last_resume )) -ge "$RESUME_EVERY" ]; then
    last_resume="$(date +%s)"
    resume_check || log "resume check failed"
  fi
  sleep "$INTERVAL"
done
