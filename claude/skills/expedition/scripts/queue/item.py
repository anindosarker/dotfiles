#!/usr/bin/env python3
"""Allocate the next D or Q id of a release and file the item under it, so two sessions
on one checkout never pick the same number.

Usage: python3 -I queue/item.py <release> D|Q "<title>" [--source Q<n>]
       [--bullet "<text>"] [--owner X] [--root PATH]
       python3 -I queue/item.py <release> --move Q<n> Open|Later|Dropped|Autofix
       python3 -I queue/item.py <release> --fact Q<n> "<text>"

Under an exclusive lock on <release folder>/.ids.lock, re-reading the files right before the
write (queue.md is a kanban board the owner may drag in the editor; lib/board.py edits it in place
and leaves every other byte as it was):

- D: under the last "## Round" heading of decisions.md: the heading, the --bullet line if
  given, then "- Source: Q<n>" if --source is given. With --source, card Q<n> moves to the end
  of Decided, unticked, with "#D<n>" at the end of its title line; a card already in Decided
  keeps the highest decision number.
- Q: a tagless card "- [ ] **Q<n>** <title>" at the end of Open, the --bullet text as its
  first fact.
- --move: card Q<n> with its sub-bullets to the end of that lane (Decided only through D
  --source; a card leaving Decided loses its #D and #E tags). --fact: one tab-indented fact
  sub-bullet at the end of card Q<n>.

Every call then syncs the Decided cards with the tag lines of decisions.md (lib/board.py sync:
the tick and the #E<n> tag), so a "[Done]" the lead wrote by hand reaches the board on the next call.

queue.md is created from templates/queue.md when missing. Commits the files it wrote and
prints the id alone, e.g. Q11.
"""
import argparse
import datetime
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
ROUND_RE = re.compile(r"^## Round\b")
die, git = C.die, C.git


def highest(paths, kind):
    head = re.compile(r"^#{2,3}\s+" + kind + r"(\d+)\b")
    top = 0
    for p in paths:
        if not p.is_file():
            continue
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            m = head.match(line)
            if m:
                top = max(top, int(m.group(1)))
    return top


def under_last_round(text, block, today):
    """Insert block at the end of the last '## Round' section; add Round 1 when none."""
    lines = text.rstrip("\n").split("\n") if text.strip() else []
    rounds = [i for i, l in enumerate(lines) if ROUND_RE.match(l)]
    if not rounds:
        lines += ["", f"## Round 1: discussion, {today}"]
        end = len(lines)
    else:
        end = len(lines)
        for i in range(rounds[-1] + 1, len(lines)):
            if lines[i].startswith("## "):
                end = i
                break
    head, tail = lines[:end], lines[end:]
    while head and not head[-1].strip():
        head.pop()
    out = head + [""] + block
    if tail:
        out += [""] + tail
    return "\n".join(out).lstrip("\n") + "\n"


def exclude_lock(root):
    """Keep .ids.lock out of git status: one line in the repo's info/exclude."""
    r = subprocess.run(["git", "-C", str(root), "rev-parse", "--git-path", "info/exclude"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return
    path = Path(r.stdout.strip())
    if not path.is_absolute():
        path = root / path
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    if ".ids.lock" not in text.split("\n"):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + ("" if not text or text.endswith("\n") else "\n") + ".ids.lock\n",
                        encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(
        usage='queue/item.py <release> D|Q "<title>" [--source Q<n>] [--bullet "<text>"] | '
              '<release> --move Q<n> Open|Later|Dropped|Autofix | <release> --fact Q<n> "<text>" '
              '[--owner X] [--root PATH]'
    )
    ap.add_argument("release")
    ap.add_argument("kind", nargs="?")
    ap.add_argument("title", nargs="?")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    ap.add_argument("--source")
    ap.add_argument("--bullet")
    ap.add_argument("--move", nargs=2, metavar=("Q<n>", "LANE"))
    ap.add_argument("--fact", nargs=2, metavar=("Q<n>", "TEXT"))
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    card_op = a.move or a.fact
    if a.move and a.fact:
        die("--move and --fact are separate calls")
    if card_op:
        if a.kind or a.title or a.source or a.bullet:
            die("--move and --fact take only a Q id and a lane or a text")
        if not SOURCE_RE.match(card_op[0]):
            die(f"bad id '{card_op[0]}', expected like Q3")
        if a.move and a.move[1] not in ("Open", "Later", "Dropped", "Autofix"):
            die(f"bad lane '{a.move[1]}': Open, Later, Dropped or Autofix (Decided only through D --source)")
    else:
        if a.kind not in ("D", "Q"):
            die(f"bad kind '{a.kind}': the kinds are D and Q")
        if a.kind == "Q" and a.source:
            die("--source is for a D item")
        if not (a.title or "").strip():
            die("empty title")
        if a.source and not SOURCE_RE.match(a.source):
            die(f"bad source '{a.source}', expected like Q3")
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
    today = datetime.date.today().isoformat()

    with open(folder / ".ids.lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        exclude_lock(root)
        if not queue.is_file():
            tpl = C.TEMPLATES / "queue.md"
            queue.write_text(tpl.read_text(encoding="utf-8"), encoding="utf-8")
        board = queue.read_text(encoding="utf-8")
        new = None
        written = []

        if card_op:
            num = int(card_op[0][1:])
            if bd.find(board, num) is None:
                die(f"{card_op[0]} is not in {queue}")
            ident = card_op[0]
            if a.move:
                new = bd.move(board, num, a.move[1])
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
            target = folder / "decisions.md"
            if not target.is_file():
                die(f"missing: {target}")
            card = bd.find(board, int(a.source[1:])) if a.source else None
            if a.source and card is None:
                die(f"{a.source} is not in {queue}")
            ident = f"D{highest([target], 'D') + 1}"
            bullet = (a.bullet if a.bullet.startswith("- ") else f"- {a.bullet}") if a.bullet else None
            block = [f"### {ident} {title}", ""] + ([bullet] if bullet else [])
            if a.source:
                block.append(f"- Source: {a.source}")
            target.write_text(under_last_round(target.read_text(encoding="utf-8"), block, today),
                              encoding="utf-8")
            written.append(target)
            if card is not None:
                old = card["d"] if card["lane"] == "Decided" else None
                keep = max(old or 0, int(ident[1:]))
                new = bd.move(board, card["num"], "Decided", keep)
                if old and old > int(ident[1:]):
                    print(f"{a.source} keeps #D{old}", file=sys.stderr)
            subject = f"{ident} {title}"

        synced, changed = bd.sync(board if new is None else new, bd.decision_tags(own, folder))
        if changed:
            print(f"synced with decisions.md: {', '.join(f'Q{n}' for n in changed)}", file=sys.stderr)
        if new is not None or changed:
            bd.write(queue, synced)
            written.append(queue)

        paths = [str(p) for p in written]
        git(root, "add", "--", *paths)
        git(root, "commit", "-q", "-m", f"docs(plan): {a.release} {subject}", "--only", "--", *paths)
        fcntl.flock(lock, fcntl.LOCK_UN)
    print(ident)


if __name__ == "__main__":
    main()
