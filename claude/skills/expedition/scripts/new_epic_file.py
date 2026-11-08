#!/usr/bin/env python3
"""Create the epic file plan/epics/E<n>.md of a release (reference/formats.md, Epic file) and commit it.

Usage: python3 -I new_epic_file.py <release> E<n> [--owner X] [--root PATH]

Writes the stub "# E<n>", an empty "Decisions:" and "Specs:" line and "## Notes", then commits
that one file. Refuses when the file exists. The lead runs it the moment the previous epic's RUN
is sent.
"""
import argparse
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

RELEASE_RE = re.compile(r"^v\d+\.\d+\.x$")
EPIC_RE = re.compile(r"^E\d+$")


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def load_ownership():
    sys.dont_write_bytecode = True
    path = Path(__file__).resolve().parent / "ownership.py"
    spec = importlib.util.spec_from_file_location("ownership", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser(usage="new_epic_file.py <release> E<n> [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("epic")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: git top level)")
    a = ap.parse_args()
    if not RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    if not EPIC_RE.match(a.epic):
        die(f"bad epic '{a.epic}', expected like E3")
    own = load_ownership()
    root = own.repo_root(a.root)
    folder = own.release_folder(root, own.detect_owner(root, a.owner), a.release)
    path = folder / own.EPICS_DIR / f"{a.epic}.md"
    if path.exists():
        die(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# {a.epic}\n\nDecisions:\nSpecs:\n\n## Notes\n", encoding="utf-8")
    for args in (["add", "--", str(path)],
                 ["commit", "-q", "-m", f"docs(plan): {a.release} {a.epic} epic file", "--only", "--", str(path)]):
        r = subprocess.run(["git", "-C", str(root)] + args, capture_output=True, text=True)
        if r.returncode:
            die(f"git {args[0]} failed: {r.stderr.strip()}")
    print(path)


if __name__ == "__main__":
    main()
