#!/usr/bin/env python3
"""Create an expedition cycle folder: .ai/plans/<cycle>/<owner>/ with stubs.

Usage: python3 -I new_cycle.py <cycle> [--owner X]
"""
import argparse
import collections
import datetime
import re
import subprocess
import sys
from pathlib import Path

CYCLE_RE = re.compile(r"^v\d+\.\d+\.x$")


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def repo_root():
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


def from_template(name, cycle, today):
    """Template head up to its Round heading, as Round 1 of a new cycle."""
    path = Path(__file__).resolve().parent.parent / "templates" / name
    if not path.is_file():
        die(f"template missing: {path}")
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## Round"):
            out.append(f"## Round 1: discussion, {today}")
            break
        out.append(line.replace("[cycle]", cycle))
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(usage="new_cycle.py <cycle> [--owner X]")
    ap.add_argument("cycle")
    ap.add_argument("--owner")
    a = ap.parse_args()
    if not CYCLE_RE.match(a.cycle):
        die(f"bad cycle '{a.cycle}', expected like v0.7.x")
    root = repo_root()
    owner = detect_owner(root, a.owner)
    folder = root / ".ai" / "plans" / a.cycle / owner
    if folder.exists():
        die(f"cycle folder exists: {folder}")
    folder.mkdir(parents=True)
    print(folder)
    (folder / "handoffs").mkdir()
    print(folder / "handoffs")
    c = a.cycle
    write_new(folder / f"{c}-plan.md", (
        f"# {c} plan\n\n"
        "Index. Decisions: [decisions.md](decisions.md); parts implement them "
        "and never re-decide.\n\n"
        "## Goals\n\n- \n\n"
        "## Parts\n\n| # | Part | Scope |\n|---|---|---|\n\n"
        "## Dependencies\n\n"
        "## Integration\n\n"
        "## Process rules\n"
    ))
    today = datetime.date.today().isoformat()
    write_new(folder / "decisions.md", from_template("decisions.md", c, today))
    write_new(folder / "findings.md", from_template("findings.md", c, today))


if __name__ == "__main__":
    main()
