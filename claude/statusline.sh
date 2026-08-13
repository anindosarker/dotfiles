#!/bin/bash

# Status line - model [effort], git branch, cwd, context bar, 5h/7d limits + reset
# Catppuccin Frappe theme

data=$(cat)

# Single jq call - extract all values at once (tab-separated, "-" = missing)
IFS=$'\t' read -r model effort cwd max_ctx used_pct fh_used fh_reset sd_used sd_reset <<< "$(echo "$data" | jq -r '[
    (.model.display_name // .model.id // "unknown"),
    (.effort.level // .effort // "-"),
    (.workspace.current_dir // "-"),
    (.context_window.context_window_size // 200000),
    (.context_window.used_percentage // "-"),
    (.rate_limits.five_hour.used_percentage // "-"),
    (.rate_limits.five_hour.resets_at // "-"),
    (.rate_limits.seven_day.used_percentage // "-"),
    (.rate_limits.seven_day.resets_at // "-")
] | @tsv')"

now=$(date +%s)

is_set() { [ -n "$1" ] && [ "$1" != "-" ] && [ "$1" != "null" ]; }

# Folder name from path
folder="${cwd##*/}"
{ [ -z "$folder" ] || [ "$folder" = "-" ]; } && folder="?"

# Git: branch + dirty status (fast combined check)
branch=""
dirty=""
if git rev-parse --git-dir > /dev/null 2>&1; then
    branch=$(git branch --show-current 2>/dev/null)
    [ -z "$branch" ] && branch=$(git rev-parse --short HEAD 2>/dev/null)

    # Truncate long branches (max 20 chars)
    if [ "${#branch}" -gt 20 ]; then
        branch="${branch:0:19}…"
    fi

    # Check for uncommitted changes (fast: just check if output exists)
    if [ -n "$(git status --porcelain 2>/dev/null | head -1)" ]; then
        dirty="●"
    fi
fi

# Catppuccin Frappe colors (24-bit true color)
BLUE='\033[38;2;140;170;238m'      # Blue - context bar (low)
RED='\033[38;2;231;130;132m'       # Red - context bar (high) / limit high
YELLOW='\033[38;2;229;200;144m'    # Yellow - limit mid
GREEN='\033[38;2;166;209;137m'     # Green - limit low
TEAL='\033[38;2;129;200;190m'      # Teal - folder
MAUVE='\033[38;2;202;158;230m'     # Mauve - git branch
LAVENDER='\033[38;2;186;187;241m'  # Lavender - model
PEACH='\033[38;2;239;159;118m'     # Peach - dirty indicator
OVERLAY='\033[38;2;115;121;148m'   # Overlay 0 - separators
SUBTEXT='\033[38;2;165;173;206m'   # Subtext 0 - secondary text
RESET='\033[0m'

# Format context bar: █████▄░░░░ 57% (96K/167K)
# Dynamic color, autocompact-aware: percentages measured against the effective
# window (total minus the 33K autocompact buffer). Warn/danger thresholds are
# proportional to the effective window (36% / 48% — equals the 60K/80K marks
# of a standard 200K window), so they stay sane on 1M-context models too.
AUTOCOMPACT_BUFFER=33000
if ! is_set "$used_pct"; then
    context_info="${OVERLAY}░░░░░░░░░░${RESET}"
else
    eff_window=$(( max_ctx - AUTOCOMPACT_BUFFER ))
    [ "$eff_window" -le 0 ] && eff_window=$max_ctx
    tokens_used=$(awk "BEGIN{printf \"%d\", ${used_pct} * ${max_ctx} / 100}")
    pct=$(( tokens_used * 100 / eff_window ))
    [ "$pct" -gt 100 ] && pct=100
    [ "$pct" -lt 0 ] && pct=0

    if [ "$pct" -ge 48 ]; then COLOR="$PEACH"
    elif [ "$pct" -ge 36 ]; then COLOR="$YELLOW"
    else COLOR="$GREEN"; fi

    used_k=$(( tokens_used / 1000 ))
    max_k=$(( eff_window / 1000 ))

    # 10-cell bar; each cell: █ full, ▄ partial, ░ empty
    bar=""
    i=0
    while [ "$i" -lt 10 ]; do
        filled=$(( pct - i * 10 ))
        if [ "$filled" -ge 8 ]; then bar="${bar}${COLOR}█${RESET}"
        elif [ "$filled" -ge 3 ]; then bar="${bar}${COLOR}▄${RESET}"
        else bar="${bar}${OVERLAY}░${RESET}"; fi
        i=$((i+1))
    done

    context_info="${bar} ${SUBTEXT}${pct}% (${used_k}K/${max_k}K)${RESET}"
fi

# Time until a reset epoch: 2d21h / 1h11m / 42m
fmt_remaining() {
    local sec=$1 d h m
    [ "$sec" -lt 0 ] && sec=0
    if [ "$sec" -ge 86400 ]; then
        d=$(( sec / 86400 )); h=$(( (sec % 86400 + 1800) / 3600 ))
        [ "$h" -ge 24 ] && { d=$((d+1)); h=0; }
        if [ "$h" -gt 0 ]; then printf '%dd%dh' "$d" "$h"; else printf '%dd' "$d"; fi
    elif [ "$sec" -ge 3600 ]; then
        h=$(( sec / 3600 )); m=$(( (sec % 3600 + 30) / 60 ))
        [ "$m" -ge 60 ] && { h=$((h+1)); m=0; }
        printf '%dh%dm' "$h" "$m"
    else
        printf '%dm' "$(( (sec + 30) / 60 ))"
    fi
}

# Rate-limit segment: <label+icon> <used%> ↻<remaining>
render_limit() { # $1=label (e.g. "session: 󱎫") $2=used_pct $3=resets_at_epoch
    local label=$1 used=$2 reset=$3 u col seg=""
    is_set "$used" || return 0
    u=$(printf "%.0f" "$used" 2>/dev/null) || return 0
    [ "$u" -gt 100 ] 2>/dev/null && u=100
    if [ "$u" -gt 80 ]; then col=$RED
    elif [ "$u" -ge 50 ]; then col=$YELLOW
    else col=$GREEN; fi
    seg="${SUBTEXT}${label}${RESET} ${col}${u}%${RESET}"
    reset=${reset%%.*}
    case "$reset" in
        ''|-|*[!0-9]*) : ;;
        *) seg="${seg} ${OVERLAY}↻$(fmt_remaining $(( reset - now )))${RESET}" ;;
    esac
    printf '%b' "$seg"
}

seg5=$(render_limit "session: 󱎫" "$fh_used" "$fh_reset")
seg7=$(render_limit "week: 󰃭" "$sd_used" "$sd_reset")

# Effort: capitalize first letter -> [High]
effort_seg=""
if is_set "$effort"; then
    effort_cap=$(printf '%s' "$effort" | awk '{print toupper(substr($0,1,1)) substr($0,2)}')
    effort_seg=" ${SUBTEXT}[${effort_cap}]${RESET}"
fi

# Caveman badge (plugin integration) — renders [CAVEMAN] / [CAVEMAN:MODE] when active
CAVEMAN_SL="$HOME/.claude/plugins/marketplaces/caveman/hooks/caveman-statusline.sh"
caveman_badge=""
[ -f "$CAVEMAN_SL" ] && caveman_badge=$(bash "$CAVEMAN_SL" 2>/dev/null)

# Build output
output="${LAVENDER}${model}${RESET}${effort_seg}"
output="${output} ${OVERLAY}│${RESET} ${TEAL}󰝰 ${folder}${RESET}"

if [ -n "$branch" ]; then
    output="${output} ${OVERLAY}│${RESET} ${MAUVE} ${branch}${RESET}"
    [ -n "$dirty" ] && output="${output}${PEACH}${dirty}${RESET}"
fi

output="${output} ${OVERLAY}│${RESET} ${context_info}"
[ -n "$seg5" ] && output="${output} ${OVERLAY}│${RESET} ${seg5}"
[ -n "$seg7" ] && output="${output} ${OVERLAY}│${RESET} ${seg7}"

# Theme line = row 1; caveman badge on its own row below
if [ -n "$caveman_badge" ]; then
    printf '%b\n%b\n' "$output" "$caveman_badge"
else
    printf '%b\n' "$output"
fi
