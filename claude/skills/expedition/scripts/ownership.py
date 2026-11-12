#!/usr/bin/env python3
"""Generate status/ownership.md for a release from the milestone blocks of its specs.

Usage: python3 -I ownership.py <release> [--epic E<n> <spec numbers>] [--owner X] [--root PATH]

Reads every plan/specs/NN-<slug>.md for "### Milestone: <name>" blocks ("#### Milestone:"
is accepted too) with the lines "- Files owned: a, b", "- Depends on: <milestone names,
spec numbers or none>" and "- Review: none | fable", and every run/trackers/fix-<slug>-tracker.md
as a fix milestone (no spec; its name is the tracker title, its files come from a
"Files owned:" line and its dependencies from a "Depends on:" line, both optional).

Edges: A to B when B lists A (or A's spec number) under Depends on, or when A and B
share a file (lower spec number first). Two milestones of one spec that share a file
while neither depends on the other are a collision; a dependency cycle is an error.
Fix milestones take part through Depends on only: the run places them in the
running sprint column (sprints.py, new_fix.py).

A milestone's column is the longest chain ending at it plus one, over every epic. The
"Derived from" cell lists the shared-file edges the scheduler added into that milestone, as
"<milestone> (`file`, ...)"; explicit edges are the Depends on cell.

Critical path per epic: over that epic's milestones only (a spec's epic is its "- Epic: E<n>"
line; fix milestones are in no epic), with the Depends on and shared-file edges inside the
epic; the longest chain, ties by lower spec number. One line per epic under "## Critical
paths": "- E6: 09 Theme panel shortcut row > 10 Theme color picker". --epic E<n> <spec
numbers> counts those untagged specs as E<n> (the lead, after the fork, before go).

status/ownership.md holds a title, the Generated line, the table
"| Milestone | Spec | Depends on | Derived from | Files |" and the "## Critical paths" section.
It is never edited by hand. On any error nothing is written and the exit code is 1.

Layout: the release folder must hold plan/ (plan/specs, plan/epics), run/ (run/trackers,
run/handoffs), status/ and queue.md. A folder without plan/ is refused with one line naming
migrate_layout.py; a folder still on the old queue files, or with a queue.md that is not yet a
kanban board, is refused with one line naming migrate_queue.py.

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
FIELD_RE = re.compile(r"^\s*(?:-\s*)?(Files owned|Depends on|Review):\s*(.*?)\s*$")
TASK_RE = re.compile(r"^\s*-\s*Task\s+\d+:")
OWNERSHIP_COLS = ["Milestone", "Spec", "Depends on", "Derived from", "Files"]
SPECS_DIR = "plan/specs"
EPICS_DIR = "plan/epics"
TRACKERS_DIR = "run/trackers"
QUEUE_MD = "queue.md"
HANDOFFS_DIR = "run/handoffs"
STATUS_DIR = "status"
OWNERSHIP_MD = "status/ownership.md"
SPRINTS_MD = "status/sprints.md"
PATHS_HEAD = "## Critical paths"
PATH_LINE_RE = re.compile(r"^-\s*E(\d+):\s*(.*?)\s*$")
FIX = "fix"
D_HEAD_RE = re.compile(r"^###\s+D(\d+)\b")
TAG_LINE_RE = re.compile(r"^\s*(?:\[(?:Done|E\d+)\]\s*)+$")
D_CITE_RE = re.compile(r"\((D\d+[^)]*)\)")
D_ID_RE = re.compile(r"^D(\d+)$")
EPIC_LINE_RE = re.compile(r"^\s*-\s*Epic:\s*E(\d+)\s*$")


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def repo_root(flag=None):
    if flag:
        p = Path(flag).resolve()
        if not p.is_dir():
            die(f"root not a folder: {p}")
        return p
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        die("not inside a git repository")
    return Path(out.stdout.strip())


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
    swimlanes.py and never committed; ownership.md and sprints.md stay in git."""
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
    return folder


def load_sibling(name):
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def num_key(num):
    if num is None or num == FIX:
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
    deps (raw text or None), review (text or None), tasks (list of (line, text)).
    """
    blocks = []
    cur = None
    level = None
    for i, line in outside_fences(read(path)):
        m = MILESTONE_RE.match(line)
        if m:
            cur = {"name": m.group(1), "line": i, "files": None, "deps": None,
                   "review": None, "tasks": []}
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
            else:
                cur["review"] = val
        elif TASK_RE.match(line):
            cur["tasks"].append((i, line.strip()))
    return blocks


def fix_milestone(path):
    """A fix tracker as a milestone: name from the title, optional files and deps lines."""
    lines = read(path).splitlines()
    first = lines[0] if lines else ""
    name = re.sub(r"^#\s*", "", first).strip()
    name = re.sub(r",\s*tracker\s*$", "", name).strip() or path.name[: -len("-tracker.md")]
    files, deps = [], None
    for line in lines[1:]:
        if line.startswith("## "):
            break
        f = FIELD_RE.match(line)
        if f and f.group(1) == "Files owned":
            files = split_files(f.group(2))
        elif f and f.group(1) == "Depends on":
            deps = f.group(2)
    return {"name": name, "files": files, "deps": deps, "path": path}


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
    trackers = folder / TRACKERS_DIR
    if trackers.is_dir():
        for p in sorted(trackers.glob("fix-*-tracker.md")):
            f = fix_milestone(p)
            f.update(spec=FIX, review=None, line=1, tasks=[])
            raw.append(f)
    names = [b["name"] for b in raw]
    for name, c in collections.Counter(names).items():
        if c > 1:
            where = ", ".join(sorted({str(b["path"].relative_to(folder)) for b in raw if b["name"] == name}))
            errors.append(f"milestone '{name}' defined {c} times: {where}")
    specs = collections.defaultdict(list)
    for b in raw:
        if b["spec"] != FIX:
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
                    "files": b["files"] or [], "review": b.get("review")})
    return out, errors


def schedule(milestones):
    """Return (columns, graph, errors, warnings) for milestones with resolved deps.

    milestones: list of dicts name, spec, order, deps, files (spec 'fix' for a fix milestone).
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
        if m["spec"] == FIX:
            continue
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

    col, prev = {}, {}
    for n in topo:
        col.setdefault(n, 1)
        for b in succ[n]:
            if col[n] + 1 > col.get(b, 1):
                col[b] = col[n] + 1
                prev[b] = n
            elif col[n] + 1 == col.get(b, 1) and b not in prev:
                prev[b] = n
    for f, names in owners.items() if not errors else ():
        seen = {}
        for n in names:
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


def cell_files(files):
    return ", ".join(f"`{f}`" for f in files) if files else "none"


def cell_derived(preds):
    return ", ".join(f"{p} ({cell_files(fs)})" for p, fs in preds.items()) or "none"


def render(release, milestones, graph, paths, today):
    by_name = {m["name"]: m for m in milestones}
    rows = [f"| {m['name']} | {m['spec']} | {', '.join(m['deps']) or 'none'} | "
            f"{cell_derived(graph['derived'].get(m['name'], {}))} | {cell_files(m['files'])} |"
            for m in milestones]
    lines = [f"- E{e}: {path_text(p, by_name)}" for e, p in sorted(paths.items())]
    return (
        f"# {release} ownership\n\n"
        f"Generated: {today} by ownership.py\n\n"
        "| " + " | ".join(OWNERSHIP_COLS) + " |\n|" + "---|" * len(OWNERSHIP_COLS) + "\n"
        + "".join(r + "\n" for r in rows)
        + f"\n{PATHS_HEAD}\n\n"
        + ("".join(l + "\n" for l in lines) or "- none\n")
    )


def read_paths(path):
    """{epic number: [milestone names]} from the "## Critical paths" section of status/ownership.md."""
    out, inside = {}, False
    if not path.is_file():
        return out
    for line in read(path).splitlines():
        if line.startswith("## "):
            inside = line.strip() == PATHS_HEAD
            continue
        m = PATH_LINE_RE.match(line) if inside else None
        if m:
            out[int(m.group(1))] = [re.sub(r"^\d{2}(?:\.\d+)?\s+", "", s.strip())
                                    for s in m.group(2).split(" > ") if s.strip()]
    return out


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


def read_ownership(path):
    """Milestones from status/ownership.md: list of dicts name, spec, order, deps, files; or (None, error)."""
    if not path.is_file():
        return None, f"{path.name} missing: run ownership.py"
    head, data = table_rows(read(path), "Milestone")
    if head is None:
        return None, f"{path.name} has no table whose header starts \"| Milestone\""
    if head != OWNERSHIP_COLS:
        return None, f"{path.name} columns {head}: expected {', '.join(OWNERSHIP_COLS)}"
    names = [r[0] for r in data if r and r[0]]
    out = []
    for i, r in enumerate(data):
        if len(r) < 5 or not r[0]:
            continue
        deps, _ = resolve_deps(r[2], [n for n in names if n != r[0]], {})
        out.append({"name": r[0], "spec": r[1], "order": i, "deps": deps,
                    "files": split_files(r[4])})
    return out, None


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


def generate(folder, release, quiet=False, assume=None):
    """Collect, schedule and write status/ownership.md. Returns (milestones, columns, paths) or
    exits 1. assume maps untagged spec numbers to an epic number (--epic)."""
    milestones, errors = collect(folder)
    if not milestones and not errors:
        errors.append("no '### Milestone:' blocks in plan/specs/*.md and no run/trackers/fix-*-tracker.md")
    col, graph, errs, warnings = schedule(milestones) if not errors else ({}, {}, [], [])
    errors += errs
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    if errors:
        for e in errors:
            print(f"error: {e}", file=sys.stderr)
        print("error: status/ownership.md not written", file=sys.stderr)
        sys.exit(1)
    paths = epic_paths(milestones, graph, epic_of_milestones(folder, milestones, assume))
    milestones.sort(key=lambda m: (num_key(m["spec"]), m["order"]))
    out = folder / OWNERSHIP_MD
    out.parent.mkdir(exist_ok=True)
    out.write_text(render(release, milestones, graph, paths, datetime.date.today().isoformat()),
                   encoding="utf-8")
    if not quiet:
        by_name = {m["name"]: m for m in milestones}
        print(out)
        print(f"{len(milestones)} milestones, {max(col.values())} columns")
        for e, p in sorted(paths.items()):
            print(f"E{e} path: {path_text(p, by_name)}")
    return milestones, col, paths


def main():
    ap = argparse.ArgumentParser(
        usage="ownership.py <release> [--overlap <spec or D ids> ...] [--epic E<n> <spec numbers>] "
              "[--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("--overlap", nargs="+", metavar="ID",
                    help="check mode: files the named specs or D ids share with running epics")
    ap.add_argument("--epic", nargs="+", metavar="ARG",
                    help="E<n> then spec numbers: count those untagged specs as E<n> for the path")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: git top level)")
    a = ap.parse_args()
    if not RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    root = repo_root(a.root)
    folder = release_folder(root, detect_owner(root, a.owner), a.release)
    assume = {}
    if a.epic:
        m = re.match(r"^E(\d+)$", a.epic[0])
        nums = [s.strip() for x in a.epic[1:] for s in x.split(",") if s.strip()]
        if not m or not nums or not all(SPEC_NUM_RE.match(n) for n in nums):
            die("--epic takes E<n> then spec numbers, e.g. --epic E6 09 10")
        assume = {n: int(m.group(1)) for n in nums}
    if a.overlap:
        items = [s.strip() for x in a.overlap for s in x.split(",") if s.strip()]
        sys.exit(1 if overlap(folder, items) else 0)
    if not (folder / SPECS_DIR).is_dir():
        die(f"specs folder missing: {folder / SPECS_DIR}")
    generate(folder, a.release, assume=assume)


if __name__ == "__main__":
    main()
