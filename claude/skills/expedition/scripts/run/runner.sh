#!/usr/bin/env bash
# Runner session for the expedition flow: a second Claude Code session in a tmux window
# of the lead's own tmux session. It receives "RUN E<n> <release folder> epic <epic file> from <lead>",
# typed into its window by "send", and replies "DONE ..." or "BLOCKED ..." by SendMessage
# (reference/run.md).
#
# Usage: runner.sh start <release> [--model M] [--new] [--from <lead>] [--cwd PATH]   reuse the live runner, resume a dead one, or open the next number; --new opens another runner beside the live one
#        runner.sh list                          registry entries with busy or idle
#        runner.sh stop <release>                close the window, mark the entry stopped
#        runner.sh send [--from <lead>] <release> "<line>"   type "ultracode <line>" into the runner window
#                                                and submit it (typed prompts opt the turn in to
#                                                ultracode; a SendMessage does not)
#        runner.sh fork <release> E<n> "<D ids>" --from <lead> [--model M] [--cwd PATH]
#                                                open window "<release> specs E<n>": a forked session
#                                                of the lead ($CLAUDE_CODE_SESSION_ID) that writes
#                                                the epic's specs and replies "SPECS E<n> ...";
#                                                its own --session-id is in the registry, and a
#                                                fork whose window died is resumed, not forked again
#        runner.sh stop "<window name>"          close a fork window ("<release> specs E<n>")
#        runner.sh watch start|stop|status        the nudge watcher (scripts/run/nudge-watch.sh)
#
# Folder: start and fork open a new window in --cwd, else in the folder the script is called
# from. A resumed runner or fork reopens in the folder stored in its registry entry. list, stop,
# send, resume and watch never use the caller's folder.
#
# Lead: start, send and fork run inside tmux record the calling window as registry key "lead"
# ({"tmux": "<session>:<window id>", "pane": "<pane id>", "session": $CLAUDE_CODE_SESSION_ID,
# "name": --from or the "from <name>" of the sent line}). start also starts the nudge watcher
# (pid file ~/.claude/expedition-runners/nudge-watch.pid), which types "NUDGE <source>: <text>"
# into the lead pane for each You Should Know note shown to a runner, a fork or an unknown
# session; stop stops it once no runner or fork window is live.
#
# Typing: send and resume type into the entry's pane (recorded at start or fork; an older entry
# without one: the window's pane running claude), literal text then Enter as a separate key, and
# only while that pane runs a program that is not a shell; otherwise nothing is typed and the
# command fails with one line.
#
# Registry: ~/.claude/expedition-runners.json, one entry per runner name
# (name, uuid, tmux target, pane, cwd, release, started, state); every write takes a lock and
# replaces the file by rename. Env overrides (tests): EXPEDITION_REGISTRY, EXPEDITION_STATE_DIR. Status files:
# ~/.claude/expedition-runners/<name>.status, written by the hooks in
# templates/runner-settings.json ("idle" on Stop, "busy" on UserPromptSubmit); the hooks find
# the name in EXPEDITION_RUNNER, exported here before exec.
# Model: --model, else $EXPEDITION_RUNNER_MODEL, else fable. Fork model: --model, else
# $EXPEDITION_FORK_MODEL, else fable. Forks are registry entries of kind "fork", no status file.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REGISTRY="${EXPEDITION_REGISTRY:-$HOME/.claude/expedition-runners.json}"
STATE_DIR="${EXPEDITION_STATE_DIR:-$HOME/.claude/expedition-runners}"
SETTINGS="$SKILL_DIR/templates/runner-settings.json"
BRIEF_TEMPLATE="$SKILL_DIR/templates/runner-brief.md"
WATCHER="$SKILL_DIR/scripts/run/nudge-watch.sh"
WATCH_PID="$STATE_DIR/nudge-watch.pid"

die() { echo "error: $*" >&2; exit 1; }

usage() {
  echo "usage: runner.sh start <release> [--model M] [--new] [--from <lead>] [--cwd PATH] | list | stop <release or window name> | send <release> \"<line>\" | resume <release or window name> | fork <release> E<n> \"<D ids>\" --from <lead> [--model M] [--cwd PATH] | watch start|stop|status" >&2
  exit 2
}

# Registry access through stdlib python: reg get <name> | reg put <name> <json> | reg all.
# put and set read, change and write under an exclusive lock on "<registry>.lock" and replace
# the file through a temp file in the same folder, so two writers never lose an entry.
reg() {
  python3 -I - "$REGISTRY" "$@" <<'PY'
import fcntl, json, os, sys, tempfile
from pathlib import Path
path, op = Path(sys.argv[1]), sys.argv[2]

def read():
    return json.loads(path.read_text()) if path.is_file() else {}

def write(change):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(path) + ".lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = read()
        change(data)
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
        with os.fdopen(fd, "w") as f:
            f.write(json.dumps(data, indent=2) + "\n")
        os.replace(tmp, path)

data = read() if op in ("get", "field", "all") else {}
if op == "get":
    e = data.get(sys.argv[3])
    print(json.dumps(e) if e else "")
elif op == "field":
    e = data.get(sys.argv[3]) or {}
    print(e.get(sys.argv[4], ""))
elif op == "put":
    def change(d):
        e = d.get(sys.argv[3], {})
        e.update(json.loads(sys.argv[4]))
        d[sys.argv[3]] = e
    write(change)
elif op == "set":
    write(lambda d: d.__setitem__(sys.argv[3], json.loads(sys.argv[4])))
elif op == "all":
    for name, e in data.items():
        if name == "lead":
            continue
        print("\t".join([name, e.get("state", ""), e.get("uuid", "") or "-", e.get("tmux", ""),
                         e.get("release", ""), e.get("started", ""), e.get("cwd", ""),
                         e.get("kind", "runner")]))
PY
}

window_alive() {
  local target="$1"
  [ -n "$target" ] || return 1
  command -v tmux >/dev/null 2>&1 || return 1
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

# entry_pane <name>: the entry's recorded pane when it still exists; for an older entry without
# one, the pane of its window running claude (claude, node, or the version-named binary).
entry_pane() {
  local pane
  pane="$(reg field "$1" pane)"
  if [ -n "$pane" ]; then
    tmux display-message -p -t "$pane" '#{pane_id}' 2>/dev/null || true
    return 0
  fi
  tmux list-panes -t "$(reg field "$1" tmux)" -F '#{pane_id} #{pane_current_command}' 2>/dev/null \
    | awk '$2 == "claude" || $2 == "node" || $2 ~ /^[0-9]+\.[0-9]+\.[0-9]+$/ { print $1; exit }'
}

# type_into <name> <line>: type the line into the entry's pane and submit it, or fail with one
# line when the pane is gone or runs a shell (nothing typed).
type_into() {
  local pane
  pane="$(entry_pane "$1")"
  [ -n "$pane" ] || die "$1: no claude pane found in its window; nothing typed"
  pane_typable "$pane" || die "$1: pane $pane is not running claude (a shell or gone); nothing typed"
  tmux send-keys -t "$pane" -l -- "$2"
  sleep 0.3
  tmux send-keys -t "$pane" Enter
  TYPED_PANE="$pane"
}

# Runner names: "<release> runner<n>". runner_name <release> returns the newest runner that is
# live or resumable (a live entry under the older key "runner-<release>" counts and keeps its
# name); nothing live: the next unused number. A number is never reused within a release.
# next_runner_name <release> always returns the next unused number (start --new).
runner_name() {
  local old="runner-$1" best="" n
  if [ -n "$(reg field "$old" uuid)" ] && [ "$(reg field "$old" state)" != stopped ]; then
    echo "$old"; return
  fi
  for n in $(seq 50 -1 1); do
    if [ -n "$(reg field "$1 runner$n" uuid)" ] && [ "$(reg field "$1 runner$n" state)" != stopped ]; then
      echo "$1 runner$n"; return
    fi
  done
  next_runner_name "$1"
}

next_runner_name() {
  local n=1
  while [ -n "$(reg field "$1 runner$n" uuid)" ]; do n=$((n+1)); done
  echo "$1 runner$n"
}

# record_lead [name]: inside tmux, store the calling window as registry key "lead"; an empty
# name keeps the recorded one.
record_lead() {
  [ -n "${TMUX:-}" ] || return 0
  local target pane name="${1:-}"
  target="$(tmux display-message -p -t "${TMUX_PANE:-}" '#{session_name}:#{window_id}')"
  pane="$(tmux display-message -p -t "${TMUX_PANE:-}" '#{pane_id}')"
  [ -n "$name" ] || name="$(python3 -I -c 'import json,sys; from pathlib import Path; p=Path(sys.argv[1]); d=json.loads(p.read_text()) if p.is_file() else {}; print((d.get("lead") or {}).get("name", ""))' "$REGISTRY")"
  reg set lead "$(python3 -I -c 'import json,sys; print(json.dumps({"tmux": sys.argv[1], "pane": sys.argv[4], "session": sys.argv[2], "name": sys.argv[3]}))' "$target" "${CLAUDE_CODE_SESSION_ID:-}" "$name" "$pane")"
}

# watch_running: the pid file names a live nudge-watch.sh process; a stale pid file (no such
# process, or a pid reused by another program) is removed.
watch_running() {
  local pid
  pid="$(cat "$WATCH_PID" 2>/dev/null || true)"
  [ -n "$pid" ] || return 1
  if [[ "$pid" =~ ^[0-9]+$ ]] && ps -p "$pid" -o command= 2>/dev/null | grep -qF nudge-watch.sh; then
    return 0
  fi
  rm -f "$WATCH_PID"
  return 1
}

watch_start() {
  if watch_running; then echo "nudge watcher running (pid $(cat "$WATCH_PID"))"; return 0; fi
  mkdir -p "$STATE_DIR"
  nohup "$WATCHER" </dev/null >/dev/null 2>&1 &
  echo $! > "$WATCH_PID"
  disown 2>/dev/null || true
  echo "nudge watcher started (pid $(cat "$WATCH_PID"))"
}

watch_stop() {
  if watch_running; then kill "$(cat "$WATCH_PID")"; echo "nudge watcher stopped"; else echo "nudge watcher not running"; fi
  rm -f "$WATCH_PID"
}

# any_live: a runner or fork entry not stopped whose window is alive.
any_live() {
  local name state uuid target rest
  while IFS=$'\t' read -r name state uuid target rest; do
    [ -n "$name" ] || continue
    [ "$state" != stopped ] && window_alive "$target" && return 0
  done <<< "$(reg all)"
  return 1
}

cmd_watch() {
  [ $# -eq 1 ] || usage
  case "$1" in
    start) watch_start ;;
    stop) watch_stop ;;
    status)
      if watch_running; then echo "nudge watcher running (pid $(cat "$WATCH_PID"))"; else echo "nudge watcher not running"; fi ;;
    *) usage ;;
  esac
}

# Status and brief files: the name with spaces replaced by "-".
file_of() { echo "$STATE_DIR/${1// /-}"; }

check_release() {
  [[ "$1" =~ ^v[0-9]+\.[0-9]+\.x$ ]] || die "bad release '$1', expected like v0.9.x"
}

# new_cwd [PATH]: the absolute folder a new window opens in: PATH, else the caller's folder.
new_cwd() {
  if [ -n "${1:-}" ]; then
    [ -d "$1" ] || die "--cwd not a folder: $1"
    (cd "$1" && pwd)
  else
    pwd
  fi
}

cmd_start() {
  local release="" model="${EXPEDITION_RUNNER_MODEL:-fable}" new=0 from="" cwd_flag=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --model) [ $# -ge 2 ] || usage; model="$2"; shift 2 ;;
      --from) [ $# -ge 2 ] || usage; from="$2"; shift 2 ;;
      --cwd) [ $# -ge 2 ] || usage; cwd_flag="$2"; shift 2 ;;
      --new) new=1; shift ;;
      -*) usage ;;
      *) [ -z "$release" ] || usage; release="$1"; shift ;;
    esac
  done
  [ -n "$release" ] || usage
  check_release "$release"
  local name
  if [ "$new" = 1 ]; then name="$(next_runner_name "$release")"; else name="$(runner_name "$release")"; fi
  local cwd
  cwd="$(new_cwd "$cwd_flag")"
  mkdir -p "$STATE_DIR"

  local state uuid target resume=0
  state="$(reg field "$name" state)"
  uuid="$(reg field "$name" uuid)"
  target="$(reg field "$name" tmux)"
  record_lead "$from"
  if [ -n "$uuid" ] && [ "$state" != "stopped" ]; then
    if window_alive "$target"; then
      echo "$name already running in $target (session $uuid)"
      watch_start
      exit 0
    fi
    resume=1
    cwd="$(reg field "$name" cwd)"
  else
    uuid="$(python3 -I -c 'import uuid; print(uuid.uuid4())')"
  fi

  local brief
  brief="$(file_of "$name").brief.md"
  sed -e "s|{{release}}|$release|g" -e "s|{{name}}|$name|g" -e "s|{{brief}}|$brief|g" "$BRIEF_TEMPLATE" > "$brief"

  local prompt="ultracode. You are $name, the expedition runner for $release. Follow the appended brief. Reply with one line: ready."
  local -a cmd=(claude -n "$name" --dangerously-skip-permissions --model "$model"
                --settings "$SETTINGS" --append-system-prompt-file "$brief")
  if [ "$resume" = 1 ]; then
    cmd+=(--resume "$uuid")
    prompt="ultracode. You are $name, resumed. Re-read the appended brief, then continue every epic that has a running row in status/sprints.md."
  else
    cmd+=(--session-id "$uuid")
  fi
  cmd+=("$prompt")

  local line
  line="export EXPEDITION_RUNNER=$(printf '%q' "${name// /-}"); cd $(printf '%q' "$cwd") && exec$(printf ' %q' "${cmd[@]}")"

  if [ -z "${TMUX:-}" ]; then
    echo "Not inside tmux. Run this in a terminal of its own:"
    echo "$line"
    exit 0
  fi

  local session
  session="$(tmux display-message -p '#{session_name}')"
  local pane
  read -r target pane < <(tmux new-window -d -P -F '#{session_name}:#{window_id} #{pane_id}' -t "$session:" -n "$name" -c "$cwd" "$line")
  printf 'busy' > "$(file_of "$name").status"
  reg put "$name" "$(python3 -I -c 'import json,sys,datetime; print(json.dumps({"name": sys.argv[1], "uuid": sys.argv[2], "tmux": sys.argv[3], "pane": sys.argv[6], "cwd": sys.argv[4], "release": sys.argv[5], "started": datetime.datetime.now().isoformat(timespec="seconds"), "state": "running"}))' "$name" "$uuid" "$target" "$cwd" "$release" "$pane")"
  if [ "$resume" = 1 ]; then
    echo "$name resumed in $target (session $uuid)"
  else
    echo "$name started in $target (session $uuid)"
  fi
  watch_start
}

cmd_list() {
  local rows
  rows="$(reg all)"
  if [ -z "$rows" ]; then
    echo "no runners"
    return 0
  fi
  local name state uuid target release started cwd kind status
  while IFS=$'\t' read -r name state uuid target release started cwd kind; do
    status="-"
    if [ "$state" != "stopped" ]; then
      if window_alive "$target"; then
        [ "$kind" = fork ] || status="$(cat "$(file_of "$name").status" 2>/dev/null || echo unknown)"
      elif [ "$kind" = fork ]; then
        status="dead (fork resumes it)"
      else
        status="dead (start resumes it)"
      fi
    fi
    printf '%s\t%s\t%s\t%s\t%s\tstarted %s\n' "$name" "$state" "$status" "$target" "$uuid" "$started"
  done <<< "$rows"
}

cmd_stop() {
  [ $# -eq 1 ] || usage
  local name="$1" target
  if [[ "$1" =~ ^v[0-9]+\.[0-9]+\.x$ ]]; then
    name="$(runner_name "$1")"
  fi
  [ -n "$(reg field "$name" state)" ] || die "no registry entry for $name"
  target="$(reg field "$name" tmux)"
  if window_alive "$target"; then
    tmux kill-window -t "$target"
  fi
  reg put "$name" '{"state": "stopped"}'
  if [ "$(reg field "$name" kind)" != fork ]; then
    printf 'stopped' > "$(file_of "$name").status"
  fi
  echo "$name stopped"
  if ! any_live && watch_running; then watch_stop; fi
}

cmd_fork() {
  local release="" epic="" ids="" from="" prompt="" model="${EXPEDITION_FORK_MODEL:-fable}" cwd_flag=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --model) [ $# -ge 2 ] || usage; model="$2"; shift 2 ;;
      --from) [ $# -ge 2 ] || usage; from="$2"; shift 2 ;;
      --cwd) [ $# -ge 2 ] || usage; cwd_flag="$2"; shift 2 ;;
      --prompt) [ $# -ge 2 ] || usage; prompt="$2"; shift 2 ;;  # tests only: replaces the prompt
      -*) usage ;;
      *)
        if [ -z "$release" ]; then release="$1"
        elif [ -z "$epic" ]; then epic="$1"
        elif [ -z "$ids" ]; then ids="$1"
        else usage
        fi
        shift ;;
    esac
  done
  [ -n "$release" ] && [ -n "$epic" ] && [ -n "$ids" ] || usage
  check_release "$release"
  [[ "$epic" =~ ^E[0-9]+$ ]] || die "bad epic '$epic', expected like E3"
  [ -n "$from" ] || die "--from <lead session name> is required"
  record_lead "$from"
  local name="$release specs $epic" cwd target uuid resume=0 parent="${CLAUDE_CODE_SESSION_ID:-}"
  cwd="$(new_cwd "$cwd_flag")"
  uuid="$(reg field "$name" uuid)"
  if [ -n "$uuid" ] && [ "$(reg field "$name" state)" != stopped ]; then
    if window_alive "$(reg field "$name" tmux)"; then
      echo "$name already running in $(reg field "$name" tmux)"
      exit 0
    fi
    # A live entry whose window is gone: resume the fork's own session, never fork again.
    resume=1
    cwd="$(reg field "$name" cwd)"
    parent="$(reg field "$name" parent)"
  else
    [ -n "$parent" ] || die "CLAUDE_CODE_SESSION_ID is unset: run fork from the lead session"
    uuid="$(python3 -I -c 'import uuid; print(uuid.uuid4())')"
  fi
  if [ "$resume" = 1 ]; then
    prompt="Resumed. Finish the task of the first prompt of this session, then stop."
  elif [ -z "$prompt" ]; then
    prompt="You are the spec writer for epic $epic of $release, decisions $ids. You hold the lead's full context. First read the epic file plan/epics/$epic.md in the release folder and every file its Notes name. Then, per SKILL.md stage 2: fill the Files column of the epic's Ownership table (the files each decision changes, as the project writes the paths); cut the epic into specs weighing the three aims; write the specs with plan/new_spec.py; run epics/table.py $release $epic <spec numbers> to complete the table; check the plan with that output and your own judgment and regroup the specs if a clearly better cut exists; then reply by SendMessage to $from with one line: SPECS $epic <spec numbers>. Do nothing else."
  fi
  local -a cmd
  if [ "$resume" = 1 ]; then
    cmd=(claude --resume "$uuid" -n "$name" --dangerously-skip-permissions --model "$model"
         --settings "$SETTINGS" "$prompt")
  else
    cmd=(claude --resume "$parent" --fork-session --session-id "$uuid" -n "$name"
         --dangerously-skip-permissions --model "$model" --settings "$SETTINGS" "$prompt")
  fi
  local line
  line="cd $(printf '%q' "$cwd") && exec$(printf ' %q' "${cmd[@]}")"
  if [ -z "${TMUX:-}" ]; then
    echo "Not inside tmux. Run this in a terminal of its own:"
    echo "$line"
    exit 0
  fi
  local pane
  read -r target pane < <(tmux new-window -d -P -F '#{session_name}:#{window_id} #{pane_id}' -t "$(tmux display-message -p '#{session_name}'):" -n "$name" -c "$cwd" "$line")
  reg put "$name" "$(python3 -I -c 'import json,sys,datetime; print(json.dumps({"name": sys.argv[1], "kind": "fork", "uuid": sys.argv[6], "parent": sys.argv[2], "tmux": sys.argv[3], "pane": sys.argv[7], "cwd": sys.argv[4], "release": sys.argv[5], "started": datetime.datetime.now().isoformat(timespec="seconds"), "state": "running"}))' "$name" "$parent" "$target" "$cwd" "$release" "$uuid" "$pane")"
  if [ "$resume" = 1 ]; then
    echo "$name resumed in $target (session $uuid, model $model)"
  else
    echo "$name started in $target (session $uuid, fork of $parent, model $model)"
  fi
}

# resume <release | "<window name>">: a live window gets the word "resume" typed in (the runner
# with the ultracode prefix, a fork without); a dead runner is started again (start resumes it);
# a dead fork prints its claude --resume line. Never stop a window on a usage limit.
cmd_resume() {
  [ $# -eq 1 ] || usage
  local name target uuid state line
  if [[ "$1" =~ ^v[0-9]+\.[0-9]+\.x$ ]]; then name="$(runner_name "$1")"; line="ultracode resume"; else name="$1"; line="resume"; fi
  uuid="$(reg field "$name" uuid)"
  [ -n "$uuid" ] || die "no registry entry for $name"
  state="$(reg field "$name" state)"
  target="$(reg field "$name" tmux)"
  if window_alive "$target"; then
    type_into "$name" "$line"
    echo "typed into $target ($TYPED_PANE): $line"
  elif [[ "$1" =~ ^v[0-9]+\.[0-9]+\.x$ ]]; then
    [ "$state" != "stopped" ] || reg put "$name" '{"state": "running"}'
    cmd_start "$1"
  else
    echo "$name window is gone. Resume it in a terminal of its own:"
    echo "cd $(printf '%q' "$(reg field "$name" cwd)") && claude -n $(printf '%q' "$name") --dangerously-skip-permissions --settings $(printf '%q' "$SETTINGS") --resume $uuid"
  fi
}

cmd_send() {
  local from=""
  if [ "${1:-}" = --from ]; then [ $# -ge 2 ] || usage; from="$2"; shift 2; fi
  [ $# -eq 2 ] || usage
  local name line="ultracode $2" target i
  # The lead name: --from, else the "from <name>" that ends a RUN or HELLO line.
  [ -n "$from" ] || from="$(sed -nE 's/.* from ([^ ]+)$/\1/p' <<< "$2")"
  record_lead "$from"
  if [[ "$1" =~ ^v[0-9]+\.[0-9]+\.x$ ]]; then name="$(runner_name "$1")"; else name="$1"; fi
  [ -n "$(reg field "$name" uuid)" ] || die "no registry entry for $name"
  [ "$(reg field "$name" state)" != "stopped" ] || die "$name is stopped: runner.sh start $1"
  target="$(reg field "$name" tmux)"
  window_alive "$target" || die "$name window is gone: runner.sh start $1 resumes it"
  type_into "$name" "$line"
  # A long line can stay in the input box after the first Enter: check, send Enter once more.
  sleep 1
  # The input box is the text between the last two rule lines of the pane.
  if tmux capture-pane -p -t "$TYPED_PANE" \
      | awk '/^[[:space:]]*─/ { n++; box[n] = buf; buf = ""; next } { buf = buf $0 } END { print box[n] }' \
      | grep -qF -- "${line:0:40}" && pane_typable "$TYPED_PANE"; then
    tmux send-keys -t "$TYPED_PANE" Enter
  fi
  echo "typed into $target ($TYPED_PANE): $line"
}

[ $# -ge 1 ] || usage
sub="$1"; shift
case "$sub" in
  start) cmd_start "$@" ;;
  list) [ $# -eq 0 ] || usage; cmd_list ;;
  stop) cmd_stop "$@" ;;
  send) cmd_send "$@" ;;
  resume) cmd_resume "$@" ;;
  fork) cmd_fork "$@" ;;
  watch) cmd_watch "$@" ;;
  *) usage ;;
esac
