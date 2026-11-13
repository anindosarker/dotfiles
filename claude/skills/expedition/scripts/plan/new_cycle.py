#!/usr/bin/env python3
"""Create an expedition release folder: .ai/plans/<release>/<owner>/ with the <release>-plan.md
(Goals and Deliverables), decisions.md and queue.md stubs, process.md copied from the newest
earlier release (else the skill template), and the sub-folders:

  plan/specs/  plan/epics/              authored
  run/trackers/  run/handoffs/   written during the run
  status/index.html  status/data/       generated; nothing under status/ is edited by hand

status/index.html is copied from templates/swimlanes.html. status/index.html and status/data/
are renders, never committed: the two .ai/plans/*/*/status/ lines are appended to the repo's
.gitignore when missing. status/sprints.md and status/data/ are written later by sprints/refresh.py.

Usage: python3 -I plan/new_cycle.py <release> [--owner X] [--root PATH]
"""
import argparse
import datetime
import importlib.util
import re
import shutil
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


def write_new(path, text):
    if path.exists():
        die(f"refusing to overwrite {path}")
    path.write_text(text, encoding="utf-8")
    print(path)


def from_template(name, release, today):
    """The template with the release filled in."""
    path = C.TEMPLATES / name
    if not path.is_file():
        die(f"template missing: {path}")
    out = [line.replace("[release]", release).replace("[cycle]", release)
           for line in path.read_text(encoding="utf-8").splitlines()]
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
        text = re.sub(r"^# Expedition process, .*$", f"# Expedition process, {release}", text, count=1, flags=re.M)
        print(f"process.md copied from {src.relative_to(root)}; trim it for this release")
        return text
    tpl = C.TEMPLATES / "process.md"
    if not tpl.is_file():
        die(f"template missing: {tpl}")
    print("process.md from the skill template; fill every [...] placeholder")
    return tpl.read_text(encoding="utf-8").replace("[project]", release, 1)




def main():
    ap = argparse.ArgumentParser(usage="plan/new_cycle.py <release> [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
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
    tpl = C.TEMPLATES / "swimlanes.html"
    if not tpl.is_file():
        die(f"template missing: {tpl}")
    shutil.copyfile(tpl, folder / "status" / "index.html")
    C.ensure_gitignore(folder)
    print(folder / "status" / "index.html")
    C.ignore_renders(folder)
    write_new(folder / "process.md", process_text(root, owner, a.release))
    c = a.release
    write_new(folder / f"{c}-plan.md", (
        f"# {c} plan\n\n"
        "Decisions: [decisions.md](decisions.md). Sprints: [status/sprints.md](status/sprints.md). "
        "Specs implement decisions and never re-decide.\n\n"
        "## Goals\n\n- \n\n"
        "## Deliverables\n\n| # | Spec | Epic | Scope |\n|---|---|---|---|\n"
    ))
    today = datetime.date.today().isoformat()
    write_new(folder / "decisions.md", from_template("decisions.md", c, today))
    write_new(folder / "queue.md", from_template("queue.md", c, today))


if __name__ == "__main__":
    main()
