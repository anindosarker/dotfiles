#!/usr/bin/env python3
"""Create a fix milestone in a release: run/trackers/fix-<slug>-tracker.md citing its queue
cards on its first line, each cited queue.md card moved to the end of the Autofix lane, then
status/ownership.md and status/sprints.md regenerated so the fix has a grid row in the current
sprint column (sprints.py: the first column holding a "[ ]" or "·" cell of an epic row, else the
column after the last column holding an epic row).

Usage: python3 -I new_fix.py <release> <slug> "Q3, Q4" [--files a,b] [--depends "<names>"]
       [--title "<Title>"] [--owner X] [--root PATH]

A fix milestone has a tracker and a grid row, no spec. Its name is the tracker title
without ", tracker": --title, else the slug in words, followed by the cited ids. A D id may be
cited too (a fix a decision asks for); it gets no tag. Commits nothing.
"""
import argparse
import fcntl
import importlib.util
import re
import sys
from pathlib import Path

RELEASE_RE = re.compile(r"^v\d+\.\d+\.x$")
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
CITES_RE = re.compile(r"^[QD]\d+(\s*,\s*[QD]\d+)*$")


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def load(name):
    sys.dont_write_bytecode = True
    path = Path(__file__).resolve().parent / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def tracker_text(title, files, depends):
    """templates/tracker.md head with the title, Status: planned, Files owned and Depends on lines."""
    path = Path(__file__).resolve().parent.parent / "templates" / "tracker.md"
    if not path.is_file():
        die(f"bundled template missing: {path}")
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            break
        if line.startswith("# "):
            line = f"# {title}, tracker"
        elif line.startswith("Status:"):
            out.append("Status: planned")
            out.append("Files owned: " + (", ".join(f"`{f}`" for f in files) if files else "none"))
            out.append(f"Depends on: {depends or 'none'}")
            continue
        out.append(line)
    return "\n".join(out).rstrip() + "\n"


def main():
    ap = argparse.ArgumentParser(
        usage='new_fix.py <release> <slug> "Q3, Q4" [--files a,b] [--depends "<names>"] '
              '[--title "<Title>"] [--owner X] [--root PATH]'
    )
    ap.add_argument("release")
    ap.add_argument("slug")
    ap.add_argument("cites")
    ap.add_argument("--files", default="")
    ap.add_argument("--depends", default="")
    ap.add_argument("--title")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: git top level)")
    a = ap.parse_args()
    if not RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    if not SLUG_RE.match(a.slug):
        die(f"bad slug '{a.slug}', expected lowercase-with-dashes")
    cites = a.cites.strip()
    if not CITES_RE.match(cites):
        die(f"bad ids '{a.cites}', expected like \"Q3, Q4\"")
    ids = [s.strip() for s in cites.split(",")]
    cites = ", ".join(ids)
    for label, val in (("title", a.title or ""), ("files", a.files), ("depends", a.depends)):
        if "|" in val:
            die(f"{label} must not contain '|'")
        if "—" in val:
            die(f"{label} contains an em dash")
    files = [f.strip() for f in a.files.split(",") if f.strip()]
    words = a.title or a.slug.replace("-", " ").capitalize()
    title = f"{words} ({cites})"

    own = load("ownership")
    root = own.repo_root(a.root)
    folder = own.release_folder(root, own.detect_owner(root, a.owner), a.release)
    if not (folder / own.SPECS_DIR).is_dir():
        die(f"specs folder missing: {folder / own.SPECS_DIR}")
    trackers = folder / own.TRACKERS_DIR
    trackers.mkdir(parents=True, exist_ok=True)
    tracker = trackers / f"fix-{a.slug}-tracker.md"
    if tracker.exists():
        die(f"refusing to overwrite {tracker}")
    queue = folder / own.QUEUE_MD
    bd = load("board")
    have = {c["num"] for c in bd.parse(queue.read_text(encoding="utf-8"))["cards"]}
    missing = [i for i in ids if i.startswith("Q") and int(i[1:]) not in have]
    if missing:
        die(f"not in {queue.name}: {', '.join(missing)}")
    tracker.write_text(tracker_text(title, files, a.depends.strip()), encoding="utf-8")
    try:
        own.generate(folder, a.release, quiet=True)
    except SystemExit:
        tracker.unlink()
        die(f"ownership.py failed with the fix; {tracker.name} removed")
    with open(folder / ".ids.lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        for i in ids:
            if i.startswith("Q"):
                queue.write_text(bd.move(queue.read_text(encoding="utf-8"), int(i[1:]), "Autofix"),
                                 encoding="utf-8")
        fcntl.flock(lock, fcntl.LOCK_UN)
    print(tracker)
    print(queue)
    print(folder / own.OWNERSHIP_MD)
    load("sprints").write(folder, a.release)
    load("swimlanes").write(folder, a.release)


if __name__ == "__main__":
    main()
