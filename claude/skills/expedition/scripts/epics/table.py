#!/usr/bin/env python3
"""The epic table, the pre-go preview: fill the Spec, Milestone and Sprint columns of the
"## Ownership" table in plan/epics/E<n>.md (reference/formats.md, Epic file) and print the facts.
The spec writer runs it before SPECS; the lead's check reads its result.

Usage: python3 -I epics/table.py <release> E<n> [<spec numbers>] [--owner X] [--root PATH]

The epic's specs: the specs with an "- Epic: E<n>" line, plus the spec numbers given, else (no
Starts value yet) every untagged spec citing a decision of the epic's "Decisions:" line;
untagged ones count as E<n>. One row per decision and spec of the epic citing it, the Files a
decision row carried split over those rows by the spec that owns each file (a file no citing
spec owns stays on the lowest spec's row), one row with an empty Decision cell per spec of the
epic citing none of its decisions; Milestone is the spec's milestone names joined by "; ",
Sprint its column, "S17 to S19" when its milestones span several. Before go the sprints are
provisional (the current sprint as the epic's start); a milestone with a grid row takes the
grid's column. Rows ordered by sprint, spec number, decision number (lib/ownership.py
fill_epic).

Then it prints the facts: the sprints the epic spans, its critical path, every pair of the
epic's specs owning the same file, each Files path that does not exist yet ("new or missing":
a new file and a typo look the same), and a row file no milestone of its spec owns. No verdict.
Commits nothing. Exit 1 only for an ownership error (sprints/check.py) or an unreadable table.
"""
import argparse
import importlib.util
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


def main():
    ap = argparse.ArgumentParser(usage="epics/table.py <release> E<n> [<spec numbers>] [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("epic", nargs="+", metavar="ARG")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        C.die(f"bad release '{a.release}', expected like v0.9.x")
    own = C.load("lib/ownership")
    root = own.repo_root(a.root, a.release)
    folder = own.release_folder(root, own.detect_owner(root, a.owner), a.release)
    if not (folder / own.SPECS_DIR).is_dir():
        own.die(f"specs folder missing: {folder / own.SPECS_DIR}")
    m = re.match(r"^E(\d+)$", a.epic[0])
    nums = [s.strip() for x in a.epic[1:] for s in x.split(",") if s.strip()]
    if not m or not all(own.SPEC_NUM_RE.match(n) for n in nums):
        own.die("takes E<n> and optional spec numbers, e.g. E6 09 10")
    own.fill_epic(folder, int(m.group(1)), nums or None)


if __name__ == "__main__":
    main()
