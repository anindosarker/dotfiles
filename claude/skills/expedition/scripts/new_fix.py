#!/usr/bin/env python3
"""Create a fix milestone in a release: run/trackers/fix-<slug>-tracker.md citing the findings
on its first line, then status/ownership.md and status/sprints.md regenerated so the fix has a grid row
in the running sprint column (the first column holding a "[ ]", else the last).

Usage: python3 -I new_fix.py <release> <slug> "F3, F4" [--files a,b] [--depends "<names>"]
       [--title "<Title>"] [--owner X] [--root PATH]

A fix milestone has a tracker and a grid row, no spec. Its name is the tracker title
without ", tracker": --title, else the slug in words, followed by the findings.
"""
import argparse
import importlib.util
import re
import sys
from pathlib import Path

RELEASE_RE = re.compile(r"^v\d+\.\d+\.x$")
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
FINDINGS_RE = re.compile(r"^[FDA]\d+(\s*,\s*[FDA]\d+)*$")


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


def tracker_text(title, files, depends):
    """templates/tracker.md head with the title, Status: planned, Files owned and Depends on lines."""
    path = Path(__file__).resolve().parent.parent / "templates" / "tracker.md"
    if not path.is_file():
        die(f"bundled template missing: {path}")
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            break
        if line.startswith("# "):
            line = f"# {title}, tracker"
        elif line.startswith("Status:"):
            out.append("Status: planned")
            out.append("Files owned: " + (", ".join(f"`{f}`" for f in files) if files else "none"))
            out.append(f"Depends on: {depends or 'none'}")
            continue
        out.append(line)
    return "\n".join(out).rstrip() + "\n"


def main():
    ap = argparse.ArgumentParser(
        usage='new_fix.py <release> <slug> "F3, F4" [--files a,b] [--depends "<names>"] '
              '[--title "<Title>"] [--owner X] [--root PATH]'
    )
    ap.add_argument("release")
    ap.add_argument("slug")
    ap.add_argument("findings")
    ap.add_argument("--files", default="")
    ap.add_argument("--depends", default="")
    ap.add_argument("--title")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: git top level)")
    a = ap.parse_args()
    if not RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    if not SLUG_RE.match(a.slug):
        die(f"bad slug '{a.slug}', expected lowercase-with-dashes")
    findings = a.findings.strip()
    if not FINDINGS_RE.match(findings):
        die(f"bad findings '{a.findings}', expected like \"F3, F4\"")
    findings = ", ".join(s.strip() for s in findings.split(","))
    for label, val in (("title", a.title or ""), ("files", a.files), ("depends", a.depends)):
        if "|" in val:
            die(f"{label} must not contain '|'")
        if "—" in val:
            die(f"{label} contains an em dash")
    files = [f.strip() for f in a.files.split(",") if f.strip()]
    words = a.title or a.slug.replace("-", " ").capitalize()
    title = f"{words} ({findings})"

    own = load("ownership")
    root = own.repo_root(a.root)
    folder = own.release_folder(root, own.detect_owner(root, a.owner), a.release)
    if not (folder / own.SPECS_DIR).is_dir():
        die(f"specs folder missing: {folder / own.SPECS_DIR}")
    trackers = folder / own.TRACKERS_DIR
    trackers.mkdir(parents=True, exist_ok=True)
    tracker = trackers / f"fix-{a.slug}-tracker.md"
    if tracker.exists():
        die(f"refusing to overwrite {tracker}")
    tracker.write_text(tracker_text(title, files, a.depends.strip()), encoding="utf-8")
    try:
        own.generate(folder, a.release, quiet=True)
    except SystemExit:
        tracker.unlink()
        die(f"ownership.py failed with the fix; {tracker.name} removed")
    print(tracker)
    print(folder / own.OWNERSHIP_MD)
    load("sprints").write(folder, a.release)
    load("swimlanes").write(folder, a.release)


if __name__ == "__main__":
    main()
