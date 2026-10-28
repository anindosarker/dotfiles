#!/usr/bin/env python3
"""Print candidate project planning-rules paths, one per line, relative to the repo root.

Usage: python3 -I find_rules.py [REPO]

Prints nothing when none are found. Matches files named like *plan*guide*.md
or planning*.md (case-insensitive), and CLAUDE.md or AGENTS.md lines (root and
.claude/) that mention plan files or planning guidelines, as PATH:LINE.
"""
import fnmatch
import os
import re
import subprocess
import sys
from pathlib import Path

MAX_DEPTH = 4
NAME_PATTERNS = ("*plan*guide*.md", "planning*.md")
SKIP_DIRS = {
    "node_modules", ".git", "worktrees", ".worktrees", "dist", "build", "out",
    ".next", ".turbo", ".vercel", ".cache", "coverage", "target", "vendor",
    ".venv", "venv", "__pycache__", "storybook-static",
}
AGENT_FILES = ("CLAUDE.md", "AGENTS.md", ".claude/CLAUDE.md", ".claude/AGENTS.md")
MENTION_RE = re.compile(
    r"\bplan(?:ning)?[ -](?:files?|guidelines?|guides?|rules?)\b", re.I
)


def repo_root(arg=None):
    start = Path(arg) if arg else Path.cwd()
    try:
        out = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        return Path(out.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return start.resolve()


def skip_dir(name, rel):
    return (
        name in SKIP_DIRS
        or name.endswith(".worktrees")
        or rel == ".ai/plans"
    )


def find_rules(root):
    """Return candidate planning-rules paths relative to root, sorted."""
    root = Path(root)
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        depth = 0 if rel_dir == "." else rel_dir.count(os.sep) + 1
        dirnames[:] = [
            d for d in dirnames
            if depth < MAX_DEPTH
            and not skip_dir(d, os.path.normpath(os.path.join(rel_dir, d)).replace(os.sep, "/"))
        ]
        for f in filenames:
            low = f.lower()
            if any(fnmatch.fnmatch(low, p) for p in NAME_PATTERNS):
                found.append(os.path.normpath(os.path.join(rel_dir, f)).replace(os.sep, "/"))
    found.sort()
    for name in AGENT_FILES:
        p = root / name
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(text.splitlines(), 1):
            if MENTION_RE.search(line):
                found.append(f"{name}:{i}")
    return found


def main():
    if len(sys.argv) > 2 or (len(sys.argv) == 2 and sys.argv[1] in ("-h", "--help")):
        print("usage: find_rules.py [REPO]", file=sys.stderr)
        sys.exit(2)
    for path in find_rules(repo_root(sys.argv[1] if len(sys.argv) == 2 else None)):
        print(path)


if __name__ == "__main__":
    main()
