#!/usr/bin/env python3
"""Check mode, writes nothing: every file the named specs' milestones own (for a D id: the specs
citing it) that a milestone of a running epic also owns.

Usage: python3 -I epics/overlap.py <release> <spec numbers or D ids> [--owner X] [--root PATH]

A running epic is a [E<n>] tag in decisions.md on a decision without [Done]; a spec's epic is
its own "- Epic: E<n>" line (epics/tag.py). Exit code 1 when a file is shared, 0 otherwise.
"""
import argparse
import importlib.util
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


def running_epics(tags):
    """Epics with at least one decision not yet [Done]."""
    return sorted({t["epic"] for t in tags.values() if t["epic"] and not t["done"]})


def overlap(own, folder, items):
    """Print files the named specs (or the specs citing the named D ids) share with
    milestones of running epics. Returns the number of shared files."""
    tags = own.read_tags(folder)
    epics = own.spec_epics(folder)
    files = dict(own.spec_files(folder))
    targets = set()
    for item in items:
        d = own.D_ID_RE.match(item)
        if d:
            hit = [num for num, (_, cited) in epics.items() if int(d.group(1)) in cited]
            if not hit:
                print(f"{item}: no spec cites it yet, files unknown")
            targets.update(hit)
        elif own.SPEC_NUM_RE.match(item) and item in files:
            targets.add(item)
        else:
            own.die(f"'{item}' is neither a spec number with a file nor a D id")
    running = set(running_epics(tags))
    owned = {}
    for num, (epic, _) in epics.items():
        if num in targets or epic not in running:
            continue
        for b in own.parse_spec(files[num]):
            for f in b["files"] or []:
                owned.setdefault(f, []).append(f"{b['name']} (E{epic})")
    shared = 0
    for num in sorted(targets, key=own.num_key):
        for b in own.parse_spec(files[num]):
            for f in b["files"] or []:
                if f in owned:
                    shared += 1
                    print(f"{num} {b['name']}: `{f}` shared with {', '.join(owned[f])}")
    print(f"running epics: {', '.join(f'E{n}' for n in sorted(running)) or 'none'}; "
          f"checked specs: {', '.join(sorted(targets, key=own.num_key)) or 'none'}; shared files: {shared}")
    return shared


def main():
    ap = argparse.ArgumentParser(usage="epics/overlap.py <release> <spec numbers or D ids> [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("items", nargs="+", metavar="ID")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        C.die(f"bad release '{a.release}', expected like v0.9.x")
    own = C.load("lib/ownership")
    root = own.repo_root(a.root, a.release)
    folder = own.release_folder(root, own.detect_owner(root, a.owner), a.release)
    items = [s.strip() for x in a.items for s in x.split(",") if s.strip()]
    sys.exit(1 if overlap(own, folder, items) else 0)


if __name__ == "__main__":
    main()
