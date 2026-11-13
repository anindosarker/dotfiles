#!/usr/bin/env python3
"""Print the owner's progress reply, in Markdown, and nothing else.

Usage: python3 -I status/progress.py <release> [--owner X] [--root PATH]

One block per epic with an unfinished row in status/sprints.md ("[ ]", "·" or "[!]"):
"**E<n>** · Specs d/t" (t the epic's specs in the grid, d those whose rows are all "[x]"), then
"- **Running**" (specs with a "[ ]" row) and "- **Blocked**" (specs with a "[!]" row, with the
first ## Attention bullet of that milestone's tracker as the reason), each spec as its number
and its Deliverables title. With nothing unfinished: the last epic's line, then
"Nothing running." and the unticked Decided cards of queue.md as "Ready for an epic: **Q<n>**, ...".
"""
import argparse
import collections
import importlib.util
import re
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
GRID_ROW_RE = re.compile(r"^E(\d+)\s+(\d{2}(?:\.\d+)?)\s+(.*)$")
UNFINISHED = ("[ ]", "·", "[!]")


num_key = C.spec_key


def print_progress(folder, plan, own, bd, q_text):
    """The owner's progress reply, from status/sprints.md, the Deliverables titles, the
    milestone trackers' ## Attention and the Decided lane of queue.md."""
    sprints = folder / C.SPRINTS_MD
    head, data = C.table_rows(C.read(sprints), "Milestone") if sprints.is_file() else (None, [])
    epics = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in data if head else []:
        m = GRID_ROW_RE.match(r[0]) if r else None
        if m:
            epics[int(m.group(1))][m.group(2)].append((m.group(3), r[1:]))
    titles = own.spec_titles(plan)
    trackers = {(num, b["name"]): b["tracker"]
                for num, bl in own.new_collect(folder, plan)["blocks"].items() for b in bl}
    done_row = lambda cells: "[x]" in cells and not any(c in UNFINISHED for c in cells)
    open_row = lambda cells: any(c in UNFINISHED for c in cells)

    def counts(specs):
        return sum(1 for rows in specs.values() if all(done_row(c) for _, c in rows)), len(specs)

    def title(num, rows):
        return titles.get(num) or rows[0][0]

    blocks = []
    for e in sorted(epics):
        specs = epics[e]
        if not any(open_row(c) for rows in specs.values() for _, c in rows):
            continue
        d, t = counts(specs)
        lines = [f"**E{e}** · Specs {d}/{t}"]
        nums = sorted(specs, key=num_key)
        running = [n for n in nums if any("[ ]" in c for _, c in specs[n])]
        blocked = [n for n in nums if any("[!]" in c for _, c in specs[n])]
        if running:
            lines.append("- **Running**")
            lines += [f"  - {n} {title(n, specs[n])}" for n in running]
        if blocked:
            lines.append("- **Blocked**")
            for n in blocked:
                reason = next((r for name, c in specs[n] if "[!]" in c
                               if (r := own.attention_reason(trackers.get((n, name))))), None)
                lines.append(f"  - {n} {title(n, specs[n])}" + (f": {reason}" if reason else ""))
        blocks.append("\n".join(lines))
    if blocks:
        print("\n\n".join(blocks))
        return
    ready = [f"**Q{c['num']}**" for c in bd.parse(q_text)["cards"]
             if c["lane"] == "Decided" and c["box"] != "x"]
    tail = "Nothing running." + (f" Ready for an epic: {', '.join(ready)}" if ready else "")
    if epics:
        last = max(epics)
        d, t = counts(epics[last])
        print(f"**E{last}** · Specs {d}/{t}\n\n{tail}")
    else:
        print(tail)


def main():
    ap = argparse.ArgumentParser(usage="status/progress.py <release> [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        C.die(f"bad release '{a.release}', expected like v0.9.x")
    root = C.repo_root(a.root, a.release)
    folder = C.release_folder(root, C.detect_owner(root, a.owner), a.release)
    queue = folder / C.QUEUE_MD
    q_text = C.read(queue) if queue.is_file() else ""
    print_progress(folder, folder / f"{a.release}-plan.md", C.load("lib/ownership"), C.load("lib/board"), q_text)


if __name__ == "__main__":
    main()
