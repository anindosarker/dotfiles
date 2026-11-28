#!/usr/bin/env python3
"""Create or start the epic file plan/epics/E<n>.md of a release (reference/formats.md, Epic
file), or append a note to it, and commit that one file.

Usage: python3 -I epics/new.py <release> E<n> [--owner X] [--root PATH]
       python3 -I epics/new.py <release> E<n> <D ids> [--owner X] [--root PATH]
       python3 -I epics/new.py <release> E<n> --note "<text>" [--owner X] [--root PATH]

Stub (no D ids): writes "# E<n>", empty "Decisions:", "Specs:" and "Starts:" lines and the empty
"## Ownership" table, no "## Notes" heading. Refuses when the file exists. run/go.py runs it for the
next epic the moment the previous epic's RUN is sent.

Start the epic (D ids, on the owner's "compose"): creates the file when it does not exist, writes
the "Decisions:" line (the ids already there plus the new ones, in number order) and one table
row per decision, "| D<n> <title from decisions.md> |  |  |  |  |"; on a rerun only the missing
rows are added, every other row kept as it is. Refuses, writing nothing, a decision that is
missing from decisions.md, superseded, already tagged with another epic, or done with nothing to
run (in Done without an epic tag). In a release whose decisions are files (lib/decisions.py
file_form) the title of a row is the title line of the decision file, and the refusals are: an
id with no decision file, an archived decision, a backlog decision, a decision with the "epic"
line of another epic, and a decision that is done with nothing to run. A blocked decision is
accepted: the owner may put it in an epic.

A release of format 2.2 (lib/status.py new_form): the front matter holds "status" and "starts"
only, with no "decisions:" and no "specs:" line; the epic's decisions are the D ids of the
Decision column of its table (the one copy). After the write of a stub or a start the status
chain runs (lib/status.py sync), so status.json and the "status:" lines follow at once, and
they are committed with the epic file.

Note (--note): appends "- <text>" at the end of the "## Notes" section, creating the section at
the end of the file when it is missing. An urgent note starts with "Urgent:".
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
EPIC_RE = re.compile(r"^E\d+$")
D_RE = re.compile(r"^D(\d+)$")
die = C.die


def stub(own, epic, folder):
    """An empty epic file: front matter (status, starts) in a release of format 2.2, (status,
    decisions, specs, starts) in a release with status/data/status.json below 2.2, the
    "Decisions:", "Specs:", "Starts:" lines in an earlier one."""
    table = "\n".join([own.OWN_HEAD, ""] + own.render_table([])) + "\n"
    st = C.load("lib/status")
    if st.new_form(folder):
        return f"---\nstatus: {st.say(folder, st.STATUSES[0])}\nstarts:\n---\n# {epic}\n\n" + table
    if st.active(folder):
        return f"---\nstatus: not started\ndecisions:\nspecs:\nstarts:\n---\n# {epic}\n\n" + table
    return f"# {epic}\n\nDecisions:\nSpecs:\nStarts:\n\n" + table


def start(own, folder, path, epic, nums):
    """Write the Decisions line and the missing rows; return True when the file changed."""
    n = int(epic[1:])
    tags = own.read_tags(folder)
    heads, bullets = own.supersedes(folder)
    gone = {**bullets, **heads}
    bad = []
    files = C.load("lib/decisions").file_form(folder)
    for d in nums:
        t = tags.get(d)
        if t is None:
            bad.append(f"D{d} has no decision file" if files else f"D{d} is not in decisions.md")
        elif d in gone:
            bad.append(f"D{d} is superseded by D{gone[d]}")
        elif files and t["status"] == "backlog":
            bad.append(f"D{d} is backlog: it moved to another release")
        elif t["epic"] and t["epic"] != n:
            bad.append(f"D{d} is already in E{t['epic']}")
        elif t["done"] and not t["epic"]:
            bad.append(f"D{d} is done with nothing to run")
    if bad:
        die("; ".join(bad) + ": nothing written")
    text = own.read(path) if path.is_file() else stub(own, epic, folder)
    rows, err = own.read_table(text)
    if err:
        die(f"{path}: {err}")
    rows = rows or []
    have = {r["decision"] for r in rows}
    ids = sorted(set(own.epic_decision_ids(folder, text)) | set(nums))
    titles = own.decision_titles(folder)
    added = [d for d in ids if d not in have]
    rows += [{"decision": d, "title": titles.get(d, ""), "files": [], "spec": "",
              "milestone": "", "sprint": ""} for d in added]
    if not own.table_form(folder):
        text = own.set_field(text, "Decisions", ", ".join(f"D{d}" for d in ids))
    new = own.put_table(text, rows)
    print(f"{epic}: Decisions {', '.join(f'D{d}' for d in ids)}; rows added: "
          f"{', '.join(f'D{d}' for d in added) or 'none'}")
    if path.is_file() and new == own.read(path):
        return False
    path.write_text(new, encoding="utf-8")
    return True


def note(own, path, text_line):
    """Append "- <text>" to the Notes section, creating it at the end of the file."""
    lines = own.read(path).rstrip("\n").split("\n")
    span = own.section(lines, own.NOTES_HEAD)
    bullet = f"- {text_line.strip()}"
    if span is None:
        lines += ["", own.NOTES_HEAD, "", bullet]
    else:
        end = span[1]
        while end > span[0] + 1 and not lines[end - 1].strip():
            end -= 1
        lines.insert(end, bullet)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(
        usage="epics/new.py <release> E<n> [<D ids> | --note \"<text>\"] [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("epic")
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--note")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    if not EPIC_RE.match(a.epic):
        die(f"bad epic '{a.epic}', expected like E3")
    items = [s.strip() for x in a.ids for s in x.split(",") if s.strip()]
    if any(not D_RE.match(i) for i in items):
        die(f"bad decision ids {' '.join(items)}, expected like D81 D82")
    if items and a.note is not None:
        die("give D ids or --note, not both")
    if a.note is not None and ("\u2014" in a.note or not a.note.strip()):
        die("the note is empty or contains an em dash")
    own = C.load("lib/ownership")
    root = own.repo_root(a.root, a.release)
    folder = own.release_folder(root, own.detect_owner(root, a.owner), a.release)
    path = folder / own.EPICS_DIR / f"{a.epic}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    if a.note is not None:
        if not path.is_file():
            die(f"{path} missing")
        note(own, path, a.note)
        C.commit(root, [path], f"docs(plan): {a.release} {a.epic} note")
    elif items:
        if start(own, folder, path, a.epic, [int(D_RE.match(i).group(1)) for i in items]):
            commit(root, folder, a.release, path, f"docs(plan): {a.release} {a.epic} epic started")
    else:
        if path.exists():
            die(f"refusing to overwrite {path}")
        path.write_text(stub(own, a.epic, folder), encoding="utf-8")
        commit(root, folder, a.release, path, f"docs(plan): {a.release} {a.epic} epic file")
    print(path)


def commit(root, folder, release, path, message):
    """Commit the epic file. In a release of format 2.2 the status chain runs first (the epic's
    status is counted from this file) and its writes go into the same commit."""
    st = C.load("lib/status")
    if not st.new_form(folder):
        C.commit(root, [path], message)
        return
    with open(C.lock_file(folder), "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with contextlib.redirect_stdout(io.StringIO()):
            st.sync(folder, release)
        st.commit(root, folder, [path], message)
        fcntl.flock(lock, fcntl.LOCK_UN)


if __name__ == "__main__":
    main()
