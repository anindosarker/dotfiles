#!/usr/bin/env python3
"""Read-only status report for an expedition release folder.

Usage: python3 -I status.py <release> [--next] [--owner X] [--root PATH]

--next prints only the first card of the Open lane of queue.md with its sub-bullets; "none"
when Open is empty.

Layout: <release>-plan.md (## Goals and ## Deliverables only), plan/specs/NN-<slug>.md,
plan/epics/E<n>.md, queue.md, status/index.html,
status/ownership.md (ownership.py), status/sprints.md (sprints.py), run/trackers/ (one per milestone,
NN-<slug>-tracker.md or fix-<slug>-tracker.md).

Decisions (### D<n>) get a derived state table from the spec files that cite them and the
Status lines of those specs' milestone trackers. Queue cards (queue.md, a kanban board, see
board.py) are listed with their lane. Queue gaps: an unknown or missing lane (a "**Complete**"
marker line under a lane heading is tolerated, the checkbox state is ignored), a card without a
**Q<n>** token, a duplicate id, a card without a from tag, a Decided card without a first
sub-bullet "Decision: D<n>" or naming a missing decision, a (Q<n>) or "Source: Q<n>" citation
of a missing card. process.md (## P<n>) must
exist with no placeholder left; (P<n>) citations must be defined.

Epics: the tag line under each "### D<n>" heading ("[E<n>]", "[Done]  [E<n>]", or "[Done]"
for a decision with nothing to run) puts the decision in an epic. The summary lists deciding
(no tag), in E<n> (no row of the epic in status/sprints.md carries a run mark), running (one does)
and done ([Done]). The stage line reports discuss and run together ("Stage: discuss, run
(E2, E3)"); a card in Open counts as discuss, never as a stage of its own.
Also under Epics: the decisions still editable in place (no citing spec has a status/sprints.md row
with "[ ]" or "[x]", not superseded); a supersede marked on one side only; an unbuilt spec
citing a superseded decision; for each epic not done, its plan/epics/E<n>.md missing or Notes bullets
without "[ack HH:MM]"; while an epic runs, the next epic file missing.

Gaps reported for the layout: a plan section other than Goals and Deliverables; a
Deliverables Scope cell over 120 characters; a spec with no "### Milestone:" block, a block without Files owned, a Task line without
Checks, no Acceptance line; status/ownership.md missing or older than a spec file ("run
ownership.py"), or one ownership.py would refuse (collision, cycle); status/sprints.md missing,
without a "| Milestone" grid, with text under the grid, with a cell not one of [x], [ ],
·, [!] or blank, or with rows that differ from status/ownership.md. Ownership also lists each
tagged epic's line under "## Critical paths" and reports a missing section or line. A folder
without plan/ is refused (migrate_layout.py), a folder still on the old queue files too
(migrate_queue.py). A tracker Status of merged counts as done. A fix tracker (and any tracker
no milestone owns) counts as citing the queue cards named on its first line.
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
STATUS_VALUE_RE = re.compile(r"^(planned|running|done|merged|skipped)\b\s*(?:\(([^)]*)\))?")
Q_SOURCE_RE = re.compile(r"Source:\s*(Q\d+(?:\s*(?:,|and)\s*Q\d+)*)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.*)$")
GATES_LINE_RE = re.compile(r"^\s*-\s*Checks:")
PLAN_SECTIONS = ("Goals", "Deliverables")
DELIVERABLES_HEAD = r"^## Deliverables\s*$(.*?)(?=^## |\Z)"
SPRINT_MARKS = ("[x]", "[ ]", "·", "[!]", "")
SCOPE_MAX = 120
SPECS_DIR = "plan/specs"
EPICS_DIR = "plan/epics"
TRACKERS_DIR = "run/trackers"
QUEUE_MD = "queue.md"
OWNERSHIP_MD = "status/ownership.md"
SPRINTS_MD = "status/sprints.md"
INDEX_HTML = "status/index.html"
PATHS_HEAD = "## Critical paths"


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


def load_ownership(name="ownership"):
    sys.dont_write_bytecode = True
    path = Path(__file__).resolve().parent / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
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
    rows, state_of = [], {}
    for n, heading, body in items:
        citing = sorted((num for num, c in cited.items() if n in c), key=num_key)
        state_of[n] = item_state(heading, body, citing, statuses)
        rows.append((f"{letter}{n}", ", ".join(citing) or "-", state_of[n]))
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
    return items, state_of


def table_rows(text):
    """Return (header cells, data rows as cell lists) of the first pipe table."""
    lines = [l.strip() for l in text.splitlines() if l.strip().startswith("|")]
    if not lines:
        return None, []
    split = lambda l: [c.strip() for c in l.strip().strip("|").split("|")]
    head = split(lines[0])
    data = [split(l) for l in lines[1:] if not re.fullmatch(r"\|[\s:|-]+\|?", l)]
    return head, data



def q_cites(text):
    """Queue numbers cited as (Q3), (Q3, Q4) or Source: Q3."""
    nums = cites(text, "Q", False)
    for m in Q_SOURCE_RE.finditer(text):
        nums |= {int(n) for n in re.findall(r"Q(\d+)", m.group(1))}
    return nums


def queue_report(folder, bd, text, docs, extra, dec_nums):
    """Print the Queue section: one row per card with its citing specs and lane, then gaps."""
    parsed = bd.parse(text)
    cards = parsed["cards"]
    print(f"Queue: {len(cards)} cards in {QUEUE_MD}")
    texts = {num: read(p) for num, p in docs}
    texts.update({key: first for key, _, first in extra})
    cited = {num: q_cites(t) for num, t in texts.items()}
    rows = []
    for c in cards:
        citing = sorted((num for num, ci in cited.items() if c["num"] in ci), key=num_key)
        rows.append((f"Q{c['num']}", ", ".join(citing) or "-", c["lane"]))
    if rows:
        w1 = max(len(r[0]) for r in rows) + 2
        w2 = max(len(r[1]) for r in rows) + 2
        for a, b, c in rows:
            print(f"  {a.ljust(w1)}{b.ljust(w2)}{c}")
    names = [l["name"] for l in parsed["lanes"]]
    for n in names:
        if n not in bd.LANES:
            print(f"  unknown lane '## {n}': only {', '.join(bd.LANES)}")
    for n in bd.LANES:
        if n not in names:
            print(f"  lane '## {n}' missing")
    for i, line in parsed["stray"]:
        print(f"  {QUEUE_MD}:{i + 1}: card without a **Q<n>** token: {line.strip()[:70]}")
    for c in cards:
        if not c["from"]:
            print(f"  Q{c['num']}: no from tag (#owner, #lead, #lookup or #run-E<n>)")
        if c["lane"] == "Decided":
            dn = bd.decision(c)
            if dn is None:
                print(f"  Q{c['num']}: in Decided without a first sub-bullet 'Decision: D<n>'")
            elif dn not in dec_nums:
                print(f"  Q{c['num']}: Decision D{dn} names a missing decision")
    have = {c["num"] for c in cards}
    sources = [folder / "decisions.md", folder / f"{folder.parent.name}-plan.md"]
    sources += sorted((folder / TRACKERS_DIR).glob("*.md")) + sorted((folder / EPICS_DIR).glob("*.md"))
    sources += [p for _, p in docs]
    missing = collections.defaultdict(set)
    for p in sources:
        if p.is_file():
            for n in q_cites(read(p)) - have:
                missing[n].add(p.relative_to(folder).as_posix())
    for n in sorted(missing):
        print(f"  Q{n} cited but undefined: {', '.join(sorted(missing[n]))}")
    dups = sorted(n for n, k in collections.Counter(c["num"] for c in cards).items() if k > 1)
    if dups:
        print(f"  duplicate numbers: {', '.join(f'Q{n}' for n in dups)}")
    return [c["num"] for c in cards if c["lane"] == "Open"]


def print_next(bd, text):
    """--next: the first card in Open with its sub-bullets, or none."""
    card = next((c for c in bd.parse(text)["cards"] if c["lane"] == "Open"), None)
    print(card["text"] if card else "none")


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def spec_rows(plan):
    """Rows of the Deliverables table: [(num, link)], long scopes [(num, len)]."""
    rows, long_scopes = [], []
    if not plan.is_file():
        return rows, long_scopes
    m = re.search(DELIVERABLES_HEAD, read(plan), re.M | re.S)
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
    """Trackers no spec or milestone owns (fix milestones and the like): (key, path, first line)."""
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
    cands = [t / f"{num}-{slugify(name)}-tracker.md"]
    if idx == 0:
        cands += [t / f"{num}-{spec_slug}-tracker.md", t / f"{num}-tracker.md"]
    return next((c for c in cands if c.is_file()), cands[0])


def new_collect(folder, plan, own):
    rows, long_scopes = spec_rows(plan)
    docs = [(num, folder / f) for num, f in rows if f and (folder / f).is_file()]
    statuses, claimed, blocks, missing = {}, set(), {}, []
    for num, p in docs:
        m = re.match(r"^\d{2}(?:\.\d+)?-(.+)\.md$", p.name)
        spec_slug = m.group(1) if m else ""
        bl = own.parse_spec(p)
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


def new_print(folder, plan, d, own):
    rows, docs, statuses = d["rows"], d["docs"], d["statuses"]
    print("Specs:")
    text = read(plan) if plan.is_file() else ""
    if not plan.is_file():
        print(f"  {plan.name} missing: new_cycle.py writes it")
    elif not re.search(r"^## Deliverables\s*$", text, re.M):
        print(f"  {plan.name} has no ## Deliverables section")
    print(f"  {plan.name} rows: {len(rows)}, linked spec files: {len(docs)}")
    for _, line in outside_fences(text):
        h = re.match(r"^##\s+(.+?)\s*$", line)
        if not h:
            continue
        if h.group(1) not in PLAN_SECTIONS:
            print(f"  {plan.name} has extra section ## {h.group(1)}: only Goals, Deliverables")
    for num, n in d["long"]:
        print(f"  row {num}: Scope {n} chars, over {SCOPE_MAX}: one outcome sentence")
    for num, f in rows:
        if not f:
            print(f"  row {num}: no linked file")
        elif not f.startswith("plan/specs/"):
            print(f"  row {num}: {f} outside plan/specs/")
        elif not (folder / f).is_file():
            print(f"  row {num}: {f} missing (waiting on decisions)")
    linked = {p.name for _, p in docs}
    if (folder / SPECS_DIR).is_dir():
        for p in sorted((folder / SPECS_DIR).iterdir(), key=lambda p: p.name):
            if p.is_file() and p.suffix == ".md" and p.name not in linked:
                print(f"  supporting: {p.relative_to(folder)}")
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
    ownership = folder / OWNERSHIP_MD
    owned = None
    if not docs and not ownership.is_file():
        print("  no specs yet")
    elif not ownership.is_file():
        print("  status/ownership.md missing: run ownership.py")
    else:
        newer = sorted(p.name for _, p in docs if p.stat().st_mtime > ownership.stat().st_mtime)
        if newer:
            print(f"  status/ownership.md older than plan/specs/{newer[0]}: run ownership.py")
        owned, err = own.read_ownership(ownership)
        if err:
            print(f"  {err}")
        current, errors = own.collect(folder)
        if not errors:
            _, _, errors, _ = own.schedule(current)
        for e in errors:
            print(f"  ownership.py would fail: {e}")
        if owned is not None and not errors:
            have = {m["name"] for m in owned}
            want = {m["name"] for m in current}
            for n in sorted(want - have):
                print(f"  milestone not in status/ownership.md: {n} (run ownership.py)")
            for n in sorted(have - want):
                print(f"  status/ownership.md row with no milestone block or fix tracker: {n} (run ownership.py)")
        if owned is not None:
            paths = own.read_paths(ownership)
            print(f"  {len(owned)} milestones; critical paths: {len(paths)} epics")
            if PATHS_HEAD not in read(ownership):
                print(f"  status/ownership.md has no '{PATHS_HEAD}' section: run ownership.py")
            tagged = sorted({e for e, _ in own.spec_epics(folder).values() if e})
            for e in tagged:
                print(f"  E{e} path: {' > '.join(paths[e])}" if e in paths
                      else f"  E{e} has no critical path line: run ownership.py")

    print("Sprints:")
    sprints = folder / SPRINTS_MD
    if owned is None:
        print("  no status/ownership.md to compare with" if docs else "  no specs yet")
    if not sprints.is_file():
        if docs:
            print("  status/sprints.md missing: run sprints.py")
    else:
        head, data = own.table_rows(read(sprints), "Milestone")
        if head is None:
            print("  status/sprints.md has no grid whose header starts \"| Milestone\"")
        else:
            lines = read(sprints).splitlines()
            start = next(i for i, l in enumerate(lines) if re.match(r"^\s*\|\s*Milestone\s*\|", l))
            end = start
            while end < len(lines) and lines[end].strip().startswith("|"):
                end += 1
            if any(l.strip() for l in lines[end:]):
                print("  status/sprints.md has text under the grid: grid only")
            for r in data:
                for c in r[1:]:
                    if c not in SPRINT_MARKS:
                        print(f"  status/sprints.md row {r[0]}: cell {c!r} not one of [x], [ ], ·, [!], blank")
            sp = load_ownership("sprints")
            grid = [sp.row_name(r[0]) for r in data if r and r[0]]
            ticked = sum(1 for r in data if "[x]" in r[1:])
            print(f"  {len(grid)} rows, {len(head) - 1} columns, {ticked} done")
            if owned is not None:
                in_epic = sp.epic_rows(folder, own, owned)
                names = [m["name"] for m in owned if m["name"] in in_epic or m["spec"] == own.FIX]
                for n in names:
                    if n not in grid:
                        print(f"  status/ownership.md row not in status/sprints.md: {n} (run sprints.py)")
                for n in grid:
                    if n not in names:
                        print(f"  status/sprints.md row not in status/ownership.md or in no epic: {n}")

    print("Spec checks:")
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


def epic_marks(path):
    """{epic number: True when a status/sprints.md row of that epic ("E<n> NN name") holds a run mark}."""
    if not path.is_file():
        return {}
    head, data = load_ownership().table_rows(read(path), "Milestone")
    out = {}
    for r in data if head else []:
        m = re.match(r"^E(\d+)\s", r[0]) if r else None
        if m:
            out[int(m.group(1))] = out.get(int(m.group(1)), False) or any(
                c in ("[ ]", "[x]", "[!]") for c in r[1:])
    return out


def built_specs(path):
    """Spec numbers with a status/sprints.md row ("E<n> NN name") holding "[ ]" or "[x]"."""
    if not path.is_file():
        return set()
    head, data = load_ownership().table_rows(read(path), "Milestone")
    out = set()
    for r in data if head else []:
        m = re.match(r"^E\d+\s+(\d{2}(?:\.\d+)?)\s", r[0]) if r else None
        if m and any(c in ("[ ]", "[x]") for c in r[1:]):
            out.add(m.group(1))
    return out


ACK_RE = re.compile(r"\[ack \d{1,2}:\d{2}\]")


def unacked_notes(path):
    """Notes bullets of an epic file without an ack."""
    out, notes = [], False
    for _, line in outside_fences(read(path)):
        if line.startswith("## "):
            notes = line.strip() == "## Notes"
        elif notes and line.startswith("- ") and not ACK_RE.search(line):
            out.append(line[2:].strip())
    return out


def main():
    ap = argparse.ArgumentParser(usage="status.py <release> [--next] [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("--next", action="store_true")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: git top level)")
    a = ap.parse_args()
    if not RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    root = repo_root(a.root)
    owner = detect_owner(root, a.owner)
    folder = load_ownership().release_folder(root, owner, a.release)
    queue = folder / QUEUE_MD
    bd = load_ownership("board")
    q_text = read(queue) if queue.is_file() else ""
    if a.next:
        print_next(bd, q_text)
        return
    rel = folder.relative_to(root)
    rules = find_rules(root)
    print(f"Planning rules: {', '.join(rules) if rules else 'none, bundled default'}")
    print(f"Release {a.release} ({rel})")

    plan = folder / f"{a.release}-plan.md"
    index = plan
    decisions = folder / "decisions.md"
    print("Files:")
    for p in (plan, folder / OWNERSHIP_MD, folder / SPRINTS_MD, folder / INDEX_HTML, decisions, queue):
        print(f"  {p.relative_to(folder)}: {'present' if p.is_file() else 'missing'}")

    own = load_ownership()
    d = new_collect(folder, plan, own)
    docs, statuses = d["docs"], d["statuses"]

    dec_items, dec_states = state_table("Decisions", "D", decisions, docs, statuses, True)
    open_q = queue_report(folder, bd, q_text, docs, d["extra"], {n for n, _, _ in dec_items})

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


    print("Epics:")
    tags = own.read_tags(folder)
    nums = [n for n, _, _ in dec_items]
    closed = lambda n: dec_states.get(n, "").startswith(("superseded", "deferred"))
    marks = epic_marks(folder / SPRINTS_MD)
    untagged = lambda n: not tags.get(n, {}).get("epic") and not tags.get(n, {}).get("done")
    deciding = [n for n in nums if untagged(n) and not closed(n)]
    done_alone = [n for n in nums if tags.get(n, {}).get("done") and not tags[n].get("epic")]
    groups = collections.defaultdict(list)
    for n in nums:
        if tags.get(n, {}).get("epic"):
            groups[tags[n]["epic"]].append(n)
    running = []
    print(f"  deciding: {', '.join(f'D{n}' for n in deciding) or 'none'}")
    if done_alone:
        print(f"  done, nothing to run: {', '.join(f'D{n}' for n in done_alone)}")
    for e in sorted(groups):
        if all(tags[n]["done"] for n in groups[e]):
            state = " done"
        else:
            state = " running" if marks.get(e) else ""
            running.append(f"E{e}")
        print(f"  E{e}{state}: {', '.join(f'D{n}' for n in groups[e])}")
    heads, bullets = own.supersedes(folder)
    gone = {**bullets, **heads}
    for old, new in sorted(bullets.items()):
        if heads.get(old) != new:
            print(f"  D{new} supersedes D{old}, but the D{old} heading lacks (superseded by D{new})")
    for old, new in sorted(heads.items()):
        if bullets.get(old) != new:
            print(f"  D{old} heading says superseded by D{new}, but D{new} lacks '- Supersedes D{old}.'")
    cited = {num: own.spec_cites(p) for num, p in docs}
    built = built_specs(folder / SPRINTS_MD)
    for num, c in cited.items():
        bad = sorted(c & set(gone)) if num not in built else []
        if bad:
            print(f"  spec {num} cites superseded {', '.join(f'D{n} (by D{gone[n]})' for n in bad)}")
    editable = [n for n in nums if n not in gone
                and not any(n in c for num, c in cited.items() if num in built)]
    print(f"  editable in place: {', '.join(f'D{n}' for n in editable) or 'none'}; every other decision changes by supersede")
    epics_dir = folder / EPICS_DIR
    for e in running:
        ef = epics_dir / f"{e}.md"
        if not ef.is_file():
            print(f"  {ef.relative_to(folder)} missing")
            continue
        for note in unacked_notes(ef):
            print(f"  {e} note without ack: {note[:90]}")
    if any(marks.get(int(e[1:])) for e in running):
        nxt = f"E{max(groups) + 1}"
        if not (epics_dir / f"{nxt}.md").is_file():
            print(f"  plan/epics/{nxt}.md missing: new_epic_file.py {a.release} {nxt}")
    parts = []
    if not dec_items or deciding or open_q:
        parts.append("discuss")
    if running:
        parts.append(f"run ({', '.join(running)})")
    print(f"Stage: {', '.join(parts) or 'discuss'}")


if __name__ == "__main__":
    main()
