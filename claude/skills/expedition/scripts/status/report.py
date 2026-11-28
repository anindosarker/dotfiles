#!/usr/bin/env python3
"""Read-only status report for an expedition release folder.

Usage: python3 -I status/report.py <release> [--owner X] [--root PATH]

The next queue card: queue/next.py. The owner's progress reply: status/progress.py.

Layout: <release>-plan.md (## Goals and ## Deliverables only), plan/specs/NN-<slug>/NN-<slug>.md (or the flat NN-<slug>.md of an earlier release),
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
sprints/refresh.py run syncs it), a (Q<n>) or "Source: Q<n>" citation of a missing card.
A release of format 2.1 keeps its queue in item files (lib/queue.py): the Queue section counts
the items per status and lists each with its status; its gaps: an item file with no "# Q<n>."
title or a number that differs from its file name, a "status" outside open, decided, later,
dropped and autofix, a decided item with no decision or one not in decisions.md, a queue.md
that differs from the list the files give, a duplicate number, a citation of a missing item.
A release of format 2.2 (lib/queue.py status_form) counts its items per status word (to-do,
blocked, done, backlog, archived); its gaps, besides the title, queue.md, duplicate and citation
gaps above: a "status" outside those five words; a "decider" that is not you, lead or agent, or a
"decider" on an item that is not done or archived (a closed item with no "decider" is no gap: it
was closed before format 2.2); a "decision" of a done item that is not in decisions.md; a
"depends_on" id that is not like Q14 or has no item file; an item that is not closed and waits for
an archived item; an item whose status differs from what the blocked check gives (fix:
sprints/refresh.py).
process.md (## P<n>) must
exist with no placeholder left; (P<n>) citations must be defined.

Epics: the #E<n> tag of a decision card puts the decision in an epic. The summary lists deciding
(the To do lane), done with nothing to run (in Done, no epic tag, not superseded or deferred),
in E<n> (no row of the epic in status/sprints.md carries a run mark), running (one does) and done
(every decision of the epic in Done). The stage line reports discuss and run together ("Stage: discuss, run
(E2, E3)"); a card in Open counts as discuss, never as a stage of its own.
Also under Epics: the decisions still editable in place (no citing spec has a status/sprints.md row
with "[ ]", "[~]" or "[x]", not superseded; a held milestone that was never launched does not count); a supersede marked on one side only; an unbuilt spec
citing a superseded decision; for each epic not done, its plan/epics/E<n>.md missing or Notes bullets
without "[ack HH:MM]" (only when the file has a ## Notes section); an epic file whose epic has
grid rows and no "Starts:" value, or a Starts value that is not S<number>; while an epic runs,
the next epic file missing. The epic files' "## Ownership" tables (lib/ownership.py epic_gaps): an epic
with grid rows whose file has no table, an unreadable table, a decision of the Decisions line
with no row, a spec of the epic with no row, a row file no milestone of its spec owns, a Sprint
cell that disagrees with the grid. Epics without an epic file are not flagged.
In a release of format 2.2 the grid rows come from status/data/status.json (lib/ownership.py
grid), never from status/sprints.md: an epic runs while a milestone of it there is not to-do, and
a spec counts as built while a milestone of it is in progress, blocked after a launch, or done.
The epic file is its Ownership table alone (no Decisions line).

Gaps reported for the layout: a plan section other than Goals and Deliverables; a
Deliverables Scope cell over 120 characters; a spec with no "### Milestone:" block, a block without Files owned, a Task line without
Checks, no Acceptance line; milestones sprints/check.py would refuse (collision, cycle);
status/sprints.md missing, without a "| Milestone" grid, with text under the grid, with a cell
not one of [x], [ ], [~], ·, [!] or blank, or with rows that differ from the milestones of the specs
with an Epic line. In a release of format 2.2 status/sprints.md is not read and not required: the
gaps are the file itself when it is left over, and a milestone of an epic with no "sprint" in the
status file (fix: sprints/refresh.py). Ownership also prints each tagged epic's critical path,
computed on the fly. A folder without plan/ is refused (migrate/pre-v1.0/layout.py), a folder still on
the old queue files too (migrate/pre-v1.0/queue.py), a decisions.md in the heading format too
(migrate/pre-v1.0/decisions.py), a folder that still has status/ownership.md too
(migrate/pre-v1.0/epics.py), a folder that still has run/trackers/fix-*-tracker.md too (migrate/pre-v1.0/fixes.py).
A tracker Status of done (or the old merged) counts as done. A tracker no milestone owns counts as citing the
queue cards named on its first line.
The last line, for a release in a lower format than the skill: the README.md of the migration
folder (skill below 2.2), or the chain of folders under scripts/migrate/ from the release's format
up, in the order to run them (skill 2.2 and higher, migration_chain); it names only folders that
exist.
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
SPRINT_MARKS = ("[x]", "[ ]", "[~]", "·", "[!]", "")


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


def items_report(folder, Q, docs, extra, dec_nums):
    """The Queue section of a release of format 2.1 (item files): the count per status, one row
    per item with its citing specs and status, then gaps. Returns the open item numbers."""
    its = Q.items(folder)
    counts = collections.Counter(it["status"] for it in its)
    print(f"Queue: {len(its)} items in {Q.QUEUE_DIR}/: "
          + ", ".join(f"{s} {counts.get(s, 0)}" for s in Q.STATUSES))
    texts = {num: read(p) for num, p in docs}
    texts.update({key: first for key, _, first in extra})
    cited = {num: q_cites(t) for num, t in texts.items()}
    rows = []
    for it in its:
        n = it["file_num"]
        citing = sorted((num for num, ci in cited.items() if n in ci), key=num_key)
        rows.append((f"Q{n}", ", ".join(citing) or "-", it["status"] or "-"))
    if rows:
        w1 = max(len(r[0]) for r in rows) + 2
        w2 = max(len(r[1]) for r in rows) + 2
        for a, b, c in rows:
            print(f"  {a.ljust(w1)}{b.ljust(w2)}{c}")
    for it in its:
        n, rel = it["file_num"], it["path"].relative_to(folder).as_posix()
        if it["num"] is None:
            print(f"  {rel}: no '# Q<n>. <title>' line")
        elif it["num"] != n:
            print(f"  {rel}: the title says Q{it['num']}, the file name Q{n}")
        if it["status"] not in Q.STATUSES:
            print(f"  {rel}: status '{it['status']}': only {', '.join(Q.STATUSES)}")
        if it["status"] == "decided":
            m = re.match(r"^D(\d+)$", it["decision"])
            if not m:
                print(f"  Q{n}: decided without a 'decision: D<n>' line")
            elif int(m.group(1)) not in dec_nums:
                print(f"  Q{n}: decision {it['decision']} is not in decisions.md")
    if not Q.list_in_step(folder):
        print(f"  {QUEUE_MD} differs from the item files: the next queue/item.py run writes it again")
    have = {it["file_num"] for it in its}
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
    dups = sorted(n for n in have if len(list((folder / Q.QUEUE_DIR).glob(f"Q{n}-*.md"))) > 1)
    if dups:
        print(f"  duplicate numbers: {', '.join(f'Q{n}' for n in dups)}")
    return [it["file_num"] for it in its if it["status"] == "open"]


ITEM_WORDS = ("to-do", "blocked", "done", "backlog", "archived")  # the status words of a queue item, format 2.2


def status_items_report(folder, Q, docs, extra, dec_nums):
    """The Queue section of a release of format 2.2: the count per status word, one row per item
    with its citing specs and status, then gaps. Returns the numbers of the items still open
    (to-do or blocked)."""
    its = Q.items(folder)
    counts = collections.Counter(it["status"] for it in its)
    print(f"Queue: {len(its)} items in {Q.QUEUE_DIR}/: "
          + ", ".join(f"{s} {counts.get(s, 0)}" for s in ITEM_WORDS))
    texts = {num: read(p) for num, p in docs}
    texts.update({key: first for key, _, first in extra})
    cited = {num: q_cites(t) for num, t in texts.items()}
    rows = []
    for it in its:
        n = it["file_num"]
        citing = sorted((num for num, ci in cited.items() if n in ci), key=num_key)
        rows.append((f"Q{n}", ", ".join(citing) or "-", it["status"] or "-"))
    if rows:
        w1 = max(len(r[0]) for r in rows) + 2
        w2 = max(len(r[1]) for r in rows) + 2
        for a, b, c in rows:
            print(f"  {a.ljust(w1)}{b.ljust(w2)}{c}")
    status_of = {f"Q{it['file_num']}": it["status"] for it in its}
    for it in its:
        n, rel, st = it["file_num"], it["path"].relative_to(folder).as_posix(), it["status"]
        if it["num"] is None:
            print(f"  {rel}: no '# Q<n>. <title>' line")
        elif it["num"] != n:
            print(f"  {rel}: the title says Q{it['num']}, the file name Q{n}")
        if st not in ITEM_WORDS:
            print(f"  {rel}: status '{st}': only {', '.join(ITEM_WORDS)}")
        if it["decider"] and it["decider"] not in Q.DECIDERS:
            print(f"  Q{n}: decider '{it['decider']}': only {', '.join(Q.DECIDERS)}")
        elif it["decider"] and st not in ("done", "archived"):
            print(f"  Q{n}: decider '{it['decider']}' on a {st or 'to-do'} item: only a done or archived item "
                  "has a decider; remove the line")
        if st == "done" and it["decision"]:
            m = re.match(r"^D(\d+)$", it["decision"])
            if not m:
                print(f"  Q{n}: decision '{it['decision']}' is not like D<n>")
            elif int(m.group(1)) not in dec_nums:
                print(f"  Q{n}: decision {it['decision']} is not in decisions.md")
        dep_gap = False
        for i in it["depends_on"]:
            if not Q.ID_RE.match(i):
                print(f"  Q{n}: depends_on names {i}: only queue item ids like Q14")
                dep_gap = True
            elif i not in status_of:
                print(f"  Q{n}: depends_on names {i}, which has no item file")
                dep_gap = True
        gone = [i for i in it["depends_on"] if status_of.get(i) == "archived"]
        if gone and st not in ("done", "archived"):
            print(f"  Q{n}: waits for {', '.join(gone)}, archived, which never gets done: "
                  f"change its depends_on with queue/item.py --depends")
            dep_gap = True
        want = Q.effective(it, its)
        if st in ("to-do", "blocked") and want != st and not dep_gap:
            print(f"  Q{n}: status '{st}', the blocked check gives '{want}': run sprints/refresh.py")
    if not Q.list_in_step(folder):
        print(f"  {QUEUE_MD} differs from the item files: the next queue/item.py run writes it again")
    have = {it["file_num"] for it in its}
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
    dups = sorted(n for n in have if len(list((folder / Q.QUEUE_DIR).glob(f"Q{n}-*.md"))) > 1)
    if dups:
        print(f"  duplicate numbers: {', '.join(f'Q{n}' for n in dups)}")
    return [it["file_num"] for it in its if it["status"] in ("to-do", "blocked", "")]


def stored_sprints(folder, own, owned):
    """The Sprints section of a release of format 2.2: the grid rows come from the status file
    (lib/ownership.py grid); status/sprints.md is not read."""
    if (folder / SPRINTS_MD).is_file():
        print(f"  {SPRINTS_MD} left over from format 2.1: delete it; the status file holds the sprint of each milestone")
    n, rows = own.grid(folder)
    if rows:
        print(f"  {len(rows)} rows, {n} columns, {sum(1 for _, c in rows if '[x]' in c)} done")
    if owned is not None:
        in_epic = C.load("lib/grid").epic_rows(folder, own, owned)
        sprint = {m["name"]: m.get("sprint") for m in (C.load("lib/status").load(folder) or {}).get("milestones", [])}
        for m in owned:
            if m["name"] in in_epic and not sprint.get(m["name"]):
                print(f"  milestone with no sprint in the status file: {m['name']} (run sprints/refresh.py)")


def new_print(folder, plan, d, own):
    rows, docs, statuses = d["rows"], d["docs"], d["statuses"]
    print("Specs:")
    text = read(plan) if plan.is_file() else ""
    if not plan.is_file():
        print(f"  {plan.name} missing: plan/new_release.py writes it")
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
            if b["files"] is None and b["id"] is None:
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
    if C.load("lib/status").new_form(folder):
        stored_sprints(folder, own, owned)
    elif not sprints.is_file():
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
            if any(l.strip() and not l.startswith("Marks:") for l in lines[end:]):
                print("  status/sprints.md has text under the grid: grid only")
            for r in data:
                for c in r[1:]:
                    if c not in SPRINT_MARKS:
                        print(f"  status/sprints.md row {r[0]}: cell {c!r} not one of [x], [ ], [~], ·, [!], blank")
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
            for t in b["tasks"]:
                tasks += 1
                if t["path"] is None:
                    if not t["checks"]:
                        print(f"  {name}:{t['line']}: Task line without Checks")
                        quiet = False
                elif not t["path"].is_file():
                    print(f"  {name}:{t['line']}: task {t['id']}: no file {t['plan']}")
                    quiet = False
                elif not re.search(r"^\s*-\s*\[[ xX]\]", read(t["path"]), re.M):
                    print(f"  {t['path'].relative_to(folder)}: no Verification box")
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
    for f, have, want in C.load("lib/status").differences(folder):
        print(f"  {f.relative_to(folder)}: status line says {have or 'nothing'}, status.json says {want}: "
              "a status is set with status/status.py, never by hand")
        quiet = False
    if quiet:
        print("  ok")


def grid_table(folder):
    """The grid rows as [label, cell, ...]: in a release of format 2.2 from the status file
    (lib/ownership.py grid), below 2.2 from status/sprints.md; [] when there is no grid."""
    if C.load("lib/status").new_form(folder):
        return [[label, *cells] for label, cells in C.load("lib/ownership").grid(folder)[1]]
    path = folder / SPRINTS_MD
    if not path.is_file():
        return []
    head, data = C.table_rows(read(path), "Milestone")
    return data if head else []


def epic_marks(data):
    """{epic number: True when a grid row of that epic ("E<n> NN name") holds a run mark}."""
    out = {}
    for r in data:
        m = re.match(r"^E(\d+)\s", r[0]) if r else None
        if m:
            out[int(m.group(1))] = out.get(int(m.group(1)), False) or any(
                c in ("[ ]", "[~]", "[x]", "[!]") for c in r[1:])
    return out


def built_specs(data, held=()):
    """Spec numbers with a grid row ("E<n> NN name") holding "[ ]", "[~]" or "[x]"; a "[~]" row
    of a milestone in held (lib/ownership.py held_unlaunched) does not count."""
    out = set()
    for r in data:
        m = re.match(r"^E\d+\s+(\d{2}(?:\.\d+)?)\s+(.*)$", r[0]) if r else None
        if m and m.group(2) not in held and any(c in ("[ ]", "[~]", "[x]") for c in r[1:]):
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


CHAIN_FROM = (2, 2)  # the first skill version whose last line names the whole chain of migrations
MIGRATE_DIR = Path(__file__).resolve().parent.parent / "migrate"
STEP_RE = re.compile(r"^v(\d+\.\d+)-v(\d+\.\d+)$")


def migration_chain(have, skill):
    """The migration folders under scripts/migrate/ that move a release from format have to the
    skill's format skill, in the order to run them: each step a folder v<a>-v<b> with a
    README.md, a starting where the step before ended. Stops where no folder goes on; the list
    names only folders that exist."""
    key = lambda v: tuple(map(int, v.split(".")))
    steps = {}
    for p in sorted(MIGRATE_DIR.iterdir()) if MIGRATE_DIR.is_dir() else []:
        m = STEP_RE.match(p.name)
        if m and (p / "README.md").is_file() and key(m.group(1)) < key(m.group(2)) <= key(skill):
            steps.setdefault(m.group(1), []).append(m.group(2))
    out, at = [], have
    while key(at) < key(skill) and at in steps:
        nxt = max(steps[at], key=key)  # the longest step, so the chain has the fewest runs
        out.append(f"scripts/migrate/v{at}-v{nxt}")
        at = nxt
    return out, at


def chain_line(have, skill):
    """The last line of the report for a release below the skill's format, skill 2.2 and higher."""
    chain, at = migration_chain(have, skill)
    head = f"this release is in format v{have}, the skill is v{skill}: "
    if not chain:
        return head + f"no folder under scripts/migrate/ moves format v{have} yet"
    if len(chain) == 1:
        text = f"see {chain[0]}/README.md"
    else:
        text = f"run, in this order, {', then '.join(chain)}; each folder has a README.md"
    if at != skill:
        text += f"; no folder under scripts/migrate/ moves format v{at} further yet"
    return head + text


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
    new = C.load("lib/status").new_form(folder)
    print("Files:")
    # format 2.2 has no status/sprints.md: the Sprints section reports one that is left over
    for p in (plan, *([] if new else [folder / SPRINTS_MD]), folder / INDEX_HTML, decisions, queue):
        # git-ignored: a fresh clone has none. An earlier release keeps its line, "missing".
        render = p.name == "index.html" and not p.is_file() and C.load("lib/status").active(folder)
        print(f"  {p.relative_to(folder)}: "
              + ("not rendered yet (sprints/swimlanes.py writes it)" if render else 'present' if p.is_file() else 'missing'))

    own = C.load("lib/ownership")
    d = own.new_collect(folder, plan)
    docs, statuses = d["docs"], d["statuses"]

    dec_cards, _ = decision_table(folder, decisions, docs)
    Q = C.load("lib/queue")
    if Q.status_form(folder):
        open_q = status_items_report(folder, Q, docs, d["extra"], {c["num"] for c in dec_cards})
    elif Q.item_form(folder):
        open_q = items_report(folder, Q, docs, d["extra"], {c["num"] for c in dec_cards})
    else:
        open_q = queue_report(folder, bd, q_text, docs, d["extra"], {c["num"] for c in dec_cards},
                              bd.decision_tags(own, folder))

    new_print(folder, plan, d, own)

    print("Process:")
    proc = folder / "process.md"
    if not proc.is_file():
        print("  process.md missing: plan/new_release.py copies it from the previous release")
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
    grid_rows = grid_table(folder)
    marks = epic_marks(grid_rows)
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
    built = built_specs(grid_rows, own.held_unlaunched(folder))
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
        if e in marks and e in starts and not v and new:
            print(f"  E{e} has milestones with a sprint in the status file and no Starts value: write "
                  f"\"Starts: S<n>\" in plan/epics/E{e}.md, the sprint of its first milestone")
        elif e in marks and e in starts and not v:
            print(f"  E{e} has rows in status/sprints.md and no Starts value: migrate/pre-v1.0/backfill_starts.py {a.release}")
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
    have, skill = C.load("lib/status").release_format(folder), C.skill_version()
    if tuple(map(int, have.split("."))) < tuple(map(int, skill.split("."))):
        if tuple(map(int, skill.split("."))) < CHAIN_FROM:
            print(f"this release is in format v{have}, the skill is v{skill}: "
                  f"see scripts/migrate/v{have}-v{skill}/README.md")
        else:
            print(chain_line(have, skill))


if __name__ == "__main__":
    main()
