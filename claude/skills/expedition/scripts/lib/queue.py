#!/usr/bin/env python3
"""The queue of a release of format 2.1 and higher: one file per item, queue/Q<n>-<slug>.md, and
queue.md, a plain list of the item files that the scripts write. Library, no CLI. A release of a
lower format keeps queue.md as a kanban board (lib/board.py); item_form() tells the two apart.

Item file (templates/queue-item.md):

    ---
    status: open                  open, decided, later, dropped or autofix
    decision: D<n>                a decided item only
    option: <n>                   the picked option, when one was given
    ---
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
recommended). changed is the time of the last commit that changed the "status:" line of the
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
QUEUE_DIR = C.QUEUE_DIR
DATA = "status/data/queue.data.js"
STATUSES = ("open", "decided", "later", "dropped", "autofix")
LANES = ("Open", "Decided", "Later", "Dropped", "Autofix")  # the lane words of the commands, in this order
FRONT_KEYS = ("status", "decision", "option")
FILE_RE = re.compile(r"^Q(\d+)-.*\.md$")
TITLE_RE = re.compile(r"^# Q(\d+)\.\s+(.*?)\s*$")
LIST_RE = re.compile(r"^- \[Q(\d+)\]\(")
OPTION_RE = re.compile(r"^(\d+)\.\s+(.*)$")
FRONT_RE = re.compile(r"\A---\n(.*?\n)?---\n", re.S)


def version(text):
    return tuple(int(x) for x in re.findall(r"\d+", text or "")) or (1, 0)


def item_form(folder):
    """True when the release keeps its queue in item files: its "format" (status/data/status.json)
    is 2.1 or higher. The skill's own version plays no part."""
    return version(C.load("lib/status").release_format(folder)) >= ITEM_FORMAT


def commit_paths(folder):
    """The queue paths a commit of the release names: queue.md, and the queue/ folder in the
    item form."""
    folder = Path(folder)
    return [folder / C.QUEUE_MD] + ([folder / QUEUE_DIR] if item_form(folder) else [])


def lane_status(lane):
    """The status word of a lane word of the commands ("Later" -> "later"); None when unknown."""
    return lane.lower() if lane.lower() in STATUSES else None


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
    """The front matter block: status, decision and option first in that order, then any other key."""
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
    """{num, title, status, decision, option, path, text} of an item file; num and title from its
    "# Q<n>." line (None when it has none)."""
    text = C.read(path)
    head = next((TITLE_RE.match(l) for l in body(text).split("\n") if TITLE_RE.match(l)), None)
    f = front(text)
    return {"num": int(head.group(1)) if head else None, "title": head.group(2) if head else "",
            "status": f.get("status", ""), "decision": f.get("decision", ""), "option": f.get("option", ""),
            "path": Path(path), "text": text}


def new_item(num, title, bullet=None):
    """The text of a new item file: front matter, title and Notes."""
    notes = f"\n{note_line(bullet)}\n" if bullet else ""
    return f"---\nstatus: open\n---\n# Q{num}. {title}\n\n## Notes\n{notes}"


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
    out = []
    for it in items(folder):
        e = {"id": f"Q{it['file_num']}", "number": it["file_num"], "title": it["title"],
             "status": it["status"] or "open", "decision": it["decision"], "option": it["option"],
             "file": it["path"].relative_to(folder).as_posix()}
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
    Returns the path written, or None."""
    if not item_form(folder):
        return None
    p = Path(folder) / DATA
    C.load("lib/status").write_json(p, f"window.QUEUE_DATA = {json.dumps(data(folder), ensure_ascii=False)};\n")
    return p
