#!/usr/bin/env python3
"""Read and write the status of a release: status/data/status.json, the only store of the
status of every epic, spec, milestone and task (lib/status.py).

Usage: python3 -I status/status.py <release> set <id> "<status>" [--reason "<text>"] [--commit <sha>]
       python3 -I status/status.py <release> get <id>
       python3 -I status/status.py <release> list [--status "<status>"] [--kind epic|spec|milestone|task]
       python3 -I status/status.py <release> drop <id>
       [--owner X] [--root PATH]

<id>: a task is "<spec>-<number>" (27-03), a milestone its tracker file name without
"-tracker.md" (27-collapse-shortcut), a spec its number (27), an epic E11.
<status>: not started, in progress, blocked, done or skipped. blocked and skipped need
--reason, a few words; the full text goes under "## Attention" of the milestone's tracker.

set works on a task or a milestone; the status of a spec and an epic is counted. It writes the
JSON file, rolls a task change up into its milestone, counts the spec, the epic and the sprint,
writes the same word into the "status:" front matter line of the task, spec and epic files,
draws status/sprints.md again, writes the page data and commits what changed. A task set to
done with an open "Owner:" box becomes blocked, "waits for the owner's look"; with another open
Verification box the change is refused. A milestone's done is its merge: it needs --commit, a
commit hash, and is refused while one of its tasks is not done, skipped or waiting for the
owner's look (sprints/mark.py <release> <milestone> merge --commit <sha> calls the same code).
A set that changes nothing writes nothing and makes no commit.

drop removes one stored milestone or task entry that no spec has any more (a renamed or removed
milestone or task). The other commands stop, naming such entries, until they are restored or
dropped: a stored status is never thrown away by itself.

It writes in the one release folder every script writes in (lib/common.py one_copy: the main
checkout's copy), also when it is run from a milestone worktree that holds its own copy of the
plan folder; the Verification boxes of a task are read from the caller's copy, where the
builder ticked them.

get prints "<id>: <status>", with the reason in brackets. list prints one line per item,
"<kind> <id>: <status> (<reason>) <name>", filtered by --status and --kind.

Refuses: a release with no status.json (made before this format: its statuses are the grid
marks and the tracker Status lines); an unknown id; a word that is not one of the five.
"""
import argparse
import contextlib
import fcntl
import importlib.util
import io
import subprocess
import sys
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
KINDS = ("epic", "spec", "milestone", "task")


def line(kind, e):
    why = f" ({e['reason']})" if e.get("reason") else ""
    return f"{kind} {e['id']}: {e['status']}{why} {e.get('name') or e.get('title') or ''}".rstrip()


def main():
    ap = argparse.ArgumentParser(
        usage='status/status.py <release> set <id> "<status>" [--reason "<text>"] [--commit <sha>]\n'
              "       status/status.py <release> get <id>\n"
              '       status/status.py <release> list [--status "<status>"] [--kind epic|spec|milestone|task]')
    ap.add_argument("release")
    ap.add_argument("action", choices=("set", "get", "list", "drop"))
    ap.add_argument("rest", nargs="*")
    ap.add_argument("--reason", default="")
    ap.add_argument("--commit", default="")
    ap.add_argument("--status")
    ap.add_argument("--kind", choices=KINDS)
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        C.die(f"bad release '{a.release}', expected like v0.9.x")
    st = C.load("lib/status")
    root, folder = C.find_folder(a.release, a.owner, a.root)
    # The caller's own copy of the release folder (a milestone worktree): the builder ticks the
    # Verification boxes there. Every write goes to the one folder find_folder gives.
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
    mine = Path(top) / folder.relative_to(root) if top and not a.root else None
    if not st.active(folder):
        C.die(f"{folder} has no {st.FILE}: a release made before this format keeps its statuses "
              "in the grid and the trackers (sprints/mark.py)")
    if a.action == "list":
        if a.rest or (a.status and a.status not in st.STATUSES):
            C.die(f"list takes --status (one of {', '.join(st.STATUSES)}) and --kind")
        data = st.load(folder)
        for kind in KINDS:
            for e in data[kind + "s"] if a.kind in (None, kind) else []:
                if a.status in (None, e["status"]):
                    print(line(kind, e))
        return
    if a.action == "get":
        if len(a.rest) != 1:
            C.die("get takes one id")
        kind, e = st.find(st.load(folder), a.rest[0])
        if kind is None:
            C.die(f"nothing has the id {a.rest[0]}")
        print(f"{e['id']}: {e['status']}" + (f" ({e['reason']})" if e.get("reason") else ""))
        return
    if a.action == "drop":
        if len(a.rest) != 1:
            C.die("drop takes one id")
        with open(C.lock_file(folder), "a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            kind = st.drop(folder, a.release, a.rest[0])
            if kind is None:
                C.die(f"status.json has no milestone or task entry {a.rest[0]}")
            st.commit(root, folder, [], f"docs(plan): {a.release} {kind} {a.rest[0]} dropped from status.json")
            fcntl.flock(lock, fcntl.LOCK_UN)
        print(f"{kind} {a.rest[0]}: dropped")
        return
    if len(a.rest) != 2:
        C.die('set takes <id> "<status>"')
    ident, word = a.rest[0], a.rest[1].strip().lower()
    with open(C.lock_file(folder), "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with contextlib.redirect_stdout(io.StringIO()):
            kind, e, stored = st.set_status(folder, a.release, ident, word, a.reason, a.commit, locked=True,
                                            boxes_in=mine if mine and mine.is_dir() else None)
        if stored is None:
            late = st.pending(folder) and st.commit(root, folder, [], f"docs(plan): {a.release} {kind} {ident} {e['status']}")
            print(f"{kind} {ident}: already {e['status']}, nothing changed" + ("; an earlier failed commit is made now" if late else ""))
            return
        paths = [folder / C.SPRINTS_MD, folder / "decisions.md", *C.load("lib/queue").commit_paths(folder)]
        paths += sorted((folder / C.EPICS_DIR).glob("E*.md"))
        st.commit(root, folder, paths, f"docs(plan): {a.release} {kind} {ident} {stored}")
        fcntl.flock(lock, fcntl.LOCK_UN)
    print(f"{kind} {ident}: {stored}" + (f" ({e['reason']})" if e["reason"] else ""))


if __name__ == "__main__":
    main()
