#!/usr/bin/env python3
"""Print candidate project planning-rules paths, one per line, relative to the repo root.

Usage: python3 -I plan/find_rules.py [REPO]

Prints nothing when none are found. Matches files named like *plan*guide*.md
or planning*.md (case-insensitive) that git tracks, outside vendored, build and
worktree folders and any folder git ignores, and CLAUDE.md or AGENTS.md lines (root and
.claude/) that mention plan files or planning guidelines, as PATH:LINE. Outside a git
repository no file name matches.
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


def git_lines(root, *args):
    """NUL-separated output of a git command in root, as a set; empty when git fails."""
    try:
        out = subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return set()
    return {x.decode("utf-8", "replace") for x in out.stdout.split(b"\0") if x}


def skip_dir(name, rel, ignored=frozenset()):
    return (
        name in SKIP_DIRS
        or name.endswith(".worktrees")
        or rel == ".ai/plans"
        or rel + "/" in ignored
    )


def find_rules(root):
    """Return candidate planning-rules paths relative to root, sorted."""
    root = Path(root)
    found = []
    tracked = git_lines(root, "ls-files", "-z")
    ignored = git_lines(root, "ls-files", "-z", "--others", "--ignored", "--exclude-standard", "--directory")
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        depth = 0 if rel_dir == "." else rel_dir.count(os.sep) + 1
        dirnames[:] = [
            d for d in dirnames
            if depth < MAX_DEPTH
            and not skip_dir(d, os.path.normpath(os.path.join(rel_dir, d)).replace(os.sep, "/"), ignored)
        ]
        for f in filenames:
            low = f.lower()
            rel = os.path.normpath(os.path.join(rel_dir, f)).replace(os.sep, "/")
            if any(fnmatch.fnmatch(low, p) for p in NAME_PATTERNS) and rel in tracked:
                found.append(rel)
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
        print("usage: plan/find_rules.py [REPO]", file=sys.stderr)
        sys.exit(2)
    for path in find_rules(repo_root(sys.argv[1] if len(sys.argv) == 2 else None)):
        print(path)


if __name__ == "__main__":
    main()
