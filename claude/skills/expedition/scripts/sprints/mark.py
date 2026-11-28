#!/usr/bin/env python3
"""The only writer of the run marks: set one milestone's run status (in status/data/status.json,
or the cell in status/sprints.md of a release without that file), then run the refresh chain
and commit, as one command per event. In a release of format 2.2 no grid file is written or
committed (lib/grid.py).

Usage: python3 -I sprints/mark.py <release> <milestone> launch|wait|resume|merge|stop [--reason "<text>"] [--commit <sha>] [--owner X] [--root PATH]

<milestone> is the milestone's tracker file name without "-tracker.md", for example
47-comparison-page for run/trackers/47-comparison-page-tracker.md (a path or the full file name
is accepted too). The runner and the workflow know it: the tracker path is in the MILESTONES
entry and in every prompt.

In a release with status/data/status.json the verb sets the milestone's status in that file
(mark_status below): wait and stop need --reason "<text>", merge needs --commit <sha>. In an
earlier release, which this paragraph describes, the two flags are accepted and not used:
launch sets the milestone's cell to "[ ]", wait to "[~]", merge to "[x]", stop to "[!]", in the
column its row has now (reference/formats.md, Milestone status). launch on a "[~]" cell resumes
the milestone. wait takes no reason: the reason stays in the tracker's Status line. wait is
refused unless the cell is "·", "[ ]" or "[~]": a held planned milestone waits too. resume is
refused unless the cell is "[~]"; it sets "[ ]" when the milestone was launched before and "·"
when it never was. Launched before means a commit "docs(plan): <release> <milestone> launch" of
this script is in the history of status/sprints.md (lib/ownership.py launched_keys); when git
cannot tell, "[ ]". Then,
under the .ids.lock lock: the grid is regenerated with a new "Updated:" line, the Sprint column
of every unfinished epic's table, the lanes of decisions.md and the Decided cards of queue.md
follow it (lib/grid.py refresh), the swimlane data is written (sprints/swimlanes.py), and the
grid, the epic files, decisions.md and queue.md the chain changed are committed with --only,
never pushed. Prints one line.

A milestone with no tracker of that name, or with no row in the grid, is refused with one line,
exit 1. A repeat call (the cell already holds the mark) changes nothing, prints one line and
exits 0.
"""
import argparse
import contextlib
import fcntl
import importlib.util
import io
import re
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


def milestone_of(own, folder, release, key):
    """(spec number, milestone name, tracker path) of the milestone whose tracker file is
    <key>-tracker.md, or None."""
    blocks = own.new_collect(folder, folder / f"{release}-plan.md")["blocks"]
    for num, bl in blocks.items():
        for b in bl:
            if b["tracker"].name == f"{key}-tracker.md":
                return num, b["name"], b["tracker"]
    return None


def mark_status(a, st, root, folder, key, num, name):
    """A release with status/data/status.json: the verb is a status of that file (lib/status.py).
    launch: in progress; in a release of format 2.2 also "launched": true in the milestone's
    entry, which no later verb changes. resume, on a blocked milestone only: in progress when it
    was launched before (format 2.2: its "launched" value; below: a launch commit of this script
    is in the history of status/sprints.md, lib/ownership.py launched_keys), not started
    (to-do in a release of format 2.2) when it never was. merge: done, with --commit (a commit hash), refused while a
    task of the milestone is not done, skipped or waiting for the owner's look. wait and stop:
    blocked, with --reason; a stop whose reason starts with a decision id ("D15 ...") is
    skipped (archived in a release of format 2.2: lib/status.py stores and prints the word of the
    release's format). It writes the one release folder the scripts keep their lock in, also when run from
    a milestone worktree that holds a copy of the plan folder. In a release of format 2.2 launch,
    wait, resume and stop write and make no commit (D22): status/sync.py commits them; merge,
    and a verb that makes an epic done, end with the sync (lib/status.py finish): one commit of
    every change under the release folder, with the message of the verb."""
    word = {"launch": "in progress", "merge": "done"}.get(a.action, "blocked")
    if a.action == "resume":
        now = st.entries(folder)[0].get(key, {}).get("status", "not started")
        if now != "blocked":
            C.die(f"{key}: {st.say(folder, now)}, not blocked: nothing to resume")
        word = "in progress" if C.load("lib/grid").resume_mark(folder, key) == "[ ]" else "not started"
    if a.action == "stop" and re.match(r"^D\d+\b", a.reason.strip()):
        word = "skipped"
    with open(C.lock_file(folder), "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        done_before = st.done_epics(folder)
        with contextlib.redirect_stdout(io.StringIO()):
            _, e, stored = st.set_status(folder, a.release, key, word, a.reason, a.commit, locked=True,
                                         launched=a.action == "launch")
        if stored is None:
            late = st.pending(folder) and st.record(root, folder, [], f"docs(plan): {a.release} {key} {a.action}")
            print(f"{key}: already {st.say(folder, e['status'])}, nothing changed" + ("; an earlier failed commit is made now" if late else ""))
            return
        paths = [*C.load("lib/grid").grid_files(folder), *C.load("lib/decisions").commit_paths(folder),
                 *C.load("lib/queue").commit_paths(folder)]
        paths += sorted((folder / C.EPICS_DIR).glob("E*.md"))
        made = st.finish(root, folder, paths, f"docs(plan): {a.release} {key} {a.action}",
                         sync=a.action == "merge", done_before=done_before)
        fcntl.flock(lock, fcntl.LOCK_UN)
    # The line says committed only when a commit was made: in format 2.2 launch, wait, resume and
    # stop make none, and their line is the same line without "; committed".
    print(f"{key}: {stored} ({num} {name})" + ("; committed" if made or not st.deferred(folder) else ""))


def main():
    ap = argparse.ArgumentParser(
        usage="sprints/mark.py <release> <milestone> launch|wait|resume|merge|stop [--reason \"<text>\"] "
              "[--commit <sha>] [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("milestone")
    ap.add_argument("action", choices=C.load("lib/grid").ACTIONS)
    ap.add_argument("--reason", default="", help="wait, stop: a few words (status.json releases)")
    ap.add_argument("--commit", default="", help="merge: the merge commit (status.json releases)")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        C.die(f"bad release '{a.release}', expected like v0.9.x")
    key = Path(a.milestone).name.removesuffix(".md").removesuffix("-tracker")
    root, folder = C.find_folder(a.release, a.owner, a.root)
    own, g = C.load("lib/ownership"), C.load("lib/grid")
    hit = milestone_of(own, folder, a.release, key)
    if hit is None:
        C.die(f"no milestone has the tracker {C.TRACKERS_DIR}/{key}-tracker.md")
    num, name, _ = hit
    st = C.load("lib/status")
    if st.active(folder):
        return mark_status(a, st, root, folder, key, num, name)
    mark = g.resume_mark(folder, key) if a.action == "resume" else g.MARKS[a.action]
    grid = folder / C.SPRINTS_MD
    with open(C.lock_file(folder), "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        old, text = g.set_mark(grid, name, mark) if grid.is_file() else (None, None)
        if old is None:
            C.die(f"{key}: milestone '{name}' of spec {num} has no row in {C.SPRINTS_MD}")
        if old == mark:
            print(f"{key}: already {mark}, nothing changed")
            return
        if a.action == "wait" and old not in g.WAITABLE:
            C.die(f"{key}: cell is {old}, finished: nothing to wait")
        if a.action == "resume" and old != "[~]":
            C.die(f"{key}: cell is {old}, not waiting: nothing to resume")
        grid.write_text(text, encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            g.refresh(folder, a.release, quiet=True, locked=True)
            C.load("sprints/swimlanes").write(folder, a.release, quiet=True)
        paths = [grid, *C.load("lib/decisions").commit_paths(folder), *C.load("lib/queue").commit_paths(folder)] + sorted((folder / C.EPICS_DIR).glob("E*.md"))
        C.commit(root, paths, f"docs(plan): {a.release} {key} {a.action}")
        fcntl.flock(lock, fcntl.LOCK_UN)
    print(f"{key}: {old} to {mark} ({num} {name}); committed")


if __name__ == "__main__":
    main()
