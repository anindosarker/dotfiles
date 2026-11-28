#!/usr/bin/env python3
"""Read-only wake check of a release's running milestones: is each one's Workflow run still alive?

Usage: python3 -I run/check.py <release> [--stale MINUTES] [--tsv] [--owner X] [--root PATH]

For every "[ ]" row of status/sprints.md: the milestone (its tracker file name without
"-tracker.md"), the run id recorded by run/runs.py, the session that owns the run, the time of
the run's last activity and one state word:
- alive: activity within the threshold (--stale, default 20 minutes);
- paused: the last limit event the run wrote is "Usage limit reached ... Workflow paused", with
  no "Usage limit reset" after it;
- silent: no activity past the threshold, or the run ended without finishing (its final state
  file says killed or failed and nothing ran after it);
- finished: the run's final state file says completed, but the row is still "[ ]";
- no run: no id recorded, or the id is in no session folder.
Every "[~]" row is listed as "waiting" and never counted as silent. A last line gives the counts.
In a release of format 2.2 there is no status/sprints.md: the rows are read from
status/data/status.json, a milestone in progress for a "[ ]" row and a blocked one for a "[~]"
row; the output lines are the same.

Where a run lives (Claude Code internals, read defensively; anything unreadable is skipped):
<projects>/<project folder>/<session uuid>/subagents/workflows/<run id>/ holds journal.jsonl and
one transcript per agent while the run goes on (activity is the newest mtime in that folder; the
journal lines carry no time), and <session uuid>/workflows/<run id>.json is the final state,
written when the run ends ("status": completed, killed or failed; "logs": the run's log lines).
<projects> is $EXPEDITION_PROJECTS, else ~/.claude/projects; every project folder is searched.
The owner is the registry entry ($EXPEDITION_REGISTRY, else ~/.claude/expedition-runners.json)
whose uuid is that session: "<name>", "<name> (stopped)", or "session <uuid8> (not in registry)".
A "no run" row with an id shows the session that recorded it, when run/runs.py had one.

--tsv prints one tab-separated line per row instead (milestone, state, run id, owner name,
session uuid, last activity as epoch seconds; "-" for none) and no count line, for
run/nudge-watch.sh. Writes nothing, exit 0 for any read; a usage error or a missing release
exits non-zero.
"""
import argparse
import datetime
import glob
import importlib.util
import json
import os
import re
import sys
import time
from pathlib import Path


def _common():
    name = "expedition_lib_common"
    if name not in sys.modules:
        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent.parent / "lib" / "common.py")
        sys.modules[name] = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sys.modules[name])
    return sys.modules[name]


C = _common()
GRID_ROW_RE = re.compile(r"^E(\d+)\s+(\d{2}(?:\.\d+)?)\s+(.*)$")
PAUSE, RESET = "Workflow paused", "Usage limit reset"
STATES = ("alive", "paused", "silent", "finished", "no run", "waiting")


def projects_root():
    return Path(os.environ.get("EXPEDITION_PROJECTS") or Path.home() / ".claude" / "projects")


def registry():
    """{session uuid: (name, state)} of the runner and fork entries; {} when unreadable."""
    p = Path(os.environ.get("EXPEDITION_REGISTRY") or Path.home() / ".claude" / "expedition-runners.json")
    try:
        d = json.loads(p.read_text())
    except (OSError, ValueError):
        return {}
    out = {}
    if isinstance(d, dict):
        for name, e in d.items():
            if name != "lead" and isinstance(e, dict) and e.get("uuid"):
                # A uuid on several entries (a hand-copied entry): the live one, else the newest name.
                if e["uuid"] not in out or e.get("state") != "stopped":
                    out[e["uuid"]] = (name, e.get("state", ""))
    return out


def rows(folder):
    """[(milestone key, cell)] of the "[ ]" and "[~]" rows of status/sprints.md. In a release of
    format 2.2, which has no grid file, from status/data/status.json: "[ ]" for each milestone
    that is in progress, "[~]" for each that is blocked, in the order of the file."""
    st = C.load("lib/status")
    if st.new_form(folder):
        cell = {"in progress": "[ ]", "blocked": "[~]"}
        return [(m["id"], cell[m["status"]]) for m in st.load(folder)["milestones"] if m.get("status") in cell]
    grid = folder / C.SPRINTS_MD
    head, data = C.table_rows(C.read(grid), "Milestone") if grid.is_file() else (None, [])
    keys = {}
    try:
        own = C.load("lib/ownership")
        for num, bl in own.new_collect(folder, folder / f"{folder.parent.name}-plan.md")["blocks"].items():
            for b in bl:
                keys[(num, b["name"])] = b["tracker"].name.removesuffix("-tracker.md")
    except Exception:  # the plan does not parse: fall back to the row text
        pass
    out = []
    for r in data if head else []:
        m = GRID_ROW_RE.match(r[0]) if r else None
        cell = next((c for c in r[1:] if c in ("[ ]", "[~]", "[x]", "[!]")), "") if r else ""
        if m and cell in ("[ ]", "[~]"):
            out.append((keys.get((m.group(2), m.group(3)), f"{m.group(2)} {m.group(3)}"), cell))
    return out


def newest_mtime(d):
    best = 0.0
    try:
        for e in os.scandir(d):
            try:
                best = max(best, e.stat().st_mtime)
            except OSError:
                pass
    except OSError:
        pass
    return best


def limit_event(texts):
    """"paused" when the last limit event in the texts is a pause, else None."""
    last = None
    for t in texts:
        if PAUSE in t:
            last = "paused"
        elif RESET in t:
            last = None
    return last


def journal_texts(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read().splitlines()
    except OSError:
        return []


def find_run(projects, run_id):
    """(session uuid, last activity, final dict or None, final mtime) of a run, or None."""
    live = [Path(p) for p in glob.glob(str(projects / "*" / "*" / "subagents" / "workflows" / glob.escape(run_id)))]
    finals = [Path(p) for p in glob.glob(str(projects / "*" / "*" / "workflows" / f"{glob.escape(run_id)}.json"))]
    if not live and not finals:
        return None
    session = (live[0].parent.parent.parent.name if live else finals[0].parent.parent.name)
    last = max([newest_mtime(d) for d in live] + [0.0])
    final, fmt = None, 0.0
    if finals:
        try:
            fmt = finals[0].stat().st_mtime
            final = json.loads(finals[0].read_text(encoding="utf-8", errors="replace"))
            final = final if isinstance(final, dict) else {}
        except (OSError, ValueError):
            final = {}
    texts = []
    for d in live:
        texts += journal_texts(d / "journal.jsonl")
    return session, max(last, fmt), final, fmt, texts


def state_of(found, stale_s, now):
    """(state word, detail) of a found run."""
    session, last, final, fmt, texts = found
    if final is not None and fmt >= last - 1:
        status = str(final.get("status", ""))
        if status == "completed":
            return "finished", ""
        logs = final.get("logs") if isinstance(final.get("logs"), list) else []
        if status in ("", "running") and limit_event(texts + [str(x) for x in logs]) == "paused":
            return "paused", ""
        return "silent", f"ended {status or 'unknown'}"
    if limit_event(texts) == "paused":
        return "paused", ""
    return ("alive", "") if now - last <= stale_s else ("silent", "")


def owner_of(reg, session):
    if not session:
        return "-"
    name, state = reg.get(session, (None, None))
    if name is None:
        return f"session {session[:8]} (not in registry)"
    return f"{name} (stopped)" if state == "stopped" else name


def main():
    ap = argparse.ArgumentParser(usage="run/check.py <release> [--stale MINUTES] [--tsv] [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("--stale", type=float, default=20.0, help="minutes without activity before silent (default 20)")
    ap.add_argument("--tsv", action="store_true", help="machine lines for run/nudge-watch.sh")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        C.die(f"bad release '{a.release}', expected like v0.9.x")
    runs = C.load("run/runs")
    _, folder = runs.folder_of(a.release, a.owner, a.root)
    record = runs.read(folder)
    projects, reg, now = projects_root(), registry(), time.time()
    counts = dict.fromkeys(STATES, 0)
    for key, cell in rows(folder):
        e = record.get(key) if isinstance(record.get(key), dict) else {}
        run_id, session, last, detail = e.get("run") or "", "", 0.0, ""
        if cell == "[~]":
            state = "waiting"
        elif not run_id:
            state = "no run"
        else:
            try:
                found = find_run(projects, run_id) if re.fullmatch(r"[A-Za-z0-9_-]+", run_id) else None
            except Exception:
                found = None
            if found is None:
                state, session, detail = "no run", e.get("session") or "", "not in any session"
            else:
                session, last = found[0], found[1]
                state, detail = state_of(found, a.stale * 60, now)
        counts[state] += 1
        owner = owner_of(reg, session)
        if a.tsv:
            print("\t".join([key, state, run_id or "-", owner, session or "-", str(int(last)) if last else "-"]))
            continue
        when = "-"
        if last:
            when = f"{datetime.datetime.fromtimestamp(last):%m-%d %H:%M} ({int((now - last) // 60)} min ago)"
        line = f"{key}  {state}  run {run_id or '-'}  owner {owner}  last {when}"
        print(line + (f"  {detail}" if detail else ""))
    if not a.tsv:
        print(", ".join(f"{s} {n}" for s, n in counts.items()))


if __name__ == "__main__":
    main()
