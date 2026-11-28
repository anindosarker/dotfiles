#!/usr/bin/env python3
"""Print the first card of the Open lane of queue.md with its sub-bullets; "none" when Open is
empty. Read-only.

A release of format 2.1 and higher (lib/queue.py): the open item with the lowest number, as its
file path on one line and the text of the file below it; "none" when no item is open.

Usage: python3 -I queue/next.py <release> [--owner X] [--root PATH]
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


def print_next(bd, text):
    """The first card in Open with its sub-bullets, or none."""
    card = next((c for c in bd.parse(text)["cards"] if c["lane"] == "Open"), None)
    print(card["text"] if card else "none")


def main():
    ap = argparse.ArgumentParser(usage="queue/next.py <release> [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        C.die(f"bad release '{a.release}', expected like v0.9.x")
    root = C.repo_root(a.root, a.release)
    folder = C.release_folder(root, C.detect_owner(root, a.owner), a.release)
    Q = C.load("lib/queue")
    if Q.item_form(folder):
        item = next((it for it in Q.items(folder) if Q.status_of(it) == "open"), None)
        print(f"{item['path']}\n{item['text'].rstrip()}" if item else "none")
        return
    queue = folder / C.QUEUE_MD
    print_next(C.load("lib/board"), C.read(queue) if queue.is_file() else "")


if __name__ == "__main__":
    main()
