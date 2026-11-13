#!/usr/bin/env python3
"""Print the owner's progress reply, in Markdown, on stdout and nothing else; each disagreement
between its sources goes to stderr as one line starting "warning: ".

Usage: python3 -I status/progress.py <release> [--owner X] [--root PATH]

One block per epic with an unfinished milestone: "**E<n>** · Specs d/t" (t the epic's specs in
the grid, d those whose milestones are all done), then "- **Running**" (specs with a running
milestone) and "- **Blocked**" (specs with a stopped or waiting milestone, each with its reason),
each spec as its number and its Deliverables title. With nothing unfinished: the last epic's
line, then "Nothing running." and the unticked Decided cards of queue.md as
"Ready for an epic: **Q<n>**, ...".

Sources, for each milestone whose grid cell is not "[x]":
- the grid cell of status/sprints.md ("[ ]" running, "·" not started, "[!]" stopped);
- the tracker's Status line, from the most advanced copy (planned < running < waiting < merged,
  done or skipped) among the main checkout (the first entry of git worktree list) and the
  worktree whose checked-out branch is the one the copy's own "Branch" line names, the milestone's
  own worktree. A worktree on another branch holds an inherited snapshot, not the milestone's
  state, and is left out; when no copy names a branch checked out anywhere, every worktree's copy
  counts. The main checkout's copy stays "planned" until the merge writes "merged (<sha>)" there.
Results: a tracker merged (or done) counts as done whatever the cell says; "skipped" counts as
stopped; a "waiting (lead: <what>)" or "waiting (owner: <what>)" milestone is listed under Blocked
as "<spec> <title>: waits on the lead: <what>" (or the owner), never under Running; a "[!]" cell
gives the first ## Attention bullet of the tracker as the reason, as before; a running tracker
under a "·" cell counts as running. Each case where the grid and the tracker disagree prints a
warning. No network, no runner, no tmux: files and one git call.
"""
import argparse
import collections
import importlib.util
import re
import subprocess
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
BRANCH_RE = re.compile(r"^Branch\s+`([^`]+)`", re.M)
CELL_WORDS = {"[ ]": "running", "·": "not started", "[!]": "stopped", "[x]": "merged", "": "empty"}
num_key = C.spec_key


def worktrees(root):
    """[(path, branch or None)] from git worktree list --porcelain; the main checkout first."""
    r = subprocess.run(["git", "-C", str(root), "worktree", "list", "--porcelain"],
                       capture_output=True, text=True)
    out, cur = [], None
    for line in r.stdout.splitlines() if r.returncode == 0 else []:
        if line.startswith("worktree "):
            cur = [Path(line[len("worktree "):]), None]
            out.append(cur)
        elif line.startswith("branch ") and cur:
            cur[1] = line[len("branch "):].removeprefix("refs/heads/")
    return [tuple(w) for w in out] or [(root, None)]


def tracker_state(own, rel, wts):
    """The most advanced (state, inner text, Status value) of the tracker at rel (a path relative
    to the repository) over the copies that count, or None when no copy has a Status line."""
    copies = []
    for i, (wt, branch) in enumerate(wts):
        p = wt / rel
        if not p.is_file():
            continue
        text = C.read(p)
        v = own.status_value(text)
        if v:
            b = BRANCH_RE.search(text)
            copies.append((i == 0, branch is not None and b is not None and b.group(1) == branch, v))
    own_copies = [c for c in copies if c[1]]
    use = [c for c in copies if c[0] or c[1]] if own_copies else copies
    if not use:
        return None
    return max(use, key=lambda c: (own.STATUS_RANK[c[2][0]], c[1]))[2]


def effective(cell, status):
    """(kind, reason, warning) of one milestone: kind done, running, waiting, stopped or planned."""
    word = CELL_WORDS.get(cell, cell)
    if status is None:
        kind = {"[ ]": "running", "[!]": "stopped", "[x]": "done"}.get(cell, "planned")
        return kind, None, None
    state, inner, value = status
    disagree = f"grid says {word}, tracker says {value}"
    if state in ("merged", "done"):
        return "done", None, disagree if cell != "[x]" else None
    if state == "skipped":
        return "stopped", None, disagree if cell != "[!]" else None
    if cell == "[!]":
        return "stopped", None, disagree if state == "waiting" else None
    if state == "waiting":
        m = own_waiting(inner)
        reason = f"waits on the {m[0]}: {m[1]}" if m else f"waits: {inner}" if inner else "waits"
        return "waiting", reason, disagree
    if state == "running":
        return "running", None, disagree if cell != "[ ]" else None
    return ("running" if cell == "[ ]" else "planned"), None, None


def own_waiting(inner):
    m = C.load("lib/ownership").WAITING_RE.match(inner or "")
    return (m.group(1), m.group(2)) if m else None


def print_progress(root, folder, plan, own, bd, q_text):
    """The owner's progress reply on stdout, the disagreements on stderr."""
    sprints = folder / C.SPRINTS_MD
    head, data = C.table_rows(C.read(sprints), "Milestone") if sprints.is_file() else (None, [])
    epics = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in data if head else []:
        m = GRID_ROW_RE.match(r[0]) if r else None
        if m:
            cells = r[1:]
            cell = next((c for c in cells if c), "")
            epics[int(m.group(1))][m.group(2)].append({"name": m.group(3), "cell": cell})
    titles = own.spec_titles(plan)
    trackers = {(num, b["name"]): b["tracker"]
                for num, bl in own.new_collect(folder, plan)["blocks"].items() for b in bl}
    wts = None
    for e in sorted(epics):
        for num in sorted(epics[e], key=num_key):
            for row in epics[e][num]:
                path = trackers.get((num, row["name"]))
                if row["cell"] == "[x]":
                    row.update(kind="done", reason=None, path=path)
                    continue
                if wts is None:
                    wts = worktrees(root)
                status = tracker_state(own, path.relative_to(root), wts) if path else None
                kind, reason, warn = effective(row["cell"], status)
                row.update(kind=kind, reason=reason, path=path)
                if warn:
                    print(f"warning: {num} {row['name']}: {warn}", file=sys.stderr)

    def counts(specs):
        return sum(1 for rows in specs.values() if all(r["kind"] == "done" for r in rows)), len(specs)

    def title(num, rows):
        return titles.get(num) or rows[0]["name"]

    def why(rows):
        for r in rows:
            if r["kind"] == "waiting":
                return r["reason"]
            if r["kind"] == "stopped" and (a := own.attention_reason(r["path"])):
                return a
        return None

    blocks = []
    for e in sorted(epics):
        specs = epics[e]
        if all(r["kind"] == "done" for rows in specs.values() for r in rows):
            continue
        d, t = counts(specs)
        lines = [f"**E{e}** · Specs {d}/{t}"]
        nums = sorted(specs, key=num_key)
        running = [n for n in nums if any(r["kind"] == "running" for r in specs[n])]
        blocked = [n for n in nums if any(r["kind"] in ("stopped", "waiting") for r in specs[n])]
        if running:
            lines.append("- **Running**")
            lines += [f"  - {n} {title(n, specs[n])}" for n in running]
        if blocked:
            lines.append("- **Blocked**")
            for n in blocked:
                reason = why([r for r in specs[n] if r["kind"] in ("stopped", "waiting")])
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
    print_progress(root, folder, folder / f"{a.release}-plan.md", C.load("lib/ownership"),
                   C.load("lib/board"), q_text)


if __name__ == "__main__":
    main()
