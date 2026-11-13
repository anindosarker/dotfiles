#!/usr/bin/env python3
"""The ownership facts of a release, computed in memory from the milestone blocks of its specs.
Library, no CLI. No file holds the facts: every script that needs them calls compute().

Reads every plan/specs/NN-<slug>.md for "### Milestone: <name>" blocks ("#### Milestone:"
is accepted too) with the lines "- Files owned: a, b", "- Depends on: <milestone names,
spec numbers or none>" and "- Review: none | fable", and the optional "- Starts: S<n>" (a
milestone added after its epic's go, by plan/new_fix.py: its own start sprint).

Edges: A to B when B lists A (or A's spec number) under Depends on, or when A and B
share a file (lower spec number first). Two milestones of one spec that share a file
while neither depends on the other are a collision; a dependency cycle is an error.

A milestone's column is the longest chain ending at it plus one, over every epic, and never
before its epic's start sprint: the "Starts: S<n>" line of plan/epics/E<n>.md (epics/tag.py
writes it on go), nor before the milestone's own "- Starts: S<n>" line. The floor
propagates along the edges; an epic file without a Starts value means no floor. A milestone
whose status/sprints.md row is running ("[ ]") or finished ("[x]", "[!]") keeps that column, and
a finished one never collides on a shared file. The epic table (epics/table.py E<n> <spec
numbers>) uses the current sprint as a provisional floor for an epic with no Starts value yet,
writing no Starts line. The current sprint is the first column of status/sprints.md holding a
"[ ]" or "·" cell of an epic row; when there is none, the column after the last column holding
an epic row (S1 for an empty grid). For an epic's own start its own rows are ignored.

Critical path per epic, computed on the fly (never stored): over that epic's milestones only (a
spec's epic is its "- Epic: E<n>" line), with the Depends on and shared-file edges inside the
epic; the longest chain, ties by lower spec number.

Errors: a file shared by two milestones of one column, a dependency cycle, a milestone without
a Files owned line or with an unknown dependency.

Also here: the epic file's "## Ownership" table (read, render, fill: fill_epic, used by
epics/table.py and run/go.py), the Sprint column sync (sync_sprint_columns, used by
sprints/sync_epic_sprints.py and the refresh chain in lib/grid.py), the epic table gaps
status/report.py prints, and the tracker and Deliverables readers of status/report.py and
status/progress.py.
"""
import collections
import importlib.util
import re
import sys
from pathlib import Path


def _common():
    name = "expedition_lib_common"
    if name not in sys.modules:
        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent / "common.py")
        sys.modules[name] = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sys.modules[name])
    return sys.modules[name]


C = _common()
RELEASE_RE = C.RELEASE_RE
SPECS_DIR, EPICS_DIR, TRACKERS_DIR, QUEUE_MD = C.SPECS_DIR, C.EPICS_DIR, C.TRACKERS_DIR, C.QUEUE_MD
HANDOFFS_DIR, STATUS_DIR, SPRINTS_MD = C.HANDOFFS_DIR, C.STATUS_DIR, C.SPRINTS_MD
LEGACY_OWNERSHIP_MD, LEGACY_FIX_GLOB = C.LEGACY_OWNERSHIP_MD, C.LEGACY_FIX_GLOB
die, repo_root, detect_owner, release_folder = C.die, C.repo_root, C.detect_owner, C.release_folder
ignore_renders, legacy_fixes, num_key, read = C.ignore_renders, C.legacy_fixes, C.num_key, C.read
outside_fences, table_rows, insert_row = C.outside_fences, C.table_rows, C.insert_row

SPEC_FILE_RE = re.compile(r"^(\d{2}(?:\.\d+)?)-([a-z0-9]+(?:-[a-z0-9]+)*)\.md$")
SPEC_NUM_RE = re.compile(r"^\d{2}(?:\.\d+)?$")
MILESTONE_RE = re.compile(r"^#{3,4}\s+Milestone:\s*(.+?)\s*$")
HEADING_RE = re.compile(r"^#{1,6}\s")
FIELD_RE = re.compile(r"^\s*(?:-\s*)?(Files owned|Depends on|Review|Starts):\s*(.*?)\s*$")
TASK_RE = re.compile(r"^\s*-\s*Task\s+\d+:")
D_HEAD_RE = re.compile(r"^###\s+D(\d+)\b")
TAG_LINE_RE = re.compile(r"^\s*(?:\[(?:Done|E\d+)\]\s*)+$")
D_CITE_RE = re.compile(r"\((D\d+[^)]*)\)")
D_ID_RE = re.compile(r"^D(\d+)$")
EPIC_LINE_RE = re.compile(r"^\s*-\s*Epic:\s*E(\d+)\s*$")

def split_files(value):
    """Files from a 'Files owned' value: the backticked spans, else comma parts; 'none' is empty."""
    value = value.strip()
    if not value or value.lower().rstrip(".") == "none":
        return []
    spans = re.findall(r"`([^`]+)`", value)
    if spans:
        return [s.strip() for s in spans if s.strip()]
    return [s.strip() for s in value.split(",") if s.strip()]


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
        die(f"{path} missing: epics/new.py {folder.parent.name} E{n} <D ids>")
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
    """The refresh chain and sprints/sync_epic_sprints.py: set the Sprint cell of every row of each unfinished epic that has gone (a
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
    """status/report.py: the gaps of the epic files' Ownership tables, as lines."""
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
                                   f"the grid ('{want}')" + ("" if finished else ": sprints/refresh.py rewrites it"))
    return out



def refuse_superseded(folder, nums, what):
    """Die when any of the D numbers is superseded."""
    heads, bullets = supersedes(folder)
    gone = {**bullets, **heads}
    hit = sorted(n for n in nums if n in gone)
    if hit:
        die(f"{what} cites superseded " + ", ".join(f"D{n} (by D{gone[n]})" for n in hit)
            + ": cite the current decision")


# Trackers and the Deliverables table, for status/report.py and status/progress.py.
DELIV_ROW_RE = re.compile(r"^\|\s*(\d{2}(?:\.\d+)?)\s*\|(.*)$")
LINK_RE = re.compile(r"\]\(([^)\s]+\.md)\)")
DELIVERABLES_HEAD = r"^## Deliverables\s*$(.*?)(?=^## |\Z)"
SCOPE_MAX = 120
STATUS_RE = re.compile(r"^Status:\s*(.*?)\s*$", re.M)
STATUS_VALUE_RE = re.compile(r"^(planned|running|done|merged|skipped)\b\s*(?:\(([^)]*)\))?")
TITLE_LINK_RE = re.compile(r"\[(.+?)\]\(")
PLACEHOLDER_RE = re.compile(r"^(?:\[[^\]]*\]|\([^)]*\))$")


def tracker_path(folder, num):
    """run/trackers/<num>-tracker.md."""
    return folder / TRACKERS_DIR / f"{num}-tracker.md"


def tracker_status(folder, num, p=None):
    """Return (state, sha) from the tracker's Status line, or None."""
    p = p or tracker_path(folder, num)
    if not p.is_file():
        return None
    m = STATUS_RE.search(read(p))
    if not m:
        return None
    v = STATUS_VALUE_RE.match(m.group(1))
    if not v:
        return None
    return v.group(1), (v.group(2) or "").strip()


def spec_titles(plan):
    """{spec number: title}: the link text of each Deliverables row."""
    out = {}
    if not plan.is_file():
        return out
    m = re.search(DELIVERABLES_HEAD, read(plan), re.M | re.S)
    for line in (m.group(1).splitlines() if m else []):
        r = DELIV_ROW_RE.match(line.strip())
        t = TITLE_LINK_RE.search(r.group(2)) if r else None
        if t:
            out[r.group(1)] = t.group(1).strip()
    return out


def attention_reason(path):
    """The first bullet under "## Attention" in a tracker, one line, without "- "; None when the
    section has no bullet or only a template placeholder ("[...]" or "(none)")."""
    if not path or not path.is_file():
        return None
    inside = False
    for _, line in outside_fences(read(path)):
        if line.startswith("## "):
            if inside:
                return None
            inside = line.strip() == "## Attention"
        elif inside and line.startswith("- "):
            text = line[2:].strip()
            return None if not text or PLACEHOLDER_RE.match(text) else text
    return None


def spec_rows(plan):
    """Rows of the Deliverables table: [(num, link)], long scopes [(num, len)]."""
    rows, long_scopes = [], []
    if not plan.is_file():
        return rows, long_scopes
    m = re.search(DELIVERABLES_HEAD, read(plan), re.M | re.S)
    if m:
        for line in m.group(1).splitlines():
            r = DELIV_ROW_RE.match(line.strip())
            if r:
                link = LINK_RE.search(r.group(2))
                rows.append((r.group(1), link.group(1) if link else None))
                cells = r.group(2).strip().strip("|").split("|")
                if len(cells) >= 2 and len(cells[-1].strip()) > SCOPE_MAX:
                    long_scopes.append((r.group(1), len(cells[-1].strip())))
    return rows, long_scopes


def other_trackers(folder, claimed, statuses):
    """Trackers no spec or milestone owns: (key, path, first line)."""
    out = []
    if (folder / TRACKERS_DIR).is_dir():
        for p in sorted((folder / TRACKERS_DIR).glob("*-tracker.md")):
            if p.name not in claimed:
                key = p.name[: -len("-tracker.md")]
                lines = read(p).splitlines()
                out.append((key, p, lines[0] if lines else ""))
                statuses[key] = tracker_status(folder, key, p)
    return out


def aggregate(states):
    """One spec state from its milestone tracker states, as tracker_status returns them."""
    if not states or any(s is None for s in states):
        return None
    kinds = {"done" if s[0] in ("merged", "done") else s[0] for s in states}
    if kinds == {"done"}:
        return "merged", ", ".join(s[1] for s in states if s[1])
    if kinds & {"running", "done"}:
        return "running", ""
    return "planned", ""


def milestone_tracker(folder, num, spec_slug, idx, name):
    """run/trackers/NN-<milestone-slug>-tracker.md; the first milestone also takes NN-<spec-slug>
    and NN-tracker.md."""
    t = folder / TRACKERS_DIR
    cands = [t / f"{num}-{C.slugify(name)}-tracker.md"]
    if idx == 0:
        cands += [t / f"{num}-{spec_slug}-tracker.md", t / f"{num}-tracker.md"]
    return next((c for c in cands if c.is_file()), cands[0])


def new_collect(folder, plan):
    """The specs of the Deliverables table with their milestone blocks, each block's tracker
    path ("tracker"), each spec's state, the trackers no milestone owns and the gaps."""
    rows, long_scopes = spec_rows(plan)
    docs = [(num, folder / f) for num, f in rows if f and (folder / f).is_file()]
    statuses, claimed, blocks, missing = {}, set(), {}, []
    for num, p in docs:
        m = re.match(r"^\d{2}(?:\.\d+)?-(.+)\.md$", p.name)
        spec_slug = m.group(1) if m else ""
        bl = parse_spec(p)
        blocks[num] = bl
        states = []
        for i, b in enumerate(bl):
            t = milestone_tracker(folder, num, spec_slug, i, b["name"])
            b["tracker"] = t
            if t.is_file():
                claimed.add(t.name)
                st = tracker_status(folder, num, t)
                states.append(st)
                if st is None:
                    missing.append(f"no Status line: {t.name}")
            else:
                states.append(("planned", ""))
                missing.append(f"no tracker yet: milestone {b['name']} ({t.relative_to(folder)})")
        if not bl:
            t = folder / TRACKERS_DIR / f"{num}-tracker.md"
            states = [tracker_status(folder, num, t)] if t.is_file() else [("planned", "")]
            if t.is_file():
                claimed.add(t.name)
        statuses[num] = aggregate(states)
    extra = other_trackers(folder, claimed, statuses)
    return {"rows": rows, "long": long_scopes, "docs": docs, "statuses": statuses,
            "extra": extra, "blocks": blocks, "missing": missing}
