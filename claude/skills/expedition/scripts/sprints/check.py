#!/usr/bin/env python3
"""Check that the milestones of a release schedule (lib/ownership.py compute, in memory) and print
the milestone and column count and one critical path per epic. Writes nothing; exit 1 on an
error: a file shared by two milestones of one column, a dependency cycle, a milestone without a
Files owned line or with an unknown dependency. The spec writer runs it after each spec.

Usage: python3 -I sprints/check.py <release> [--owner X] [--root PATH]
"""
import argparse
import importlib.util
import sys
from pathlib import Path


def _common():
    name = "expedition_lib_common"
    if name not in sys.modules:
        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent.parent / "lib" / "common.py")
        sys.modules[name] = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sys.modules[name])
    return sys.modules[name]


C = _common()


def check(own, folder):
    """Plain run: the milestone and column count and each epic's critical path; exit 1 on an error."""
    comp = own.compute(folder)
    if not comp["milestones"] and not comp["errors"]:
        comp["errors"].append("no '### Milestone:' blocks in plan/specs/*.md")
    if comp["errors"]:
        own.print_errors(comp["errors"], "ownership does not own.compute")
    by_name = {m["name"]: m for m in comp["milestones"]}
    print(f"{len(comp['milestones'])} milestones, {max(comp['col'].values())} columns")
    for e, p in sorted(comp["paths"].items()):
        print(f"E{e} path: {own.path_text(p, by_name)}")


def main():
    ap = argparse.ArgumentParser(usage="sprints/check.py <release> [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        C.die(f"bad release '{a.release}', expected like v0.9.x")
    own = C.load("lib/ownership")
    root = own.repo_root(a.root, a.release)
    folder = own.release_folder(root, own.detect_owner(root, a.owner), a.release)
    if not (folder / own.SPECS_DIR).is_dir():
        own.die(f"specs folder missing: {folder / own.SPECS_DIR}")
    check(own, folder)


if __name__ == "__main__":
    main()
