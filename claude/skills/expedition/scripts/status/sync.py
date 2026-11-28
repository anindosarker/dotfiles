#!/usr/bin/env python3
"""The sync (D22): commit every change under the release folder in one commit.

Usage: python3 -I status/sync.py <release> [-m "<message>"] [--owner X] [--root PATH]

In a release of format 2.2 a status change (status/status.py set, sprints/mark.py launch,
wait, resume, stop) writes its files and makes no commit; this command commits them, with the
boxes a builder ticked and the trackers. sprints/mark.py merge and a status change that makes
an epic done end with the same sync. A session runs it before a handoff and a roll over.

It stages the changed, new and removed files under the release folder (git-ignored renders
stay out) and commits them by that path only, under the scripts' lock (lib/common.py
lock_file): a change outside the folder stays uncommitted. Default message:
"docs(plan): <release> sync". Prints "synced: <n> file(s), <short sha>", or "nothing to sync"
and exit 0 when the folder has no change. It works in a release of every format; below
format 2.2 the status commands commit on their own, so it commits only what is left.
"""
import argparse
import fcntl
import importlib.util
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


def main():
    ap = argparse.ArgumentParser(usage='status/sync.py <release> [-m "<message>"] [--owner X] [--root PATH]')
    ap.add_argument("release")
    ap.add_argument("-m", "--message", default="", help='the commit subject (default: "docs(plan): <release> sync")')
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        C.die(f"bad release '{a.release}', expected like v0.9.x")
    root, folder = C.find_folder(a.release, a.owner, a.root)
    st = C.load("lib/status")
    with open(C.lock_file(folder), "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        made = st.sync_commit(root, folder, a.message.strip() or f"docs(plan): {a.release} sync")
        fcntl.flock(lock, fcntl.LOCK_UN)
    if not made:
        print("nothing to sync")
        return
    repo, _ = C.plan_repo(root, [folder])
    show = subprocess.run(["git", "-C", str(repo), "show", "--name-only", "--format=%h", "HEAD"],
                          capture_output=True, text=True).stdout.split("\n")
    show = [l for l in show if l.strip()]
    print(f"synced: {len(show) - 1} file(s), {show[0] if show else 'HEAD'}")


if __name__ == "__main__":
    main()
