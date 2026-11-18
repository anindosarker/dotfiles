#!/usr/bin/env python3
"""The Workflow run id of each milestone, recorded at launch so a later session finds it.

Usage: python3 -I run/runs.py <release> set <milestone> <run id> [--owner X] [--root PATH]
       python3 -I run/runs.py <release> get <milestone> [--owner X] [--root PATH]
       python3 -I run/runs.py <release> list [--owner X] [--root PATH]

<milestone> is the tracker file name without "-tracker.md", as for sprints/mark.py. The record
is status/data/runs.json in the main checkout's release folder (the first entry of git worktree
list, also when called from a worktree): git-ignored with the rest of status/data, so it is
never committed, never conflicts with the builder's tracker writes in the milestone worktree,
and stays on disk across sessions. One entry per milestone, {"run": <id>, "session": <the
calling session's $CLAUDE_CODE_SESSION_ID or "">, "at": <time>}; set replaces the entry, so
the newest id wins (a relaunch, or a fresh run after a dead session). A run that covers several
milestones is set once per milestone. Writes take the release's .ids.lock lock and replace the
file by rename.

set prints one line. get prints the run id, or "none". list prints one line per milestone:
milestone, run id, session, time. A milestone with no tracker of that name is refused with one
line, exit 1. Reads fail soft: a missing or unreadable runs.json reads as empty.
"""
import argparse
import datetime
import fcntl
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
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
RUNS_JSON = "status/data/runs.json"
RUN_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def main_checkout(root):
    """The main checkout of the repository at root (the first entry of git worktree list), else root."""
    try:
        out = subprocess.run(["git", "-C", str(root), "worktree", "list", "--porcelain"],
                             capture_output=True, text=True)
    except FileNotFoundError:
        return root
    for line in out.stdout.splitlines():
        if line.startswith("worktree "):
            p = Path(line[len("worktree "):])
            return p if p.is_dir() else root
    return root


def folder_of(release, owner=None, root=None):
    """(root, release folder) in the main checkout."""
    r, folder = C.find_folder(release, owner, root)
    main = main_checkout(r)
    other = main / folder.relative_to(r)
    if main != r and other.is_dir():
        return main, other
    return r, folder


def read(folder):
    """The record as a dict, {} when missing or unreadable."""
    try:
        d = json.loads((folder / RUNS_JSON).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def run_of(folder, key):
    """The recorded run id of a milestone, or None."""
    e = read(folder).get(key)
    return e.get("run") if isinstance(e, dict) and e.get("run") else None


def write(folder, key, run_id):
    path = folder / RUNS_JSON
    with open(C.lock_file(folder), "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        d = read(folder)
        d[key] = {"run": run_id, "session": os.environ.get("CLAUDE_CODE_SESSION_ID", ""),
                  "at": datetime.datetime.now().isoformat(timespec="seconds")}
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix="runs.", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(d, indent=2, sort_keys=True) + "\n")
        os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser(
        usage="run/runs.py <release> set <milestone> <run id> | get <milestone> | list [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("action", choices=["set", "get", "list"])
    ap.add_argument("args", nargs="*")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        C.die(f"bad release '{a.release}', expected like v0.9.x")
    want = {"set": 2, "get": 1, "list": 0}[a.action]
    if len(a.args) != want:
        ap.error(f"{a.action} takes {want} argument(s)")
    _, folder = folder_of(a.release, a.owner, a.root)
    if a.action == "list":
        for key, e in sorted(read(folder).items()):
            if isinstance(e, dict):
                print(f"{key}\t{e.get('run', '')}\t{e.get('session', '') or '-'}\t{e.get('at', '')}")
        return
    key = Path(a.args[0]).name.removesuffix(".md").removesuffix("-tracker")
    if not (folder / C.TRACKERS_DIR / f"{key}-tracker.md").is_file():
        C.die(f"no milestone has the tracker {C.TRACKERS_DIR}/{key}-tracker.md")
    if a.action == "get":
        print(run_of(folder, key) or "none")
        return
    run_id = a.args[1]
    if not RUN_ID_RE.match(run_id):
        C.die(f"bad run id '{run_id}', expected like wf_00f59832-63b")
    old = run_of(folder, key)
    write(folder, key, run_id)
    print(f"{key}: run {run_id}" + (f" (was {old})" if old and old != run_id else ""))


if __name__ == "__main__":
    main()
