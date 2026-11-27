#!/usr/bin/env python3
"""Close an iterative spec, on the owner's word.

Usage: python3 -I plan/close_spec.py <release> <spec> [--owner X] [--root PATH]

An iterative spec stays open, and counts as unfinished, until it is closed. This writes
"closed: <today>" into the spec's front matter, runs the refresh chain (lib/grid.py refresh)
and the page data, and commits the spec with the files the chain changed. A closed spec takes
no new milestone or task.

Refuses, writing nothing: a spec with no file; a spec that is not iterative; a spec closed
already; a milestone whose grid cell is not "[x]" or "[!]" (merge it or stop it first; an empty
milestone that will never run is removed from the spec by hand).
"""
import argparse
import contextlib
import datetime
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
NUM_RE = re.compile(r"^\d{2}(?:\.\d+)?$")
die, load = C.die, C.load


def main():
    ap = argparse.ArgumentParser(usage="plan/close_spec.py <release> <spec> [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("spec")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    if not NUM_RE.fullmatch(a.spec):
        die(f"bad spec number '{a.spec}', expected like 41 or 41.1")
    own, sp = load("lib/ownership"), load("lib/specs")
    root, folder = C.find_folder(a.release, a.owner, a.root)
    path = dict(own.spec_files(folder)).get(a.spec)
    if path is None:
        die(f"spec {a.spec} has no file in {own.SPECS_DIR}")
    doc = own.read_spec(path)
    if doc["type"] != "iterative":
        die(f"spec {a.spec} is not iterative: it is finished when its milestones are")
    if doc["closed"]:
        die(f"spec {a.spec} is closed already ({doc['closed']})")
    cells = sp.grid_cells(folder, a.spec)
    still = [b["name"] for b in doc["blocks"] if cells.get(b["name"]) not in ("[x]", "[!]")]
    if still:
        die(f"spec {a.spec} has unfinished milestones: {', '.join(still)}")
    today = datetime.date.today().isoformat()
    with open(C.lock_file(folder), "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path.write_text(own.set_front(own.read(path), "closed", today), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            load("lib/grid").refresh(folder, a.release, quiet=True, locked=True)
            load("sprints/swimlanes").write(folder, a.release, quiet=True)
        paths = [path, folder / own.SPRINTS_MD, folder / "decisions.md", folder / own.QUEUE_MD]
        paths += sorted((folder / own.EPICS_DIR).glob("E*.md"))
        C.commit(root, paths, f"docs(plan): {a.release} spec {a.spec} closed")
        fcntl.flock(lock, fcntl.LOCK_UN)
    print(f"spec {a.spec}: closed {today}")


if __name__ == "__main__":
    main()
