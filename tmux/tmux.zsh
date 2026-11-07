# tmux helpers, sourced from ~/.zshrc

# tmx: sessions for this folder (<folder>, <folder>-2, ...).
# none: create <folder>. one: join it. several: join and show the list to pick from.
unalias tmx 2>/dev/null
tmx() {
  local base="$(basename "$PWD")"
  local -a mine
  mine=(${(f)"$(tmux ls -F '#S' 2>/dev/null | awk -v b="$base" '$0==b || index($0, b"-")==1 && substr($0, length(b)+2) ~ /^[0-9]+$/')"})
  local filter="#{||:#{==:#{session_name},$base},#{m:$base-*,#{session_name}}}"
  if (( ${#mine} == 0 )); then
    tmux new-session -s "$base" -c "$PWD"
  elif [[ -n $TMUX ]]; then
    if (( ${#mine} == 1 )); then tmux switch-client -t "=${mine[1]}"; else tmux choose-tree -s -f "$filter"; fi
  elif (( ${#mine} == 1 )); then
    tmux attach -t "=${mine[1]}"
  else
    tmux attach -t "=${mine[1]}" \; choose-tree -s -f "$filter"
  fi
}

# tmxn: always start a fresh session in this folder: <folder>-2, <folder>-3, ...
# Jump between all sessions from inside tmux with prefix s.
tmxn() {
  local base="$(basename "$PWD")" n=2
  while tmux has-session -t "=$base-$n" 2>/dev/null; do ((n++)); done
  tmux new-session -s "$base-$n" -c "$PWD"
}

# tmxa <name>: attach to a session (prefix of the name is enough if unique).
# Inside tmux it switches instead. No name: list sessions to pick from.
tmxa() {
  if [[ -z $1 ]]; then
    if [[ -n $TMUX ]]; then tmux choose-tree -s; else tmux a \; choose-tree -s; fi
  elif [[ -n $TMUX ]]; then
    tmux switch-client -t "$1"
  else
    tmux a -t "$1"
  fi
}
