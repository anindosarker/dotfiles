#!/usr/bin/env python3
"""Move a release that is in work from the earlier form to the present one: spec folders with
task files, and status/data/status.json as the store of every status.

Usage: python3 -I migrate/v0.1-v0.2/format.py <release> [--dry-run] [--force] [--owner X] [--root PATH]

In the release folder:
- Each flat spec plan/specs/NN-<slug>.md moves (git mv) to plan/specs/NN-<slug>/NN-<slug>.md
  and gets the front matter lines "status:" and "migrated: true" (the Done rule does not ask
  every module of such a spec for a task). Every "specs/NN-<slug>.md" in another file of the
  release folder (the Deliverables links, epic files, trackers, handoffs) follows; a "../" link
  inside a moved spec gets one more "../".
- Inside a spec with a "### 2.1 Milestones" section of "### Milestone: <Name>" blocks: the
  section becomes "### 2.1 Tasks" (one pointer line per old "- Task N:" line, numbered across
  the spec) and "### 2.2 Milestones" ("#### 2.2.N Milestone: <Name>" with "- Tasks:" and the
  block's other lines as they were); "### 2.2 Checks" becomes "### 2.3 Checks". Section 1 is
  not rewritten.
- Each old task line becomes tasks/NN-<slug>.md from templates/task.md: its title from the task
  text, "## Goals" with the whole task text, "## Verification" with one box per check of its
  "Checks:" part, ticked when the milestone is done. A decision cite of a task line that names
  a section 1.6.N goes onto that module's heading; any other cite stays on the pointer line, so
  the scripts still find it in the spec, and in the Goals line.
- A spec the steps above do not fit (no "### 2.1 Milestones" heading, or no block) is moved and
  keeps its body: its "### Milestone:" blocks and "- Task N:" lines are still read. It is named
  in the output.
- Epic files: the "Decisions:", "Specs:", "Starts:" lines become front matter, with "status:".
- status/data/status.json, from the grid cell and the tracker of each milestone: "·" not
  started, "[ ]" in progress, "[x]" done with the merge commit the tracker holds (its Status
  brackets or its "Merge:" line), "[~]" blocked with the tracker's waiting text, "[!]" blocked
  with the tracker's reason, or skipped when that reason starts with a decision id. A milestone
  with no grid row takes its tracker's word. The tasks of a done milestone are done, of a
  skipped one skipped, every other task not started.
- Trackers of milestones lose the "Status:" line and their "- Task N" lines; the rest stays. A
  tracker no milestone owns is left as it is and named.
- process.md gets "updated:" in its front matter; the repo's .gitignore gets the pair that
  keeps status.json in git.
Then the chain every status change runs (the roll-up, the "status:" lines, status/sprints.md
drawn from the file, the page data) and one commit of the release folder, never pushed by hand.

Prints one line per spec and the counts before and after (specs, milestones, tasks, done
milestones); they must be equal, else nothing is committed. --dry-run prints the same and
writes nothing. A second run finds status.json and changes nothing.

Refuses: a release that has status.json already (nothing to do); a release folder with
uncommitted changes; free-standing fix trackers (migrate/v0.0-v0.1/fixes.py first); milestones that do
not schedule; a running milestone ("[ ]") unless --force: a builder in the middle of a
milestone holds the earlier text, so let it merge first or tell it.
"""
import argparse
import contextlib
import datetime
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
OLD_SECTION_RE = re.compile(r"^###\s+2\.1\s+Milestones\s*$")
OLD_CHECKS_RE = re.compile(r"^(###\s+)2\.2(\s+Checks\s*)$")
TASK_LINE_RE = re.compile(r"^-\s*Task\s+\d+:\s*(.*)$")
TRACKER_TASK_RE = re.compile(r"^-\s*Task\s+\d+\b")
PAREN_RE = re.compile(r"\(([^()]*)\)")
SHA_RE = re.compile(r"\b[0-9a-f]{7,40}\b")
MARK_WORD = {"·": "not started", "[ ]": "in progress", "[x]": "done", "[~]": "blocked", "[!]": "blocked"}
TITLE_MAX = 100


def split_task(text):
    """(title, module section or None, D ids, checks) of the text of an old task line."""
    body, _, checks = text.partition("Checks:")
    body = body.strip()
    module, ds = None, []
    for m in PAREN_RE.finditer(body):
        sec = re.search(r"\b1\.\d+\.\d+\b", m.group(1))
        module = module or (sec.group(0) if sec else None)
    for m in PAREN_RE.finditer(text):  # every cite on the line, its Checks part included
        for i in re.findall(r"\b[DQ]\d+\b", m.group(1)) if re.match(r"\s*[DQ]\d+", m.group(1)) else []:
            ds += [i] if i not in ds else []
    title = PAREN_RE.sub(lambda m: "" if re.search(r"\bD\d+\b|\b1\.\d+\.\d+\b|\bQ\d+\b", m.group(1)) else m.group(0), body)
    title = re.sub(r"\s+", " ", title).strip().rstrip(".:,; ").replace("·", "-")
    if len(title) > TITLE_MAX:
        cut = max(title.rfind(s, 30, TITLE_MAX) for s in ("; ", ": ", ", "))
        title = (title[:cut] if cut > 0 else title[:TITLE_MAX].rsplit(" ", 1)[0]).rstrip(".:,; ")
    boxes = [c.strip().rstrip(".") for c in checks.split(";") if c.strip().rstrip(".")]
    return title or "Task", module, ds, boxes


def task_file(sp, title, goal, boxes, done):
    """templates/task.md filled from an old task line."""
    out, section = [], None
    for line in sp.task_file_text(title, "feat").splitlines():
        if line.startswith("## "):
            section = line.strip()
            out.append(line)
            if section == "## Goals":
                out.append(f"- {goal}")
            elif section == "## Verification":
                out += [f"- [{'x' if done else ' '}] {b}" for b in boxes or [title]]
            continue
        if section in ("## Goals", "## Verification") and line.startswith("- "):
            continue
        out.append(line)
    return "\n".join(out).rstrip("\n") + "\n"


def convert(own, sp, text, done_names):
    """(new spec text, {task file name: text}, task count) of an old-form spec text, or None
    when it has no "### 2.1 Milestones" section with milestone blocks."""
    lines = text.split("\n")
    fenced = {i - 1 for i, _ in C.outside_fences(text)}
    start = next((i for i in sorted(fenced) if OLD_SECTION_RE.match(lines[i])), None)
    if start is None:
        return None
    end = next((i for i in range(start + 1, len(lines)) if i in fenced and own.HEADING_RE.match(lines[i])
                and not own.MILESTONE_RE.match(lines[i]) and len(lines[i]) - len(lines[i].lstrip("#")) <= 3),
               len(lines))
    blocks, cur, intro = [], None, []
    for i in range(start + 1, end):
        m = own.MILESTONE_RE.match(lines[i]) if i in fenced else None
        if m:
            cur = {"name": m.group("name"), "lines": [], "tasks": []}
            blocks.append(cur)
        elif cur is None:
            intro.append(lines[i])
        else:
            t = TASK_LINE_RE.match(lines[i]) if i in fenced else None
            if t:
                cur["tasks"].append([t.group(1)])
            elif cur["tasks"] and lines[i][:1] in (" ", "\t") and lines[i].strip():
                cur["tasks"][-1].append(lines[i].strip())
            else:
                cur["lines"].append(lines[i])
    if not blocks:
        return None
    modules = {m.group(1): i for i in sorted(fenced) if (m := own.MODULE_RE.match(lines[i]))}
    pointers, files, out_blocks, n = [], {}, [], 0
    for k, b in enumerate(blocks, 1):
        numbers = []
        for parts in b["tasks"]:
            n += 1
            num = f"{n:02d}"
            title, module, ds, boxes = split_task(parts[0])
            if module not in modules:
                module = None
            keep = []
            for d in ds:
                if module and d.startswith("D"):
                    if int(d[1:]) not in own.cited(lines[modules[module]]):
                        lines[modules[module]] = lines[modules[module]].rstrip() + f" ({d})"
                else:
                    keep.append(d)
            name = f"{num}-{sp.file_slug(title) or 'task'}.md"
            # one bracket per kind of id: status/report.py counts "(D7, D8)" and "(Q3)", not "(D7, Q3)"
            cite = "".join(f" ({', '.join(g)})" for g in ([i for i in keep if i[0] == k] for k in "DQ") if g)
            pointers.append(f"- {num} {title}{cite}" + (f" · module {module}" if module else "") + f" · tasks/{name}")
            goal = " ".join(parts).split("Checks:")[0].strip() if len(parts) == 1 else " ".join(parts)
            files[name] = task_file(sp, title, goal, boxes, b["name"] in done_names)
            numbers.append(num)
        body = [l for l in b["lines"]]
        while body and not body[0].strip():
            body.pop(0)
        while body and not body[-1].strip():
            body.pop()
        out_blocks += ["", f"#### 2.2.{k} Milestone: {b['name']}", f"- Tasks: {', '.join(numbers)}".rstrip()] + body
    while intro and not intro[-1].strip():
        intro.pop()
    new = lines[:start] + ["### 2.1 Tasks", ""] + pointers + ["", "### 2.2 Milestones"] + intro + out_blocks + [""]
    new += [OLD_CHECKS_RE.sub(r"\g<1>2.3\g<2>", l) if i in fenced else l for i, l in enumerate(lines[end:], end)]
    return "\n".join(new), files, n


def milestone_status(own, cell, tracker, path=None):
    """(status, reason, commit) of one milestone from its grid cell and its tracker text."""
    v = own.status_value(tracker) if tracker else None
    state, inner = (v[0], v[1]) if v else (None, "")
    if cell is None:
        cell = {"running": "[ ]", "waiting": "[~]", "stopped": "[!]", "done": "[x]"}.get(state, "·")
    word = MARK_WORD.get(cell, "not started")
    reason = commit = ""
    if cell == "[x]":
        merge = re.search(r"^Merge:\s*(.*)$", tracker or "", re.M)
        sha = SHA_RE.search(inner) or (SHA_RE.search(merge.group(1)) if merge else None)
        commit = sha.group(0) if sha else ""
    elif cell == "[~]":
        reason = inner if state == "waiting" and inner else "waits"
    elif cell == "[!]":
        if state == "stopped" and re.match(r"^D\d+\b", inner):
            word = "skipped"
        reason = (word == "blocked" and own.attention_reason(path)) or (inner if state == "stopped" else "") or "stopped"
    return word, reason, commit


def epic_front(own, text):
    """An epic file's text with its Decisions, Specs and Starts lines as front matter."""
    if text.startswith("---\n"):
        return text
    vals, body = {}, []
    for line in text.split("\n"):
        m = re.match(r"^(Decisions|Specs|Starts):[ \t]*(.*?)\s*$", line)
        if m and m.group(1).lower() not in vals:
            vals[m.group(1).lower()] = m.group(2)
        else:
            body.append(line)
    front = ["---", "status: not started"] + [f"{k}: {vals.get(k, '')}".rstrip() for k in ("decisions", "specs", "starts")]
    return "\n".join(front + ["---"]) + "\n" + re.sub(r"\n{3,}", "\n\n", "\n".join(body))


def counts(own, st, folder):
    """(specs, milestones, tasks, done milestones) of the release as the scripts read it now."""
    ms, _ = own.collect(folder)
    blocks = [b for _, p in own.spec_files(folder) for b in own.parse_spec(p)]
    if st.active(folder):
        done = sum(1 for m in st.entries(folder)[0].values() if m["status"] == "done")
    else:
        done = sum(1 for _, cells in own.grid(folder)[1] if "[x]" in cells)
    return len(own.spec_files(folder)), len(ms), sum(len(b["tasks"]) for b in blocks), done


def main():
    ap = argparse.ArgumentParser(usage="migrate/v0.1-v0.2/format.py <release> [--dry-run] [--force] [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="migrate while a milestone is running")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        C.die(f"bad release '{a.release}', expected like v0.9.x")
    root, folder = C.find_folder(a.release, a.owner, a.root)
    own, sp, st = C.load("lib/ownership"), C.load("lib/specs"), C.load("lib/status")
    if st.active(folder):
        print(f"{folder / st.FILE} exists: the release has the present form, nothing to change")
        return
    if C.legacy_fixes(folder):
        C.die(f"{folder} has free-standing fix trackers: run migrate/v0.0-v0.1/fixes.py first")
    real = folder.resolve()
    git = lambda *args: subprocess.run(["git", "-C", str(real), *args], capture_output=True, text=True)
    if git("status", "--porcelain", "--", ".").stdout.strip():
        C.die(f"{folder} has uncommitted changes: commit them first")
    comp = own.compute(folder)
    if comp["errors"]:
        own.print_errors(comp["errors"], "nothing written")
    plan = folder / f"{a.release}-plan.md"
    coll = own.new_collect(folder, plan)
    cells = {}
    for label, cs in own.grid(folder)[1]:
        m = re.match(r"^E\d+\s+(\d{2}(?:\.\d+)?)\s+(.*)$", label)
        if m:
            cells[(m.group(1), m.group(2))] = (next((c for c in cs if c), ""), next((i + 1 for i, c in enumerate(cs) if c), 0))
    running = [name for (_, name), (c, _) in cells.items() if c == "[ ]"]
    if running and not a.force:
        C.die(f"{len(running)} milestone(s) are running ({', '.join(running[:3])}{', ...' if len(running) > 3 else ''}): "
              "a builder in the middle of a milestone holds the earlier text. Let them merge, or pass --force")
    before = counts(own, st, folder)

    # What each milestone and tracker becomes.
    stored_m, trackers, done_names = [], {}, set()
    linked = {num for num, _ in coll["docs"]}
    for num, p in own.spec_files(folder):
        slug = p.stem.split("-", 1)[1]
        for i, b in enumerate(own.parse_spec(p)):
            t = own.milestone_tracker(folder, num, slug, i, b["name"])
            text = own.read(t) if t.is_file() else None
            cell, col = cells.get((num, b["name"]), (None, 0))
            word, reason, commit = milestone_status(own, cell, text, t)
            stored_m.append({"id": t.name.removesuffix("-tracker.md"), "name": b["name"], "spec": num,
                             "sprint": f"S{col}" if col else "", "status": word, "reason": reason,
                             "changed": "", "commit": commit})
            if word == "done":
                done_names.add(b["name"])
            if text is not None:
                kept = [l for l in text.split("\n") if not own.STATUS_RE.match(l) and not TRACKER_TASK_RE.match(l)]
                trackers[t] = re.sub(r"\n{3,}", "\n\n", "\n".join(kept))
    extra = [p for p in sorted((folder / C.TRACKERS_DIR).glob("*-tracker.md")) if p not in trackers]

    # What each spec becomes.
    moves, writes, plain, tasks_new, stored_t = [], {}, [], 0, []
    status_of = {m["id"]: m["status"] for m in stored_m}
    for num, p in own.spec_files(folder):
        if p.parent.name == p.stem:
            continue
        new_path = p.with_suffix("") / p.name
        moves.append((p, new_path))
        text = own.read(p)
        res = convert(own, sp, text, done_names)
        if res is None:
            plain.append(p.name)
            n = sum(len(b["tasks"]) for b in own.parse_spec(p))
        else:
            text, files, n = res
            for name, body in files.items():
                writes[new_path.parent / "tasks" / name] = body
        tasks_new += n
        text = re.sub(r"\]\((\.\./)", r"](../\1", text)
        # "migrated": the modules of this spec were written before tasks pointed at modules
        writes[new_path] = own.set_front(own.set_front(text, "migrated", "true"), "status", "not started", first=True)
        print(f"{p.relative_to(folder)}: to {new_path.parent.relative_to(folder)}/, "
              + (f"{n} task files" if res else "body kept (no '### 2.1 Milestones' section with blocks)"))
    stems = {old.stem for old, _ in moves}
    link_re = re.compile(r"specs/(" + "|".join(sorted(map(re.escape, stems), key=len, reverse=True)) + r")\.md") if stems else None
    for f in sorted(folder.rglob("*.md")):
        if "status" in f.relative_to(folder).parts[:1] or f in dict(moves):
            continue
        text = trackers.get(f, None)
        text = own.read(f) if text is None else text
        new = link_re.sub(r"specs/\1/\1.md", text) if link_re else text
        if f.parent == folder / C.EPICS_DIR and re.match(r"^E\d+\.md$", f.name):
            new = epic_front(own, new)
        if f == folder / "process.md":
            new = own.set_front(new, "updated", f"{datetime.datetime.now():%Y-%m-%d %H:%M}")
        if new != own.read(f):
            writes[f] = new
    for p, new_path in moves:
        writes[new_path] = link_re.sub(r"specs/\1/\1.md", writes[new_path])
    print(f"{len(moves)} specs moved ({len(plain)} with the body kept), {tasks_new} tasks, "
          f"{len(stored_m)} milestones, {len(trackers)} trackers cleaned, {len(extra)} trackers no milestone owns left as they are")
    for p in extra:
        print(f"left as it is: {p.relative_to(folder)}")
    orphan = [f"{n} {name}" for (n, name) in cells if name not in {m["name"] for m in stored_m}]
    for o in orphan:
        print(f"grid row with no milestone, not carried over: {o}")
    if a.dry_run:
        print(f"before: specs {before[0]}, milestones {before[1]}, tasks {before[2]}, done milestones {before[3]}")
        print("dry run; nothing written")
        return

    with open(C.lock_file(folder), "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        for old, new in moves:
            new.parent.mkdir(parents=True)
            r = git("mv", str(old.resolve()), str(new.resolve().parent / new.name))
            if r.returncode:
                C.die(f"git mv failed: {(r.stderr or r.stdout).strip()}")
        for p, text in writes.items():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
        C.ensure_gitignore(folder)
        # Tasks follow their milestone: done with it, skipped with it, else not started.
        for num, p in own.spec_files(folder):
            slug = p.stem.split("-", 1)[1]
            for i, b in enumerate(own.parse_spec(p)):
                mid = own.milestone_tracker(folder, num, slug, i, b["name"]).name.removesuffix("-tracker.md")
                word = status_of.get(mid)
                for t in b["tasks"]:
                    stored_t.append({"id": f"{num}-{t['id']}", "status": word if word in st.CLOSED else st.STATUSES[0],
                                     "reason": next(m["reason"] for m in stored_m if m["id"] == mid) if word == "skipped" else "",
                                     "changed": ""})
        st.write_json(st.path(folder), json.dumps({"release": a.release, "format": C.skill_version(), "milestones": stored_m, "tasks": stored_t}, indent=2) + "\n")
        with contextlib.redirect_stdout(io.StringIO()):
            C.load("lib/grid").refresh(folder, a.release, quiet=True, locked=True)
            C.load("sprints/swimlanes").write(folder, a.release, quiet=True)
        st.CHANGED.clear()
        after = counts(own, st, folder)
        print(f"before: specs {before[0]}, milestones {before[1]}, tasks {before[2]}, done milestones {before[3]}")
        print(f"after:  specs {after[0]}, milestones {after[1]}, tasks {after[2]}, done milestones {after[3]}")
        if before != after:
            C.die("the counts differ: nothing committed; look at the files, then `git checkout` and `git clean` the release folder")
        top = Path(git("rev-parse", "--show-toplevel").stdout.strip())
        C.commit(root, [folder, top / ".gitignore"], f"docs(plan): {a.release} moved to spec folders, task files and status.json")
        fcntl.flock(lock, fcntl.LOCK_UN)
    print("committed")


if __name__ == "__main__":
    main()
