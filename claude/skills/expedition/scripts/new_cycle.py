#!/usr/bin/env python3
"""Create an expedition release folder: .ai/plans/<release>/<owner>/ with the <release>-plan.md
(Goals and Deliverables), decisions.md and findings.md stubs, the specs, trackers, attentions,
handoffs and reference folders, and process.md copied from the newest earlier release
(else the skill template). sprints.md is not written here: sprints.py makes it from
ownership.md once the specs hold their milestone blocks.

Usage: python3 -I new_cycle.py <release> [--owner X] [--root PATH]
"""
import argparse
import collections
import datetime
import re
import subprocess
import sys
from pathlib import Path

RELEASE_RE = re.compile(r"^v\d+\.\d+\.x$")


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def repo_root(flag=None):
    if flag:
        p = Path(flag).resolve()
        if not p.is_dir():
            die(f"root not a folder: {p}")
        return p
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        die("not inside a git repository")
    return Path(out.stdout.strip())


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


def write_new(path, text):
    if path.exists():
        die(f"refusing to overwrite {path}")
    path.write_text(text, encoding="utf-8")
    print(path)


def from_template(name, release, today):
    """Template head up to its Round heading, as Round 1 of a new release."""
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


def main():
    ap = argparse.ArgumentParser(usage="new_cycle.py <release> [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: git top level)")
    a = ap.parse_args()
    if not RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    root = repo_root(a.root)
    owner = detect_owner(root, a.owner)
    folder = root / ".ai" / "plans" / a.release / owner
    if folder.exists():
        die(f"release folder exists: {folder}")
    folder.mkdir(parents=True)
    print(folder)
    for sub in ("specs", "trackers", "attentions", "handoffs", "reference"):
        (folder / sub).mkdir()
        print(folder / sub)
    write_new(folder / "process.md", process_text(root, owner, a.release))
    c = a.release
    write_new(folder / f"{c}-plan.md", (
        f"# {c} plan\n\n"
        "Decisions: [decisions.md](decisions.md). Sprints: [sprints.md](sprints.md). "
        "Specs implement decisions and never re-decide.\n\n"
        "## Goals\n\n- \n\n"
        "## Deliverables\n\n| # | Spec | Epic | Scope |\n|---|---|---|---|\n"
    ))
    today = datetime.date.today().isoformat()
    write_new(folder / "decisions.md", from_template("decisions.md", c, today))
    write_new(folder / "findings.md", from_template("findings.md", c, today))


if __name__ == "__main__":
    main()
