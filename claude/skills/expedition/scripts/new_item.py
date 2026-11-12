#!/usr/bin/env python3
"""Allocate the next D or Q id of a release and file the item under it, so two sessions
on one checkout never pick the same number.

Usage: python3 -I new_item.py <release> D|Q "<title>" [--from <text>] [--source Q<n>]
       [--bullet "<text>"] [--owner X] [--root PATH]

Under an exclusive lock on <release folder>/.ids.lock: re-read the file, take the highest
number of that kind, and append the item.

- D: under the last "## Round" heading of decisions.md: the heading, the --bullet line if
  given, then "- Source: Q<n>" if --source is given. With --source, the "- Tags:" bullet of
  that queue entry gets the new D id in the same commit, unless it already names a decision.
- Q: at the end of queue.md (created from templates/queue.md when missing): the heading,
  "- Tags:" (empty, the entry is open), "- From: <text>." (--from, required), then the
  --bullet line if given.

Commits the files it wrote and prints the id alone, e.g. Q11.
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
SOURCE_RE = re.compile(r"^Q\d+$")
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
        usage='new_item.py <release> D|Q "<title>" [--from <text>] [--source Q<n>] '
              '[--bullet "<text>"] [--owner X] [--root PATH]'
    )
    ap.add_argument("release")
    ap.add_argument("kind")
    ap.add_argument("title")
    ap.add_argument("--from", dest="source_of")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: git top level)")
    ap.add_argument("--source")
    ap.add_argument("--bullet")
    a = ap.parse_args()
    if a.kind not in ("D", "Q"):
        die(f"bad kind '{a.kind}': the kinds are D and Q")
    if not RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    if a.kind == "Q" and not (a.source_of or "").strip():
        die("a Q item needs --from: owner, lead, lookup or run E<n>")
    if a.kind == "Q" and a.source:
        die("--source is for a D item")
    if a.source_of and a.kind == "D":
        die("--from is for a Q item")
    title = a.title.strip()
    if not title:
        die("empty title")
    if a.source and not SOURCE_RE.match(a.source):
        die(f"bad source '{a.source}', expected like Q3")
    for label, val in (("title", title), ("bullet", a.bullet or ""), ("from", a.source_of or "")):
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
        if a.kind == "Q":
            target = folder / own.QUEUE_MD
            if not target.is_file():
                tpl = Path(__file__).resolve().parent.parent / "templates" / "queue.md"
                target.write_text(tpl.read_text(encoding="utf-8").replace("[release]", a.release),
                                  encoding="utf-8")
        else:
            target = folder / "decisions.md"
            if not target.is_file():
                die(f"missing: {target}")
        ident = f"{a.kind}{highest([target], a.kind) + 1}"
        bullet = (a.bullet if a.bullet.startswith("- ") else f"- {a.bullet}") if a.bullet else None
        written = [target]

        if a.kind == "Q":
            who = a.source_of.strip().rstrip(".")
            block = [f"### {ident} {title}", "- Tags:", f"- From: {who}."] + ([bullet] if bullet else [])
            target.write_text(appended(target.read_text(encoding="utf-8"), block), encoding="utf-8")
        else:
            if a.source:
                queue = folder / own.QUEUE_MD
                if not any(e["num"] == int(a.source[1:]) for e in own.parse_queue(queue)):
                    die(f"{a.source} is not in {queue}")
            block = [f"### {ident} {title}", ""] + ([bullet] if bullet else [])
            if a.source:
                block.append(f"- Source: {a.source}")
            target.write_text(under_last_round(target.read_text(encoding="utf-8"), block, today),
                              encoding="utf-8")
            if a.source:
                entry = next(e for e in own.parse_queue(queue) if e["num"] == int(a.source[1:]))
                if re.fullmatch(r"D\d+", entry["tag"] or ""):
                    print(f"{a.source} keeps Tags {entry['tag']}", file=sys.stderr)
                else:
                    own.set_queue_tag(queue, int(a.source[1:]), ident)
                    written.append(queue)

        paths = [str(p) for p in written]
        git(root, "add", "--", *paths)
        git(root, "commit", "-q", "-m", f"docs(plan): {a.release} {ident} {title}", "--only", "--", *paths)
        fcntl.flock(lock, fcntl.LOCK_UN)
    print(ident)


if __name__ == "__main__":
    main()
