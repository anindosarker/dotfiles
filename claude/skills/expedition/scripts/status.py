#!/usr/bin/env python3
"""Read-only status report for an expedition release folder.

Usage: python3 -I status.py <release> [--owner X] [--root PATH]

Layout: plan.md (## Goals and ## Epics only), epics/NN-<slug>.md, ownership.md
(ownership.py), sprints.md (sprints.py), trackers/ (one per milestone, NN-<slug>-tracker.md
or fix-<slug>-tracker.md). A folder with "<release>-plan.md" and no plan.md (specs/, a
## Stories table, a "| Story" grid) is read as the legacy layout with the legacy checks;
nothing is rewritten.

Decisions (### D<n>) and findings (### F<n>) get a derived state table from the epic files
that cite them and the Status lines of those epics' milestone trackers. ATTENTION items
(## A<n>) are untriaged until a decision (Source: A<n>) or an epic cites them. process.md
(## P<n>) must exist with no placeholder left; (P<n>) citations must be defined.

Gaps reported for the layout: a plan.md section other than Goals and Epics (a ## Stories
section: "legacy Stories table, delete it"); an Epics Scope cell over 120 characters; an
epic with no "### Milestone:" block, a block without Files owned, a Task line without
Checks, no Acceptance line; ownership.md missing or older than an epic file ("run
ownership.py"), or one ownership.py would refuse (collision, cycle); sprints.md missing,
without a "| Milestone" grid, with text under the grid, with a cell not one of [x], [ ],
·, [!] or blank, or with rows that differ from ownership.md. A tracker Status of merged
counts as done. A fix tracker (and any tracker no milestone owns) counts as citing the
findings named on its first line.
"""
import argparse
import collections
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

RELEASE_RE = re.compile(r"^v\d+\.\d+\.x$")
SPEC_RE = re.compile(r"^(\d{2}(?:\.\d+)?)-.+\.md$")
ROW_RE = re.compile(r"^\|\s*(\d{2}(?:\.\d+)?)\s*\|(.*)$")
LINK_RE = re.compile(r"\]\(([^)\s]+\.md)\)")
LEGACY_ITEM_RE = re.compile(r"^(\d+)\. ")
SECTION_RE = re.compile(r"^#{1,3}\s")
SUPERSEDED_RE = re.compile(r"\(superseded by ([A-Z]\d+)\)")
DEFERRED_RE = re.compile(r"^\s*-\s*Deferred to\b")
LIST = r"(\d+(?:\s*(?:,|and|to)\s*\d+)*)"
DEC_PAREN_RE = re.compile(r"\(decisions? " + LIST + r"\)")
DEC_BARE_RE = re.compile(r"\bdecision (\d+)(?![\d-])", re.I)
STATUS_RE = re.compile(r"^Status:\s*(.*?)\s*$", re.M)
STATUS_VALUE_RE = re.compile(r"^(planned|running|done|merged)\b\s*(?:\(([^)]*)\))?")
A_HEAD_RE = re.compile(r"^##\s+A(\d+)\b")
SOURCE_RE = re.compile(r"Source:\s*(A\d+(?:\s*(?:,|and)\s*A\d+)*)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.*)$")
GATES_LINE_RE = re.compile(r"^\s*-\s*Checks:")
PLAN_SECTIONS = ("Goals", "Epics")
LEGACY_INDEX_SECTIONS = ("Goals", "Epics", "Stories")
LEGACY_SECTIONS = ("Specs", "Run plan")
EPICS_HEAD = r"^## (?:Epics|Specs)\s*$(.*?)(?=^## |\Z)"
STORY_COLS = ["Story", "Files owned"]  # legacy layout only
SPRINT_MARKS = ("[x]", "[ ]", "·", "[!]", "")
SCOPE_MAX = 120


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


def load_ownership():
    sys.dont_write_bytecode = True
    path = Path(__file__).resolve().parent / "ownership.py"
    spec = importlib.util.spec_from_file_location("ownership", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def find_rules(root):
    sys.dont_write_bytecode = True
    path = Path(__file__).resolve().parent / "find_rules.py"
    spec = importlib.util.spec_from_file_location("find_rules", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.find_rules(root)


def num_key(num):
    try:
        return (0,) + tuple(int(x) for x in num.split("."))
    except ValueError:
        return (1, num)


def read(p):
    return p.read_text(encoding="utf-8", errors="replace")


def expand(listing):
    nums = set()
    for chunk in re.split(r"\s*(?:,|and)\s*", listing):
        m = re.fullmatch(r"(\d+)\s*to\s*(\d+)", chunk.strip())
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            nums.update(range(min(a, b), max(a, b) + 1))
        elif chunk.strip().isdigit():
            nums.add(int(chunk.strip()))
    return nums


def fence_flags(text):
    """Yield (line, inside_fence) for every line."""
    fence = None
    for line in text.splitlines():
        s = line.lstrip()
        m = re.match(r"^(`{3,}|~{3,})", s)
        if m:
            mark = m.group(1)
            if fence is None:
                fence = mark
            elif mark[0] == fence[0] and len(mark) >= len(fence) and s.strip() == mark:
                fence = None
            yield line, True
            continue
        yield line, fence is not None


def outside_fences(text):
    for i, (line, inside) in enumerate(fence_flags(text), 1):
        if not inside:
            yield i, line


def parse_items(path, letter):
    """Return (fmt, items): items is a list of (num, heading, body lines).

    fmt is 'ids' for ### <letter><n> headings, 'legacy' for a numbered list,
    'none' when the file has neither.
    """
    if not path.is_file():
        return "none", []
    head_re = re.compile(r"^###\s+" + letter + r"(\d+)\b(.*)$")
    lines = list(fence_flags(read(path)))
    for fmt, start_re in (("ids", head_re), ("legacy", LEGACY_ITEM_RE)):
        items = []
        for line, inside in lines:
            m = None if inside else start_re.match(line)
            if m:
                rest = m.group(2) if fmt == "ids" else ""
                items.append((int(m.group(1)), rest, []))
            elif items and not inside and SECTION_RE.match(line):
                items.append(None)
            elif items and items[-1] is not None:
                items[-1][2].append(line)
        items = [i for i in items if i is not None]
        if items:
            return fmt, items
    return "none", []


def cites(text, letter, legacy):
    """Numbers cited as (D7) or (D6, D7); legacy adds (decision N) forms."""
    nums = set()
    paren = re.compile(
        r"\(\s*(" + letter + r"\d+(?:\s*(?:,|and)\s*" + letter + r"\d+)*)\s*\)"
    )
    for m in paren.finditer(text):
        nums |= {int(n) for n in re.findall(letter + r"(\d+)", m.group(1))}
    if legacy:
        for m in DEC_PAREN_RE.finditer(text):
            nums |= expand(m.group(1))
        for m in DEC_BARE_RE.finditer(text):
            nums.add(int(m.group(1)))
    return nums


def tracker_path(folder, num):
    """trackers/<num>-tracker.md, else the legacy flat <num>-tracker.md."""
    p = folder / "trackers" / f"{num}-tracker.md"
    return p if p.is_file() else folder / f"{num}-tracker.md"


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


def item_state(heading, body, citing, statuses):
    sup = SUPERSEDED_RE.search(heading)
    if sup:
        return f"superseded by {sup.group(1)}"
    if any(DEFERRED_RE.match(l) for l in body):
        return "deferred"
    if not citing:
        return "unplanned"
    st = [statuses[n] for n in citing]
    if any(s is None for s in st):
        return "unknown"
    states = {"done" if s[0] == "merged" else s[0] for s in st}
    if states == {"done"}:
        shas = [s[1] for s in st if s[1]]
        return f"done ({', '.join(shas)})" if shas else "done"
    if states & {"running", "done"}:
        return "running"
    return "planned"


def state_table(label, letter, path, docs, statuses, legacy_cites, extra=()):
    fmt, items = parse_items(path, letter)
    note = {"ids": "", "legacy": ", legacy numbered list", "none": ""}[fmt]
    print(f"{label}: {len(items)} in {path.name}{note}")
    if fmt == "none" and path.is_file():
        heads = sum(1 for _, l in outside_fences(read(path)) if l.startswith("### "))
        if heads:
            print(f"  legacy format, {heads} headings")
    texts = {num: read(p) for num, p in docs}
    texts.update(dict(extra))
    cited = {num: cites(t, letter, legacy_cites)
             for num, t in texts.items()}
    rows = []
    for n, heading, body in items:
        citing = sorted((num for num, c in cited.items() if n in c), key=num_key)
        rows.append((f"{letter}{n}", ", ".join(citing) or "-",
                     item_state(heading, body, citing, statuses)))
    if rows:
        w1 = max(len(r[0]) for r in rows) + 2
        w2 = max(len(r[1]) for r in rows) + 2
        for a, b, c in rows:
            print(f"  {a.ljust(w1)}{b.ljust(w2)}{c}")
    defined = [n for n, _, _ in items]
    all_cited = set().union(*cited.values()) if cited else set()
    undefined = sorted(all_cited - set(defined))
    if undefined:
        print(f"  cited but undefined: {', '.join(f'{letter}{n}' for n in undefined)}")
    dups = sorted(n for n, c in collections.Counter(defined).items() if c > 1)
    if dups:
        print(f"  duplicate numbers: {', '.join(f'{letter}{n}' for n in dups)}")
    return items


def table_rows(text):
    """Return (header cells, data rows as cell lists) of the first pipe table."""
    lines = [l.strip() for l in text.splitlines() if l.strip().startswith("|")]
    if not lines:
        return None, []
    split = lambda l: [c.strip() for c in l.strip().strip("|").split("|")]
    head = split(lines[0])
    data = [split(l) for l in lines[1:] if not re.fullmatch(r"\|[\s:|-]+\|?", l)]
    return head, data


def story_checks(folder, index_text):
    """Legacy layout: Stories table columns, sprints.md presence, rows and cell marks."""
    m = re.search(r"^## Stories\s*$(.*?)(?=^## |\Z)", index_text, re.M | re.S)
    if not m:
        print("  index has no ## Stories section (files.md)")
        stories = None
    else:
        head, data = table_rows(m.group(1))
        if head is None:
            print("  ## Stories has no table")
            stories = None
        else:
            if head != STORY_COLS:
                print(f"  Stories columns {head}: exactly Story, Files owned (files.md)")
            stories = [r[0] for r in data if r and r[0]]
    sprints = folder / "sprints.md"
    if not sprints.is_file():
        print("  sprints.md missing beside the index (files.md)")
        return
    lines = [l.strip() for l in read(sprints).splitlines()]
    start = next((i for i, l in enumerate(lines) if re.match(r"^\|\s*Story\b", l)), None)
    if start is None:
        print("  sprints.md has no table whose header starts \"| Story\"")
        return
    block = []
    for l in lines[start:]:
        if not l.startswith("|"):
            break
        block.append(l)
    head, data = table_rows("\n".join(block))
    grid = [r[0] for r in data if r and r[0]]
    for r in data:
        for c in r[1:]:
            if c not in SPRINT_MARKS:
                print(f"  sprints.md row {r[0]}: cell {c!r} not one of [x], [ ], ·, [!], blank")
    if stories is not None:
        for name in grid:
            if name not in stories:
                print(f"  mid-run story: {name}")
        for name in stories:
            if name not in grid:
                print(f"  Stories row not in sprints.md: {name}")


def a_cites(text, source_only):
    nums = set()
    for m in SOURCE_RE.finditer(text):
        nums |= {int(n) for n in re.findall(r"A(\d+)", m.group(1))}
    if not source_only:
        nums |= cites(text, "A", False)
    return nums


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def epic_rows(plan):
    """Rows of the Epics table (legacy ## Specs too): [(num, link)], long scopes [(num, len)]."""
    rows, long_scopes = [], []
    if not plan.is_file():
        return rows, long_scopes
    m = re.search(EPICS_HEAD, read(plan), re.M | re.S)
    if m:
        for line in m.group(1).splitlines():
            r = ROW_RE.match(line.strip())
            if r:
                link = LINK_RE.search(r.group(2))
                rows.append((r.group(1), link.group(1) if link else None))
                cells = r.group(2).strip().strip("|").split("|")
                if len(cells) >= 2 and len(cells[-1].strip()) > SCOPE_MAX:
                    long_scopes.append((r.group(1), len(cells[-1].strip())))
    return rows, long_scopes


def other_trackers(folder, claimed, statuses):
    """Trackers no epic or milestone owns (fix milestones and the like): (key, path, first line)."""
    out = []
    if (folder / "trackers").is_dir():
        for p in sorted((folder / "trackers").glob("*-tracker.md")):
            if p.name not in claimed:
                key = p.name[: -len("-tracker.md")]
                lines = read(p).splitlines()
                out.append((key, p, lines[0] if lines else ""))
                statuses[key] = tracker_status(folder, key, p)
    return out


def aggregate(states):
    """One epic state from its milestone tracker states, as tracker_status returns them."""
    if not states or any(s is None for s in states):
        return None
    kinds = {"done" if s[0] in ("merged", "done") else s[0] for s in states}
    if kinds == {"done"}:
        return "merged", ", ".join(s[1] for s in states if s[1])
    if kinds & {"running", "done"}:
        return "running", ""
    return "planned", ""


def legacy_collect(folder, index):
    rows, long_scopes = epic_rows(index)
    docs = [(num, folder / f) for num, f in rows if f and (folder / f).is_file()]
    statuses = {num: tracker_status(folder, num) for num, _ in docs}
    claimed = {f"{num}-tracker.md" for num, _ in docs}
    extra = other_trackers(folder, claimed, statuses)
    return {"rows": rows, "long": long_scopes, "docs": docs, "statuses": statuses, "extra": extra}


def legacy_print(folder, index, d):
    rows, docs, statuses = d["rows"], d["docs"], d["statuses"]
    print("Specs:")
    print(f"  legacy layout: {index.name}, specs/; legacy checks, nothing rewritten")
    if index.is_file() and not rows and not re.search(r"^## (?:Epics|Specs)\s*$", read(index), re.M):
        print("  index has no ## Epics section")
    print(f"  index rows: {len(rows)}, linked spec files: {len(docs)}")
    if index.is_file():
        for _, line in outside_fences(read(index)):
            h = re.match(r"^##\s+(.+?)\s*$", line)
            if h and h.group(1) not in LEGACY_INDEX_SECTIONS + LEGACY_SECTIONS:
                print(f"  index has extra section ## {h.group(1)}: only Goals, Epics, Stories (files.md)")
    for num, n in d["long"]:
        print(f"  row {num}: Scope {n} chars, over {SCOPE_MAX}: one outcome sentence (files.md)")
    for num, f in rows:
        if not f:
            print(f"  row {num}: no linked file")
        elif not (folder / f).is_file():
            print(f"  row {num}: {f} missing (waiting on decisions)")
    linked = {p.name for _, p in docs}
    for sub in [x for x in (folder / "specs", folder) if x.is_dir()]:
        for p in sorted(sub.iterdir(), key=lambda p: p.name):
            if (p.is_file() and SPEC_RE.match(p.name)
                    and not p.name.endswith("-tracker.md") and p.name not in linked):
                print(f"  supporting: {p.relative_to(folder)}")
    for num, _ in docs:
        t = tracker_path(folder, num)
        if not t.is_file():
            print(f"  no tracker: spec {num}")
        elif statuses[num] is None:
            print(f"  no Status line: {t.name}")
    for key, p, _ in d["extra"]:
        if statuses[key] is None:
            print(f"  no Status line: {p.name}")
    if docs and index.is_file():
        idx = read(index)
        if re.search(r"^## Run plan\s*$", idx, re.M):
            print("  legacy index: ## Run plan, no Stories or sprints.md checks")
        else:
            story_checks(folder, idx)

    print("Spec checks:")
    quiet = True
    for _, p in docs:
        text = read(p)
        has_gates = False
        for i, line in outside_fences(text):
            h = HEADING_RE.match(line)
            if h:
                if re.search(r"\bGates\b", h.group(1)):
                    has_gates = True
                continue
            if GATES_LINE_RE.match(line):
                has_gates = True
        if not has_gates:
            print(f"  {p.name}: no checks")
            quiet = False
        if not re.search(r"^\s*-\s*Acceptance:", text, re.M):
            print(f"  {p.name}: no Acceptance line")
            quiet = False
        for i, line in outside_fences(text):
            if line.rstrip().endswith("?"):
                print(f"  {p.name}:{i}: open question? {line.strip()[:80]}")
                quiet = False
    if quiet:
        print("  ok")


def milestone_tracker(folder, num, epic_slug, idx, name):
    """trackers/NN-<milestone-slug>-tracker.md; the first milestone also takes NN-<epic-slug>
    and NN-tracker.md."""
    t = folder / "trackers"
    cands = [t / f"{num}-{slugify(name)}-tracker.md"]
    if idx == 0:
        cands += [t / f"{num}-{epic_slug}-tracker.md", t / f"{num}-tracker.md"]
    return next((c for c in cands if c.is_file()), cands[0])


def new_collect(folder, plan, own):
    rows, long_scopes = epic_rows(plan)
    docs = [(num, folder / f) for num, f in rows if f and (folder / f).is_file()]
    statuses, claimed, blocks, missing = {}, set(), {}, []
    for num, p in docs:
        m = re.match(r"^\d{2}(?:\.\d+)?-(.+)\.md$", p.name)
        epic_slug = m.group(1) if m else ""
        bl = own.parse_epic(p)
        blocks[num] = bl
        states = []
        for i, b in enumerate(bl):
            t = milestone_tracker(folder, num, epic_slug, i, b["name"])
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
            t = folder / "trackers" / f"{num}-tracker.md"
            states = [tracker_status(folder, num, t)] if t.is_file() else [("planned", "")]
            if t.is_file():
                claimed.add(t.name)
        statuses[num] = aggregate(states)
    extra = other_trackers(folder, claimed, statuses)
    return {"rows": rows, "long": long_scopes, "docs": docs, "statuses": statuses,
            "extra": extra, "blocks": blocks, "missing": missing}


def new_print(folder, plan, d, own):
    rows, docs, statuses = d["rows"], d["docs"], d["statuses"]
    print("Epics:")
    text = read(plan) if plan.is_file() else ""
    if not plan.is_file():
        print("  plan.md missing: new_cycle.py writes it")
    elif not re.search(r"^## Epics\s*$", text, re.M):
        print("  plan.md has no ## Epics section")
    print(f"  plan.md rows: {len(rows)}, linked epic files: {len(docs)}")
    for _, line in outside_fences(text):
        h = re.match(r"^##\s+(.+?)\s*$", line)
        if not h:
            continue
        if h.group(1) == "Stories":
            print("  plan.md: legacy Stories table, delete it (ownership.md replaces it)")
        elif h.group(1) not in PLAN_SECTIONS:
            print(f"  plan.md has extra section ## {h.group(1)}: only Goals, Epics")
    for num, n in d["long"]:
        print(f"  row {num}: Scope {n} chars, over {SCOPE_MAX}: one outcome sentence")
    for num, f in rows:
        if not f:
            print(f"  row {num}: no linked file")
        elif not f.startswith("epics/"):
            print(f"  row {num}: {f} outside epics/")
        elif not (folder / f).is_file():
            print(f"  row {num}: {f} missing (waiting on decisions)")
    linked = {p.name for _, p in docs}
    if (folder / "epics").is_dir():
        for p in sorted((folder / "epics").iterdir(), key=lambda p: p.name):
            if p.is_file() and p.suffix == ".md" and p.name not in linked:
                print(f"  supporting: {p.relative_to(folder)}")
    if (folder / "specs").is_dir():
        print("  legacy specs/ folder beside plan.md: move its files to epics/")
    for num, p in docs:
        bl = d["blocks"][num]
        if not bl:
            print(f"  {p.relative_to(folder)}: no '### Milestone:' block")
        for b in bl:
            if b["files"] is None:
                print(f"  {p.relative_to(folder)}:{b['line']}: milestone {b['name']}: no Files owned line")
    for line in d["missing"]:
        print(f"  {line}")
    for key, p, _ in d["extra"]:
        if statuses[key] is None:
            print(f"  no Status line: {p.name}")

    print("Ownership:")
    ownership = folder / "ownership.md"
    owned = None
    if not docs and not ownership.is_file():
        print("  no epics yet")
    elif not ownership.is_file():
        print("  ownership.md missing: run ownership.py")
    else:
        newer = sorted(p.name for _, p in docs if p.stat().st_mtime > ownership.stat().st_mtime)
        if newer:
            print(f"  ownership.md older than epics/{newer[0]}: run ownership.py")
        owned, err = own.read_ownership(ownership)
        if err:
            print(f"  {err}")
        current, errors = own.collect(folder)
        if not errors:
            _, path, errors, _ = own.schedule(current)
        for e in errors:
            print(f"  ownership.py would fail: {e}")
        if owned is not None and not errors:
            have = {m["name"] for m in owned}
            want = {m["name"] for m in current}
            for n in sorted(want - have):
                print(f"  milestone not in ownership.md: {n} (run ownership.py)")
            for n in sorted(have - want):
                print(f"  ownership.md row with no milestone block or fix tracker: {n} (run ownership.py)")
        if owned is not None:
            cp = re.search(r"^Critical path:\s*(.*)$", read(ownership), re.M)
            print(f"  {len(owned)} milestones; critical path: {cp.group(1) if cp else 'line missing'}")

    print("Sprints:")
    sprints = folder / "sprints.md"
    if owned is None:
        print("  no ownership.md to compare with" if docs else "  no epics yet")
    if not sprints.is_file():
        if docs:
            print("  sprints.md missing: run sprints.py")
    else:
        head, data = own.table_rows(read(sprints), "Milestone")
        if head is None:
            if own.table_rows(read(sprints), "Story")[0] is not None:
                print("  sprints.md has a legacy \"| Story\" grid: run sprints.py")
            else:
                print("  sprints.md has no grid whose header starts \"| Milestone\"")
        else:
            lines = read(sprints).splitlines()
            start = next(i for i, l in enumerate(lines) if re.match(r"^\s*\|\s*Milestone\s*\|", l))
            end = start
            while end < len(lines) and lines[end].strip().startswith("|"):
                end += 1
            if any(l.strip() for l in lines[end:]):
                print("  sprints.md has text under the grid: grid only")
            for r in data:
                for c in r[1:]:
                    if c not in SPRINT_MARKS:
                        print(f"  sprints.md row {r[0]}: cell {c!r} not one of [x], [ ], ·, [!], blank")
            grid = [r[0] for r in data if r and r[0]]
            ticked = sum(1 for r in data if "[x]" in r[1:])
            print(f"  {len(grid)} rows, {len(head) - 1} sprints, {ticked} done")
            if owned is not None:
                names = [m["name"] for m in owned]
                for n in names:
                    if n not in grid:
                        print(f"  ownership.md row not in sprints.md: {n} (run sprints.py)")
                for n in grid:
                    if n not in names:
                        print(f"  sprints.md row not in ownership.md: {n}")

    print("Epic checks:")
    quiet = True
    for num, p in docs:
        text = read(p)
        name = p.relative_to(folder)
        tasks = 0
        for b in d["blocks"][num]:
            for i, t in b["tasks"]:
                tasks += 1
                if "Checks:" not in t:
                    print(f"  {name}:{i}: Task line without Checks")
                    quiet = False
        if not tasks and not any(GATES_LINE_RE.match(l) for _, l in outside_fences(text)):
            print(f"  {name}: no checks")
            quiet = False
        if not re.search(r"^\s*-\s*Acceptance:", text, re.M):
            print(f"  {name}: no Acceptance line")
            quiet = False
        for i, line in outside_fences(text):
            if line.rstrip().endswith("?"):
                print(f"  {name}:{i}: open question? {line.strip()[:80]}")
                quiet = False
    if quiet:
        print("  ok")


def main():
    ap = argparse.ArgumentParser(usage="status.py <release> [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: git top level)")
    a = ap.parse_args()
    if not RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    root = repo_root(a.root)
    owner = detect_owner(root, a.owner)
    folder = root / ".ai" / "plans" / a.release / owner
    if not folder.is_dir():
        die(f"release folder missing: {folder}")
    rel = folder.relative_to(root)
    rules = find_rules(root)
    print(f"Planning rules: {', '.join(rules) if rules else 'none, bundled default'}")
    print(f"Release {a.release} ({rel})")

    plan = folder / "plan.md"
    legacy_index = folder / f"{a.release}-plan.md"
    legacy = not plan.is_file() and legacy_index.is_file()
    index = legacy_index if legacy else plan
    decisions = folder / "decisions.md"
    findings = folder / "findings.md"
    print("Files:" + (" legacy layout" if legacy else ""))
    shown = (index, decisions, findings) if legacy else (
        plan, folder / "ownership.md", folder / "sprints.md", decisions, findings)
    for p in shown:
        print(f"  {p.name}: {'present' if p.is_file() else 'missing'}")
    if not legacy and legacy_index.is_file():
        print(f"  legacy: {legacy_index.name} beside plan.md")
    for name in ("decisions-review.md", "findings-review.md"):
        if (folder / name).is_file():
            print(f"  legacy: {name}")

    own = None if legacy else load_ownership()
    d = legacy_collect(folder, index) if legacy else new_collect(folder, plan, own)
    docs, statuses = d["docs"], d["statuses"]

    dec_items = state_table("Decisions", "D", decisions, docs, statuses, True)
    state_table("Findings", "F", findings, docs, statuses, False,
                [(key, first) for key, _, first in d["extra"]])

    if legacy:
        legacy_print(folder, index, d)
    else:
        new_print(folder, plan, d, own)

    print("Process:")
    proc = folder / "process.md"
    if not proc.is_file():
        print("  process.md missing: new_cycle.py copies it from the previous release")
        p_ids = []
    else:
        lines = [l for _, l in outside_fences(read(proc))]
        p_ids = [int(m.group(1)) for l in lines if (m := re.match(r"^##\s+P(\d+)\b", l))]
        left = [(i, l.strip()[:70]) for i, l in outside_fences(read(proc))
                if re.search(r"\[[^\]`\n]+\]", l) and "[...]" not in l]
        print(f"  process.md: {len(p_ids)} rules" + (f", P{min(p_ids)} to P{max(p_ids)}" if p_ids else ""))
        for i, l in left:
            print(f"  placeholder at line {i}: {l}")
        dups = sorted(n for n, c in collections.Counter(p_ids).items() if c > 1)
        if dups:
            print(f"  duplicate numbers: {', '.join(f'P{n}' for n in dups)}")
    cited_p = set()
    for _, p in docs:
        cited_p |= cites(read(p), "P", False)
    if index.is_file():
        cited_p |= cites(read(index), "P", False)
    undefined_p = sorted(cited_p - set(p_ids))
    if undefined_p:
        print(f"  cited but undefined: {', '.join(f'P{n}' for n in undefined_p)}")

    print("ATTENTION:")
    attention = sorted(list(folder.glob("ATTENTION-*.md")) + list((folder / "attentions").glob("ATTENTION-*.md")))
    a_ids = []
    if not attention:
        print("  none")
    for p in attention:
        lines = [l for _, l in outside_fences(read(p))]
        ids = [int(m.group(1)) for l in lines if (m := A_HEAD_RE.match(l))]
        if ids:
            a_ids += ids
            print(f"  {p.name}: {len(ids)} items, A{min(ids)} to A{max(ids)}")
        else:
            bullets = sum(1 for l in lines if l.startswith("- "))
            print(f"  {p.name}: legacy format, {bullets} bullets")
    cited_a = a_cites(read(decisions), True) if decisions.is_file() else set()
    for _, p in docs:
        cited_a |= a_cites(read(p), False)
    uncited = sorted(set(a_ids) - cited_a)
    if a_ids:
        print(f"  untriaged: {', '.join(f'A{n}' for n in uncited) or 'none'}")
    dups = sorted(n for n, c in collections.Counter(a_ids).items() if c > 1)
    if dups:
        print(f"  duplicate numbers: {', '.join(f'A{n}' for n in dups)}")

    if not dec_items:
        stage = "discuss"
    elif not docs:
        stage = "plan"
    elif uncited:
        stage = "triage"
    else:
        stage = "run"
    print(f"Stage: {stage}")


if __name__ == "__main__":
    main()
