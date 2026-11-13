#!/usr/bin/env python3
"""decisions.md as a kanban board, in the card grammar of queue.md (lib/board.py parses and
rewrites both). Library for the other scripts, no CLI.

File shape: the frontmatter "kanban-plugin: basic", the lanes "## To do", "## In progress" and
"## Done", always all three, in this order, then the "%% kanban:settings ... %%" block (list
view, title "<release> decisions"). A card is "- [ ] **D<n>** <title> <tags>", the decision's
bullets under it indented with one TAB (a bullet's nested lines and fenced code blocks keep their
own indentation after that tab; a blank line inside a fence is a lone TAB). Cards are ordered by
D number inside each lane; a D number is never reused.

Tags, at the end of the title line only, in this order: "#superseded" or "#deferred" when it
applies, "#E<n>" when the decision is in an epic, "#R<n>" the round it was recorded in. A
superseded decision keeps "(superseded by D<n>)" at the end of its title, before the tags.

The lane is the state, from the Done rule (rule_lanes):
1. A "(superseded by D<n>)" mark or a "- Deferred to" bullet: Done.
2. Rows in the Ownership table of an epic file that has gone (a "Starts: S<n>" value) with a
   Spec cell: its own specs are the row specs that cite it "(D<n>)" in a heading line (the title
   line, a "### Milestone:" heading or any "#" heading); none, then every row spec. Done when
   every milestone tracker of every own spec is merged or skipped, else In progress.
3. No such row: Done when it is closed by hand (a ticked card in Done: decisions/close.py writes
   it for a decision with nothing to run, migrate/decisions.py for an old "[Done]" tag line) or
   when any spec citing it has merged; In progress when it carries "#E<n>"; else To do.
The checkbox is [x] only in Done. sync() moves every card whose lane disagrees with the rule,
sets every card's tick to its lane and writes its tags in the order above; the scripts are the
only writers of lanes, ticks and tags (a drag or tick in the extension is not a state change).
"""
import collections
import fcntl
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
DECISIONS_MD = "decisions.md"
TODO, PROGRESS, DONE = "To do", "In progress", "Done"
LANES = (TODO, PROGRESS, DONE)
SETTINGS = ('%% kanban:settings\n'
            '{"kanban-plugin":"basic","lane-width":600,"date-format":"YYYY-MM-DD","time-format":"HH:mm",'
            '"tag-action":"kanban","set-view":"list","full-list-lane-width":true,"show-add-list":false,'
            '"show-archive-all":false,"custom-title":"[release] decisions"}\n'
            '%%')
TAG_OK_RE = re.compile(r"^(?:superseded|deferred|E\d+|R\d+)$")
TRAIL_RE = re.compile(r"(?:\s+#(?:superseded|deferred|[ER]\d+))+\s*$")
MARK_RE = re.compile(r"\s*\(superseded by D(\d+)\)")
SUPERSEDES_RE = re.compile(r"^\s*-\s*Supersedes D(\d+)\b")
DEFERRED_RE = re.compile(r"^\s*-\s*Deferred to\b")
D_CITE_RE = re.compile(r"\((D\d+[^)]*)\)")
MERGED = ("merged", "done", "skipped")


def bd():
    return C.load("lib/board")


def own():
    return C.load("lib/ownership")


def path_of(folder):
    return Path(folder) / DECISIONS_MD


def settings(release):
    return SETTINGS.replace("[release]", release)


def is_board(text):
    return bd().is_board(text, "To do")


def inner(subs):
    """A card's sub-lines without the one leading TAB: the decision's bullets as written."""
    return [l[1:] if l.startswith("\t") else l for l in subs]


def outside(lines):
    """The lines of a card body outside code fences."""
    return [l for l, inside in C.fence_flags("\n".join(lines)) if not inside]


def parse(text):
    """{lanes, cards, stray} of decisions.md. A card: num, lane, line, end, box, ticked, title
    (without tags, the superseded marks kept), base (title without the marks), sup_by (D numbers
    of the marks, in order), tags (every #token of the title line), epic and round (the highest
    #E and #R numbers or None), deferred, supersedes (D numbers of "- Supersedes D<n>" bullets),
    body (the sub-lines without their leading TAB), subs (as written)."""
    b = bd()
    p = b.parse(text, "D")
    lines = text.split("\n")
    idr = b.id_re("D")
    cards = []
    for c in p["cards"]:
        head = lines[c["line"]]
        rest = b.CARD_RE.match(head).group(1)
        tags = b.tags_of(rest)
        title = TRAIL_RE.sub("", idr.sub("", rest, count=1)).strip()
        nums = collections.defaultdict(list)
        for t in tags:
            m = re.match(r"^([ER])(\d+)$", t)
            if m:
                nums[m.group(1)].append(int(m.group(2)))
        body = inner(c["subs"])
        out = outside(body)
        cards.append({"num": c["num"], "lane": c["lane"], "line": c["line"], "end": c["end"],
                      "box": c["box"], "ticked": c["box"] == "x", "title": title,
                      "base": MARK_RE.sub("", title).strip(),
                      "sup_by": [int(n) for n in MARK_RE.findall(title)], "tags": tags,
                      "epic": max(nums["E"]) if nums["E"] else None,
                      "round": max(nums["R"]) if nums["R"] else None,
                      "deferred": any(DEFERRED_RE.match(l) for l in out),
                      "supersedes": [int(m.group(1)) for l in out if (m := SUPERSEDES_RE.match(l))],
                      "body": body, "subs": c["subs"]})
    return {"lanes": p["lanes"], "cards": cards, "stray": p["stray"]}


def read_cards(folder):
    """parse() of the release's decisions.md; empty when the file is missing or not a board."""
    path = path_of(folder)
    if not path.is_file():
        return {"lanes": [], "cards": [], "stray": []}
    text = C.read(path)
    if not is_board(text):
        return {"lanes": [], "cards": [], "stray": []}
    return parse(text)


def tag_words(card):
    """The card's tags in order: #superseded or #deferred, #E<n>, #R<n>."""
    out = []
    if card["sup_by"]:
        out.append("#superseded")
    elif card["deferred"]:
        out.append("#deferred")
    if card["epic"]:
        out.append(f"#E{card['epic']}")
    if card["round"]:
        out.append(f"#R{card['round']}")
    return out


def head_line(card, lane):
    """The card's title line for lane: its checkbox, id, title with the superseded marks at the
    end, then its tags."""
    box = "[x]" if lane == DONE else "[ ]"
    title = card["base"] + "".join(f" (superseded by D{n})" for n in card["sup_by"])
    return " ".join([f"- {box} **D{card['num']}** {title}".rstrip()] + tag_words(card))


def new_card(num, title, round_, bullets=()):
    """The lines of a new card in To do: title escaped like a queue title, one tab-indented line
    per bullet."""
    card = {"num": num, "base": bd().escape_tags(title.strip()), "sup_by": [], "deferred": False,
            "epic": None, "round": round_}
    return [head_line(card, TODO)] + ["\t" + (x if x.startswith("- ") else f"- {x}") for x in bullets]


def highest(cards):
    return max([c["num"] for c in cards] or [0])


def highest_round(cards):
    return max([c["round"] or 0 for c in cards] or [0])


# The Done rule.
def started_rows(folder):
    """{D: [spec numbers]}: the rows with a Spec cell of the Ownership table of every epic file
    that has gone (a "Starts: S<n>" value)."""
    o = own()
    starts = o.epic_starts(folder)
    out = collections.defaultdict(list)
    for n in o.epic_numbers(folder):
        if not o.SPRINT_VALUE_RE.match(starts.get(n) or ""):
            continue
        rows, _ = o.read_table(o.read(o.epic_path(folder, n)))
        for r in rows or []:
            if r["decision"] is not None and r["spec"] and r["spec"] not in out[r["decision"]]:
                out[r["decision"]].append(r["spec"])
    return out


def spec_merged(folder, num, path):
    """True when every milestone tracker of the spec is merged or skipped."""
    o = own()
    m = re.match(r"^\d{2}(?:\.\d+)?-(.+)\.md$", path.name)
    slug = m.group(1) if m else ""
    blocks = o.parse_spec(path)
    if blocks:
        trackers = [o.milestone_tracker(folder, num, slug, i, b["name"]) for i, b in enumerate(blocks)]
    else:
        trackers = [folder / o.TRACKERS_DIR / f"{num}-tracker.md"]
    states = [o.tracker_status(folder, num, t) for t in trackers]
    return all(s is not None and s[0] in MERGED for s in states)


def spec_facts(folder):
    """{spec number: (D numbers cited in a heading line, D numbers cited anywhere, merged)}."""
    o = own()
    out = {}
    for num, p in o.spec_files(folder):
        head, every = set(), set()
        for _, line in o.outside_fences(o.read(p)):
            found = set()
            for m in D_CITE_RE.finditer(line):
                found |= {int(n) for n in re.findall(r"\bD(\d+)\b", m.group(1))}
            every |= found
            if line.startswith("#"):
                head |= found
        out[num] = (head, every, spec_merged(folder, num, p))
    return out


def hand_closed(card):
    """Closed by hand: a ticked card in Done (rule 3 asks it only of a card with no row)."""
    return card["lane"] == DONE and card["ticked"]


def rule_lanes(folder, cards):
    """{D: lane} of every card by the Done rule (module docstring)."""
    rows = started_rows(folder)
    facts = spec_facts(folder)
    out = {}
    for c in cards:
        n = c["num"]
        if c["sup_by"] or c["deferred"]:
            out[n] = DONE
        elif rows.get(n):
            mine = [s for s in rows[n] if s in facts and n in facts[s][0]] or rows[n]
            out[n] = DONE if all(s in facts and facts[s][2] for s in mine) else PROGRESS
        elif hand_closed(c) or any(n in f[1] and f[2] for f in facts.values()):
            out[n] = DONE
        elif c["epic"]:
            out[n] = PROGRESS
        else:
            out[n] = TODO
    return out


# Edits.
def move(text, num, lane, head=None):
    """Card D<num> with its body to lane, in D number order; head replaces its title line (else
    only the checkbox follows the lane). A lane left empty gets back its single blank line."""
    b = bd()
    card = b.find(text, num, "D")
    if card is None:
        raise KeyError(num)
    lines = text.split("\n")
    block = lines[card["line"]:card["end"]]
    block[0] = head if head is not None else b.set_box(block[0], "[x]" if lane == DONE else "[ ]")
    if card["lane"] == lane:
        lines[card["line"]] = block[0]
        return "\n".join(lines)
    i = card["line"]
    del lines[i:card["end"]]
    if 0 < i < len(lines) and not lines[i - 1].strip() and not lines[i].strip():
        del lines[i]
    return b.insert_card("\n".join(lines), lane, block, num, "D")


def set_head(text, num, head):
    """text with card D<num>'s title line replaced."""
    card = bd().find(text, num, "D")
    if card is None:
        raise KeyError(num)
    lines = text.split("\n")
    lines[card["line"]] = head
    return "\n".join(lines)


def sync(text, folder):
    """Every card to the lane of the Done rule, its tick to its lane, its tags in order.
    Returns (text, [(D number, old lane, new lane)] of the cards moved)."""
    cards = parse(text)["cards"]
    want = rule_lanes(folder, cards)
    moved = []
    for c in cards:
        lane = want[c["num"]] if c["lane"] in LANES else c["lane"]
        head = head_line(c, lane)
        if lane != c["lane"]:
            moved.append((c["num"], c["lane"], lane))
        elif head != text.split("\n")[c["line"]]:
            text = set_head(text, c["num"], head)
    for num, _, lane in moved:
        c = next(x for x in parse(text)["cards"] if x["num"] == num)
        text = move(text, num, lane, head_line(c, lane))
    return text, moved


def sync_file(folder, lock_path=None):
    """sync() on the release's decisions.md under an exclusive lock on lock_path (when given):
    re-read inside the lock, written only when it changed. Returns the cards moved."""
    path = path_of(folder)
    if not path.is_file():
        return []
    lock = open(lock_path, "a") if lock_path else None
    try:
        if lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
        text = path.read_text(encoding="utf-8")
        if not is_board(text):
            return []
        new, moved = sync(text, folder)
        if new != text:
            bd().write(path, new)
        return moved
    finally:
        if lock:
            fcntl.flock(lock, fcntl.LOCK_UN)
            lock.close()


def moved_text(moved):
    return ", ".join(f"D{n} to {lane}" for n, _, lane in moved)


def render(release, by_lane):
    """A whole decisions board: by_lane maps a lane to a list of card blocks."""
    return bd().render(by_lane, settings(release), LANES)
