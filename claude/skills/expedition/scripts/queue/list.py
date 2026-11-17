#!/usr/bin/env python3
"""Print the cards of one lane of queue.md in board order, one line each: the id, the title,
the #D and #E tags, and in Decided the tick ("[x]" or "[ ]") first. --facts adds each card's
sub-bullets under it. Lane "all" prints one line per lane with its card count. Default lane
Open; lane names are case-insensitive; an empty lane prints "none". Read-only.

Usage: python3 -I queue/list.py <release> [lane] [--facts] [--owner X] [--root PATH]
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


def card_line(card):
    """Q<n> <title> #D<d> #E<e>, with the tick first in Decided."""
    tags = (f" #D{card['d']}" if card["d"] else "") + (f" #E{card['e']}" if card["e"] else "")
    tick = ("[x] " if card["box"] == "x" else "[ ] ") if card["lane"] == "Decided" else ""
    return f"{tick}Q{card['num']} {card['title']}{tags}"


def print_lane(bd, text, lane, facts):
    """Every card of lane in board order, or none."""
    cards = [c for c in bd.parse(text)["cards"] if c["lane"] == lane]
    if not cards:
        print("none")
    for c in cards:
        print(card_line(c))
        if facts:
            for s in c["subs"]:
                if s.strip():
                    print(s)


def print_counts(bd, text):
    """One line per lane with its card count: the board's lanes, then any missing known lane."""
    board = bd.parse(text)
    cards = board["cards"]
    names = [l["name"] for l in board["lanes"]]
    names += [n for n in bd.LANES if n not in names]
    for n in names:
        print(f"{n} {sum(1 for c in cards if c['lane'] == n)}")


def main():
    ap = argparse.ArgumentParser(usage="queue/list.py <release> [lane] [--facts] [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("lane", nargs="?", default="Open")
    ap.add_argument("--facts", action="store_true", help="add each card's sub-bullets")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        C.die(f"bad release '{a.release}', expected like v0.9.x")
    bd = C.load("lib/board")
    lane = None
    if a.lane.lower() != "all":
        lane = next((n for n in bd.LANES if n.lower() == a.lane.lower()), None)
        if lane is None:
            C.die(f"unknown lane '{a.lane}', expected one of: {', '.join(bd.LANES)}, all")
    root = C.repo_root(a.root, a.release)
    folder = C.release_folder(root, C.detect_owner(root, a.owner), a.release)
    queue = folder / C.QUEUE_MD
    text = C.read(queue) if queue.is_file() else ""
    if lane is None:
        print_counts(bd, text)
    else:
        print_lane(bd, text, lane, a.facts)


if __name__ == "__main__":
    main()
