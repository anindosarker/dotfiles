#!/usr/bin/env python3
"""Sync the Decided cards of queue.md with the lanes of decisions.md (lib/board.py sync: the
tick and the #E<n> tag), under the .ids.lock lock. Prints the cards it changed. Commits nothing.

Usage: python3 -I queue/sync.py <release> [--owner X] [--root PATH]

queue/item.py, epics/tag.py, sprints/refresh.py and sprints/mark.py run the same sync.

A release of format 2.1 and higher keeps its queue in item files (lib/queue.py): a decided item
holds its decision id only, so there is nothing to sync. The script prints that, writes nothing
and exits 0; the path stays, because sessions run it by path.
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


def main():
    ap = argparse.ArgumentParser(usage="queue/sync.py <release> [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        C.die(f"bad release '{a.release}', expected like v0.9.x")
    _, folder = C.find_folder(a.release, a.owner, a.root)
    if C.load("lib/queue").item_form(folder):
        print(f"{a.release}: the queue is in item files (format 2.1); nothing to sync")
        return
    C.load("lib/grid").sync_queue(folder)


if __name__ == "__main__":
    main()
