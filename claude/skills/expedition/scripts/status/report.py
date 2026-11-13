#!/usr/bin/env python3
"""Read-only status report for an expedition release folder.

Usage: python3 -I status/report.py <release> [--owner X] [--root PATH]

The next queue card: queue/next.py. The owner's progress reply: status/progress.py.

Layout: <release>-plan.md (## Goals and ## Deliverables only), plan/specs/NN-<slug>.md,
plan/epics/E<n>.md, queue.md, status/index.html, status/sprints.md (sprints/refresh.py), run/trackers/
(one per milestone, NN-<slug>-tracker.md). The ownership facts come from
lib/ownership.py compute, in memory.

Decisions (the **D<n>** cards of the decisions.md board, lib/decisions.py) are listed with the
specs citing them and their state from the Done rule (to do, in progress, done, superseded by
D<n>, deferred). Board gaps, one line each: a missing lane, a card without a **D<n>** token, a
tag other than #superseded, #deferred, #E<n> and #R<n>, a duplicate id, ids out of order inside
a lane, a card whose lane disagrees with the Done rule (a hand drag; the next sync moves it back),
a tick that disagrees with its lane. Queue cards (queue.md, a kanban board, see
lib/board.py) are listed with their lane. Queue gaps: an unknown or missing lane (a "**Complete**"
marker line under a lane heading is tolerated), a card without a **Q<n>** token, a duplicate id,
a tag on a title line that is not #D<n> or #E<n>, a leftover "Decision:" sub-bullet, a Decided
card without #D<n> or with a #D<n> naming a missing decision, a Decided card whose tick or #E<n>
tag disagrees with the lane of its decision (the next queue/item.py, epics/tag.py or
sprints/refresh.py run syncs it), a (Q<n>) or "Source: Q<n>" citation of a missing card. process.md (## P<n>) must
exist with no placeholder left; (P<n>) citations must be defined.

Epics: the #E<n> tag of a decision card puts the decision in an epic. The summary lists deciding
(the To do lane), done with nothing to run (in Done, no epic tag, not superseded or deferred),
in E<n> (no row of the epic in status/sprints.md carries a run mark), running (one does) and done
(every decision of the epic in Done). The stage line reports discuss and run together ("Stage: discuss, run
(E2, E3)"); a card in Open counts as discuss, never as a stage of its own.
Also under Epics: the decisions still editable in place (no citing spec has a status/sprints.md row
with "[ ]" or "[x]", not superseded); a supersede marked on one side only; an unbuilt spec
citing a superseded decision; for each epic not done, its plan/epics/E<n>.md missing or Notes bullets
without "[ack HH:MM]" (only when the file has a ## Notes section); an epic file whose epic has
grid rows and no "Starts:" value, or a Starts value that is not S<number>; while an epic runs,
the next epic file missing. The epic files' "## Ownership" tables (lib/ownership.py epic_gaps): an epic
with grid rows whose file has no table, an unreadable table, a decision of the Decisions line
with no row, a spec of the epic with no row, a row file no milestone of its spec owns, a Sprint
cell that disagrees with the grid. Epics without an epic file are not flagged.

Gaps reported for the layout: a plan section other than Goals and Deliverables; a
Deliverables Scope cell over 120 characters; a spec with no "### Milestone:" block, a block without Files owned, a Task line without
Checks, no Acceptance line; milestones sprints/check.py would refuse (collision, cycle);
status/sprints.md missing, without a "| Milestone" grid, with text under the grid, with a cell
not one of [x], [ ], ·, [!] or blank, or with rows that differ from the milestones of the specs
with an Epic line. Ownership also prints each tagged epic's critical path,
computed on the fly. A folder without plan/ is refused (migrate/layout.py), a folder still on
the old queue files too (migrate/queue.py), a decisions.md in the heading format too
(migrate/decisions.py), a folder that still has status/ownership.md too
(migrate/epics.py), a folder that still has run/trackers/fix-*-tracker.md too (migrate/fixes.py).
A tracker Status of merged counts as done. A tracker no milestone owns counts as citing the
queue cards named on its first line.
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
read, fence_flags, outside_fences, die = C.read, C.fence_flags, C.outside_fences, C.die
SPECS_DIR, EPICS_DIR, TRACKERS_DIR, QUEUE_MD = C.SPECS_DIR, C.EPICS_DIR, C.TRACKERS_DIR, C.QUEUE_MD
SPRINTS_MD, INDEX_HTML = C.SPRINTS_MD, C.INDEX_HTML

SPEC_RE = re.compile(r"^(\d{2}(?:\.\d+)?)-.+\.md$")
LIST = r"(\d+(?:\s*(?:,|and|to)\s*\d+)*)"
DEC_PAREN_RE = re.compile(r"\(decisions? " + LIST + r"\)")
DEC_BARE_RE = re.compile(r"\bdecision (\d+)(?![\d-])", re.I)
Q_SOURCE_RE = re.compile(r"Source:\s*(Q\d+(?:\s*(?:,|and)\s*Q\d+)*)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.*)$")
GATES_LINE_RE = re.compile(r"^\s*-\s*Checks:")
PLAN_SECTIONS = ("Goals", "Deliverables")
SPRINT_MARKS = ("[x]", "[ ]", "·", "[!]", "")


num_key = C.spec_key


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


def decision_state(card, lane):
    """The state column of a decision: its Done rule lane, or why it is closed."""
    if card["sup_by"]:
        return f"superseded by D{card['sup_by'][0]}"
    if card["deferred"]:
        return "deferred"
    return lane.lower()


def decision_table(folder, path, docs, extra=()):
    """Print the Decisions section: one row per card (id, citing specs, state), then the board
    gaps. Returns (cards, {D: rule lane})."""
    dc = C.load("lib/decisions")
    parsed = dc.parse(read(path)) if path.is_file() else {"lanes": [], "cards": [], "stray": []}
    cards = parsed["cards"]
    print(f"Decisions: {len(cards)} in {path.name}")
    texts = {num: read(p) for num, p in docs}
    texts.update(dict(extra))
    cited = {num: cites(t, "D", True) for num, t in texts.items()}
    want = dc.rule_lanes(folder, cards)
    rows = []
    for c in sorted(cards, key=lambda c: c["num"]):
        citing = sorted((num for num, ci in cited.items() if c["num"] in ci), key=num_key)
        rows.append((f"D{c['num']}", ", ".join(citing) or "-", decision_state(c, want[c["num"]])))
    if rows:
        w1 = max(len(r[0]) for r in rows) + 2
        w2 = max(len(r[1]) for r in rows) + 2
        for a, b, c in rows:
            print(f"  {a.ljust(w1)}{b.ljust(w2)}{c}")
    names = [l["name"] for l in parsed["lanes"]]
    for n in dc.LANES:
        if n not in names:
            print(f"  lane '## {n}' missing")
    for i, line in parsed["stray"]:
        print(f"  {path.name}:{i + 1}: card without a **D<n>** token: {line.strip()[:70]}")
    for c in cards:
        bad = [f"#{t}" for t in c["tags"] if not dc.TAG_OK_RE.match(t)]
        if bad:
            print(f"  D{c['num']}: tag {', '.join(bad)} on the title line: only #superseded, #deferred, #E<n>, #R<n>")
    for lane in dc.LANES:
        nums = [c["num"] for c in cards if c["lane"] == lane]
        if nums != sorted(nums):
            print(f"  {lane}: ids out of order: {', '.join(f'D{n}' for n in nums)}")
    for c in cards:
        if c["lane"] in dc.LANES and c["lane"] != want[c["num"]]:
            print(f"  D{c['num']}: in {c['lane']}, the Done rule says {want[c['num']]} (a hand drag): "
                  f"the next sync moves it")
        elif c["lane"] in dc.LANES and c["ticked"] != (c["lane"] == dc.DONE):
            print(f"  D{c['num']}: {'ticked' if c['ticked'] else 'unticked'} in {c['lane']}: "
                  f"the next sync sets the tick of its lane")
    defined = [c["num"] for c in cards]
    all_cited = set().union(*cited.values()) if cited else set()
    undefined = sorted(all_cited - set(defined))
    if undefined:
        print(f"  cited but undefined: {', '.join(f'D{n}' for n in undefined)}")
    dups = sorted(n for n, k in collections.Counter(defined).items() if k > 1)
    if dups:
        print(f"  duplicate numbers: {', '.join(f'D{n}' for n in dups)}")
    return cards, want


def q_cites(text):
    """Queue numbers cited as (Q3), (Q3, Q4) or Source: Q3."""
    nums = cites(text, "Q", False)
    for m in Q_SOURCE_RE.finditer(text):
        nums |= {int(n) for n in re.findall(r"Q(\d+)", m.group(1))}
    return nums


LEFT_DECISION_RE = re.compile(r"^\s+-\s*Decision:\s*D\d+")


def queue_report(folder, bd, text, docs, extra, dec_nums, tags):
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
        bad = [f"#{t}" for t in c["tags"] if not bd.CARD_TAG_RE.match(t)]
        if bad:
            print(f"  Q{c['num']}: tag {', '.join(bad)} on the title line: only #D<n> and #E<n>")
        if any(LEFT_DECISION_RE.match(s) for s in c["subs"]):
            print(f"  Q{c['num']}: leftover 'Decision:' sub-bullet: the decision is the #D<n> tag")
        if c["lane"] != "Decided":
            continue
        if c["d"] is None:
            print(f"  Q{c['num']}: in Decided without a #D<n> tag")
        elif c["d"] not in dec_nums:
            print(f"  Q{c['num']}: #D{c['d']} names a missing decision")
        else:
            box, epic = bd.want(c, tags)
            have = "[x]" if c["box"] == "x" else "[ ]"
            if (have, c["e"]) != (box, epic):
                shows = have + (f" #E{c['e']}" if c["e"] else "")
                says = box + (f" #E{epic}" if epic else "")
                print(f"  Q{c['num']}: shows {shows}, the lane of D{c['d']} says {says}: "
                      f"the next queue/item.py, epics/tag.py or sprints/refresh.py run syncs it")
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


def new_print(folder, plan, d, own):
    rows, docs, statuses = d["rows"], d["docs"], d["statuses"]
    print("Specs:")
    text = read(plan) if plan.is_file() else ""
    if not plan.is_file():
        print(f"  {plan.name} missing: plan/new_cycle.py writes it")
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
        print(f"  row {num}: Scope {n} chars, over {own.SCOPE_MAX}: one outcome sentence")
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
    comp = own.compute(folder)
    owned = None
    if not docs:
        print("  no specs yet")
    else:
        for e in comp["errors"]:
            print(f"  sprints/check.py would fail: {e}")
        if not comp["errors"]:
            owned = comp["milestones"]
            by_name = {m["name"]: m for m in owned}
            print(f"  {len(owned)} milestones, {max(comp['col'].values(), default=0)} columns")
            tagged = sorted({e for e, _ in own.spec_epics(folder).values() if e})
            for e in tagged:
                print(f"  E{e} path: {own.path_text(comp['paths'].get(e, []), by_name)}")

    print("Sprints:")
    sprints = folder / SPRINTS_MD
    if owned is None:
        print("  no milestones to compare with" if docs else "  no specs yet")
    if not sprints.is_file():
        if docs:
            print("  status/sprints.md missing: run sprints/refresh.py")
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
            sp = C.load("lib/grid")
            grid = [sp.row_name(r[0]) for r in data if r and r[0]]
            ticked = sum(1 for r in data if "[x]" in r[1:])
            print(f"  {len(grid)} rows, {len(head) - 1} columns, {ticked} done")
            if owned is not None:
                in_epic = sp.epic_rows(folder, own, owned)
                names = [m["name"] for m in owned if m["name"] in in_epic]
                for n in names:
                    if n not in grid:
                        print(f"  milestone not in status/sprints.md: {n} (run sprints/refresh.py)")
                for n in grid:
                    if n not in names:
                        print(f"  status/sprints.md row with no milestone or in no epic: {n}")

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
    head, data = C.table_rows(read(path), "Milestone")
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
    head, data = C.table_rows(read(path), "Milestone")
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
    ap = argparse.ArgumentParser(
        usage="status/report.py <release> [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    root = C.repo_root(a.root, a.release)
    owner = C.detect_owner(root, a.owner)
    folder = C.release_folder(root, owner, a.release)
    queue = folder / QUEUE_MD
    bd = C.load("lib/board")
    q_text = read(queue) if queue.is_file() else ""
    rel = folder.relative_to(root)
    rules = C.find_rules(root)
    print(f"Planning rules: {', '.join(rules) if rules else 'none, bundled default'}")
    print(f"Release {a.release} ({rel})")

    plan = folder / f"{a.release}-plan.md"
    index = plan
    decisions = folder / "decisions.md"
    print("Files:")
    for p in (plan, folder / SPRINTS_MD, folder / INDEX_HTML, decisions, queue):
        print(f"  {p.relative_to(folder)}: {'present' if p.is_file() else 'missing'}")

    own = C.load("lib/ownership")
    d = own.new_collect(folder, plan)
    docs, statuses = d["docs"], d["statuses"]

    dec_cards, _ = decision_table(folder, decisions, docs)
    open_q = queue_report(folder, bd, q_text, docs, d["extra"], {c["num"] for c in dec_cards},
                          bd.decision_tags(own, folder))

    new_print(folder, plan, d, own)

    print("Process:")
    proc = folder / "process.md"
    if not proc.is_file():
        print("  process.md missing: plan/new_cycle.py copies it from the previous release")
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
    nums = sorted(c["num"] for c in dec_cards)
    card = {c["num"]: c for c in dec_cards}
    marks = epic_marks(folder / SPRINTS_MD)
    deciding = [n for n in nums if card[n]["lane"] == "To do"]
    done_alone = [n for n in nums if card[n]["lane"] == "Done" and not card[n]["epic"]
                  and not card[n]["sup_by"] and not card[n]["deferred"]]
    groups = collections.defaultdict(list)
    for n in nums:
        if card[n]["epic"]:
            groups[card[n]["epic"]].append(n)
    running = []
    print(f"  deciding: {', '.join(f'D{n}' for n in deciding) or 'none'}")
    if done_alone:
        print(f"  done, nothing to run: {', '.join(f'D{n}' for n in done_alone)}")
    for e in sorted(groups):
        if all(card[n]["lane"] == "Done" for n in groups[e]):
            state = " done"
        else:
            state = " running" if marks.get(e) else ""
            running.append(f"E{e}")
        print(f"  E{e}{state}: {', '.join(f'D{n}' for n in groups[e])}")
    heads, bullets = own.supersedes(folder)
    gone = {**bullets, **heads}
    for old, new in sorted(bullets.items()):
        if heads.get(old) != new:
            print(f"  D{new} supersedes D{old}, but the D{old} title lacks (superseded by D{new})")
    for old, new in sorted(heads.items()):
        if bullets.get(old) != new:
            print(f"  D{old} title says superseded by D{new}, but D{new} lacks '- Supersedes D{old}.'")
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
    starts = own.epic_starts(folder)
    for e in sorted(set(marks) | {n for n, v in starts.items() if v}):
        v = starts.get(e)
        if e in marks and e in starts and not v:
            print(f"  E{e} has rows in status/sprints.md and no Starts value: sprints/backfill_starts.py {a.release}")
        elif v and not own.SPRINT_VALUE_RE.match(v):
            print(f"  plan/epics/E{e}.md: Starts '{v}' is not S<number>")
    for gap in own.epic_gaps(folder, own.compute(folder)):
        print(f"  {gap}")
    if any(marks.get(int(e[1:])) for e in running):
        nxt = f"E{max(groups) + 1}"
        if not (epics_dir / f"{nxt}.md").is_file():
            print(f"  plan/epics/{nxt}.md missing: epics/new.py {a.release} {nxt}")
    parts = []
    if not dec_cards or deciding or open_q:
        parts.append("discuss")
    if running:
        parts.append(f"run ({', '.join(running)})")
    print(f"Stage: {', '.join(parts) or 'discuss'}")


if __name__ == "__main__":
    main()
