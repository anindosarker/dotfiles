#!/usr/bin/env python3
"""Add a fix found during a run to the epic it belongs to. A fix is never free-standing: it is a
milestone of the spec it repairs, or a small follow-up spec in a running epic.

Usage: python3 -I plan/new_fix.py <release> <slug> "<Title>" <spec> --files a,b --checks "<checks>"
       [--cites "Q3, Q4"] [--depends "<milestone names>"] [--epic E<n>] [--owner X] [--root PATH]

<spec> is the spec whose work the fix repairs. The form follows from the grid:
- The spec has a status/sprints.md row that is not "[x]" (it is still building): a new
  "### Milestone: <Title>" block is appended after the spec's last milestone block, with its
  tracker run/trackers/NN-<title slug>-tracker.md (the name status/report.py looks up); the title is
  added to the Milestone cell of the spec's rows in the epic file's Ownership table.
- Every row of the spec is "[x]" (merged): a follow-up spec NN.M (the next free number after
  NN) with that one milestone: plan/specs/NN.M-<slug>.md with "- Epic: E<n>", an Acceptance
  line and the block; run/trackers/NN.M-<slug>-tracker.md; its Deliverables row with E<n>; in
  plan/epics/E<n>.md the spec on the "Specs:" line and an Ownership row with an empty Decision
  cell. The spec it follows is never reopened. Its epic: the epic of <spec> while that epic has
  an unfinished row ("[ ]", "·" or "[!]"), else the one running epic; --epic picks one when
  several run, and is required then.
The block: "- Files owned:" the --files, "- Depends on:" every other milestone owning one of
those files plus --depends (so the fix lands after them), "- Review: none", "- Starts: S<n>"
(the current sprint, so the row never lands in a finished sprint), and "- Task 1: <Title>
(<cites>). Checks: <checks>". The tracker's first line cites the cards, "Status: planned".

Refuses, writing nothing: a D id among --cites (a decision goes through the queue and into an
epic); a Q id not in queue.md; a spec with no file; a spec with no Epic line (not gone yet: write
the change into the spec); no epic running for a follow-up spec (file a queue card instead);
several running and no --epic; a milestone name already taken; milestones that no longer
schedule (sprints/check.py names the error). Then each cited card moves to the end of Autofix,
ticked, without tags, under the .ids.lock lock; the refresh chain (lib/grid.py refresh: the grid,
the epic files' Sprint column, the decisions lanes, the queue sync) and the swimlane data run (the
lock is free meanwhile, the syncs take it); the files written, the grid, decisions.md and the epic
files the chain synced are committed under the lock (shared-file rules), never pushed. Prints one line naming
the form, the spec, the milestone and its sprint.
"""
import argparse
import contextlib
import fcntl
import importlib.util
import io
import re
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
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
NUM_RE = re.compile(r"^\d{2}(?:\.\d+)?$")
CITES_RE = re.compile(r"^[QD]\d+(\s*,\s*[QD]\d+)*$")
EPIC_RE = re.compile(r"^E(\d+)$")
UNFINISHED = ("[ ]", "·", "[!]")
die, slugify, load = C.die, C.slugify, C.load


def block_text(name, files, deps, start, title, cites, checks, level="###"):
    lines = [f"{level} Milestone: {name}", "",
             "- Files owned: " + ", ".join(f"`{f}`" for f in files),
             f"- Depends on: {', '.join(deps) or 'none'}",
             "- Review: none",
             f"- Starts: S{start}",
             f"- Task 1: {title}" + (f" ({', '.join(cites)})" if cites else "") + f". Checks: {checks}"]
    return "\n".join(lines) + "\n"


def tracker_text(num, title, cites):
    text = C.tracker_text(num, title)
    if cites:
        text = text.replace(f"# {num}: {title}, tracker", f"# {num}: {title} ({', '.join(cites)}), tracker", 1)
    return text


def append_block(text, block):
    """The spec text with block after the end of its last milestone block (the next heading of
    the same or a higher level, else the end of the file)."""
    own = load("lib/ownership")
    lines = text.split("\n")
    last, level = None, None
    for i, line in enumerate(lines):
        m = own.MILESTONE_RE.match(line)
        if m:
            last, level = i, len(line) - len(line.lstrip("#"))
    if last is None:
        return None, None
    end = len(lines)
    for i in range(last + 1, len(lines)):
        if own.HEADING_RE.match(lines[i]) and len(lines[i]) - len(lines[i].lstrip("#")) <= level:
            end = i
            break
    head = lines[:end]
    while head and not head[-1].strip():
        head.pop()
    tail = lines[end:]
    out = "\n".join(head) + "\n\n" + block.replace("### Milestone:", "#" * level + " Milestone:", 1)
    if tail and any(l.strip() for l in tail):
        out += "\n" + "\n".join(tail)
    return out.rstrip("\n") + "\n", level


def grid_by_spec(own, folder):
    """{spec number: [(epic, cells)]} of status/sprints.md."""
    out = {}
    for label, cells in own.grid(folder)[1]:
        m = re.match(r"^E(\d+)\s+(\d{2}(?:\.\d+)?)\s", label)
        if m:
            out.setdefault(m.group(2), []).append((int(m.group(1)), cells))
    return out


def running_epics(rows):
    return sorted({e for lst in rows.values() for e, cells in lst if any(c in UNFINISHED for c in cells)})


def main():
    ap = argparse.ArgumentParser(
        usage='plan/new_fix.py <release> <slug> "<Title>" <spec> --files a,b --checks "<checks>" '
              '[--cites "Q3, Q4"] [--depends "<milestone names>"] [--epic E<n>] [--owner X] [--root PATH]'
    )
    ap.add_argument("release")
    ap.add_argument("slug")
    ap.add_argument("title")
    ap.add_argument("spec")
    ap.add_argument("--files", required=True)
    ap.add_argument("--checks", required=True)
    ap.add_argument("--cites", default="")
    ap.add_argument("--depends", default="")
    ap.add_argument("--epic")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    if not SLUG_RE.fullmatch(a.slug):
        die(f"bad slug '{a.slug}', expected lowercase-with-dashes")
    if not NUM_RE.fullmatch(a.spec):
        die(f"bad spec number '{a.spec}', expected like 41 or 41.1")
    for label, val in (("title", a.title), ("files", a.files), ("depends", a.depends), ("checks", a.checks)):
        if "|" in val and label != "checks":
            die(f"{label} must not contain '|'")
        if "\u2014" in val:
            die(f"{label} contains an em dash")
    ids = []
    if a.cites.strip():
        if not CITES_RE.match(a.cites.strip()):
            die(f"bad ids '{a.cites}', expected like \"Q3, Q4\"")
        ids = [s.strip() for s in a.cites.split(",")]
    decisions = [i for i in ids if i.startswith("D")]
    if decisions:
        die(f"{', '.join(decisions)}: a decision is never a fix; it goes through the queue and into an epic")
    files = [f.strip().strip("`") for f in a.files.split(",") if f.strip()]
    if not files:
        die("--files names no file")
    want_epic = None
    if a.epic:
        m = EPIC_RE.match(a.epic)
        if not m:
            die(f"bad epic '{a.epic}', expected like E12")
        want_epic = int(m.group(1))

    own = load("lib/ownership")
    bd = load("lib/board")
    root = own.repo_root(a.root, a.release)
    folder = own.release_folder(root, own.detect_owner(root, a.owner), a.release)
    with open(C.lock_file(folder), "a") as lock:
        run(a, own, bd, root, folder, ids, files, want_epic, lock)


def run(a, own, bd, root, folder, ids, files, want_epic, lock):
    fcntl.flock(lock, fcntl.LOCK_EX)
    queue = folder / own.QUEUE_MD
    have = {c["num"] for c in bd.parse(own.read(queue))["cards"]}
    missing = [i for i in ids if int(i[1:]) not in have]
    if missing:
        die(f"not in {queue.name}: {', '.join(missing)}")
    specs = dict(own.spec_files(folder))
    if a.spec not in specs:
        die(f"spec {a.spec} has no file in {own.SPECS_DIR}")
    epic = own.spec_epic(specs[a.spec])
    if not epic:
        die(f"spec {a.spec} is in no epic yet: write the change into the spec itself")
    rows = grid_by_spec(own, folder)
    building = any(c != "[x]" for _, cells in rows.get(a.spec, []) for c in cells if c)
    running = running_epics(rows)
    if building:
        if want_epic and want_epic != epic:
            die(f"spec {a.spec} is still building in E{epic}: the fix is its milestone, --epic E{want_epic} does not apply")
    else:
        if not running:
            die("no epic is running: file a queue card instead (queue/item.py <release> Q \"<title>\")")
        if want_epic:
            if want_epic not in running:
                die(f"E{want_epic} is not running; running: {', '.join(f'E{e}' for e in running)}")
            epic = want_epic
        elif epic not in running:
            if len(running) > 1:
                die(f"several epics run ({', '.join(f'E{e}' for e in running)}): pass --epic E<n>")
            epic = running[0]

    comp = own.compute(folder)
    if comp["errors"]:
        own.print_errors(comp["errors"], "nothing written")
    names = {m["name"] for m in comp["milestones"]}
    if a.title in names:
        die(f"milestone '{a.title}' exists already: pick another title")
    deps = [m["name"] for m in comp["milestones"] if set(m["files"]) & set(files)]
    extra, unknown = own.resolve_deps(a.depends, sorted(names), {})
    if unknown:
        die(f"--depends names unknown milestones: {', '.join(unknown)}")
    deps += [d for d in extra if d not in deps]
    start = own.current_sprint(folder)
    block = block_text(a.title, files, deps, start, a.title, ids, a.checks)

    writes = {}
    trackers = folder / own.TRACKERS_DIR
    if building:
        form, num = "milestone", a.spec
        text, _ = append_block(own.read(specs[a.spec]), block)
        if text is None:
            die(f"spec {a.spec} has no '### Milestone:' block to follow")
        writes[specs[a.spec]] = text
        tracker = trackers / f"{num}-{slugify(a.title)}-tracker.md"
        epic_file = own.epic_path(folder, epic)
        table, err = own.read_table(own.read(epic_file)) if epic_file.is_file() else (None, None)
        if table and not err and any(r["spec"] == num for r in table):
            for r in table:
                if r["spec"] == num:
                    r["milestone"] = "; ".join(x for x in (r["milestone"], a.title) if x)
            writes[epic_file] = own.put_table(own.read(epic_file), table)
    else:
        form = "follow-up spec"
        plan = folder / f"{a.release}-plan.md"
        plan_text = own.read(plan)
        taken = set(specs) | set(re.findall(r"^\|\s*(\d{2}(?:\.\d+)?)\s*\|", plan_text, re.M))
        base = a.spec.split(".")[0]
        m = max((int(n.split(".")[1]) for n in taken if re.fullmatch(re.escape(base) + r"\.\d+", n)), default=0)
        num = f"{base}.{m + 1}"
        spec_path = folder / own.SPECS_DIR / f"{num}-{a.slug}.md"
        writes[spec_path] = (f"# {num}: {a.title}\n- Epic: E{epic}\n\nFollow-up of spec {a.spec}"
                             + (f" ({', '.join(ids)})" if ids else "") + ".\n\n"
                             "- Acceptance: the checks of Task 1 pass.\n\n"
                             "## 2. Instructions for AI\n\n### 2.1 Milestones\n\n" + block)
        writes[plan] = C.insert_row(plan_text, num,
                                           f"| {num} | [{a.title}](plan/specs/{spec_path.name}) | E{epic} | {a.title} |")
        epic_file = own.epic_path(folder, epic)
        if epic_file.is_file():
            et = own.read(epic_file)
            sm = own.SPECS_LINE_RE.search(et)
            have_specs = [s.strip() for s in (sm.group(1) if sm else "").split(",") if s.strip()]
            et = own.set_field(et, "Specs", ", ".join(sorted(have_specs + [num], key=own.num_key)))
            table, err = own.read_table(et)
            if table is not None and not err:
                table.append({"decision": None, "title": "", "files": files, "spec": num,
                              "milestone": a.title, "sprint": ""})
                et = own.put_table(et, table)
            writes[epic_file] = et
        tracker = trackers / f"{num}-{a.slug}-tracker.md"
    if tracker.exists():
        die(f"refusing to overwrite {tracker}")
    writes[tracker] = tracker_text(num, a.title, ids)

    old = {p: (own.read(p) if p.exists() else None) for p in writes}
    for p, t in writes.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(t, encoding="utf-8")
    comp = own.compute(folder)
    if comp["errors"]:
        for p, t in old.items():
            if t is None:
                p.unlink()
            else:
                p.write_text(t, encoding="utf-8")
        own.print_errors(comp["errors"], "the fix does not schedule; nothing written")
    q_text = own.read(queue)
    for i in ids:
        q_text = bd.move(q_text, int(i[1:]), "Autofix")
    if ids:
        bd.write(queue, q_text)
    fcntl.flock(lock, fcntl.LOCK_UN)
    with contextlib.redirect_stdout(io.StringIO()):
        load("lib/grid").refresh(folder, a.release, quiet=True)
        load("sprints/swimlanes").write(folder, a.release, quiet=True)
    fcntl.flock(lock, fcntl.LOCK_EX)
    paths = [str(p) for p in writes] + [str(folder / own.SPRINTS_MD), str(folder / "decisions.md")]
    paths += [str(queue)] if ids else []
    paths += [str(p) for p in sorted((folder / own.EPICS_DIR).glob("E*.md"))]
    C.commit(root, paths, f"docs(plan): {a.release} fix {num} {a.title}")
    fcntl.flock(lock, fcntl.LOCK_UN)
    col = own.compute(folder)["col"].get(a.title)
    rel = tracker.relative_to(folder).as_posix()
    if form == "milestone":
        print(f"milestone of spec {num}: '{a.title}' in E{epic}, S{col}, tracker {rel}")
    else:
        print(f"follow-up spec {num} of spec {a.spec}: milestone '{a.title}' in E{epic}, S{col}, tracker {rel}")


if __name__ == "__main__":
    main()
