#!/usr/bin/env python3
"""Move a release folder from the flat layout to plan/, run/ and status/.

Usage: python3 -I migrate_layout.py <release> [--owner X] [--root PATH]

git mv: specs/ and epics/ into plan/; trackers/ and handoffs/ into run/;
ownership.md and sprints.md into status/ (a plain move when a path is untracked). Copies
templates/swimlanes.html to status/index.html. Rewrites links: specs/ to plan/specs/ (and the
sprints.md link) in <release>-plan.md; specs/, epics/, trackers/, handoffs/,
ownership.md and sprints.md paths of this release inside the handoffs and the epic files.
A folder without a kanban-board queue.md then goes through migrate_queue.py before the reruns.
Appends the status/index.html and status/data/ render lines to the repo's .gitignore when
missing (renders, never committed). Then reruns ownership.py, sprints.py, swimlanes.py and status.py. Commits nothing. Refuses a
folder that already has plan/specs/; a target folder that exists already (an epic file
new_epic_file.py wrote into plan/epics/) gets the old folder's files merged in, a name clash
refused.
"""
import argparse
import collections
import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path

RELEASE_RE = re.compile(r"^v\d+\.\d+\.x$")
HERE = Path(__file__).resolve().parent
MOVES = [("specs", "plan/specs"), ("epics", "plan/epics"), ("trackers", "run/trackers"),
         ("handoffs", "run/handoffs"),
         ("ownership.md", "status/ownership.md"), ("sprints.md", "status/sprints.md")]
DIRS = {"specs": "plan", "epics": "plan", "trackers": "run", "handoffs": "run"}


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def load_ownership():
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("ownership", HERE / "ownership.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def repo_root(flag=None):
    if flag:
        p = Path(flag).resolve()
        if not p.is_dir():
            die(f"root not a folder: {p}")
        return p
    r = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if r.returncode:
        die("not inside a git repository")
    return Path(r.stdout.strip())


def detect_owner(root, flag):
    if flag:
        return flag
    counts = collections.Counter(p.name for p in (root / ".ai" / "plans").glob("v*.x/*") if p.is_dir())
    if not counts:
        die("no owner found under .ai/plans/v*.x/*/; pass --owner")
    return counts.most_common(1)[0][0]


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
    for name in ("ownership.md", "sprints.md"):
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



def ensure_gitignore(folder):
    """Append the status render ignores to the repo's .gitignore when missing."""
    import subprocess
    try:
        root = subprocess.run(["git", "-C", str(folder), "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return
    gi = Path(root) / ".gitignore"
    lines = [".ai/plans/*/*/status/index.html", ".ai/plans/*/*/status/data/"]
    have = gi.read_text().splitlines() if gi.is_file() else []
    missing = [l for l in lines if l not in have]
    if missing:
        with gi.open("a") as f:
            if have and not have[-1].strip() == "":
                f.write("\n")
            f.write("\n".join(missing) + "\n")


def main():
    ap = argparse.ArgumentParser(usage="migrate_layout.py <release> [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: git top level)")
    a = ap.parse_args()
    sys.stdout.reconfigure(line_buffering=True)
    if not RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    root = repo_root(a.root)
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
            # a file made in the new place before the migration (new_epic_file.py): merge
            for child in sorted(s.iterdir()):
                move(root, folder, child, d / child.name)
            s.rmdir()
        else:
            move(root, folder, s, d)
    for sub in ("plan/specs", "plan/epics", "run/trackers", "run/handoffs", "status/data"):
        (folder / sub).mkdir(parents=True, exist_ok=True)
    tpl = HERE.parent / "templates" / "swimlanes.html"
    if not tpl.is_file():
        die(f"template missing: {tpl}")
    shutil.copyfile(tpl, folder / "status" / "index.html")
    ensure_gitignore(folder)
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
    if not queue.is_file() or "kanban-plugin:" not in queue.read_text(encoding="utf-8").split("\n---", 1)[0]:
        print("== migrate_queue.py")
        r = subprocess.run([sys.executable, "-I", str(HERE / "migrate_queue.py")] + args, cwd=str(root))
        if r.returncode:
            die(f"migrate_queue.py failed (exit {r.returncode}); the moves stay, fix and rerun it")
    for script in ("ownership.py", "sprints.py", "swimlanes.py", "status.py"):
        print(f"== {script}")
        r = subprocess.run([sys.executable, "-I", str(HERE / script)] + args, cwd=str(root))
        if r.returncode:
            die(f"{script} failed (exit {r.returncode}); the moves stay, fix and rerun {script}")
    print("migrated; nothing committed")


if __name__ == "__main__":
    main()
