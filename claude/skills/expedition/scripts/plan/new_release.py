#!/usr/bin/env python3
"""Create an expedition release folder: .ai/plans/<release>/<owner>/ with the <release>-plan.md
(Goals and Deliverables), decisions.md and queue.md stubs, process.md copied from the newest
earlier release (else the skill template), and the sub-folders:

  plan/specs/  plan/epics/              authored
  run/trackers/  run/handoffs/   written during the run
  status/index.html  status/src/  status/data/   generated; nothing under status/ is edited by hand

The page follows the skill's version, which is the format of the new release: from 2.2 on
status/index.html is board/dashboard.html (D15) with status/src/, the files of board/src/
(sprints/swimlanes.py install_dashboard), and the script prints both paths; below 2.2 it is
board/task-board.html. status/index.html, status/src/ and status/data/ are renders, never
committed: the .ai/plans/*/*/status/ lines are appended to the repo's .gitignore when missing,
the status/src/ line only from 2.2 on. status/data/ (and status/sprints.md, below format 2.2) are
written later by sprints/refresh.py.

The plan file follows the skill's version too: templates/plan.md holds the form of 2.2, with no
link to status/sprints.md; below 2.2 the script adds the link (PLAN_LINK), as releases of that
format have the file.

The queue takes the form of the skill's version (SKILL.md), which is also the new release's
format: below 2.1 the board stub from templates/queue.md; from 2.1 on queue.md from
templates/queue-list.md, an empty list, and an empty queue/ folder for the item files
(lib/queue.py).

The decisions take the form of the skill's version too: from 2.2 on decisions.md is the list of
templates/decisions-list.md with no decision line (lib/decisions.py render_list) and an empty
decisions/ folder for the decision files (templates/decision.md); below 2.2 the board of
templates/decisions.md.

Usage: python3 -I plan/new_release.py <release> [--owner X] [--root PATH]
"""
import argparse
import datetime
import importlib.util
import re
import shutil
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
die, detect_owner = C.die, C.detect_owner
# Below format 2.2 the plan file links the grid file (spec 04, D13); templates/plan.md has the 2.2 form.
PLAN_DECISIONS = "Decisions: [decisions.md](decisions.md)."
PLAN_LINK = " Sprints: [status/sprints.md](status/sprints.md)."
NO_GRID_FILE = (2, 2)


def write_new(path, text):
    if path.exists():
        die(f"refusing to overwrite {path}")
    path.write_text(text, encoding="utf-8")
    print(path)


def from_template(name, release, today):
    """The template with the release filled in."""
    out = [line.replace("[release]", release).replace("[cycle]", release)
           for line in C.template(name).splitlines()]
    return "\n".join(out) + "\n"


def release_key(name):
    return tuple(int(x) for x in re.findall(r"\d+", name))


def process_text(root, owner, release):
    """The newest earlier release's process.md with its title updated, else the template."""
    plans = root / ".ai" / "plans"
    earlier = sorted(
        (p for p in plans.glob(f"v*.x/{owner}/process.md") if p.parent.parent.name != release),
        key=lambda p: release_key(p.parent.parent.name),
    )
    if earlier:
        src = earlier[-1]
        text = src.read_text(encoding="utf-8")
        text = re.sub(r"^# (?:Expedition process|Process), .*$", f"# Process, {release}", text, count=1, flags=re.M)
        print(f"process.md copied from {src.relative_to(root)}; trim it for this release")
    else:
        print("process.md from the skill template; write one topic per project fact")
        text = C.template("process.md").replace("[release]", release, 1)
    return C.load("lib/ownership").set_front(text, "updated", f"{datetime.datetime.now():%Y-%m-%d %H:%M}")




def main():
    ap = argparse.ArgumentParser(usage="plan/new_release.py <release> [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    print(f"re-read the expedition skill (SKILL.md) before the first spec: this release is format {C.skill_version()}, "
          f"specs are folders with task files and statuses are set with status/status.py {a.release} set|get|list",
          file=sys.stderr)
    root = C.repo_root(a.root, a.release, new=True)
    owner = detect_owner(root, a.owner)
    folder = root / ".ai" / "plans" / a.release / owner
    if folder.exists():
        die(f"release folder exists: {folder}")
    folder.mkdir(parents=True)
    print(folder)
    for sub in ("plan/specs", "plan/epics", "run/trackers", "run/handoffs", "status/data"):
        (folder / sub).mkdir(parents=True)
        print(folder / sub)
    sw = C.load("sprints/swimlanes")
    dashboard = C.load("lib/status").version(C.skill_version()) >= sw.DASHBOARD_FORMAT
    if dashboard:
        sw.install_dashboard(folder)
    else:
        tpl = C.BOARD / "task-board.html"
        if not tpl.is_file():
            die(f"template missing: {tpl}")
        shutil.copyfile(tpl, folder / "status" / "index.html")
    C.ensure_gitignore(folder, page_src=dashboard)
    print(folder / "status" / "index.html")
    if dashboard:
        print(folder / "status" / "src")
    C.ignore_renders(folder, page_src=dashboard)
    write_new(folder / "process.md", process_text(root, owner, a.release))
    c = a.release
    plan = "".join(l + "\n" for l in from_template("plan.md", c, None).splitlines() if not l.startswith("| [NN]"))
    if C.load("lib/status").version(C.skill_version()) < NO_GRID_FILE:
        if PLAN_DECISIONS not in plan:
            die(f"templates/plan.md has no line starting {PLAN_DECISIONS!r}: restore it from git")
        plan = plan.replace(PLAN_DECISIONS, PLAN_DECISIONS + PLAN_LINK, 1)
    write_new(folder / f"{c}-plan.md", plan)
    today = datetime.date.today().isoformat()
    dc = C.load("lib/decisions")
    if C.load("lib/status").version(C.skill_version()) >= dc.FILE_FORMAT:
        if not (C.TEMPLATES / "decisions-list.md").is_file():
            die(f"bundled template missing: {C.TEMPLATES / 'decisions-list.md'}")
        write_new(dc.path_of(folder), dc.render_list(c, []))
        dc.dir_of(folder).mkdir()
        print(dc.dir_of(folder))
    else:
        write_new(dc.path_of(folder), from_template("decisions.md", c, today))
    Q = C.load("lib/queue")
    if Q.version(C.skill_version()) >= Q.ITEM_FORMAT:
        text = "".join(l + "\n" for l in from_template("queue-list.md", c, today).splitlines()
                       if not l.startswith("- [Q[n]]"))
        write_new(folder / "queue.md", text.rstrip("\n") + "\n")
        (folder / Q.QUEUE_DIR).mkdir()
        print(folder / Q.QUEUE_DIR)
    else:
        write_new(folder / "queue.md", from_template("queue.md", c, today))
    st = C.load("lib/status")
    st.save(folder, st.build(folder, c, ({}, {})))
    print(st.path(folder))
    open(C.lock_file(folder), "a").close()


if __name__ == "__main__":
    main()
