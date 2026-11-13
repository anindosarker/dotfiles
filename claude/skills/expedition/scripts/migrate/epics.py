#!/usr/bin/env python3
"""Move a release folder off status/ownership.md: the ownership facts are computed in memory
(lib/ownership.py compute) and each epic file carries its own "## Ownership" table.

Usage: python3 -I migrate/epics.py <release> [--dry-run] [--owner X] [--root PATH]

For every plan/epics/E<n>.md without an "## Ownership" section: writes the table from the specs
(reference/formats.md, Epic file): one row per decision of the "Decisions:" line and spec of the
epic citing it, one row with an empty Decision cell per spec of the epic citing none of them, a
decision no spec cites gets a row with empty Spec, Milestone and Sprint cells. Files are the
files the row's spec's milestones own (the per-decision split was never recorded); Milestone and
Sprint as epics/table.py writes them, the Sprint from status/sprints.md. The epic's specs
are its tagged specs ("- Epic: E<n>"); for an epic with no Starts value also the untagged specs
citing its decisions. An empty "## Notes" section (no line under the heading) is removed; a
non-empty one is kept as it is. An existing "## Ownership" table is left alone. Then
status/ownership.md is removed with git rm.

Prints one line per epic file. --dry-run prints the same and writes nothing. Commits nothing. A
second run changes nothing. Every other script refuses a folder that still has
status/ownership.md, with one line naming this script; migrate/layout.py runs it.
"""
import argparse
import importlib.util
import re
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
HERE = Path(__file__).resolve().parent


die = C.die


def load(name):
    """lib/ownership.py and migrate/queue.py, by their old names."""
    return C.load({"ownership": "lib/ownership", "migrate_queue": "migrate/queue"}[name])


def drop_empty_notes(own, text):
    """(text, state): the "## Notes" section removed when nothing but blank lines is under its
    heading; state is "removed", "kept" or "none"."""
    lines = text.rstrip("\n").split("\n")
    span = own.section(lines, own.NOTES_HEAD)
    if span is None:
        return text, "none"
    start, end = span
    if any(l.strip() for l in lines[start + 1:end]):
        return text, "kept"
    lines = lines[:start] + lines[end:]
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines) + "\n", "removed"


def main():
    ap = argparse.ArgumentParser(usage="migrate/epics.py <release> [--dry-run] [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    own = load("ownership")
    root = own.repo_root(a.root, a.release)
    folder = root / ".ai" / "plans" / a.release / own.detect_owner(root, a.owner)
    if not folder.is_dir():
        die(f"release folder missing: {folder}")
    if not (folder / "plan").is_dir():
        die(f"{folder} has the old layout (no plan/): run python3 -I {HERE / 'layout.py'} {a.release}")
    old = load("migrate_queue").refusal(folder, a.release)
    if old:
        die(old)
    comp = own.compute(folder)
    if comp["errors"]:
        own.print_errors(comp["errors"], "the milestones do not schedule; nothing written")
    gcols = own.grid_columns(folder)
    writes = []
    for n in own.epic_numbers(folder):
        path = own.epic_path(folder, n)
        text = own.read(path)
        rows, err = own.read_table(text)
        if err:
            die(f"{path}: {err}")
        if rows is not None:
            new, notes = drop_empty_notes(own, text)
            print(f"E{n}: table kept, {len(rows)} rows; Notes {notes}")
        else:
            decisions = own.epic_decisions(text)
            specs, _ = own.epic_specs(folder, n, decisions)
            rows = own.build_table(folder, decisions, specs, [], comp, gcols, from_specs=True)
            new, notes = drop_empty_notes(own, own.put_table(text, rows))
            print(f"E{n}: {len(rows)} rows, specs {', '.join(specs) or 'none'}; Notes {notes}")
        if new != text:
            writes.append((path, new))
    legacy = folder / own.LEGACY_OWNERSHIP_MD
    print(f"{own.LEGACY_OWNERSHIP_MD}: {'removed' if legacy.exists() else 'already gone'}")
    if a.dry_run:
        print("dry run; nothing written")
        return
    for path, new in writes:
        path.write_text(new, encoding="utf-8")
    if legacy.exists():
        r = subprocess.run(["git", "-C", str(root), "rm", "-q", "--", str(legacy)],
                           capture_output=True, text=True)
        if r.returncode:
            legacy.unlink()
    print(f"{len(writes)} epic files written; nothing committed" if writes else "nothing to change")


if __name__ == "__main__":
    main()
