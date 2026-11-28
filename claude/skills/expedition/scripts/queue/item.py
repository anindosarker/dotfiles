#!/usr/bin/env python3
"""Allocate the next D or Q id of a release and file the item under it, so two sessions
on one checkout never pick the same number.

Usage: python3 -I queue/item.py <release> D|Q "<title>" [--source Q<n>] [--option <n>]
       [--decider you|lead] [--bullet "<text>"] [--new-round] [--owner X] [--root PATH]
       python3 -I queue/item.py <release> --move Q<n> Open|Later|Dropped|Autofix|to-do|backlog|archived|done
       [--decider you|lead|agent]
       python3 -I queue/item.py <release> --fact Q<n> "<text>"
       python3 -I queue/item.py <release> --depends Q<n> "<Q ids>"

Under an exclusive lock on <release folder>/status/data/.ids.lock, re-reading the files right before the
write (queue.md is a kanban board the owner may drag in the editor; lib/board.py edits it in place
and leaves every other byte as it was):

- D: a card "- [ ] **D<n>** <title> #R<n>" at the end of To do in decisions.md (a kanban board,
  lib/decisions.py), the --bullet line if given, then "- Source: Q<n>" if --source is given, as
  tab-indented lines. <n> is the highest D number in the file plus one; the round is the
  highest #R number in the file (1 when none), the next one with --new-round. With --source,
  card Q<n> moves to the end
  of Decided, unticked, with "#D<n>" at the end of its title line; a card already in Decided
  keeps the highest decision number.
- Q: a tagless card "- [ ] **Q<n>** <title>" at the end of Open, the --bullet text as its
  first fact.
- --move: card Q<n> with its sub-bullets to the end of that lane (Decided only through D
  --source; a card leaving Decided loses its #D and #E tags). --fact: one tab-indented fact
  sub-bullet at the end of card Q<n>.

Every call then moves the decisions.md cards to the lanes of the Done rule (lib/decisions.py
sync) and syncs the Decided cards with those lanes (lib/board.py sync: the tick and the #E<n>
tag), and commits decisions.md when the sync changed it.

queue.md is created from templates/queue.md when missing. Commits the files it wrote and
prints the id alone, e.g. Q11. --option is refused in this form: a card holds no option.

A release of format 2.1 and higher (lib/queue.py) keeps each item in queue/Q<n>-<slug>.md and
queue.md as a list the script writes again after each change; nothing is synced into the queue:

- Q: a new item file with "status: open", the title and the --bullet text under "## Notes";
  <n> is one above every item file and every line of queue.md.
- --fact: one bullet at the end of "## Notes"; no other line of the file changes.
- --move: "status" set to the lane word in lower case; an item leaving decided loses its
  "decision" and "option" lines.
- D: the decision card as above; with --source, the item gets "status: decided" ("done" in
  format 2.2),
  "decision: D<n>" (an item already decided keeps the highest decision number) and, with
  --option, "option: <n>". An option number the item's "## Options:" does not have is refused
  before anything is written; --option needs --source.

It writes the item file, queue.md and status/data/queue.data.js (the Queue view of the task
board, git-ignored), commits the item file, queue.md and decisions.md, and prints the id alone.

--move takes the lane words and the words of format 2.2 in every format, in any case: to-do is
Open, backlog is Later, archived is Dropped, done is Autofix. It stores the word of the release's
format (lib/queue.py move_status); on a board the word moves the card to that lane.

A release of format 2.2 and higher (lib/queue.py status_form) stores the words of format 2.2: Q
writes "status: to-do"; --move writes to-do, backlog, archived or done. A call that closes an
item needs --decider and is refused without it, before anything is written:

- --move Dropped (archived): --decider you or lead; --move Autofix (done): --decider agent. The
  item gets "decider: <word>". Every --move removes "decision", "option" and "decider" first;
  Open and Later need no --decider and write none.
- D --source: --decider you or lead (agent is refused: a decided item is closed by you or
  lead); the item gets "decider" with "status: done",
  "decision" and "option". The decision card is the same as in format 2.1: nothing about the
  decider goes into decisions.md. D with no --source needs no --decider.

--depends Q<n> "Q14, Q15" replaces the "depends_on" line of Q<n>; an empty text removes it.
Refused, before anything is written: an id that is not a queue item id, an id with no item file,
the item itself, a ring of items that wait for each other. After every command the blocked check
(lib/queue.py settle) sets "blocked" or "to-do" on each to-do or blocked item from what it waits
for, and the files it changed are committed with the rest.

Below format 2.2 --decider is accepted and not stored, and --depends is refused.

A release whose decisions are files (lib/decisions.py file_form: format 2.2 and decisions.md
not a board) records a decision in a file of its own:

- D needs --decider you, lead or agent on every call, also one with no --source, and is refused
  without it before anything is written (D --source still takes you or lead only). It writes
  decisions/D<n>-<slug>.md with "status: to-do", "decider" and, with --source, "source"; the
  title line; the --bullet line as the body. No "- Source:" line. <n> is one above the highest
  decision file; the slug is the rule of a queue item file. The round goes to
  status/data/status.json, "decisions.D<n>.round", by the rule above (lib/status.py
  set_decision). Then the status rule on every decision file and decisions.md as a list
  (lib/decisions.py sync_files), one commit of the decision file, decisions.md, status.json and,
  with --source, the item file, and the page and dashboard data written again.
- The statement above that D with no --source needs no --decider, and that nothing about the
  decider goes into decisions.md, holds for the board form only.
"""
import argparse
import fcntl
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
SOURCE_RE = re.compile(r"^Q\d+$")
die = C.die
BOARD_LANES = {"open": "Open", "later": "Later", "dropped": "Dropped", "autofix": "Autofix"}


class _Once(argparse.Action):
    def __call__(self, parser, ns, value, option_string=None):
        if getattr(ns, self.dest) is not None:
            parser.error(f"{option_string} is given twice: one bullet per card, add more with --fact")
        setattr(ns, self.dest, value)

def main():
    ap = argparse.ArgumentParser(
        usage='queue/item.py <release> D|Q "<title>" [--source Q<n>] [--option <n>] [--decider W] [--bullet "<text>"] [--new-round] | '
              '<release> --move Q<n> Open|Later|Dropped|Autofix|to-do|backlog|archived|done [--decider W] | <release> --fact Q<n> "<text>" | '
              '<release> --depends Q<n> "<Q ids>" [--owner X] [--root PATH]'
    )
    ap.add_argument("release")
    ap.add_argument("kind", nargs="?")
    ap.add_argument("title", nargs="?")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    ap.add_argument("--source")
    ap.add_argument("--option", help="2.1: the number of the option the owner picked (D --source)")
    ap.add_argument("--decider", help="2.2: you, lead or agent, who closed the item (--move Dropped|Autofix, D --source); "
                    "with decision files, who made the call (every D)")
    ap.add_argument("--bullet", action=_Once)
    ap.add_argument("--move", nargs=2, metavar=("Q<n>", "LANE"))
    ap.add_argument("--fact", nargs=2, metavar=("Q<n>", "TEXT"))
    ap.add_argument("--depends", nargs=2, metavar=("Q<n>", "IDS"), help='2.2: the items Q<n> waits for, "Q14, Q15"')
    ap.add_argument("--new-round", action="store_true")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    card_op = a.move or a.fact or a.depends
    if sum(1 for x in (a.move, a.fact, a.depends) if x) > 1:
        die("--move, --fact and --depends are separate calls")
    if card_op:
        if a.kind or a.title or a.source or a.bullet or a.new_round or a.option:
            die("--move, --fact and --depends take only a Q id and a lane or a text")
        if not SOURCE_RE.match(card_op[0]):
            die(f"bad id '{card_op[0]}', expected like Q3")
        if a.move and C.load("lib/queue").move_status(a.move[1]) is None:
            die(f"bad lane '{a.move[1]}': Open, Later, Dropped or Autofix, or to-do, backlog, archived or done "
                "(Decided only through D --source)")
    else:
        if a.kind not in ("D", "Q"):
            die(f"bad kind '{a.kind}': the kinds are D and Q")
        if a.kind == "Q" and (a.source or a.new_round or a.option):
            die("--source, --option and --new-round are for a D item")
        if a.option is not None and not re.fullmatch(r"[1-9]\d*", a.option):
            die(f"bad option '{a.option}', expected a number like 2")
        if a.option is not None and not a.source:
            die("--option needs --source: it is the option picked on that item")
        if not (a.title or "").strip():
            die("empty title")
        if a.source and not SOURCE_RE.match(a.source):
            die(f"bad source '{a.source}', expected like Q3")
    if a.decider is not None and a.decider not in C.load("lib/queue").DECIDERS:
        die(f"bad decider '{a.decider}': you, lead or agent")
    title = (a.title or "").strip()
    fact = a.fact[1] if a.fact else ""
    for label, val in (("title", title), ("bullet", a.bullet or ""), ("fact", fact)):
        if "\n" in val:
            die(f"{label} must be one line")
        if "\u2014" in val:
            die(f"{label} contains an em dash")

    own = C.load("lib/ownership")
    bd = C.load("lib/board")
    root = own.repo_root(a.root, a.release)
    folder = own.release_folder(root, own.detect_owner(root, a.owner), a.release)
    queue = folder / own.QUEUE_MD
    dc = C.load("lib/decisions")
    target = dc.path_of(folder)
    Q = C.load("lib/queue")
    if a.depends and not Q.status_form(folder):
        die(f"--depends needs a release of format 2.2: move {a.release} first with scripts/migrate/v2.1-v2.2")
    if Q.item_form(folder):
        return items(a, root, folder, Q, dc, target, card_op, title, fact)
    if a.option is not None:
        die(f"--option needs a release of format 2.1 or higher: {a.release} keeps its queue on a board")

    with open(C.lock_file(folder), "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not queue.is_file():
            queue.write_text(C.template("queue.md"), encoding="utf-8")
        board = queue.read_text(encoding="utf-8")
        new = None
        written = []

        if card_op:
            num = int(card_op[0][1:])
            if bd.find(board, num) is None:
                die(f"{card_op[0]} is not in {queue}")
            ident = card_op[0]
            if a.move:
                new = bd.move(board, num, BOARD_LANES[Q.move_status(a.move[1])])
                subject = f"{ident} to {a.move[1]}"
            else:
                new = bd.add_fact(board, num, fact)
                subject = f"{ident} fact"
        elif a.kind == "Q":
            ident = f"Q{max([c['num'] for c in bd.parse(board)['cards']] or [0]) + 1}"
            block = [bd.card_line(ident[1:], title, "Open")]
            if a.bullet:
                block.append(bd.fact_line(a.bullet))
            new = bd.append_card(board, "Open", block)
            subject = f"{ident} {title}"
        else:
            if not target.is_file():
                die(f"missing: {target}")
            card = bd.find(board, int(a.source[1:])) if a.source else None
            if a.source and card is None:
                die(f"{a.source} is not in {queue}")
            d_text = target.read_text(encoding="utf-8")
            cards = dc.parse(d_text)["cards"]
            ident = f"D{dc.highest(cards) + 1}"
            rnd = dc.next_round(cards, a.new_round)
            bullets = ([a.bullet] if a.bullet else []) + ([f"Source: {a.source}"] if a.source else [])
            block = dc.new_card(int(ident[1:]), title, rnd, bullets)
            bd.write(target, bd.insert_card(d_text, dc.TODO, block, int(ident[1:]), "D"))
            written.append(target)
            if card is not None:
                old = card["d"] if card["lane"] == "Decided" else None
                keep = max(old or 0, int(ident[1:]))
                new = bd.move(board, card["num"], "Decided", keep)
                if old and old > int(ident[1:]):
                    print(f"{a.source} keeps #D{old}", file=sys.stderr)
            subject = f"{ident} {title}"

        moved = dc.sync_file(folder)
        if moved:
            print(f"decisions.md lanes synced: {dc.moved_text(moved)}", file=sys.stderr)
        synced, changed = bd.sync(board if new is None else new, bd.decision_tags(own, folder))
        if changed:
            print(f"synced with decisions.md: {', '.join(f'Q{n}' for n in changed)}", file=sys.stderr)
        if new is not None or changed:
            bd.write(queue, synced)
            written.append(queue)

        paths = [str(p) for p in written]
        if target not in written and target.is_file():
            paths.append(str(target))
        C.commit(root, paths, f"docs(plan): {a.release} {subject}")
        fcntl.flock(lock, fcntl.LOCK_UN)
    print(ident)


def items(a, root, folder, Q, dc, target, card_op, title, fact):
    """The commands on a release of format 2.1 and higher (item files, lib/queue.py)."""
    bd = C.load("lib/board")
    new22 = Q.status_form(folder)
    closes = None  # format 2.2: the status a --move closes the item with, which needs --decider
    if new22 and a.move:
        word = Q.move_status(a.move[1], True)
        closes = word if word in Q.CLOSERS else None
        want = Q.CLOSERS.get(closes, ())
        if closes and a.decider is None:
            die(f"--move {a.move[0]} {a.move[1]} needs --decider {' or --decider '.join(want)}")
        if closes and a.decider not in want:
            die(f"--decider {a.decider} cannot close {a.move[0]} as {closes}: "
                f"{'an archived item is closed by you or lead' if closes == 'archived' else 'a done item with no decision is closed by agent'}")
    files = a.kind == "D" and dc.file_form(folder)  # the decision goes into a file of its own
    if files and a.decider is None:
        die("D needs --decider you, lead or agent: who made the call (nothing was written)")
    if new22 and a.source and a.decider is None:
        die(f"D --source {a.source} needs --decider you or lead in a release of format 2.2")
    if new22 and a.source and a.decider not in Q.DECISION_DECIDERS:
        die(f"--decider {a.decider} cannot close {a.source} with a decision: a decided item is closed by you or lead")
    deps = Q.split_ids(a.depends[1]) if a.depends else []
    with open(C.lock_file(folder), "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        written = []
        if card_op:
            ident = card_op[0]
            item = Q.find(folder, int(ident[1:]))
            if item is None:
                die(f"{ident} is not in {folder / Q.QUEUE_DIR}")
            if a.depends:
                why = Q.check_depends(folder, int(ident[1:]), deps)
                if why:
                    die(why)
                new = Q.set_front(item["text"], depends_on=", ".join(deps))
                subject = f"{ident} depends on {', '.join(deps) or 'nothing'}"
            elif a.move:
                word = Q.move_status(a.move[1], new22)
                new = Q.set_front(item["text"], status=word, decision=None, option=None,
                                  decider=a.decider if closes else None)
                subject = f"{ident} to {a.move[1]}"
            else:
                new = Q.add_note(item["text"], fact)
                subject = f"{ident} fact"
            if new != item["text"]:
                Q.write_item(item["path"], new)
                written.append(item["path"])
        elif a.kind == "Q":
            ident = f"Q{Q.next_number(folder)}"
            path = Q.item_path(folder, int(ident[1:]), title)
            if path.exists():
                die(f"refusing to overwrite {path}")
            Q.write_item(path, Q.new_item(int(ident[1:]), title, a.bullet, new22))
            written.append(path)
            subject = f"{ident} {title}"
        else:
            if not files and not target.is_file():
                die(f"missing: {target}")
            item = Q.find(folder, int(a.source[1:])) if a.source else None
            if a.source and item is None:
                die(f"{a.source} is not in {folder / Q.QUEUE_DIR}")
            if a.option is not None:
                keys = [o["key"] for o in Q.options(item["text"])]
                if a.option not in keys:
                    die(f"{a.source} has no option {a.option}: its options are "
                        f"{', '.join(keys) if keys else 'not written yet (no ## Options: section)'}")
            if files:
                cards = dc.file_cards(folder)
                ident = f"D{dc.highest(cards) + 1}"
                path = dc.new_path(folder, int(ident[1:]), title)
                if path.exists():
                    die(f"refusing to overwrite {path}")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(dc.new_text(int(ident[1:]), title, a.decider, a.source, a.bullet), encoding="utf-8")
                written += [path, C.load("lib/status").set_decision(
                    folder, ident, round=dc.next_round(cards, a.new_round))]
            else:
                d_text = target.read_text(encoding="utf-8")
                cards = dc.parse(d_text)["cards"]
                ident = f"D{dc.highest(cards) + 1}"
                rnd = dc.next_round(cards, a.new_round)
                bullets = ([a.bullet] if a.bullet else []) + ([f"Source: {a.source}"] if a.source else [])
                block = dc.new_card(int(ident[1:]), title, rnd, bullets)
                bd.write(target, bd.insert_card(d_text, dc.TODO, block, int(ident[1:]), "D"))
                written.append(target)
            if item is not None:
                closed = "done" if new22 else "decided"
                m = re.match(r"^D(\d+)$", item["decision"]) if item["status"] == closed else None
                old = int(m.group(1)) if m else None
                who = {"decider": item["decider"] or a.decider} if new22 else {}
                if old and old > int(ident[1:]):
                    print(f"{a.source} keeps D{old}", file=sys.stderr)
                    new = Q.set_front(item["text"], status=closed, **who)
                else:
                    new = Q.set_front(item["text"], status=closed, decision=ident, option=a.option,
                                      **({"decider": a.decider} if new22 else {}))
                if new != item["text"]:
                    Q.write_item(item["path"], new)
                    written.append(item["path"])
            subject = f"{ident} {title}"

        written += [p for p in Q.settle(folder) if p not in written]
        moved = dc.sync_file(folder)
        if moved:
            print(f"decisions.md lanes synced: {dc.moved_text(moved)}", file=sys.stderr)
        queue = folder / C.QUEUE_MD
        if not Q.list_in_step(folder):
            Q.write_list(folder)
            written.append(queue)
        paths = [str(p) for p in written]
        for p in (*dc.commit_paths(folder), queue):
            if p not in written and p.exists():
                paths.append(str(p))
        C.commit(root, paths, f"docs(plan): {a.release} {subject}")
        if files:  # after the commit: "changed" is read from git; status.data.js has the round
            C.load("lib/status").write_page_data(folder)
        else:
            Q.write_data(folder)  # after the commit: "changed" is read from git
        fcntl.flock(lock, fcntl.LOCK_UN)
    print(ident)


if __name__ == "__main__":
    main()
