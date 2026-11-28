#!/usr/bin/env python3
"""Print the cards of one lane of queue.md in board order, one line each: the id, the title,
the #D and #E tags, and in Decided the tick ("[x]" or "[ ]") first. --facts adds each card's
sub-bullets under it. Lane "all" prints one line per lane with its card count. Default lane
Open; lane names are case-insensitive; an empty lane prints "none". Read-only.

A release of format 2.1 and higher (lib/queue.py): the lane word selects the items whose
"status" is that word in lower case, in number order, one line "Q<n> <title>" each; --facts adds
the lines of each item's "## Notes" under it, each indented with one TAB. Lane "all" prints one
line per lane word with its item count.

The word may also be one of the six status words of format 2.2 (to-do, in progress, blocked,
done, backlog, archived), in every format. On a board: to-do is Open, backlog Later, archived
Dropped, done Decided then Autofix; blocked and in progress print "none". Format 2.1: each word
names the status it maps to (lib/queue.py select).

A release of format 2.2 and higher (lib/queue.py status_form): Open lists the to-do and the
blocked items, Decided the done items with a decision line, Autofix the done items without one,
Later the backlog items, Dropped the archived ones; the six words select by status alone. A
blocked item has " (blocked: waits for Q14, Q15)" after its title: the items of its depends_on
line that are not done. The status counts by the blocked check (lib/queue.py effective), also
after a hand edit. Lane "all" counts the items of each lane word.

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


def print_words(bd, text, word, facts):
    """A board and a word of format 2.2: the cards of the lanes it maps to, or none."""
    lanes = {"to-do": ("Open",), "backlog": ("Later",), "archived": ("Dropped",),
             "done": ("Decided", "Autofix")}.get(word, ())
    cards = [c for n in lanes for c in bd.parse(text)["cards"] if c["lane"] == n]
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


def print_items(Q, its, lane, facts, new=False):
    """The item form: the items of one lane word, or the count of each lane word (lane None)."""
    status = (lambda it: Q.effective(it, its)) if new else None
    if lane is None:
        for n in Q.LANES:
            print(f"{n} {len(Q.select(its, n, new, status))}")
        return
    mine = Q.select(its, lane, new, status)
    if not mine:
        print("none")
    for it in mine:
        wait = ""
        if new and status(it) == "blocked":
            wait = f" (blocked: waits for {', '.join(Q.waits_for(it, its))})"
        print(f"Q{it['file_num']} {it['title']}{wait}")
        if facts:
            for s in Q.notes(it["text"]).split("\n"):
                if s.strip():
                    print("\t" + s)


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
        lane = next((n for n in (*bd.LANES, *C.load("lib/queue").WORDS_22) if n.lower() == a.lane.lower()), None)
        if lane is None:
            C.die(f"unknown lane '{a.lane}', expected one of: {', '.join(bd.LANES)}, all, "
                  f"or {', '.join(C.load('lib/queue').WORDS_22)}")
    root = C.repo_root(a.root, a.release)
    folder = C.release_folder(root, C.detect_owner(root, a.owner), a.release)
    Q = C.load("lib/queue")
    if Q.item_form(folder):
        print_items(Q, Q.items(folder), lane, a.facts, Q.status_form(folder))
        return
    queue = folder / C.QUEUE_MD
    text = C.read(queue) if queue.is_file() else ""
    if lane is None:
        print_counts(bd, text)
    elif lane in bd.LANES:
        print_lane(bd, text, lane, a.facts)
    else:
        print_words(bd, text, lane, a.facts)


if __name__ == "__main__":
    main()
