#!/usr/bin/env python3
"""Move the queue of a release from the kanban board to item files: format 2.0 to 2.1.

Usage: python3 -I migrate/v2.0-v2.1/format.py <release> [--check] [--owner X] [--root PATH]

Its first line, on stderr, tells the session that runs it to read the skill again: the queue
commands of a release of format 2.1 write item files, not board cards.

In the release folder:
- Each card of the board queue.md becomes one item file queue/Q<n>-<slug>.md (lib/queue.py):
  the lane gives "status" (Open, Decided, Later, Dropped, Autofix to open, decided, later,
  dropped, autofix), the tag "#D<n>" of a card in Decided gives "decision: D<n>" (the highest
  one when it has two), the title after "**Q<n>**" gives
  "# Q<n>. <title>", and every line under the card, nested bullets too, goes under "## Notes"
  one indent level less, so each bullet keeps its depth. The tick and the tag "#E<n>" are
  dropped: the scripts read both from decisions.md. A "#D<n>" tag of a card outside Decided,
  and a lower second "#D<n>" tag, are dropped too, with one printed line each: an item that is
  not decided has no "decision" line. No "## Details", no "## Options:", no "option": the lead
  writes them when it writes an item out.
- queue.md becomes the plain list of the item files (lib/queue.py write_list).
- "format" in status/data/status.json becomes "2.1", written last; then the page data
  (status.data.js, queue.data.js) and the page status/index.html (sprints/swimlanes.py).
- One commit of queue.md, queue/ and status.json: "docs(plan): <release> queue moved to item
  files". decisions.md, the specs, the trackers and the statuses are not touched.

Prints one line per item file and the counts: cards read, item files written, bullets read,
bullets written. A difference stops it before the commit. --check prints the same and writes
nothing.

Refuses, writing nothing: a release that is not in format 2.0 (for 1.0 it names
migrate/v1.0-v2.0); a queue.md with uncommitted changes; a queue/ folder that already exists (a
second run); a queue.md that is no board, or that holds a line no card holds, a card in a lane
that is not one of the five, or two cards with one number.
"""
import argparse
import contextlib
import fcntl
import importlib.util
import io
import json
import re
import subprocess
import sys
from pathlib import Path


def _common():
    name = "expedition_lib_common"
    if name not in sys.modules:
        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent.parent.parent / "lib" / "common.py")
        sys.modules[name] = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sys.modules[name])
    return sys.modules[name]


C = _common()
FROM, TO = (2, 0), "2.1"
REREAD = ("The expedition skill keeps the queue of a release of format 2.1 in item files: read SKILL.md "
          "and scripts/migrate/v2.0-v2.1/README.md again before the next queue command.")
BULLET_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s")
RULE_RE = re.compile(r"^\s*(\*\*\*|---|___)\s*$")


def bullets(lines):
    return sum(1 for l in lines if BULLET_RE.match(l))


def plural(n, word):
    return f"{n} {word}" + ("" if n == 1 else "s")


def notes_lines(subs):
    """The lines under a card, one indent level less: one TAB, or the spaces of the first line
    indented with spaces. A blank line stays blank."""
    unit = next((len(l) - len(l.lstrip(" ")) for l in subs if l.strip() and l.startswith(" ")), 0)
    out = []
    for l in subs:
        if not l.strip():
            out.append("")
        elif l.startswith("\t"):
            out.append(l[1:])
        else:
            cut = min(unit, len(l) - len(l.lstrip(" ")))
            out.append(l[cut:])
    while out and not out[0]:
        out.pop(0)
    while out and not out[-1]:
        out.pop()
    return out


def decision_of(card, status):
    """The decision id the item keeps ("D<n>" or None), and one line per "#D<n>" tag dropped."""
    nums = [int(t[1:]) for t in card["tags"] if re.fullmatch(r"D\d+", t)]
    keep = max(nums) if nums and status == "decided" else None
    dropped = [n for n in nums if n != keep]
    why = "a lower second tag of the card" if keep else f"the card is in {card['lane']}, not in Decided"
    return (f"D{keep}" if keep else None), [f"Q{card['num']}: #D{n} dropped, {why}" for n in dropped]


def item_text(q, card, status):
    """The item file of one card."""
    text = q.new_item(card["num"], card["title"])
    lines = notes_lines(card["subs"])
    if lines:
        text += "\n" + "\n".join(lines) + "\n"
    return q.set_front(text, status=status, decision=decision_of(card, status)[0])


def read_board(bd, q, folder):
    """[(card, status)] of queue.md in file order; dies with one line on what it cannot carry
    over word for word."""
    path = folder / C.QUEUE_MD
    if not path.is_file():
        return []
    text = C.read(path)
    # C.find_folder refuses a queue.md that is no board, or has old-form cards, before the lock;
    # this re-check under the lock catches a second migration that ran while this one waited
    if not bd.is_board(text):
        C.die(f"{path} is no kanban board: nothing to move")
    board = bd.parse(text)
    if board["stray"]:
        i, line = board["stray"][0]
        C.die(f"{path}:{i + 1} is a list item with no **Q<n>**, it would be lost: make it a card or remove it, then run again")
    lines = text.split("\n")
    stop = bd._body_end(lines)
    held = {l["line"] for l in board["lanes"]}
    for c in board["cards"]:
        held.update(range(c["line"], c["end"]))
    start = 0
    if lines and lines[0].strip() == "---":
        start = next((i for i in range(1, stop) if lines[i].strip() == "---"), 0) + 1
    # the settings block runs to its closing "%%"; a line after it is no card either
    close = next((i for i in range(stop + 1, len(lines)) if lines[i].strip() == "%%"), len(lines))
    for i in list(range(start, stop)) + list(range(close + 1, len(lines))):
        if i not in held and lines[i].strip() and not RULE_RE.match(lines[i]) and not bd.MARKER_RE.match(lines[i]):
            C.die(f"{path}:{i + 1} is a line no card holds, it would be lost: move it into a card or remove it, then run again")
    out, seen = [], set()
    for c in board["cards"]:
        status = q.lane_status(c["lane"])
        if status is None:
            C.die(f"{path}: Q{c['num']} is in the lane '{c['lane']}', not one of {', '.join(q.LANES)}")
        if c["num"] in seen:
            C.die(f"{path}: two cards are Q{c['num']}: give one a free number, then run again")
        seen.add(c["num"])
        out.append((c, status))
    return out


def written_counts(q, texts):
    """(item files, bullets) of item texts, as lib/queue.py reads them back."""
    return len(texts), sum(bullets(q.notes(t).split("\n")) for t in texts)


def main():
    ap = argparse.ArgumentParser(usage="migrate/v2.0-v2.1/format.py <release> [--check] [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("--check", action="store_true", help="print what it would write and the counts; write nothing")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    print(REREAD, file=sys.stderr)
    if not C.RELEASE_RE.match(a.release):
        C.die(f"bad release '{a.release}', expected like v0.9.x")
    root, folder = C.find_folder(a.release, a.owner, a.root)
    st, q, bd = C.load("lib/status"), C.load("lib/queue"), C.load("lib/board")
    fmt = st.release_format(folder)
    if q.version(fmt) < FROM:
        C.die(f"{a.release} is in format {fmt}: run migrate/v1.0-v2.0/format.py first (scripts/migrate/v1.0-v2.0/README.md)")
    if q.version(fmt) != FROM:
        C.die(f"{a.release} is in format {fmt}, not 2.0: its queue is in item files already; nothing to change")
    if (folder / q.QUEUE_DIR).exists():
        C.die(f"{folder / q.QUEUE_DIR} exists already: nothing written; remove it, or revert the migration commit")
    real = folder.resolve()
    git = lambda *args: subprocess.run(["git", "-C", str(real), *args], capture_output=True, text=True)
    r = git("status", "--porcelain", "--", C.QUEUE_MD)
    if r.returncode:
        C.die(f"{folder} is not in a git repository: {(r.stderr or r.stdout).strip()}")
    if r.stdout.strip():
        C.die(f"{folder / C.QUEUE_MD} has uncommitted changes: commit them first")

    lock = None if a.check else open(C.lock_file(folder), "a")
    if lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
    cards = read_board(bd, q, folder)
    files = {}
    for c, status in cards:
        p = q.item_path(folder, c["num"], c["title"])
        files[p] = item_text(q, c, status)
        decision, dropped = decision_of(c, status)
        rel = p.relative_to(folder).as_posix()
        print(f"{'would write ' if a.check else ''}{rel}: {status}"
              + (f", {decision}" if decision else "") + f", {plural(bullets(c['subs']), 'bullet')}")
        for line in dropped:
            print(line)
    read_n = (len(cards), sum(bullets(c["subs"]) for c, _ in cards))
    wrote_n = written_counts(q, list(files.values()))
    counts = lambda w: f"cards read {read_n[0]}, item files written {w[0]}; bullets read {read_n[1]}, bullets written {w[1]}"
    if a.check:
        print(f"would write {C.QUEUE_MD}: a list of {len(files)} lines")
        print(f"would set format {TO} in {st.FILE}")
        print(counts(wrote_n))
        if read_n != wrote_n:
            C.die("the counts differ: the migration would stop before its commit")
        print("check; nothing written")
        return
    if read_n != wrote_n:
        C.die(f"{counts(wrote_n)}: the counts differ; nothing written")
    for p, text in files.items():
        q.write_item(p, text)
    q.write_list(folder)
    data = st.load(folder)
    data["format"] = TO
    # the status file last: with it the release is in the new form
    st.write_json(st.path(folder), json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    with contextlib.redirect_stdout(io.StringIO()):
        C.load("sprints/swimlanes").write(folder, a.release, quiet=True)
    on_disk = [C.read(p) for p in q.item_files(folder).values()]
    disk_n = written_counts(q, on_disk)
    print(counts(disk_n))
    if read_n != disk_n or not q.list_in_step(folder):
        C.die("the counts differ, or queue.md is out of step: nothing committed; "
              f"`git checkout -- {C.QUEUE_MD} {st.FILE}` and remove {q.QUEUE_DIR}/ in the release folder")
    C.commit(root, [folder / C.QUEUE_MD, folder / q.QUEUE_DIR, st.path(folder)],
             f"docs(plan): {a.release} queue moved to item files")
    q.write_data(folder)  # again after the commit: the "changed" time of each item is its commit
    fcntl.flock(lock, fcntl.LOCK_UN)
    lock.close()
    print("committed")


if __name__ == "__main__":
    main()
