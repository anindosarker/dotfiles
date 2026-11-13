#!/usr/bin/env python3
"""Move a release folder from the flat layout to plan/, run/ and status/.

Usage: python3 -I migrate/layout.py <release> [--owner X] [--root PATH]

git mv: specs/ and epics/ into plan/; trackers/ and handoffs/ into run/; sprints.md into
status/ (a plain move when a path is untracked); the old ownership.md is git rm'ed (the
ownership facts are computed in memory; migrate/epics.py fills the epic files' tables). Copies
templates/swimlanes.html to status/index.html. Rewrites links: specs/ to plan/specs/ (and the
sprints.md link) in <release>-plan.md; specs/, epics/, trackers/, handoffs/,
sprints.md paths of this release inside the handoffs and the epic files.
A folder without a kanban-board queue.md, or with a board in the old card format, then goes
through migrate/queue.py, and every folder through migrate/epics.py, before the reruns. A folder
with run/trackers/fix-*-tracker.md stops there after the migrate/fixes.py dry run, with one line
naming the remaining steps.
Appends the status/index.html and status/data/ render lines to the repo's .gitignore when
missing (renders, never committed). Then reruns sprints/check.py, sprints/refresh.py and status/report.py. Commits nothing. Refuses a
folder that already has plan/specs/; a target folder that exists already (an epic file
epics/new.py wrote into plan/epics/) gets the old folder's files merged in, a name clash
refused.
"""
import argparse
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
HERE = Path(__file__).resolve().parent
MOVES = [("specs", "plan/specs"), ("epics", "plan/epics"), ("trackers", "run/trackers"),
         ("handoffs", "run/handoffs"),
         ("sprints.md", "status/sprints.md")]
DIRS = {"specs": "plan", "epics": "plan", "trackers": "run", "handoffs": "run"}


die, detect_owner = C.die, C.detect_owner


def load_ownership():
    return C.load("lib/ownership")


def move(root, folder, src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["git", "-C", str(root), "mv", "--", str(src), str(dst)], capture_output=True, text=True)
    if r.returncode:
        shutil.move(str(src), str(dst))
    how = "moved (untracked)" if r.returncode else "git mv"
    print(f"{how}: {src.relative_to(folder)} -> {dst.relative_to(folder)}")


def rewrite_paths(text, prefix):
    """Old-layout paths of this release to the new ones. prefix: '.ai/plans/<release>/<owner>/'."""
    p = re.escape(prefix)
    for old, top in DIRS.items():
        text = re.sub(p + old + "/", prefix + f"{top}/{old}/", text)
        text = re.sub(r"(?<![\w./-])" + old + "/", f"{top}/{old}/", text)
    for name in ("sprints.md",):
        text = re.sub(p + re.escape(name), prefix + "status/" + name, text)
        text = re.sub(r"(?<![\w./-])" + re.escape(name), "status/" + name, text)
    return text


def rewrite_plan(text):
    text = re.sub(r"\]\(specs/", "](plan/specs/", text)
    return re.sub(r"\]\(sprints\.md\)", "](status/sprints.md)", text)


def edit(path, fn):
    old = path.read_text(encoding="utf-8")
    new = fn(old)
    if new != old:
        path.write_text(new, encoding="utf-8")
        print(f"rewrote links: {path.name}")




def main():
    ap = argparse.ArgumentParser(usage="migrate/layout.py <release> [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    sys.stdout.reconfigure(line_buffering=True)
    if not C.RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    root = load_ownership().repo_root(a.root, a.release)
    owner = detect_owner(root, a.owner)
    folder = root / ".ai" / "plans" / a.release / owner
    if not folder.is_dir():
        die(f"release folder missing: {folder}")
    if (folder / "plan" / "specs").exists():
        die(f"{folder / 'plan' / 'specs'} exists: already migrated")
    for src, dst in MOVES:
        s, d = folder / src, folder / dst
        if not s.exists() or not d.exists():
            continue
        if s.is_file() or not d.is_dir():
            die(f"{d} exists: move it away first")
        clash = sorted(c.name for c in s.iterdir() if (d / c.name).exists())
        if clash:
            die(f"{d / clash[0]} exists in both {src}/ and {dst}/: keep one")

    for src, dst in MOVES:
        s, d = folder / src, folder / dst
        if not s.exists():
            continue
        if d.is_dir():
            # a file made in the new place before the migration (epics/new.py): merge
            for child in sorted(s.iterdir()):
                move(root, folder, child, d / child.name)
            s.rmdir()
        else:
            move(root, folder, s, d)
    if (folder / "ownership.md").exists():
        r = subprocess.run(["git", "-C", str(root), "rm", "-q", "--", str(folder / "ownership.md")],
                           capture_output=True, text=True)
        if r.returncode:
            (folder / "ownership.md").unlink()
        print("removed: ownership.md (computed in memory now)")
    for sub in ("plan/specs", "plan/epics", "run/trackers", "run/handoffs", "status/data"):
        (folder / sub).mkdir(parents=True, exist_ok=True)
    tpl = C.TEMPLATES / "swimlanes.html"
    if not tpl.is_file():
        die(f"template missing: {tpl}")
    shutil.copyfile(tpl, folder / "status" / "index.html")
    C.ensure_gitignore(folder)
    print("copied: templates/swimlanes.html -> status/index.html")
    load_ownership().ignore_renders(folder)

    plan = folder / f"{a.release}-plan.md"
    if plan.is_file():
        edit(plan, rewrite_plan)
    prefix = f".ai/plans/{a.release}/{owner}/"
    for path in sorted((folder / "run" / "handoffs").glob("*.md")) + sorted((folder / "plan" / "epics").glob("*.md")):
        edit(path, lambda t: rewrite_paths(t, prefix))

    args = [a.release, "--owner", owner, "--root", str(root)]
    queue = folder / "queue.md"
    if not queue.is_file() or C.load("migrate/queue").refusal(folder, a.release):
        print("== migrate/queue.py")
        r = subprocess.run([sys.executable, "-I", str(HERE / "queue.py")] + args, cwd=str(root))
        if r.returncode:
            die(f"migrate/queue.py failed (exit {r.returncode}); the moves stay, fix and rerun it")
    print("== migrate/epics.py")
    r = subprocess.run([sys.executable, "-I", str(HERE / "epics.py")] + args, cwd=str(root))
    if r.returncode:
        die(f"migrate/epics.py failed (exit {r.returncode}); the moves stay, fix and rerun it")
    if load_ownership().legacy_fixes(folder):
        print("== migrate/fixes.py --dry-run")
        subprocess.run([sys.executable, "-I", str(HERE / "fixes.py")] + args + ["--dry-run"], cwd=str(root))
        die(f"free-standing fix trackers left: check the table above, run migrate/fixes.py {a.release} "
            f"(with --map <slug>=E<n>:<NN> where a choice is wrong), then sprints/check.py, "
            f"sprints/refresh.py, status/report.py")
    for script in ("sprints/check.py", "sprints/refresh.py", "status/report.py"):
        print(f"== {script}")
        r = subprocess.run([sys.executable, "-I", str(C.SCRIPTS / script)] + args, cwd=str(root))
        if r.returncode:
            die(f"{script} failed (exit {r.returncode}); the moves stay, fix and rerun {script}")
    print("migrated; nothing committed")


if __name__ == "__main__":
    main()
