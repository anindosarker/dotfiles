#!/usr/bin/env python3
"""The queue of a release of format 2.1 and higher: one file per item, queue/Q<n>-<slug>.md, and
queue.md, a plain list of the item files that the scripts write. Library, no CLI. A release of a
lower format keeps queue.md as a kanban board (lib/board.py); item_form() tells the two apart.

Item file (templates/queue-item.md), format 2.1:

    ---
    status: open                  open, decided, later, dropped or autofix
    decision: D<n>                a decided item only
    option: <n>                   the picked option, when one was given
    ---

A release of format 2.2 and higher (status_form()) stores the words of format 2.2 in the same
line: to-do, blocked, done, backlog or archived (STATUSES_22). The map: open is to-do, decided is
done with a decision line, autofix is done with none, later is backlog, dropped is archived;
blocked has no word in format 2.1. A command takes the words of both formats and stores the word
of the release's format (move_status(), select()). A 2.2 file with no status line counts as to-do.
A closed item of format 2.2 (done or archived) also has "decider: you|lead|agent", the one who
made the call (DECIDERS); it is removed when the item is opened again. A done item closed by a
decision has the decision line and decider you or lead (or agent); a done item with no decision
has decider agent; an archived item has you or lead (CLOSERS).

"depends_on: Q14, Q15" (format 2.2) names the items an item waits for; the line is absent when
there are none. blocked is never set by hand: the blocked check (settle()) makes an item that is
to-do or blocked "blocked" while an item it names is not done, and "to-do" when every named item
is done; an item in another status keeps it. It runs on every write of an item, of queue.md and
of the page data (write_data(), which lib/status.py runs on every save, so sprints/refresh.py
also runs it after a hand edit).
    # Q<n>. <title>

    ## Notes

    - <the owner's remark, a first finding>

    ## Details                    written by the lead, absent until then

    ## Options:                   written by the lead: "1. Recommended: ...", "2. ..."

This library writes the front matter, the title and the Notes bullets only. It reads Details and
Options and never writes or reorders them: a status change rewrites the front matter block and
leaves every other byte of the file as it was. <slug> is made from the title at filing, as a task
file's slug is (lib/specs.py file_slug), and never changes after.

queue.md (templates/queue-list.md): "# Queue, <release>", then one line per item file in number
order, "- [Q<n>](queue/Q<n>-<slug>.md): <title>". write_list() writes the whole file after each
change of an item; nobody edits it by hand.

status/data/queue.data.js, "window.QUEUE_DATA = {...};", is the data of the Queue view of the
task board (board/task-board.html): release, format, updated, root, and items with id, number,
title, status, decision, option, file, changed, notes, details and options (key, title, body,
recommended). Format 2.2 adds decider ("" when none) and depends_on (a list of ids, [] when
none) after option. changed is the time of the last commit that changed the "status:" line of the
file, left out while the file is not committed. It is a render, git-ignored with the rest of
status/data/, written only for a release of format 2.1 and higher.

The callers hold the .ids.lock lock (lib/common.py lock_file) around every write, as the board
writes are.
"""
import datetime
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path


def _common():
    name = "expedition_lib_common"
    if name not in sys.modules:
        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent / "common.py")
        sys.modules[name] = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sys.modules[name])
    return sys.modules[name]


C = _common()
ITEM_FORMAT = (2, 1)
STATUS_FORMAT = (2, 2)  # the status words of format 2.2 (STATUSES_22)
QUEUE_DIR = C.QUEUE_DIR
DATA = "status/data/queue.data.js"
STATUSES = ("open", "decided", "later", "dropped", "autofix")  # format 2.1
STATUSES_22 = ("to-do", "blocked", "done", "backlog", "archived")  # format 2.2 and higher
# A word of a command of either format: (the status of format 2.1, the status of format 2.2).
MOVES = {"open": ("open", "to-do"), "to-do": ("open", "to-do"), "later": ("later", "backlog"),
         "backlog": ("later", "backlog"), "dropped": ("dropped", "archived"), "archived": ("dropped", "archived"),
         "autofix": ("autofix", "done"), "done": ("autofix", "done")}
# The words queue/list.py takes besides LANES: the six status words; in progress is no queue status.
WORDS_22 = ("to-do", "in progress", "blocked", "done", "backlog", "archived")
LANES = ("Open", "Decided", "Later", "Dropped", "Autofix")  # the lane words of the commands, in this order
FRONT_KEYS = ("status", "decision", "option", "decider", "depends_on")
DECIDERS = ("you", "lead", "agent")
CLOSERS = {"archived": ("you", "lead"), "done": ("agent",)}  # the deciders of a --move to that status
ID_RE = re.compile(r"^Q(\d+)$")
FILE_RE = re.compile(r"^Q(\d+)-.*\.md$")
TITLE_RE = re.compile(r"^# Q(\d+)\.\s+(.*?)\s*$")
LIST_RE = re.compile(r"^- \[Q(\d+)\]\(")
OPTION_RE = re.compile(r"^(\d+)\.\s+(.*)$")
FRONT_RE = re.compile(r"\A---\r?\n(.*?\r?\n)?---\r?\n", re.S)


def version(text):
    return tuple(int(x) for x in re.findall(r"\d+", text or "")) or (1, 0)


def item_form(folder):
    """True when the release keeps its queue in item files: its "format" (status/data/status.json)
    is 2.1 or higher. The skill's own version plays no part."""
    return version(C.load("lib/status").release_format(folder)) >= ITEM_FORMAT


def status_form(folder):
    """True when the release stores the status words of format 2.2: its "format" is 2.2 or
    higher, whatever version the skill's own SKILL.md states."""
    return version(C.load("lib/status").release_format(folder)) >= STATUS_FORMAT


def commit_paths(folder):
    """The queue paths a commit of the release names: queue.md, and the queue/ folder in the
    item form."""
    folder = Path(folder)
    return [folder / C.QUEUE_MD] + ([folder / QUEUE_DIR] if item_form(folder) else [])


def status_of(it, new=False):
    """The status an item counts with on the page, in queue/list.py and in queue/next.py: its
    "status" line, or "open" ("to-do" in format 2.2, new=True) when the file has none
    (status/report.py still reports the file)."""
    return it["status"] or ("to-do" if new else "open")


def lane_status(lane):
    """The status word of a lane word of the commands ("Later" -> "later"); None when unknown."""
    return lane.lower() if lane.lower() in STATUSES else None


def move_status(word, new=False):
    """The status queue/item.py --move stores for word, a lane word (Open, Later, Dropped,
    Autofix) or a word of format 2.2 (to-do, backlog, archived, done), in any case: the word of
    format 2.1, or of format 2.2 when new. None for any other word."""
    pair = MOVES.get(word.lower())
    return pair[1 if new else 0] if pair else None


def select(its, word, new=False, status=None):
    """The items of its that the word of queue/list.py names, in their order; None for an unknown
    word. word: a lane word (Open, Decided, Later, Dropped, Autofix) or one of the six status
    words, in any case. Format 2.1: each word names the status it maps to (done: decided and
    autofix; blocked and in progress: none). Format 2.2 (new): Open is to-do and blocked, Decided
    is done with a decision line, Autofix is done without one, Later is backlog, Dropped is
    archived; the six words select by status alone. status(it) gives the status an item counts
    with (default status_of)."""
    w = word.lower()
    st = status or (lambda it: status_of(it, new))
    if new:
        want = {"open": lambda it: st(it) in ("to-do", "blocked"),
                "decided": lambda it: st(it) == "done" and bool(it["decision"]),
                "autofix": lambda it: st(it) == "done" and not it["decision"],
                "later": lambda it: st(it) == "backlog", "dropped": lambda it: st(it) == "archived"}.get(w)
        if want is None and w in WORDS_22:
            want = lambda it: st(it) == w
    else:
        words = {"to-do": ("open",), "backlog": ("later",), "archived": ("dropped",),
                 "done": ("decided", "autofix"), "blocked": (), "in progress": ()}.get(w)
        if words is None and w in STATUSES:
            words = (w,)
        want = None if words is None else (lambda it: st(it) in words)
    return None if want is None else [it for it in its if want(it)]


# --- one item file ---

def front(text):
    """The front matter of an item file as an ordered dict of its "key: value" lines."""
    m = FRONT_RE.match(text)
    out = {}
    for line in (m.group(1) or "").splitlines() if m else []:
        k, sep, v = line.partition(":")
        if sep and k.strip():
            out[k.strip()] = v.strip()
    return out


def body(text):
    """The text after the front matter."""
    m = FRONT_RE.match(text)
    return text[m.end():] if m else text


def front_text(fields):
    """The front matter block: the keys of FRONT_KEYS first in that order, then any other key."""
    keys = [k for k in FRONT_KEYS if fields.get(k)] + [k for k in fields if k not in FRONT_KEYS and fields[k] != ""]
    return "---\n" + "".join(f"{k}: {fields[k]}\n" for k in keys) + "---\n"


def set_front(text, **fields):
    """The item text with the front matter keys set (a value None or "" removes the line). Only the
    front matter block is rewritten; the rest of the file stays byte for byte."""
    have = front(text)
    for k, v in fields.items():
        if v is None or v == "":
            have.pop(k, None)
        else:
            have[k] = str(v)
    return front_text(have) + body(text)


def sections(text):
    """{name: text} of the "## " sections of an item: the name in lower case without a trailing
    ":", the text stripped. A heading inside a code fence is no section."""
    out, name, buf = {}, None, []
    for line, inside in C.fence_flags(body(text)):
        if not inside and line.startswith("## "):
            if name is not None:
                out[name] = "\n".join(buf).strip()
            name, buf = line[3:].strip().rstrip(":").strip().lower(), []
        elif name is not None:
            buf.append(line)
    if name is not None:
        out[name] = "\n".join(buf).strip()
    return out


def dedent(lines):
    ind = [len(l) - len(l.lstrip()) for l in lines if l.strip()]
    cut = min(ind) if ind else 0
    return "\n".join(l[cut:] for l in lines).strip()


def options(text):
    """The options of an item: [{key, title, body, recommended}], one per top-level "<n>." line of
    "## Options:"; the "Recommended:" prefix is removed from the title and its next letter put in
    upper case; body is the indented lines below it, dedented."""
    out = []
    for line in sections(text).get("options", "").split("\n"):
        m = OPTION_RE.match(line)
        if m:
            rec = re.match(r"(?i)^Recommended:\s*", m.group(2))
            title = m.group(2)
            if rec:
                rest = title[rec.end():]
                title = rest[:1].upper() + rest[1:]
            out.append({"key": m.group(1), "title": title, "body": [], "recommended": bool(rec)})
        elif out:
            out[-1]["body"].append(line)
    for o in out:
        o["body"] = dedent(o["body"])
    return out


def read_item(path):
    """{num, title, status, decision, option, decider, depends_on, path, text} of an item file;
    num and title from its "# Q<n>." line (None when it has none); depends_on the list of the ids
    of its "depends_on" line, [] when none."""
    text = C.read(path)
    head = next((TITLE_RE.match(l) for l in body(text).split("\n") if TITLE_RE.match(l)), None)
    f = front(text)
    return {"num": int(head.group(1)) if head else None, "title": head.group(2) if head else "",
            "status": f.get("status", ""), "decision": f.get("decision", ""), "option": f.get("option", ""),
            "decider": f.get("decider", ""), "depends_on": split_ids(f.get("depends_on", "")),
            "path": Path(path), "text": text}


def split_ids(text):
    """The ids of a "Q14, Q15" text, in order, each once; blank parts left out."""
    return list(dict.fromkeys(t.strip() for t in (text or "").split(",") if t.strip()))


# --- depends_on and the blocked check (format 2.2) ---

def waits_for(it, its):
    """The ids of the depends_on line of it that are not done (an id with no item file counts as
    not done), in the order of the line."""
    done = {f"Q{x['file_num']}" for x in its if status_of(x, True) == "done"}
    return [d for d in it["depends_on"] if d not in done]


def effective(it, its):
    """The status an item of format 2.2 has by the blocked check: blocked or to-do for an item
    that is to-do or blocked (or has no status line), from what it waits for; else its status."""
    st = status_of(it, True)
    if st not in ("to-do", "blocked"):
        return st
    return "blocked" if waits_for(it, its) else "to-do"


def settle(folder):
    """The blocked check: write the status of each item of a release of format 2.2 whose stored
    status differs from effective(); a file with no status line that is to-do stays as it is.
    Returns the paths written; [] below format 2.2."""
    if not status_form(folder):
        return []
    its = items(folder)
    out = []
    for it in its:
        want = effective(it, its)
        if want != status_of(it, True):
            write_item(it["path"], set_front(it["text"], status=want))
            out.append(it["path"])
    return out


def check_depends(folder, num, ids):
    """The refusal of "--depends Q<num> <ids>", one line, or None: an id that is not like Q14
    (a decision id among them), an id with no item file, the item itself, a ring of items that
    wait for each other."""
    bad = [i for i in ids if not ID_RE.match(i)]
    if bad:
        return f"bad id {', '.join(bad)}: depends_on names queue item ids only, like Q14"
    files = item_files(folder)
    missing = [i for i in ids if int(i[1:]) not in files]
    if missing:
        return f"no item file for {', '.join(missing)} in {Path(folder) / QUEUE_DIR}"
    if f"Q{num}" in ids:
        return f"Q{num} cannot wait for itself"
    graph = {f"Q{it['file_num']}": it["depends_on"] for it in items(folder)}
    graph[f"Q{num}"] = ids
    path, seen = [], set()

    def ring(node):
        if node == f"Q{num}" and path:
            return True
        if node in seen:
            return False
        seen.add(node)
        path.append(node)
        found = any(ring(n) for n in graph.get(node, []))
        if not found:
            path.pop()
        return found

    if any(ring(i) for i in ids):
        return f"a ring: Q{num} waits for {' which waits for '.join(path)}, which waits for Q{num}"
    return None


def new_item(num, title, bullet=None, new=False):
    """The text of a new item file: front matter, title and Notes. new: format 2.2 (to-do)."""
    notes = f"\n{note_line(bullet)}\n" if bullet else ""
    return f"---\nstatus: {'to-do' if new else 'open'}\n---\n# Q{num}. {title}\n\n## Notes\n{notes}"


def note_line(text):
    text = text.strip()
    return "- " + (text[2:] if text.startswith("- ") else text)


def add_note(text, note):
    """The item text with one bullet added at the end of "## Notes" (after its last non-blank
    line); every other line stays as it was. A file without the section gets it at the end."""
    lines = text.split("\n")
    offset = text[:len(text) - len(body(text))].count("\n")
    flags = list(C.fence_flags("\n".join(lines[offset:])))
    head = next((offset + i for i, (l, inside) in enumerate(flags)
                 if not inside and l.rstrip().rstrip(":").strip() == "## Notes"), None)
    if head is None:
        tail = text.rstrip("\n")
        return tail + "\n\n## Notes\n\n" + note_line(note) + "\n"
    end = next((offset + i for i, (l, inside) in enumerate(flags)
                if offset + i > head and not inside and l.startswith("## ")), len(lines))
    last = head
    for i in range(head + 1, end):
        if lines[i].strip():
            last = i
    add = [note_line(note)]
    if last == head:
        add = [""] + add
    if end < len(lines) and last + 1 == end:
        add.append("")
    lines[last + 1:last + 1] = add
    out = "\n".join(lines)
    return out if out.endswith("\n") else out + "\n"


def notes(text):
    """The Notes section of an item, as written."""
    return sections(text).get("notes", "")


# --- the queue folder ---

def item_files(folder):
    """{num: path} of the item files, by the number in the file name."""
    d = Path(folder) / QUEUE_DIR
    out = {}
    for p in sorted(d.glob("Q*.md")) if d.is_dir() else []:
        m = FILE_RE.match(p.name)
        if m:
            out.setdefault(int(m.group(1)), p)
    return out


def items(folder):
    """Every item file read, in number order (read_item, with num the file name's number when the
    title has none)."""
    out = []
    for n, p in sorted(item_files(folder).items()):
        it = read_item(p)
        it["file_num"] = n
        out.append(it)
    return out


def find(folder, num):
    """The item with number num, or None."""
    p = item_files(folder).get(num)
    return read_item(p) if p else None


def listed(folder):
    """The Q numbers that queue.md lists."""
    q = Path(folder) / C.QUEUE_MD
    return {int(m.group(1)) for l in (C.read(q).split("\n") if q.is_file() else []) if (m := LIST_RE.match(l))}


def next_number(folder):
    """The next free Q number: one above every item file and every line of queue.md."""
    return max([0, *item_files(folder), *listed(folder)]) + 1


def item_path(folder, num, title):
    slug = C.load("lib/specs").file_slug(title) or "item"
    return Path(folder) / QUEUE_DIR / f"Q{num}-{slug}.md"


def release_of(folder):
    return Path(folder).parent.name


def render_list(release, its):
    """The text of queue.md for the items its (each with num, title and path)."""
    lines = [f"- [Q{it['file_num']}]({QUEUE_DIR}/{it['path'].name}): {it['title']}" for it in its]
    return f"# Queue, {release}\n" + ("\n" + "\n".join(lines) + "\n" if lines else "")


def write_list(folder):
    """Write queue.md from the item files; returns its path."""
    p = Path(folder) / C.QUEUE_MD
    p.write_text(render_list(release_of(folder), items(folder)), encoding="utf-8")
    return p


def list_in_step(folder):
    """True when queue.md is what write_list() would write."""
    p = Path(folder) / C.QUEUE_MD
    return p.is_file() and C.read(p) == render_list(release_of(folder), items(folder))


def write_item(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# --- the page data ---

def changed(folder, path):
    """Time of the last commit that changed the "status:" line of the file; "" when none."""
    r = subprocess.run(["git", "-C", str(folder), "log", "-1", "-G", "^status:", "--format=%ad",
                        "--date=format:%Y-%m-%d %H:%M", "--", str(Path(path).relative_to(folder))],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def data(folder):
    """The queue data of the page, with root."""
    folder = Path(folder)
    new = status_form(folder)
    its = items(folder)
    out = []
    for it in its:
        e = {"id": f"Q{it['file_num']}", "number": it["file_num"], "title": it["title"],
             "status": effective(it, its) if new else status_of(it), "decision": it["decision"], "option": it["option"],
             "file": it["path"].relative_to(folder).as_posix()}
        if new:
            e["decider"] = it["decider"]
            e["depends_on"] = it["depends_on"]
        when = changed(folder, it["path"])
        if when:
            e["changed"] = when
        s = sections(it["text"])
        e.update(notes=s.get("notes", ""), details=s.get("details", ""), options=options(it["text"]))
        out.append(e)
    return {"release": release_of(folder), "format": C.load("lib/status").release_format(folder),
            "updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "root": str(folder), "items": out}


def write_data(folder):
    """status/data/queue.data.js of a release in the item form; nothing for a lower format.
    Format 2.2: first the blocked check (settle) and queue.md when it is not in step. Returns the
    path written, or None."""
    if not item_form(folder):
        return None
    if status_form(folder):
        settle(folder)
        if not list_in_step(folder):
            write_list(folder)
    p = Path(folder) / DATA
    C.load("lib/status").write_json(p, f"window.QUEUE_DATA = {json.dumps(data(folder), ensure_ascii=False)};\n")
    return p
