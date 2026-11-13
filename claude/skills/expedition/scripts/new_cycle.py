#!/usr/bin/env python3
"""Create an expedition release folder: .ai/plans/<release>/<owner>/ with the <release>-plan.md
(Goals and Deliverables), decisions.md and queue.md stubs, process.md copied from the newest
earlier release (else the skill template), and the sub-folders:

  plan/specs/  plan/epics/              authored
  run/trackers/  run/handoffs/   written during the run
  status/index.html  status/data/       generated; nothing under status/ is edited by hand

status/index.html is copied from templates/swimlanes.html. status/index.html and status/data/
are renders, never committed: the two .ai/plans/*/*/status/ lines are appended to the repo's
.gitignore when missing. status/ownership.md, status/sprints.md
and status/data/ are written later by ownership.py, sprints.py and swimlanes.py.

Usage: python3 -I new_cycle.py <release> [--owner X] [--root PATH]
"""
import argparse
import collections
import datetime
import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path

RELEASE_RE = re.compile(r"^v\d+\.\d+\.x$")


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def detect_owner(root, flag):
    if flag:
        return flag
    plans = root / ".ai" / "plans"
    counts = collections.Counter(
        p.name for p in plans.glob("v*.x/*") if p.is_dir()
    )
    if not counts:
        die("no owner found under .ai/plans/v*.x/*/; pass --owner")
    return counts.most_common(1)[0][0]


def load_ownership():
    sys.dont_write_bytecode = True
    path = Path(__file__).resolve().parent / "ownership.py"
    spec = importlib.util.spec_from_file_location("ownership", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write_new(path, text):
    if path.exists():
        die(f"refusing to overwrite {path}")
    path.write_text(text, encoding="utf-8")
    print(path)


def from_template(name, release, today):
    """Template head up to its Round heading, as Round 1 of a new release (the whole template
    when it has no Round heading)."""
    path = Path(__file__).resolve().parent.parent / "templates" / name
    if not path.is_file():
        die(f"template missing: {path}")
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## Round"):
            out.append(f"## Round 1: discussion, {today}")
            break
        out.append(line.replace("[release]", release).replace("[cycle]", release))
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
    tpl = Path(__file__).resolve().parent.parent / "templates" / "process.md"
    if not tpl.is_file():
        die(f"template missing: {tpl}")
    print("process.md from the skill template; fill every [...] placeholder")
    return tpl.read_text(encoding="utf-8").replace("[project]", release, 1)



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
    ap = argparse.ArgumentParser(usage="new_cycle.py <release> [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    root = load_ownership().repo_root(a.root, a.release, new=True)
    owner = detect_owner(root, a.owner)
    folder = root / ".ai" / "plans" / a.release / owner
    if folder.exists():
        die(f"release folder exists: {folder}")
    folder.mkdir(parents=True)
    print(folder)
    for sub in ("plan/specs", "plan/epics", "run/trackers", "run/handoffs", "status/data"):
        (folder / sub).mkdir(parents=True)
        print(folder / sub)
    tpl = Path(__file__).resolve().parent.parent / "templates" / "swimlanes.html"
    if not tpl.is_file():
        die(f"template missing: {tpl}")
    shutil.copyfile(tpl, folder / "status" / "index.html")
    ensure_gitignore(folder)
    print(folder / "status" / "index.html")
    load_ownership().ignore_renders(folder)
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
