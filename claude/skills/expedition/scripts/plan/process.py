#!/usr/bin/env python3
"""Print the release's process.md, for the skill to load at invocation. Read-only.

Usage: python3 -I plan/process.py [words...]

The release is the first word that is a release name (like v0.9.x); other words (the stage
words discuss, plan, run, triage) are ignored. With no release name, the highest-numbered
release folder that holds a process.md. The repository root and the owner come from
lib/common.py (the cwd or one level below it, as for every script).

Prints a header line with the absolute path of the file, then the file in full. Nothing found:
one line naming the folder searched. Always exits 0 and never prints a traceback, so a failure
never breaks the skill load.
"""
import contextlib
import importlib.util
import io
import re
import sys
from pathlib import Path


def load_common():
    sys.dont_write_bytecode = True
    path = Path(__file__).resolve().parent.parent / "lib" / "common.py"
    spec = importlib.util.spec_from_file_location("expedition_lib_common", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["expedition_lib_common"] = mod
    spec.loader.exec_module(mod)
    return mod


def release_key(name):
    return tuple(int(x) for x in re.findall(r"\d+", name))


def find(words):
    """(path or None, the folder searched)."""
    C = load_common()
    release = next((w for w in words if C.RELEASE_RE.match(w)), None)
    searched = Path.cwd()
    with contextlib.redirect_stderr(io.StringIO()):
        try:
            root = C.repo_root(None, release, new=release is None)
            if not (root / ".ai" / "plans").is_dir():
                root = C.repo_root(None, None, new=True)
            searched = root / ".ai" / "plans"
            owner = C.detect_owner(root, None)
        except SystemExit:
            return None, searched
    if release:
        path = searched / release / owner / "process.md"
        return (path if path.is_file() else None), path.parent
    found = sorted(
        (p for p in searched.glob(f"v*.x/{owner}/process.md") if C.RELEASE_RE.match(p.parent.parent.name)),
        key=lambda p: release_key(p.parent.parent.name),
    )
    return (found[-1] if found else None), searched


def main():
    try:
        path, searched = find(sys.argv[1:])
        if path is None:
            print(f"No process.md found; searched {searched}")
            return
        print(f"process.md: {path.resolve()}")
        sys.stdout.write(path.read_text(encoding="utf-8"))
    except BaseException as e:  # never break the skill load
        print(f"No process.md found; searched from {Path.cwd()} ({type(e).__name__}: {e})")


if __name__ == "__main__":
    main()
    sys.exit(0)
