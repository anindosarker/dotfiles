#!/usr/bin/env bash
# Runner session for the expedition batch flow: a second Claude Code session in a tmux window
# of the talker's own tmux session. It receives "RUN <batch> <release folder>" and replies
# "DONE ..." or "BLOCKED ..." (reference/run.md).
#
# Usage: runner.sh start <release> [--model M]   open the window, or resume a dead runner
#        runner.sh list                          registry entries with busy or idle
#        runner.sh stop <release>                close the window, mark the entry stopped
#
# Registry: ~/.claude/expedition-runners.json, one entry per runner name
# (name, uuid, tmux target, cwd, release, started, state). Status files:
# ~/.claude/expedition-runners/<name>.status, written by the hooks in
# templates/runner-settings.json ("idle" on Stop, "busy" on UserPromptSubmit); the hooks find
# the name in EXPEDITION_RUNNER, exported here before exec.
# Model: --model, else $EXPEDITION_RUNNER_MODEL, else opus.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REGISTRY="$HOME/.claude/expedition-runners.json"
STATE_DIR="$HOME/.claude/expedition-runners"
SETTINGS="$SKILL_DIR/templates/runner-settings.json"
BRIEF_TEMPLATE="$SKILL_DIR/templates/runner-brief.md"

die() { echo "error: $*" >&2; exit 1; }

usage() {
  echo "usage: runner.sh start <release> [--model M] | list | stop <release>" >&2
  exit 2
}

# Registry access through stdlib python: reg get <name> | reg put <name> <json> | reg all
reg() {
  python3 -I - "$REGISTRY" "$@" <<'PY'
import json, sys
from pathlib import Path
path, op = Path(sys.argv[1]), sys.argv[2]
data = json.loads(path.read_text()) if path.is_file() else {}
if op == "get":
    e = data.get(sys.argv[3])
    print(json.dumps(e) if e else "")
elif op == "field":
    e = data.get(sys.argv[3]) or {}
    print(e.get(sys.argv[4], ""))
elif op == "put":
    e = data.get(sys.argv[3], {})
    e.update(json.loads(sys.argv[4]))
    data[sys.argv[3]] = e
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")
elif op == "all":
    for name, e in data.items():
        print("\t".join([name, e.get("state", ""), e.get("uuid", ""), e.get("tmux", ""),
                         e.get("release", ""), e.get("started", ""), e.get("cwd", "")]))
PY
}

window_alive() {
  local target="$1"
  [ -n "$target" ] || return 1
  command -v tmux >/dev/null 2>&1 || return 1
  tmux list-windows -a -F '#{session_name}:#{window_id}' 2>/dev/null | grep -qxF "$target"
}

check_release() {
  [[ "$1" =~ ^v[0-9]+\.[0-9]+\.x$ ]] || die "bad release '$1', expected like v0.9.x"
}

cmd_start() {
  local release="" model="${EXPEDITION_RUNNER_MODEL:-opus}"
  while [ $# -gt 0 ]; do
    case "$1" in
      --model) [ $# -ge 2 ] || usage; model="$2"; shift 2 ;;
      -*) usage ;;
      *) [ -z "$release" ] || usage; release="$1"; shift ;;
    esac
  done
  [ -n "$release" ] || usage
  check_release "$release"
  local name="runner-$release"
  local cwd
  cwd="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
  mkdir -p "$STATE_DIR"

  local state uuid target resume=0
  state="$(reg field "$name" state)"
  uuid="$(reg field "$name" uuid)"
  target="$(reg field "$name" tmux)"
  if [ -n "$uuid" ] && [ "$state" != "stopped" ]; then
    if window_alive "$target"; then
      echo "$name already running in $target (session $uuid)"
      exit 0
    fi
    resume=1
    cwd="$(reg field "$name" cwd)"
  else
    uuid="$(python3 -I -c 'import uuid; print(uuid.uuid4())')"
  fi

  local brief="$STATE_DIR/$name.brief.md"
  sed -e "s|{{release}}|$release|g" -e "s|{{name}}|$name|g" "$BRIEF_TEMPLATE" > "$brief"

  local prompt="ultracode. You are $name, the expedition runner for $release. Follow the appended brief. Reply with one line: ready."
  local -a cmd=(claude -n "$name" --dangerously-skip-permissions --model "$model"
                --settings "$SETTINGS" --append-system-prompt-file "$brief")
  if [ "$resume" = 1 ]; then
    cmd+=(--resume "$uuid")
    prompt="ultracode. You are $name, resumed. Re-read the appended brief, then continue every batch whose sprints.md column is running."
  else
    cmd+=(--session-id "$uuid")
  fi
  cmd+=("$prompt")

  local line
  line="export EXPEDITION_RUNNER=$(printf '%q' "$name"); cd $(printf '%q' "$cwd") && exec$(printf ' %q' "${cmd[@]}")"

  if [ -z "${TMUX:-}" ]; then
    echo "Not inside tmux. Run this in a terminal of its own:"
    echo "$line"
    exit 0
  fi

  local session
  session="$(tmux display-message -p '#{session_name}')"
  target="$(tmux new-window -d -P -F '#{session_name}:#{window_id}' -t "$session:" -n "$name" -c "$cwd" "$line")"
  printf 'busy' > "$STATE_DIR/$name.status"
  reg put "$name" "$(python3 -I -c 'import json,sys,datetime; print(json.dumps({"name": sys.argv[1], "uuid": sys.argv[2], "tmux": sys.argv[3], "cwd": sys.argv[4], "release": sys.argv[5], "started": datetime.datetime.now().isoformat(timespec="seconds"), "state": "running"}))' "$name" "$uuid" "$target" "$cwd" "$release")"
  if [ "$resume" = 1 ]; then
    echo "$name resumed in $target (session $uuid)"
  else
    echo "$name started in $target (session $uuid)"
  fi
}

cmd_list() {
  local rows
  rows="$(reg all)"
  if [ -z "$rows" ]; then
    echo "no runners"
    return 0
  fi
  local name state uuid target release started cwd status
  while IFS=$'\t' read -r name state uuid target release started cwd; do
    status="-"
    if [ "$state" != "stopped" ]; then
      if window_alive "$target"; then
        status="$(cat "$STATE_DIR/$name.status" 2>/dev/null || echo unknown)"
      else
        status="dead (start resumes it)"
      fi
    fi
    printf '%s\t%s\t%s\t%s\t%s\tstarted %s\n' "$name" "$state" "$status" "$target" "$uuid" "$started"
  done <<< "$rows"
}

cmd_stop() {
  [ $# -eq 1 ] || usage
  check_release "$1"
  local name="runner-$1" target
  [ -n "$(reg field "$name" uuid)" ] || die "no registry entry for $name"
  target="$(reg field "$name" tmux)"
  if window_alive "$target"; then
    tmux kill-window -t "$target"
  fi
  reg put "$name" '{"state": "stopped"}'
  printf 'stopped' > "$STATE_DIR/$name.status"
  echo "$name stopped"
}

[ $# -ge 1 ] || usage
sub="$1"; shift
case "$sub" in
  start) cmd_start "$@" ;;
  list) [ $# -eq 0 ] || usage; cmd_list ;;
  stop) cmd_stop "$@" ;;
  *) usage ;;
esac
