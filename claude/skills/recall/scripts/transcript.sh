#!/usr/bin/env bash
# Print the user and assistant text of a Claude Code session transcript around a pattern.
# Tool calls, tool results, thinking and attachments are never printed.
#
# Usage: transcript.sh <uuid | registry name | path.jsonl> "<regex>" [--context N] [--all]
#   uuid            session id; the file is found under ~/.claude/projects/*/<uuid>.jsonl
#   registry name   an expedition runner or fork name from ~/.claude/expedition-runners.json
#   --context N     turns of text printed before and after each match (default 1)
#   --all           no pattern: print every user and assistant text turn (long; pipe to a reader)
# Output: one block per turn, "HH:MM role: text", matches marked with ">".
set -euo pipefail
[ $# -ge 1 ] || { echo "usage: transcript.sh <uuid|name|path> \"<regex>\" [--context N] [--all]" >&2; exit 2; }
python3 -I - "$@" <<'PY'
import json, re, sys, glob, os
from pathlib import Path
args = sys.argv[1:]
target = args.pop(0)
pattern = None; ctx = 1; all_ = False
while args:
    a = args.pop(0)
    if a == "--context": ctx = int(args.pop(0))
    elif a == "--all": all_ = True
    else: pattern = a
home = Path.home()
path = None
if target.endswith(".jsonl") and Path(target).is_file():
    path = Path(target)
else:
    uuid = target
    reg = home / ".claude/expedition-runners.json"
    if reg.is_file():
        e = json.loads(reg.read_text()).get(target)
        if e and e.get("uuid"): uuid = e["uuid"]
    hits = glob.glob(str(home / f".claude/projects/*/{uuid}.jsonl"))
    if not hits: sys.exit(f"no transcript for {target}")
    path = Path(hits[0])
turns = []
for line in path.open():
    try: j = json.loads(line)
    except json.JSONDecodeError: continue
    t = j.get("type")
    if t not in ("user", "assistant") or j.get("isMeta"): continue
    m = j.get("message") or {}
    c = m.get("content")
    texts = []
    if isinstance(c, str): texts.append(c)
    elif isinstance(c, list):
        for b in c:
            if isinstance(b, dict) and b.get("type") == "text": texts.append(b.get("text", ""))
    text = "\n".join(s for s in texts if s.strip())
    if not text.strip(): continue
    if text.startswith("<") and ("system-reminder" in text[:40] or "local-command" in text[:40]): continue
    ts = (j.get("timestamp") or "")[11:16]
    turns.append((ts, t, text.strip()))
if all_ or not pattern:
    sel = set(range(len(turns)))
else:
    rx = re.compile(pattern, re.I)
    hit = [i for i, (_, _, x) in enumerate(turns) if rx.search(x)]
    if not hit: sys.exit(f"no match for /{pattern}/ in {path.name} ({len(turns)} text turns)")
    sel = set()
    for i in hit:
        sel.update(range(max(0, i - ctx), min(len(turns), i + ctx + 1)))
    hit = set(hit)
last = None
for i in sorted(sel):
    if last is not None and i != last + 1: print("...")
    ts, role, text = turns[i]
    mark = ">" if (not all_ and pattern and i in hit) else " "
    print(f"{mark}{ts} {role}: {text}")
    last = i
PY
