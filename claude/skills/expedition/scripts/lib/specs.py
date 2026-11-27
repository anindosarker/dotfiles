#!/usr/bin/env python3
"""Edits of a spec file, for plan/new_spec.py, plan/milestone.py and plan/task.py. Library, no
CLI. The reader of both spec forms is lib/ownership.py read_spec; statuses are lib/status.py.

A new-form spec has the sections "### 1.6 Modules", "### 2.1 Tasks" and "### 2.2 Milestones".
New work is three additions, and the numbers only go up: add_module writes the next
"#### 1.6.N <title> (D<n>)", add_pointer the line "- 03 <title> · module 1.6.2 ·
tasks/03-<slug>.md" in 2.1 (the task itself is a file, task_file_text), add_milestone the next
"#### 2.2.N Milestone: <name>" with its "- Tasks:" line; link_task adds a task number to an
existing milestone. An old-form spec ("### Milestone:" blocks with "- Task N:" lines) takes a
whole block, append_old_block.
"""
import contextlib
import importlib.util
import io
import re
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
SECTION_RE = re.compile(r"^(#{2,4})\s+(\d+(?:\.\d+)*)\s+(Modules|Tasks|Milestones)\s*$")
TASK_TYPES = ("feat", "bug")


def own():
    return C.load("lib/ownership")


def section(text, name):
    """(start, end, level, number) of the section "Modules", "Tasks" or "Milestones": the 0-based
    index of its heading and of the line after its last line. None when the spec has none."""
    lines = text.split("\n")
    heads = [(i - 1, line) for i, line in C.outside_fences(text) if own().HEADING_RE.match(line)]
    for k, (i, line) in enumerate(heads):
        m = SECTION_RE.match(line.rstrip())
        if m and m.group(3) == name:
            level = len(m.group(1))
            end = next((j for j, l in heads[k + 1:] if len(l) - len(l.lstrip("#")) <= level), len(lines))
            return i, end, level, m.group(2)
    return None


def new_form(text):
    return all(section(text, n) is not None for n in ("Modules", "Tasks", "Milestones"))


def _append(text, name, block):
    """text with the lines of block at the end of the section name; block gets the section's
    number and the heading marks of an entry inside it."""
    start, end, level, number = section(text, name)
    lines = text.split("\n")
    head = lines[:end]
    while head and not head[-1].strip():
        head.pop()
    tail = lines[end:]
    new = block(number, "#" * (level + 1))
    gap = [] if new[0].startswith("- ") and head[-1].startswith("- ") else [""]
    out = head + gap + new
    if any(l.strip() for l in tail):
        out += [""] + tail
    return "\n".join(out).rstrip("\n") + "\n"


def empty_section(text, name):
    """text with the section name cut down to its heading (plan/new_spec.py removes the
    template's placeholder entries, so the first real entry is number 1)."""
    start, end, _, _ = section(text, name)
    lines = text.split("\n")
    return "\n".join(lines[:start + 1] + [""] + lines[end:])


SLUG_MAX = 60


def check_title(what, title):
    """Die unless title can be a heading and a file name: no "[" at the start (a template
    placeholder), no control character or line break, and something left for the file name."""
    if title.startswith("["):
        C.die(f"{what} '{title}' starts with '[': that is a template placeholder, write the real title")
    if any(ord(c) < 32 or ord(c) == 127 for c in title):
        C.die(f"{what} holds a control character or a line break: one plain line is needed")
    if not C.slugify(title):
        C.die(f"{what} '{title}' has no letter or digit: nothing is left for its file name")


def file_slug(title):
    """The slug of a task file name, cut to SLUG_MAX characters at a word end."""
    slug = C.slugify(title)
    return slug if len(slug) <= SLUG_MAX else slug[:SLUG_MAX].rsplit("-", 1)[0]


def next_id(ids, number):
    last = max((int(i.rsplit(".", 1)[1]) for i in ids if i.rsplit(".", 1)[0] == number), default=0)
    return f"{number}.{last + 1}"


def add_module(text, modules, title, cites=()):
    """(text, module id): the next module heading at the end of 1.6 Modules, with a line to fill."""
    out = {}

    def block(number, marks):
        out["id"] = next_id(modules, number)
        cite = f" ({', '.join(cites)})" if cites else ""
        return [f"{marks} {out['id']} {title}{cite}", "", "- [What is wanted and how it should behave.]"]
    return _append(text, "Modules", block), out["id"]


def next_task(doc, spec_path):
    """The next task number of a spec, two digits: after its pointers and its task files."""
    have = [int(n) for n in doc["tasks"]]
    have += [int(m.group(1)) for p in (spec_path.parent / "tasks").glob("*.md")
             if (m := re.match(r"^(\d{2,})-", p.name))]
    return f"{max(have, default=0) + 1:02d}"


def add_pointer(text, number, title, module, rel):
    """text with the task's pointer line at the end of 2.1 Tasks."""
    return _append(text, "Tasks", lambda *_: [f"- {number} {title} · module {module} · {rel}"])


def task_file_text(title, kind):
    """templates/task.md for a new task: its title and type, "status: not started", no quote (an
    agent never writes the owner's words) and no Instructions section (added when needed)."""
    out, skip = [], False
    for line in C.template("task.md").splitlines():
        if line.startswith("## "):
            skip = line.strip() == "## Instructions"
        if skip or line.startswith("> "):
            continue
        if line.startswith("type:"):
            line = f"type: {kind}"
        elif line.startswith("# "):
            line = f"# {title}"
        out.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).rstrip("\n") + "\n"


def add_milestone(text, ids, name, tasks=(), files=(), deps=(), start=None):
    """(text, milestone id): a milestone block at the end of 2.2 Milestones."""
    out = {}

    def block(number, marks):
        out["id"] = next_id(ids, number)
        lines = [f"{marks} {out['id']} Milestone: {name}", f"- Tasks: {', '.join(tasks)}".rstrip()]
        lines += ["- Files owned: " + ", ".join(f"`{f}`" for f in files)] if files else []
        lines += [f"- Depends on: {', '.join(deps)}"] if deps else []
        lines += [f"- Starts: S{start}"] if start else []
        return lines
    return _append(text, "Milestones", block), out["id"]


def link_task(text, milestone, task_id):
    """text with task_id on the "- Tasks:" line of the milestone named milestone."""
    o = own()
    lines = text.split("\n")
    at = next(i - 1 for i, line in C.outside_fences(text)
              if (m := o.MILESTONE_RE.match(line)) and m.group("name") == milestone)
    for i in range(at + 1, len(lines)):
        if o.HEADING_RE.match(lines[i]):
            break
        m = re.match(r"^(\s*-\s*Tasks:)\s*(.*?)\s*$", lines[i])
        if m:
            have = [x.strip() for x in m.group(2).split(",") if x.strip()]
            lines[i] = f"{m.group(1)} {', '.join(have + [task_id])}"
            return "\n".join(lines)
    lines.insert(at + 1, f"- Tasks: {task_id}")
    return "\n".join(lines)


def old_block(name, files, deps, start, cites, checks):
    """An old-form milestone block with its one task."""
    lines = [f"### Milestone: {name}", "",
             "- Files owned: " + ", ".join(f"`{f}`" for f in files),
             f"- Depends on: {', '.join(deps) or 'none'}",
             "- Review: none"]
    lines += [f"- Starts: S{start}"] if start else []
    lines += [f"- Task 1: {name}" + (f" ({', '.join(cites)})" if cites else "") + f". Checks: {checks}"]
    return "\n".join(lines) + "\n"


def append_old_block(text, block):
    """The old-form spec text with block after the end of its last milestone block (the next
    heading of the same or a higher level, else the end of the file); None when it has none."""
    o = own()
    lines = text.split("\n")
    last, level = None, None
    for i, line in enumerate(lines):
        if o.MILESTONE_RE.match(line):
            last, level = i, len(line) - len(line.lstrip("#"))
    if last is None:
        return None
    end = len(lines)
    for i in range(last + 1, len(lines)):
        if o.HEADING_RE.match(lines[i]) and len(lines[i]) - len(lines[i].lstrip("#")) <= level:
            end = i
            break
    head = lines[:end]
    while head and not head[-1].strip():
        head.pop()
    tail = lines[end:]
    out = "\n".join(head) + "\n\n" + block.replace("### Milestone:", "#" * level + " Milestone:", 1)
    if tail and any(l.strip() for l in tail):
        out += "\n" + "\n".join(tail)
    return out.rstrip("\n") + "\n"


# Decisions.
def check_decision(folder, d, epic):
    """Die unless decision D<d> may join a spec of epic (a number or None)."""
    o = own()
    tag = o.read_tags(folder).get(d)
    if tag is None:
        C.die(f"D{d} is not in decisions.md")
    o.refuse_superseded(folder, {d}, "--decision")
    if tag["epic"] and tag["epic"] != epic:
        C.die(f"D{d} is in E{tag['epic']} already")


def grid_cells(folder, num):
    """{milestone name: its grid cell} of the rows of spec num in status/sprints.md."""
    out = {}
    for label, cells in own().grid(folder)[1]:
        m = re.match(r"^E\d+\s+(\d{2}(?:\.\d+)?)\s+(.*)$", label)
        if m and m.group(1) == num:
            out[m.group(2)] = next((c for c in cells if c), "")
    return out


def tag_decision(folder, epic, d):
    """Decision D<d> joins epic E<epic> after its go: its id on the epic file's "Decisions:" line,
    the Ownership table rebuilt (lib/ownership.py fill_epic), and the "#E<n>" tag that moves the
    card to In progress (epics/tag.py). Prints nothing."""
    o = own()
    path = o.epic_path(folder, epic)
    if path.is_file():
        text = o.read(path)
        if d not in o.epic_decisions(text):
            m = o.DECISIONS_LINE_RE.search(text)
            value = m.group(1) if m else ""
            path.write_text(o.set_field(text, "Decisions", f"{value}, D{d}".lstrip(", ")), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            o.fill_epic(folder, epic, quiet=True)
            C.load("epics/tag").tag_epic(folder, f"E{epic}", [f"D{d}"])
