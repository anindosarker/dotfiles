#!/usr/bin/env python3
"""Allocate the next D, F or A id of a release and file the item under it, so two sessions
on one checkout never pick the same number.

Usage: python3 -I new_item.py <release> D|F|A "<title>" [--owner X] [--root PATH]
       [--source A<n>] [--bullet "<first bullet>"]

Under an exclusive lock on <release folder>/.ids.lock: re-read the files, take the highest
number of that kind across the release (A: every ATTENTION file), append the heading
(D in decisions.md and F in findings.md under the last "## Round" heading, A in today's
run/attentions/ATTENTION-<YYYY-MM-DD>.md), then the first bullet if given, and commit that one
file. Prints the id alone, e.g. F11.
"""
import argparse
import datetime
import fcntl
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

RELEASE_RE = re.compile(r"^v\d+\.\d+\.x$")
SOURCE_RE = re.compile(r"^A\d+$")
ROUND_RE = re.compile(r"^## Round\b")


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def load(name):
    sys.dont_write_bytecode = True
    path = Path(__file__).resolve().parent / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def attention_files(folder, own):
    """Every ATTENTION file of the release, under run/attentions/."""
    return sorted((folder / own.ATTENTIONS_DIR).glob("ATTENTION-*.md"))


def highest(paths, kind):
    head = re.compile(r"^#{2,3}\s+" + kind + r"(\d+)\b")
    top = 0
    for p in paths:
        if not p.is_file():
            continue
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            m = head.match(line)
            if m:
                top = max(top, int(m.group(1)))
    return top


def under_last_round(text, block, today):
    """Insert block at the end of the last '## Round' section; add Round 1 when none."""
    lines = text.rstrip("\n").split("\n") if text.strip() else []
    rounds = [i for i, l in enumerate(lines) if ROUND_RE.match(l)]
    if not rounds:
        lines += ["", f"## Round 1: discussion, {today}"]
        end = len(lines)
    else:
        end = len(lines)
        for i in range(rounds[-1] + 1, len(lines)):
            if lines[i].startswith("## "):
                end = i
                break
    head, tail = lines[:end], lines[end:]
    while head and not head[-1].strip():
        head.pop()
    out = head + [""] + block
    if tail:
        out += [""] + tail
    return "\n".join(out).lstrip("\n") + "\n"


def appended(text, block):
    body = text.rstrip("\n")
    return (body + "\n\n" if body else "") + "\n".join(block) + "\n"


def git(root, *args):
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    if r.returncode != 0:
        die(f"git {' '.join(args[:1])} failed: {(r.stderr or r.stdout).strip()}")


def exclude_lock(root):
    """Keep .ids.lock out of git status: one line in the repo's info/exclude."""
    r = subprocess.run(["git", "-C", str(root), "rev-parse", "--git-path", "info/exclude"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return
    path = Path(r.stdout.strip())
    if not path.is_absolute():
        path = root / path
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    if ".ids.lock" not in text.split("\n"):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + ("" if not text or text.endswith("\n") else "\n") + ".ids.lock\n",
                        encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(
        usage='new_item.py <release> D|F|A "<title>" [--owner X] [--root PATH] '
              '[--source A<n>] [--bullet "<first bullet>"]'
    )
    ap.add_argument("release")
    ap.add_argument("kind", choices=["D", "F", "A"])
    ap.add_argument("title")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: git top level)")
    ap.add_argument("--source")
    ap.add_argument("--bullet")
    a = ap.parse_args()
    if not RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    title = a.title.strip()
    if not title:
        die("empty title")
    if a.source and not SOURCE_RE.match(a.source):
        die(f"bad source '{a.source}', expected like A3")
    for label, val in (("title", title), ("bullet", a.bullet or "")):
        if "\n" in val:
            die(f"{label} must be one line")
        if "—" in val:
            die(f"{label} contains an em dash")

    own = load("ownership")
    root = own.repo_root(a.root)
    folder = own.release_folder(root, own.detect_owner(root, a.owner), a.release)
    today = datetime.date.today().isoformat()

    with open(folder / ".ids.lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        exclude_lock(root)
        if a.kind == "A":
            scan = attention_files(folder, own)
            target = folder / own.ATTENTIONS_DIR / f"ATTENTION-{today}.md"
        else:
            target = folder / ("decisions.md" if a.kind == "D" else "findings.md")
            if not target.is_file():
                die(f"missing: {target}")
            scan = [target]
        ident = f"{a.kind}{highest(scan, a.kind) + 1}"

        block = [f"{'##' if a.kind == 'A' else '###'} {ident} {title}", ""]
        if a.source:
            block.append(f"- Source: {a.source}")
        if a.bullet:
            block.append(a.bullet if a.bullet.startswith("- ") else f"- {a.bullet}")

        if a.kind == "A":
            target.parent.mkdir(parents=True, exist_ok=True)
            text = target.read_text(encoding="utf-8") if target.is_file() else f"# Attention, {today}\n"
            target.write_text(appended(text, block), encoding="utf-8")
        else:
            text = target.read_text(encoding="utf-8")
            target.write_text(under_last_round(text, block, today), encoding="utf-8")

        git(root, "add", "--", str(target))
        git(root, "commit", "-q", "-m", f"docs(plan): {a.release} {ident} {title}", "--only", "--", str(target))
        fcntl.flock(lock, fcntl.LOCK_UN)
    print(ident)


if __name__ == "__main__":
    main()
