#!/usr/bin/env python3
"""Compute the ownership facts of a release from the milestone blocks of its specs, in memory.
No file holds them: sprints.py, swimlanes.py, status.py, new_fix.py and go.py call compute().

Usage: python3 -I ownership.py <release> [--owner X] [--root PATH]
       python3 -I ownership.py <release> --epic E<n> [<spec numbers>]
       python3 -I ownership.py <release> --overlap <spec numbers or D ids>
       python3 -I ownership.py <release> --backfill-starts [--dry-run]

Plain: prints the milestone and column count and one critical path per epic; writes nothing;
exit 1 on an error (below). The spec writer runs it after each spec.

Reads every plan/specs/NN-<slug>.md for "### Milestone: <name>" blocks ("#### Milestone:"
is accepted too) with the lines "- Files owned: a, b", "- Depends on: <milestone names,
spec numbers or none>" and "- Review: none | fable", and the optional "- Starts: S<n>" (a
milestone added after its epic's go, by new_fix.py: its own start sprint).

Edges: A to B when B lists A (or A's spec number) under Depends on, or when A and B
share a file (lower spec number first). Two milestones of one spec that share a file
while neither depends on the other are a collision; a dependency cycle is an error.

A milestone's column is the longest chain ending at it plus one, over every epic, and never
before its epic's start sprint: the "Starts: S<n>" line of plan/epics/E<n>.md (new_spec.py
--epic writes it on go), nor before the milestone's own "- Starts: S<n>" line. The floor
propagates along the edges; an epic file without a Starts value means no floor. A milestone
whose status/sprints.md row is running ("[ ]") or finished ("[x]", "[!]") keeps that column, and
a finished one never collides on a shared file. --epic E<n> <spec numbers> uses the current
sprint as a provisional floor for an epic with no Starts value yet, writing no Starts line.
The current sprint is the first column of status/sprints.md holding a "[ ]" or "·" cell of an
epic row; when there is none, the column after the last column holding an epic row (S1 for an
empty grid). For an epic's own start its own rows are ignored.

Critical path per epic, computed on the fly (never stored): over that epic's milestones only (a
spec's epic is its "- Epic: E<n>" line), with the Depends on and
shared-file edges inside the epic; the longest chain, ties by lower spec number.

Epic table: python3 -I ownership.py <release> --epic E<n> [<spec numbers>], the pre-go preview
(the spec writer, then the lead's check reads its result). The epic's specs: the specs with an
"- Epic: E<n>" line, plus the spec numbers given, else (no Starts value yet) every untagged spec
citing a decision of the epic's "Decisions:" line; untagged ones count as E<n>. It fills the
Spec, Milestone and Sprint columns of the "## Ownership" table in plan/epics/E<n>.md
(reference/formats.md, Epic file): one row per decision and spec of the epic citing it, the
Files a decision row carried split over those rows by the spec that owns each file (a file no
citing spec owns stays on the lowest spec's row), one row with an empty Decision cell per spec
of the epic citing none of its decisions; Milestone is the spec's milestone names joined by
"; ", Sprint its column, "S17 to S19" when its milestones span several. Before go the sprints
are provisional (the current sprint as the epic's start); a milestone with a grid row takes the
grid's column. Rows ordered by sprint, spec number, decision number. Then it prints the facts:
the sprints the epic spans, its critical path, every pair of the epic's specs owning the same
file, each Files path that does not exist yet ("new or missing": a new file and a typo look
the same), and a row file no milestone of its spec
owns. No verdict. Commits nothing. Exit 1 only for an error below or an unreadable table.

Backfill: ownership.py <release> --backfill-starts [--dry-run] writes "Starts: S<n>" into the
epic file of every epic that has rows in status/sprints.md and no Starts value: the lowest
column among its finished rows ("[x]", "[!]"), else the current sprint (that epic's own rows
ignored). It commits nothing and prints the value per epic and every row whose column changes
at the next ownership.py and sprints.py run, with its old and new column. Finished rows never
move: sprints.py keeps their cells; a running row carries its "[ ]" to its new column.

Errors: a file shared by two milestones of one column, a dependency cycle, a milestone without
a Files owned line or with an unknown dependency. On an error nothing is written, exit 1.

Layout: the release folder must hold plan/ (plan/specs, plan/epics), run/ (run/trackers,
run/handoffs), status/ and queue.md. A folder without plan/ is refused with one line naming
migrate_layout.py; a folder still on the old queue files, or with a queue.md that is not yet a
kanban board, is refused with one line naming migrate_queue.py; a folder that still has
status/ownership.md is refused with one line naming migrate_epics.py; a folder that still has
run/trackers/fix-*-tracker.md (free-standing fix milestones of older releases) is refused with
one line naming migrate_fixes.py.

Check mode: ownership.py <release> --overlap <spec numbers or D ids> writes nothing. It
reports every file the named specs' milestones own (for a D id: the specs citing it) that a
milestone of a running epic also owns. A running epic is a [E<n>] tag in decisions.md on a
decision without [Done]; a spec's epic is its own "- Epic: E<n>" line (new_spec.py --epic).
Exit code 1 when a file is shared, 0 otherwise.
"""
import argparse
import collections
import datetime
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

RELEASE_RE = re.compile(r"^v\d+\.\d+\.x$")
SPEC_FILE_RE = re.compile(r"^(\d{2}(?:\.\d+)?)-([a-z0-9]+(?:-[a-z0-9]+)*)\.md$")
SPEC_NUM_RE = re.compile(r"^\d{2}(?:\.\d+)?$")
MILESTONE_RE = re.compile(r"^#{3,4}\s+Milestone:\s*(.+?)\s*$")
HEADING_RE = re.compile(r"^#{1,6}\s")
FIELD_RE = re.compile(r"^\s*(?:-\s*)?(Files owned|Depends on|Review|Starts):\s*(.*?)\s*$")
TASK_RE = re.compile(r"^\s*-\s*Task\s+\d+:")
SPECS_DIR = "plan/specs"
EPICS_DIR = "plan/epics"
TRACKERS_DIR = "run/trackers"
QUEUE_MD = "queue.md"
HANDOFFS_DIR = "run/handoffs"
STATUS_DIR = "status"
SPRINTS_MD = "status/sprints.md"
LEGACY_OWNERSHIP_MD = "status/ownership.md"
LEGACY_FIX_GLOB = "fix-*-tracker.md"
D_HEAD_RE = re.compile(r"^###\s+D(\d+)\b")
TAG_LINE_RE = re.compile(r"^\s*(?:\[(?:Done|E\d+)\]\s*)+$")
D_CITE_RE = re.compile(r"\((D\d+[^)]*)\)")
D_ID_RE = re.compile(r"^D(\d+)$")
EPIC_LINE_RE = re.compile(r"^\s*-\s*Epic:\s*E(\d+)\s*$")


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def repo_root(flag, release, new=False):
    """The repository root every script works in. Order: --root; else the git top level of the
    cwd when it holds .ai/plans/<release>/; else the one direct child folder of the cwd or of
    that top level that holds it. new=True (new_cycle.py, release not made yet) looks for
    .ai/plans/ instead. Several matches stop with the list. No match falls back to the git top
    level, so the caller's usual error follows."""
    if flag:
        p = Path(flag).resolve()
        if not p.is_dir():
            die(f"root not a folder: {p}")
        return p
    mark = Path(".ai", "plans") if new else Path(".ai", "plans", release)
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
        top = Path(out.stdout.strip()) if out.returncode == 0 else None
    except FileNotFoundError:
        top = None
    if top and (top / mark).is_dir():
        return top
    found = []
    for base in (Path.cwd(), top):
        try:
            kids = sorted(base.iterdir()) if base else []
        except OSError:
            continue
        for d in kids:
            try:
                hit = d.is_dir() and (d / mark).is_dir()
            except OSError:
                hit = False
            if hit and d.resolve() not in found:
                found.append(d.resolve())
    if len(found) == 1:
        return found[0]
    if found:
        die(f"several folders hold {mark}/; pass --root with one of:\n"
            + "\n".join(f"  {d}" for d in found))
    if top is None:
        die("not inside a git repository")
    return top


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


RENDER_IGNORES = (".ai/plans/*/*/status/index.html", ".ai/plans/*/*/status/data/")


def ignore_renders(folder):
    """Append the status/ render lines to the repo's .gitignore when missing (repo root from
    git rev-parse run in the plan folder). index.html and data/ are regenerated by
    swimlanes.py and never committed; sprints.md stays in git."""
    r = subprocess.run(["git", "-C", str(folder), "rev-parse", "--show-toplevel"],
                       capture_output=True, text=True)
    if r.returncode:
        print(f"warning: {folder} is not in a git repo; .gitignore not touched", file=sys.stderr)
        return
    path = Path(r.stdout.strip()) / ".gitignore"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    have = {l.strip() for l in text.splitlines()}
    missing = [l for l in RENDER_IGNORES if l not in have]
    if missing:
        sep = "" if not text or text.endswith("\n") else "\n"
        path.write_text(text + sep + "".join(l + "\n" for l in missing), encoding="utf-8")
        print(f"{path}: added {', '.join(missing)}")


def release_folder(root, owner, release):
    folder = root / ".ai" / "plans" / release / owner
    if not folder.is_dir():
        die(f"release folder missing: {folder}")
    if not (folder / "plan").is_dir():
        die(f"{folder} has the old layout (no plan/): run python3 -I "
            f"{Path(__file__).resolve().parent / 'migrate_layout.py'} {release}")
    old = load_sibling("migrate_queue").refusal(folder, release)
    if old:
        die(old)
    if (folder / LEGACY_OWNERSHIP_MD).is_file():
        die(f"{folder} still has {LEGACY_OWNERSHIP_MD}: run python3 -I "
            f"{Path(__file__).resolve().parent / 'migrate_epics.py'} {release}")
    fixes = legacy_fixes(folder)
    if fixes:
        die(f"{folder} still has {len(fixes)} free-standing fix trackers ({fixes[0].name}): run python3 -I "
            f"{Path(__file__).resolve().parent / 'migrate_fixes.py'} {release} --dry-run, then without --dry-run")
    return folder


def legacy_fixes(folder):
    """The run/trackers/fix-<slug>-tracker.md files of an unmigrated folder, sorted."""
    return sorted((folder / TRACKERS_DIR).glob(LEGACY_FIX_GLOB))


def load_sibling(name):
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def num_key(num):
    if num is None:
        return (1,)
    return (0,) + tuple(int(x) for x in num.split("."))


def read(p):
    return p.read_text(encoding="utf-8", errors="replace")


def split_files(value):
    """Files from a 'Files owned' value: the backticked spans, else comma parts; 'none' is empty."""
    value = value.strip()
    if not value or value.lower().rstrip(".") == "none":
        return []
    spans = re.findall(r"`([^`]+)`", value)
    if spans:
        return [s.strip() for s in spans if s.strip()]
    return [s.strip() for s in value.split(",") if s.strip()]


def outside_fences(text):
    fence = None
    for i, line in enumerate(text.splitlines(), 1):
        s = line.lstrip()
        m = re.match(r"^(`{3,}|~{3,})", s)
        if m:
            mark = m.group(1)
            if fence is None:
                fence = mark
            elif mark[0] == fence[0] and len(mark) >= len(fence) and s.strip() == mark:
                fence = None
            continue
        if fence is None:
            yield i, line


def parse_spec(path):
    """Milestone blocks of one spec file, in order.

    Each block: dict name, line, files (list or None when the line is missing),
    deps (raw text or None), review (text or None), starts (column number or None),
    tasks (list of (line, text)).
    """
    blocks = []
    cur = None
    level = None
    for i, line in outside_fences(read(path)):
        m = MILESTONE_RE.match(line)
        if m:
            cur = {"name": m.group(1), "line": i, "files": None, "deps": None,
                   "review": None, "starts": None, "tasks": []}
            level = len(line) - len(line.lstrip("#"))
            blocks.append(cur)
            continue
        if cur is None:
            continue
        if HEADING_RE.match(line) and len(line) - len(line.lstrip("#")) <= level:
            cur = None
            continue
        f = FIELD_RE.match(line)
        if f:
            key, val = f.group(1), f.group(2)
            if key == "Files owned":
                cur["files"] = split_files(val)
            elif key == "Depends on":
                cur["deps"] = val
            elif key == "Starts":
                s = SPRINT_VALUE_RE.match(val)
                cur["starts"] = int(s.group(1)) if s else None
            else:
                cur["review"] = val
        elif TASK_RE.match(line):
            cur["tasks"].append((i, line.strip()))
    return blocks


def spec_files(folder):
    d = folder / SPECS_DIR
    if not d.is_dir():
        return []
    out = []
    for p in d.iterdir():
        m = SPEC_FILE_RE.match(p.name)
        if p.is_file() and m:
            out.append((m.group(1), p))
    return sorted(out, key=lambda x: num_key(x[0]))


def resolve_deps(text, names, specs):
    """Milestone names a Depends on value lists; spec numbers expand to the spec's milestones.

    Returns (resolved names, unknown parts). Known names may contain commas.
    """
    if text is None:
        return [], []
    rest = text.strip()
    if not rest or rest.lower().rstrip(".") == "none":
        return [], []
    found = []
    for name in sorted(names, key=len, reverse=True):
        pat = re.compile(r"(?:^|(?<=[,\s]))" + re.escape(name) + r"(?=\s*(?:,|$))")
        if pat.search(rest):
            found.append(name)
            rest = pat.sub("", rest)
    unknown = []
    for part in (s.strip().strip("`") for s in rest.split(",")):
        if not part:
            continue
        num = re.sub(r"^(?:spec\s+)", "", part, flags=re.I)
        if SPEC_NUM_RE.match(num) and num in specs:
            found.extend(specs[num])
        else:
            unknown.append(part)
    order = {n: i for i, n in enumerate(names)}
    return sorted(set(found), key=lambda n: order.get(n, 0)), unknown


def collect(folder):
    """Return (milestones, errors). A milestone: name, spec, order, deps (names), files, review."""
    errors = []
    raw = []
    for num, path in spec_files(folder):
        blocks = parse_spec(path)
        for b in blocks:
            b["spec"] = num
            b["path"] = path
            raw.append(b)
    names = [b["name"] for b in raw]
    for name, c in collections.Counter(names).items():
        if c > 1:
            where = ", ".join(sorted({str(b["path"].relative_to(folder)) for b in raw if b["name"] == name}))
            errors.append(f"milestone '{name}' defined {c} times: {where}")
    specs = collections.defaultdict(list)
    for b in raw:
        specs[b["spec"]].append(b["name"])
    out = []
    for i, b in enumerate(raw):
        where = f"{b['path'].relative_to(folder)}:{b['line']}"
        if "|" in b["name"]:
            errors.append(f"{where}: milestone name '{b['name']}' contains '|'")
        if b["files"] is None:
            errors.append(f"{where}: milestone '{b['name']}' has no Files owned line")
        for f in b["files"] or []:
            if "|" in f:
                errors.append(f"{where}: file '{f}' contains '|'")
        deps, unknown = resolve_deps(b["deps"], [n for n in names if n != b["name"]], specs)
        deps = [d for d in deps if d != b["name"]]
        for u in unknown:
            errors.append(f"{where}: milestone '{b['name']}' depends on unknown '{u}'")
        out.append({"name": b["name"], "spec": b["spec"], "order": i, "deps": deps,
                    "files": b["files"] or [], "review": b.get("review"), "starts": b.get("starts")})
    return out, errors


def schedule(milestones, floor=None, fixed=None):
    """Return (columns, graph, errors, warnings) for milestones with resolved deps.

    floor: {name: lowest column} (the epic's start sprint); the column is never below it.
    fixed: {name: (column, finished)} of the started milestones (a "[ ]", "[x]" or "[!]" grid
    cell): they keep that column; two milestones sharing a file never collide when one of them
    is finished ("[x]" or "[!]").

    milestones: list of dicts name, spec, order, deps, files.
    graph: {"succ": {name: set of successors}, "derived": {name: {pred: [files]}}}, the
    explicit and shared-file edges the columns come from; derived holds the shared-file ones.
    """
    errors, warnings = [], []
    by_name = {m["name"]: m for m in milestones}
    succ = collections.defaultdict(set)
    explicit = collections.defaultdict(set)
    for m in milestones:
        for d in m["deps"]:
            if d in by_name:
                succ[d].add(m["name"])
                explicit[d].add(m["name"])

    def reaches(a, b):
        seen, stack = set(), [a]
        while stack:
            x = stack.pop()
            if x == b:
                return True
            if x in seen:
                continue
            seen.add(x)
            stack.extend(explicit[x])
        return False

    derived = collections.defaultdict(dict)
    owners = collections.defaultdict(list)
    for m in milestones:
        for f in m["files"]:
            if m["name"] not in owners[f]:
                owners[f].append(m["name"])
    for f, names in owners.items():
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                if reaches(a, b) or reaches(b, a):
                    continue
                ea, eb = by_name[a]["spec"], by_name[b]["spec"]
                if ea == eb:
                    errors.append(f"collision: file '{f}' owned by '{a}' and '{b}' (spec {ea}), neither depends on the other")
                    continue
                lo, hi = (a, b) if num_key(ea) < num_key(eb) else (b, a)
                succ[lo].add(hi)
                derived[hi].setdefault(lo, []).append(f)

    indeg = {m["name"]: 0 for m in milestones}
    for a in succ:
        for b in succ[a]:
            indeg[b] += 1
    order_of = {m["name"]: m["order"] for m in milestones}
    ready = sorted((n for n, d in indeg.items() if d == 0), key=order_of.get)
    topo = []
    while ready:
        n = ready.pop(0)
        topo.append(n)
        for b in sorted(succ[n], key=order_of.get):
            indeg[b] -= 1
            if indeg[b] == 0:
                ready.append(b)
        ready.sort(key=order_of.get)
    if len(topo) < len(milestones):
        left = {n for n, d in indeg.items() if d > 0}
        errors.append("dependency cycle: " + " > ".join(find_cycle(left, succ)))
        return {}, {}, errors, warnings

    floor, fixed = floor or {}, fixed or {}
    col, prev = {}, {}
    for n in topo:
        col[n] = fixed[n][0] if n in fixed else max(col.get(n, 1), floor.get(n, 1))
        for b in succ[n]:
            if col[n] + 1 > col.get(b, 1):
                col[b] = col[n] + 1
                prev[b] = n
            elif col[n] + 1 == col.get(b, 1) and b not in prev:
                prev[b] = n
    for f, names in owners.items() if not errors else ():
        seen = {}
        for n in names:
            if n in fixed and fixed[n][1]:
                continue
            if col[n] in seen:
                errors.append(f"collision: file '{f}' owned by '{seen[col[n]]}' and '{n}' in column S{col[n]}")
            seen[col[n]] = n

    return col, {"succ": succ, "derived": derived, "topo": topo}, errors, warnings


def epic_paths(milestones, graph, epic_of):
    """{epic: [names]}: per epic, the longest chain over that epic's milestones and the graph
    edges between them; ties by lower spec number (then milestone order) along the chain."""
    by_name = {m["name"]: m for m in milestones}
    key = lambda n: (num_key(by_name[n]["spec"]), by_name[n]["order"])
    better = lambda a, b: (len(a), [tuple(-x for x in k[0]) + (-k[1],) for k in map(key, a)]) > \
        (len(b), [tuple(-x for x in k[0]) + (-k[1],) for k in map(key, b)])
    out = {}
    for e in sorted({v for v in epic_of.values() if v}):
        inside = {n for n in by_name if epic_of.get(n) == e}
        best = {}
        for n in graph["topo"]:
            if n not in inside:
                continue
            chain = [n]
            for p, succs in graph["succ"].items():
                if p in inside and n in succs and p in best and better(best[p] + [n], chain):
                    chain = best[p] + [n]
            best[n] = chain
        top = []
        for chain in best.values():
            if not top or better(chain, top):
                top = chain
        out[e] = top
    return out


def epic_of_milestones(folder, milestones, assume=None):
    """{name: epic number or None} from each spec's Epic line; assume maps spec numbers to an epic."""
    assume = assume or {}
    epics = {num: spec_epic(path) for num, path in spec_files(folder)}
    return {m["name"]: assume.get(m["spec"]) or epics.get(m["spec"]) for m in milestones}


STARTS_RE = re.compile(r"^Starts:[ \t]*(.*?)\s*$", re.M)
SPRINT_VALUE_RE = re.compile(r"^S(\d+)$")


def epic_starts(folder):
    """{epic number: Starts value as written ("" when empty, None when the line is missing)}
    for every plan/epics/E<n>.md."""
    out = {}
    for p in sorted((folder / EPICS_DIR).glob("E*.md")):
        m = re.match(r"^E(\d+)\.md$", p.name)
        if m:
            s = STARTS_RE.search(read(p))
            out[int(m.group(1))] = s.group(1) if s else None
    return out


def grid(folder):
    """(column count, [(row label, cells)]) of status/sprints.md; (0, []) when missing."""
    path = folder / SPRINTS_MD
    if not path.is_file():
        return 0, []
    head, data = table_rows(read(path), "Milestone")
    if head is None:
        return 0, []
    n = len(head) - 1
    return n, [(r[0], (r[1:] + [""] * n)[:n]) for r in data if r and r[0]]


def current_sprint(folder, exclude=None):
    """The first column holding a "[ ]" or "·" cell of an epic row, else the column after the
    last column holding an epic row (1-based, 1 for an empty grid). The rows of epic exclude (a
    number) are ignored."""
    n, rows = grid(folder)
    epic = []
    for label, cells in rows:
        m = re.match(r"^E(\d+)\s", label)
        if m and int(m.group(1)) != exclude:
            epic.append(cells)
    for i in range(n):
        if any(c[i] in ("[ ]", "·") for c in epic):
            return i + 1
    used = [i + 1 for c in epic for i, x in enumerate(c) if x]
    return max(used) + 1 if used else 1


def started_columns(folder, milestones):
    """{milestone name: (grid column, finished)} of each milestone whose status/sprints.md row
    is running ("[ ]") or finished ("[x]" or "[!]")."""
    names = {m["name"] for m in milestones}
    out = {}
    for label, cells in grid(folder)[1]:
        m = re.match(r"^E\d+\s+\d{2}(?:\.\d+)?\s+(.*)$", label)
        name = m.group(1) if m else label
        at = next((i + 1 for i, c in enumerate(cells) if c in ("[ ]", "[x]", "[!]")), None)
        if name in names and at:
            out[name] = (at, cells[at - 1] != "[ ]")
    return out


def floors(folder, milestones, assume=None):
    """{milestone name: start sprint} from the epic files; an epic named by assume with no
    Starts value gets the current sprint (the pre-go preview). A milestone's own Starts line
    raises its floor."""
    starts = epic_starts(folder)
    provisional = set((assume or {}).values())
    cur = {}
    out = {}
    for name, epic in epic_of_milestones(folder, milestones, assume).items():
        if not epic:
            continue
        v = SPRINT_VALUE_RE.match(starts.get(epic) or "")
        if v:
            out[name] = int(v.group(1))
        elif epic in provisional:
            cur.setdefault(epic, current_sprint(folder, exclude=epic))
            out[name] = cur[epic]
    for m in milestones:
        if m.get("starts"):
            out[m["name"]] = max(out.get(m["name"], 1), m["starts"])
    return out


def set_starts(path, value):
    """Write "Starts: <value>" under the Specs: line of an epic file. Returns the value kept when
    one is already there, else None."""
    text = read(path)
    m = STARTS_RE.search(text)
    if m and m.group(1):
        return m.group(1)
    lines = text.split("\n")
    if m:
        i = text[:m.start()].count("\n")
        lines[i] = f"Starts: {value}"
    else:
        i = next((k for k, l in enumerate(lines) if l.startswith("Specs:")), None)
        if i is None:
            i = next((k for k, l in enumerate(lines) if l.startswith("Decisions:")), 0)
        lines.insert(i + 1, f"Starts: {value}")
    path.write_text("\n".join(lines), encoding="utf-8")
    return None


def backfill_starts(folder, dry_run=False):
    """--backfill-starts: Starts for every epic with grid rows and an epic file without one."""
    n, rows = grid(folder)
    starts = epic_starts(folder)
    by_epic = collections.defaultdict(list)
    for label, cells in rows:
        m = re.match(r"^E(\d+)\s", label)
        if m:
            by_epic[int(m.group(1))].append((label, cells))
    written = {}
    for e in sorted(by_epic):
        path = folder / EPICS_DIR / f"E{e}.md"
        if not path.is_file():
            print(f"E{e}: no epic file, no floor")
            continue
        if starts.get(e):
            print(f"E{e}: Starts: {starts[e]} kept")
            continue
        done = [i + 1 for _, cells in by_epic[e] for i, c in enumerate(cells) if c in ("[x]", "[!]")]
        value = f"S{min(done)}" if done else f"S{current_sprint(folder, exclude=e)}"
        why = "lowest finished column" if done else "current sprint"
        print(f"E{e}: Starts: {value} ({why})")
        written[e] = value
        if not dry_run:
            set_starts(path, value)
    milestones, errors = collect(folder)
    if errors:
        for e in errors:
            print(f"error: {e}", file=sys.stderr)
        return
    fl = floors(folder, milestones)
    for name, epic in epic_of_milestones(folder, milestones).items():
        if epic in written:
            fl[name] = int(written[epic][1:])
    col, _, errs, _ = schedule(milestones, fl, started_columns(folder, milestones))
    for e in errs:
        print(f"error: {e}", file=sys.stderr)
    if errs:
        return
    sp = load_sibling("sprints")
    label = sp.epic_rows(folder, load_sibling("ownership"), milestones)
    shown = [m for m in milestones if m["name"] in label]
    text, _ = sp.build(folder.parent.name, shown, col, (n, [(sp.row_name(l), c) for l, c in rows]),
                       num_key, label)
    _, new_rows = table_rows(text, "Milestone")
    before = {sp.row_name(l): c for l, c in rows}
    moved = []
    for r in new_rows:
        name, cells = sp.row_name(r[0]), r[1:]
        old_at = next((i + 1 for i, x in enumerate(before.get(name, [])) if x), None)
        new_at = next((i + 1 for i, x in enumerate(cells) if x), None)
        if old_at and old_at != new_at:
            mark = next((x for x in cells if x), "")
            moved.append(f"  {r[0]} {mark}: S{old_at} to S{new_at}")
    print(f"rows that move: {len(moved) or 'none'}")
    for line in moved:
        print(line)
    print("dry run; nothing written" if dry_run else "nothing committed")


def path_text(names, by_name):
    return " > ".join(f"{by_name[n]['spec']} {n}" for n in names) or "none"


def find_cycle(nodes, succ):
    for start in sorted(nodes):
        stack, seen = [(start, [start])], set()
        while stack:
            n, trail = stack.pop()
            for b in sorted(succ[n]):
                if b == start:
                    return trail + [start]
                if b in nodes and b not in seen:
                    seen.add(b)
                    stack.append((b, trail + [b]))
    return sorted(nodes)


def table_rows(text, first_col):
    """Header and data rows of the first pipe table whose header starts with first_col."""
    lines = [l.strip() for l in text.splitlines()]
    start = next((i for i, l in enumerate(lines)
                  if re.match(r"^\|\s*" + re.escape(first_col) + r"\s*\|", l)), None)
    if start is None:
        return None, []
    split = lambda l: [c.strip() for c in l.strip().strip("|").split("|")]
    block = []
    for l in lines[start:]:
        if not l.startswith("|"):
            break
        block.append(l)
    head = split(block[0])
    data = [split(l) for l in block[1:] if not re.fullmatch(r"\|[\s:|-]+\|?", l)]
    return head, data


def read_tags(folder):
    """Decision tags: {D number: {"epic": n or None, "done": bool, "line": heading index}}.

    The tag line is the first non-blank line under a "### D<n>" heading, e.g. "[E1]" or
    "[Done]  [E1]". A decision without one is in no epic.
    """
    path = folder / "decisions.md"
    tags = {}
    if not path.is_file():
        return tags
    lines = read(path).splitlines()
    for i, line in outside_fences(read(path)):
        m = D_HEAD_RE.match(line)
        if not m:
            continue
        nxt = next((l for l in lines[i:] if l.strip()), "")
        epic, done = None, False
        if TAG_LINE_RE.match(nxt):
            b = re.search(r"\[E(\d+)\]", nxt)
            epic = int(b.group(1)) if b else None
            done = "[Done]" in nxt
        tags[int(m.group(1))] = {"epic": epic, "done": done, "line": i - 1}
    return tags


def spec_cites(path):
    """Decision numbers a spec cites: (D7), (D6, D7), (D10 addendum)."""
    nums = set()
    for _, line in outside_fences(read(path)):
        for m in D_CITE_RE.finditer(line):
            nums |= {int(n) for n in re.findall(r"\bD(\d+)\b", m.group(1))}
    return nums


def spec_epic(path):
    """The spec's own "- Epic: E<n>" line, as n; None when the spec is in no epic."""
    for _, line in outside_fences(read(path)):
        m = EPIC_LINE_RE.match(line)
        if m:
            return int(m.group(1))
    return None


SUPERSEDED_HEAD_RE = re.compile(r"\(superseded by D(\d+)\)")
SUPERSEDES_RE = re.compile(r"^\s*-\s*Supersedes D(\d+)\b")


def supersedes(folder):
    """(heads, bullets): {old D: new D} from "### D7 (superseded by D15)" heading marks and from
    "- Supersedes D7." bullets under a later decision. A superseded decision is a key of either."""
    path = folder / "decisions.md"
    heads, bullets, cur = {}, {}, None
    if not path.is_file():
        return heads, bullets
    for _, line in outside_fences(read(path)):
        m = D_HEAD_RE.match(line)
        if m:
            cur = int(m.group(1))
            s = SUPERSEDED_HEAD_RE.search(line)
            if s:
                heads[cur] = int(s.group(1))
            continue
        if line.startswith("#"):
            cur = None
        s = SUPERSEDES_RE.match(line)
        if s and cur is not None:
            bullets[int(s.group(1))] = cur
    return heads, bullets


def spec_epics(folder):
    """{spec number: (epic or None, sorted cited D numbers)}; epic from the spec's Epic line only."""
    return {num: (spec_epic(path), sorted(spec_cites(path))) for num, path in spec_files(folder)}


def running_epics(tags):
    """Epics with at least one decision not yet [Done]."""
    return sorted({t["epic"] for t in tags.values() if t["epic"] and not t["done"]})


def overlap(folder, items):
    """Print files the named specs (or the specs citing the named D ids) share with
    milestones of running epics. Returns the number of shared files."""
    tags = read_tags(folder)
    epics = spec_epics(folder)
    files = dict(spec_files(folder))
    targets = set()
    for item in items:
        d = D_ID_RE.match(item)
        if d:
            hit = [num for num, (_, cited) in epics.items() if int(d.group(1)) in cited]
            if not hit:
                print(f"{item}: no spec cites it yet, files unknown")
            targets.update(hit)
        elif SPEC_NUM_RE.match(item) and item in files:
            targets.add(item)
        else:
            die(f"'{item}' is neither a spec number with a file nor a D id")
    running = set(running_epics(tags))
    owned = {}
    for num, (epic, _) in epics.items():
        if num in targets or epic not in running:
            continue
        for b in parse_spec(files[num]):
            for f in b["files"] or []:
                owned.setdefault(f, []).append(f"{b['name']} (E{epic})")
    shared = 0
    for num in sorted(targets, key=num_key):
        for b in parse_spec(files[num]):
            for f in b["files"] or []:
                if f in owned:
                    shared += 1
                    print(f"{num} {b['name']}: `{f}` shared with {', '.join(owned[f])}")
    print(f"running epics: {', '.join(f'E{n}' for n in sorted(running)) or 'none'}; "
          f"checked specs: {', '.join(sorted(targets, key=num_key)) or 'none'}; shared files: {shared}")
    return shared


def compute(folder, assume=None):
    """The ownership facts of a release, in memory, from the milestone blocks of its specs and
    the epics' Starts lines. Returns {"milestones", "col", "graph", "paths",
    "errors"}: milestones in spec order, each a dict name, spec, order,
    deps (names), files, review, starts; col {name: column}; paths {epic: [names]}, the critical path
    of each epic; errors, a list (then col and paths are empty). assume maps untagged spec
    numbers to an epic number (the pre-go preview)."""
    milestones, errors = collect(folder)
    col, graph, paths = {}, {}, {}
    if not errors:
        col, graph, errors, _ = schedule(milestones, floors(folder, milestones, assume),
                                         started_columns(folder, milestones))
    if not errors:
        paths = epic_paths(milestones, graph, epic_of_milestones(folder, milestones, assume))
    return {"milestones": milestones, "col": col, "graph": graph, "paths": paths, "errors": errors}


GRID_ROW_RE = re.compile(r"^E\d+\s+\d{2}(?:\.\d+)?\s+(.*)$")


def grid_columns(folder):
    """{milestone name: its column in status/sprints.md (1-based, the first non-blank cell)}."""
    _, rows = grid(folder)
    out = {}
    for label, cells in rows:
        m = GRID_ROW_RE.match(label)
        at = next((i + 1 for i, c in enumerate(cells) if c), None)
        if at:
            out[m.group(1) if m else label] = at
    return out


def grid_epics(folder):
    """Epic numbers with at least one row in status/sprints.md."""
    _, rows = grid(folder)
    return {int(m.group(1)) for label, _ in rows if (m := re.match(r"^E(\d+)\s", label))}


# The epic file's "## Ownership" table (reference/formats.md, Epic file).
OWN_HEAD = "## Ownership"
NOTES_HEAD = "## Notes"
TABLE_COLS = ["Decision", "Files", "Spec", "Milestone", "Sprint"]
DECISIONS_LINE_RE = re.compile(r"^Decisions:[ \t]*(.*?)[ \t]*$", re.M)
SPECS_LINE_RE = re.compile(r"^Specs:[ \t]*(.*?)[ \t]*$", re.M)
ROW_DECISION_RE = re.compile(r"^D(\d+)\b\s*(.*)$")


def epic_path(folder, n):
    return folder / EPICS_DIR / f"E{n}.md"


def epic_numbers(folder):
    """Epic numbers of every plan/epics/E<n>.md, in order."""
    out = []
    for p in (folder / EPICS_DIR).glob("E*.md"):
        m = re.match(r"^E(\d+)\.md$", p.name)
        if m:
            out.append(int(m.group(1)))
    return sorted(out)


def epic_decisions(text):
    """D numbers of the "Decisions:" line, in number order; ids in parentheses (cited, not run)
    are left out."""
    m = DECISIONS_LINE_RE.search(text)
    if not m:
        return []
    v = re.sub(r"\([^)]*\)", "", m.group(1))
    return sorted({int(x) for x in re.findall(r"\bD(\d+)\b", v)})


def section(lines, head):
    """(heading index, end index) of the section under head; end is the next "## " heading or
    the line count. None when the heading is missing."""
    start = next((i for i, l in enumerate(lines) if l.strip() == head), None)
    if start is None:
        return None
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return start, end


def split_row(line):
    s = line.strip()
    s = s[1:] if s.startswith("|") else s
    s = s[:-1] if s.endswith("|") else s
    return [c.strip() for c in s.split("|")]


def read_table(text):
    """(rows, error) of the "## Ownership" table: (None, None) when the section is missing.
    A row: decision (int or None), title, files (list), spec, milestone, sprint, line (index
    in text.split("\\n"))."""
    lines = text.split("\n")
    span = section(lines, OWN_HEAD)
    if span is None:
        return None, None
    tl = [i for i in range(span[0] + 1, span[1]) if lines[i].strip().startswith("|")]
    if not tl:
        return None, f"{OWN_HEAD} has no table"
    if split_row(lines[tl[0]]) != TABLE_COLS:
        return None, f"{OWN_HEAD} table columns are not {' | '.join(TABLE_COLS)}"
    rows = []
    for i in tl[1:]:
        cells = split_row(lines[i])
        if all(re.fullmatch(r":?-+:?", c) for c in cells if c):
            continue
        if len(cells) != len(TABLE_COLS):
            return None, f"{OWN_HEAD} table line {i + 1} has {len(cells)} cells, not {len(TABLE_COLS)}"
        dec, title = None, ""
        if cells[0]:
            m = ROW_DECISION_RE.match(cells[0])
            if not m:
                return None, f"{OWN_HEAD} table line {i + 1}: Decision cell '{cells[0]}' is not D<n> <title>"
            dec, title = int(m.group(1)), m.group(2)
        files = [f.strip().strip("`").strip() for f in cells[1].split(",")]
        rows.append({"decision": dec, "title": title, "files": [f for f in files if f],
                     "spec": cells[2], "milestone": cells[3], "sprint": cells[4], "line": i})
    return rows, None


def render_table(rows):
    out = ["| " + " | ".join(TABLE_COLS) + " |", "|" + "---|" * len(TABLE_COLS)]
    for r in rows:
        dec = f"D{r['decision']} {r['title']}".strip() if r["decision"] is not None else ""
        cells = [dec, ", ".join(r["files"]), r["spec"] or "", r["milestone"], r["sprint"]]
        out.append("| " + " | ".join(cells) + " |")
    return out


def put_table(text, rows):
    """text with its "## Ownership" section replaced by the table of rows, or the section added
    before "## Notes" (else at the end)."""
    lines = text.rstrip("\n").split("\n")
    block = [OWN_HEAD, ""] + render_table(rows)
    span = section(lines, OWN_HEAD)
    if span:
        start, end = span
        lines = lines[:start] + block + ([""] + lines[end:] if end < len(lines) else [])
    else:
        notes = section(lines, NOTES_HEAD)
        if notes:
            lines = lines[:notes[0]] + block + [""] + lines[notes[0]:]
        else:
            lines = lines + ([""] if lines and lines[-1].strip() else []) + block
    return "\n".join(lines) + "\n"


def set_field(text, key, value):
    """text with the line "<key>: <value>"; a missing line goes under the last of the
    Decisions, Specs and Starts lines (else under the title)."""
    lines = text.rstrip("\n").split("\n")
    i = next((k for k, l in enumerate(lines) if re.match(rf"^{key}:", l)), None)
    line = f"{key}: {value}".rstrip()
    if i is not None:
        lines[i] = line
    else:
        at = [k for k, l in enumerate(lines) if re.match(r"^(Decisions|Specs|Starts):", l)]
        lines.insert((at[-1] if at else 0) + 1, line)
    return "\n".join(lines) + "\n"


def decision_titles(folder):
    """{D number: heading title} from decisions.md, without a "(superseded by ...)" mark; "|"
    becomes "/" so the title fits a table cell."""
    path = folder / "decisions.md"
    out = {}
    if not path.is_file():
        return out
    for _, line in outside_fences(read(path)):
        m = D_HEAD_RE.match(line)
        if m:
            t = re.sub(r"^###\s+D\d+\b", "", line)
            t = re.sub(r"\(superseded by D\d+\)", "", t).strip().lstrip(":.-").strip()
            out[int(m.group(1))] = t.replace("|", "/")
    return out


def epic_specs(folder, n, decisions, given=None):
    """(spec numbers of epic n, assume map for compute): the specs with an "- Epic: E<n>" line,
    plus the untagged spec numbers given, else, while the epic has no Starts value, every
    untagged spec citing one of its decisions."""
    eps = spec_epics(folder)
    tagged = [num for num, (e, _) in eps.items() if e == n]
    started = SPRINT_VALUE_RE.match(epic_starts(folder).get(n) or "")
    if given is not None:
        extra = [g for g in given if g in eps and eps[g][0] is None]
    elif not started:
        extra = [num for num, (e, c) in eps.items() if e is None and set(c) & set(decisions)]
    else:
        extra = []
    specs = sorted(set(tagged) | set(extra), key=num_key)
    return specs, {num: n for num in extra}


def sprint_text(cols):
    cols = sorted(c for c in set(cols) if c)
    if not cols:
        return ""
    return f"S{cols[0]}" if len(cols) == 1 else f"S{cols[0]} to S{cols[-1]}"


def spec_milestones(comp):
    """{spec number: [milestone dicts]}."""
    out = collections.defaultdict(list)
    for m in comp["milestones"]:
        out[m["spec"]].append(m)
    return out


def owned_files(ms):
    return list(dict.fromkeys(f for m in ms for f in m["files"]))


def spec_sprint(ms, comp, gcols):
    """Sprint cell of a spec: the grid column of each milestone with a grid row, else its
    computed column."""
    return sprint_text([gcols.get(m["name"]) or comp["col"].get(m["name"]) for m in ms])


def build_table(folder, decisions, specs, old_rows, comp, gcols, from_specs=False):
    """The rows of an epic's table. Decision rows keep the Files the spec writer wrote, split
    over the citing specs by owner (a file no citing spec owns stays on the lowest spec's
    row); from_specs=True (the migration) takes each row's Files from its spec's milestones."""
    titles = decision_titles(folder)
    paths = dict(spec_files(folder))
    by_spec = spec_milestones(comp)
    cites = {s: spec_cites(paths[s]) for s in specs}
    owned = {s: owned_files(by_spec[s]) for s in specs}
    d_files = collections.OrderedDict()
    old_title = {}
    for r in old_rows or []:
        if r["decision"] is not None:
            fl = d_files.setdefault(r["decision"], [])
            fl += [f for f in r["files"] if f not in fl]
            old_title.setdefault(r["decision"], r["title"])
    rows = []

    def add(d, files, s):
        rows.append({"decision": d, "title": (titles.get(d) or old_title.get(d, "")) if d is not None else "",
                     "files": files, "spec": s or "",
                     "milestone": "; ".join(m["name"] for m in by_spec[s]) if s else "",
                     "sprint": spec_sprint(by_spec[s], comp, gcols) if s else ""})

    for d in decisions:
        citing = [s for s in specs if d in cites[s]]
        if from_specs:
            if not citing:
                add(d, [], None)
            for s in citing:
                add(d, list(owned[s]), s)
            continue
        fl = d_files.get(d, [])
        if not citing:
            add(d, fl, None)
            continue
        assign = {s: [] for s in citing}
        for f in fl:
            for s in [s for s in citing if f in owned[s]] or citing[:1]:
                assign[s].append(f)
        for s in citing:
            add(d, assign[s], s)
    for s in specs:
        if not cites[s] & set(decisions):
            add(None, list(owned[s]), s)

    def key(r):
        first = re.match(r"^S(\d+)", r["sprint"])
        return (int(first.group(1)) if first else 10 ** 6,
                num_key(r["spec"]) if r["spec"] else (2,),
                r["decision"] if r["decision"] is not None else 10 ** 9)
    return sorted(rows, key=key)


def repo_of(folder):
    return next((p.parent for p in folder.parents if p.name == ".ai"), folder)


def path_exists(root, f):
    if (root / f).exists():
        return True
    if any(ch in f for ch in "*?["):
        try:
            return any(root.glob(f.lstrip("/")))
        except (ValueError, NotImplementedError):
            return False
    return (root / f).exists()


def row_label(r):
    if r["decision"] is None:
        return f"spec {r['spec']}"
    return f"D{r['decision']}" + (f" (spec {r['spec']})" if r["spec"] else "")


def table_facts(folder, rows, comp):
    """(missing, unowned): [(row, file)] for each Files path that does not exist in the repo and
    each row file no milestone of the row's spec owns."""
    root = repo_of(folder)
    by_spec = spec_milestones(comp)
    missing = [(r, f) for r in rows for f in r["files"] if not path_exists(root, f)]
    unowned = [(r, f) for r in rows if r["spec"] for f in r["files"]
               if f not in owned_files(by_spec.get(r["spec"], []))]
    return missing, unowned


def shared_pairs(specs, comp):
    """[(spec a, spec b, [files])] for each pair of the specs whose milestones own a same file."""
    by_spec = spec_milestones(comp)
    owned = {s: owned_files(by_spec.get(s, [])) for s in specs}
    out = []
    for i, a in enumerate(specs):
        for b in specs[i + 1:]:
            common = [f for f in owned[a] if f in owned[b]]
            if common:
                out.append((a, b, common))
    return out


def print_errors(errors, what="nothing written"):
    for e in errors:
        print(f"error: {e}", file=sys.stderr)
    print(f"error: {what}", file=sys.stderr)
    sys.exit(1)


def fill_epic(folder, n, given=None, quiet=False):
    """--epic: fill the Spec, Milestone and Sprint columns of plan/epics/E<n>.md, then print the
    facts (unless quiet). Returns (specs, rows, comp). Exits 1 on an ownership error or an
    unreadable table, before writing."""
    path = epic_path(folder, n)
    if not path.is_file():
        die(f"{path} missing: new_epic_file.py {folder.parent.name} E{n} <D ids>")
    text = read(path)
    old, err = read_table(text)
    if err:
        die(f"{path}: {err}")
    decisions = epic_decisions(text)
    if given:
        have = dict(spec_files(folder))
        bad = [g for g in given if g not in have]
        if bad:
            die(f"no spec file for {', '.join(bad)}")
    specs, assume = epic_specs(folder, n, decisions, given)
    comp = compute(folder, assume)
    if comp["errors"]:
        print_errors(comp["errors"])
    gcols = grid_columns(folder)
    rows = build_table(folder, decisions, specs, old, comp, gcols)
    new = put_table(text, rows)
    if new != text:
        path.write_text(new, encoding="utf-8")
    if quiet:
        return specs, rows, comp
    provisional = not SPRINT_VALUE_RE.match(epic_starts(folder).get(n) or "")
    by_spec = spec_milestones(comp)
    by_name = {m["name"]: m for m in comp["milestones"]}
    cols = sorted({gcols.get(m["name"]) or comp["col"][m["name"]] for s in specs for m in by_spec[s]})
    print(f"{path}: {len(rows)} rows, specs {', '.join(specs) or 'none'}")
    print(f"E{n} sprints: {', '.join(f'S{c}' for c in cols) or 'none'}"
          + (" (provisional: the current sprint as the start)" if provisional else ""))
    print(f"E{n} path: {path_text(comp['paths'].get(n, []), by_name)}")
    pairs = shared_pairs(specs, comp)
    for a, b, files in pairs:
        print(f"shared: {a} and {b}: {', '.join(f'`{f}`' for f in files)}")
    if not pairs:
        print("shared: none")
    missing, unowned = table_facts(folder, rows, comp)
    for r, f in missing:
        print(f"new or missing: {row_label(r)}: `{f}`")
    for r, f in unowned:
        print(f"not owned: {row_label(r)}: `{f}` is owned by no milestone of spec {r['spec']}")
    return specs, rows, comp


def finished_epics(folder):
    """Epic numbers that are finished: every decision tagged with the epic is [Done], or the
    epic has rows in status/sprints.md and every one is "[x]" or "[!]"."""
    tags = read_tags(folder)
    _, rows = grid(folder)
    marks = collections.defaultdict(list)
    for label, cells in rows:
        m = re.match(r"^E(\d+)\s", label)
        if m:
            marks[int(m.group(1))].append(next((c for c in cells if c), ""))
    out = set()
    for e in set(marks) | {t["epic"] for t in tags.values() if t["epic"]}:
        ds = [t for t in tags.values() if t["epic"] == e]
        if (ds and all(t["done"] for t in ds)) or (marks[e] and all(c in ("[x]", "[!]") for c in marks[e])):
            out.add(e)
    return out


def unfinished_started_epics(folder):
    """Epic numbers with a Starts value that are not finished."""
    done = finished_epics(folder)
    return [e for e, v in sorted(epic_starts(folder).items())
            if SPRINT_VALUE_RE.match(v or "") and e not in done]


def sync_sprint_columns(folder, comp):
    """sprints.py: set the Sprint cell of every row of each unfinished epic that has gone (a
    Starts value) from status/sprints.md; no other cell or line changes. Returns the paths
    written."""
    gcols = grid_columns(folder)
    by_spec = spec_milestones(comp)
    written = []
    for e in unfinished_started_epics(folder):
        path = epic_path(folder, e)
        if not path.is_file():
            continue
        text = read(path)
        rows, err = read_table(text)
        if err:
            print(f"warning: {path}: {err}; Sprint column not synced", file=sys.stderr)
        if not rows:
            continue
        lines = text.split("\n")
        for r in rows:
            if not r["spec"]:
                continue
            want = spec_sprint(by_spec.get(r["spec"], []), comp, gcols)
            if want != r["sprint"]:
                cells = lines[r["line"]].rstrip().split("|")
                cells[-2] = f" {want} "
                lines[r["line"]] = "|".join(cells)
        new = "\n".join(lines)
        if new != text:
            path.write_text(new, encoding="utf-8")
            written.append(path)
    return written


def epic_gaps(folder, comp):
    """status.py: the gaps of the epic files' Ownership tables, as lines."""
    out = []
    done = finished_epics(folder)
    gcols = grid_columns(folder)
    with_rows = grid_epics(folder)
    by_spec = spec_milestones(comp)
    tagged = collections.defaultdict(list)
    for num, (e, _) in spec_epics(folder).items():
        if e:
            tagged[e].append(num)
    for n in epic_numbers(folder):
        path = epic_path(folder, n)
        rel = path.relative_to(folder).as_posix()
        text = read(path)
        rows, err = read_table(text)
        if err:
            out.append(f"{rel}: {err}")
            continue
        if rows is None:
            if n in with_rows:
                out.append(f"{rel}: no {OWN_HEAD} table, but E{n} has rows in {SPRINTS_MD}")
            continue
        have_d = {r["decision"] for r in rows}
        for d in epic_decisions(text):
            if d not in have_d:
                out.append(f"{rel}: D{d} on the Decisions line has no row")
        have_s = {r["spec"] for r in rows}
        for s in sorted(tagged.get(n, []), key=num_key):
            if s not in have_s:
                out.append(f"{rel}: spec {s} of E{n} has no row")
        finished = n in done
        _, unowned = table_facts(folder, rows, comp)
        for r, f in unowned:
            out.append(f"{rel}: {row_label(r)}: `{f}` is owned by no milestone of spec {r['spec']}")
        if n in with_rows:
            for r in rows:
                if r["spec"]:
                    want = spec_sprint(by_spec.get(r["spec"], []), comp, gcols)
                    if want != r["sprint"]:
                        out.append(f"{rel}: {row_label(r)}: Sprint '{r['sprint']}' disagrees with "
                                   f"the grid ('{want}')" + ("" if finished else ": sprints.py rewrites it"))
    return out


def check(folder):
    """Plain run: the milestone and column count and each epic's critical path; exit 1 on an error."""
    comp = compute(folder)
    if not comp["milestones"] and not comp["errors"]:
        comp["errors"].append("no '### Milestone:' blocks in plan/specs/*.md")
    if comp["errors"]:
        print_errors(comp["errors"], "ownership does not compute")
    by_name = {m["name"]: m for m in comp["milestones"]}
    print(f"{len(comp['milestones'])} milestones, {max(comp['col'].values())} columns")
    for e, p in sorted(comp["paths"].items()):
        print(f"E{e} path: {path_text(p, by_name)}")


def main():
    ap = argparse.ArgumentParser(
        usage="ownership.py <release> [--epic E<n> [<spec numbers>] | --overlap <spec or D ids> ... | "
              "--backfill-starts [--dry-run]] [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("--overlap", nargs="+", metavar="ID",
                    help="check mode: files the named specs or D ids share with running epics")
    ap.add_argument("--epic", nargs="+", metavar="ARG",
                    help="E<n> [spec numbers]: fill the epic file's Ownership table and print the facts")
    ap.add_argument("--backfill-starts", action="store_true",
                    help="write Starts into epic files that have grid rows and none yet")
    ap.add_argument("--dry-run", action="store_true", help="with --backfill-starts: write nothing")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    root = repo_root(a.root, a.release)
    folder = release_folder(root, detect_owner(root, a.owner), a.release)
    if a.backfill_starts:
        backfill_starts(folder, a.dry_run)
        return
    if a.overlap:
        items = [s.strip() for x in a.overlap for s in x.split(",") if s.strip()]
        sys.exit(1 if overlap(folder, items) else 0)
    if not (folder / SPECS_DIR).is_dir():
        die(f"specs folder missing: {folder / SPECS_DIR}")
    if a.epic:
        m = re.match(r"^E(\d+)$", a.epic[0])
        nums = [s.strip() for x in a.epic[1:] for s in x.split(",") if s.strip()]
        if not m or not all(SPEC_NUM_RE.match(n) for n in nums):
            die("--epic takes E<n> and optional spec numbers, e.g. --epic E6 09 10")
        fill_epic(folder, int(m.group(1)), nums or None)
        return
    check(folder)


if __name__ == "__main__":
    main()
