#!/usr/bin/env python3
"""queue.md as a kanban board in the obsidian-kanban Markdown format (the owner views and
drags it with the VS Code extension Unified Kanban). Library for the other scripts, no CLI.

File shape: a frontmatter with "kanban-plugin: basic", then one "## <Lane>" heading per lane,
in this order: Open, Decided, Later, Dropped, Autofix. A card is one top-level list item,
"- [ ] **Q<n>** <title>", its facts sub-bullets indented with one TAB per level. Two tags
exist, at the end of the title line, decision before epic: "#D<n>" (the decision that settled
the card) and "#E<n>" (the epic that decision is in). The checkbox is [ ] in Open and Later,
[x] in Dropped and Autofix. In Decided it mirrors the decision's tag line in decisions.md:
[ ] with no #E tag while the decision has no tag (ready for an epic), [x] with "#E<n>" once it
carries "[E<n>]", [x] with no epic tag when it carries "[Done]" alone or is closed without a tag
(superseded or deferred: it never goes into an epic). sync() sets it. The file ends with the
"%% kanban:settings ... %%" block.

The extension rewrites the file between script calls, so every edit here is surgical: the
caller re-reads the file inside its lock, a card is found by its **Q<n>** token and its lane by
the "## " heading above it, and every other byte (settings block, other cards) stays as it was.
The extension may drop the frontmatter when it saves its settings: a file with a settings block
and a "## Open" lane is still a board, and write() restores the frontmatter.

Old card format (a from tag "#owner", "#lead", "#lookup", "#run", "#run-E<n>" on the title
line, or a "Decision: D<n>" sub-bullet): is_old() is true, and only migrate/queue.py reads it.
"""
import fcntl
import re

LANES = ("Open", "Decided", "Later", "Dropped", "Autofix")
TICKED_LANES = ("Dropped", "Autofix")
LANE_RE = re.compile(r"^##\s+(.*?)\s*$")
CARD_RE = re.compile(r"^- (?:\[[^\]\n]?\]\s*)?(.*)$")
CHECK_RE = re.compile(r"^- \[([^\]\n]?)\]")
ID_RE = re.compile(r"\*\*Q(\d+)\*\*")
FROM_RE = re.compile(r"(?<![\w`])#(owner|lead|lookup|run(?:-E\d+)?)(?![\w-])")
DECISION_RE = re.compile(r"^\t-\s*Decision:\s*D(\d+)\s*$")
MARKER_RE = re.compile(r"^\*\*Complete\*\*\s*$")
SETTINGS_RE = re.compile(r"^%%\s*kanban:settings")
FRONT_KEY = "kanban-plugin:"
FRONT = ["---", "kanban-plugin: basic", "---", ""]
SETTINGS = ('%% kanban:settings\n'
            '{"kanban-plugin":"basic","lane-width":300,"date-format":"YYYY-MM-DD","time-format":"HH:mm",'
            '"tag-action":"kanban"}\n'
            '%%')
TAG_TOKEN_RE = re.compile(r"(?<![\w`#])#([\w][\w/-]*)")
CARD_TAG_RE = re.compile(r"^(D|E)(\d+)$")
TRAIL_TAGS_RE = re.compile(r"(?:\s+#[DE]\d+)+\s*$")


def has_front(text):
    """True when the text opens with a frontmatter naming the kanban plugin."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return False
    for line in lines[1:]:
        if line.strip() == "---":
            return False
        if line.strip().startswith(FRONT_KEY):
            return True
    return False


def is_board(text):
    """A board: the kanban frontmatter, or a settings block together with a '## Open' lane."""
    if has_front(text):
        return True
    lines = text.split("\n")
    return (any(SETTINGS_RE.match(l) for l in lines)
            and any(LANE_RE.match(l) and LANE_RE.match(l).group(1) == "Open" for l in lines))


def with_front(text):
    """The text with the kanban frontmatter put back when the extension dropped it."""
    if has_front(text):
        return text
    return "\n".join(FRONT) + "\n" + text.lstrip("\n")


def write(path, text):
    """Write a board, frontmatter restored."""
    path.write_text(with_front(text), encoding="utf-8")


def outside_code(text):
    """Split text on code spans: even parts are outside, odd parts are the spans."""
    return re.split(r"(`+[^`]*`+)", text)


def escape_tags(text):
    """Wrap each #token outside code spans in backticks, so the extension shows no tag badge."""
    parts = outside_code(text)
    return "".join(p if i % 2 else TAG_TOKEN_RE.sub(lambda m: f"`{m.group(0)}`", p)
                   for i, p in enumerate(parts))


def tags_of(line):
    """Every #token outside code spans on a line, without the '#'."""
    parts = outside_code(line)
    return [m.group(1) for i, p in enumerate(parts) if not i % 2 for m in TAG_TOKEN_RE.finditer(p)]


def box_for(lane, ticked=False):
    """The checkbox of a card in lane; Decided takes ticked (sync() decides it)."""
    if lane == "Decided":
        return "[x]" if ticked else "[ ]"
    return "[x]" if lane in TICKED_LANES else "[ ]"


def card_line(num, title, lane):
    """A new card line with no tags; a Decided card starts unticked."""
    return f"- {box_for(lane)} **Q{num}** {escape_tags(title)}"


def fact_line(text, depth=1):
    text = text.strip()
    if text.startswith("- "):
        text = text[2:]
    return "\t" * depth + "- " + escape_tags(text)


def set_tags(line, d=None, e=None):
    """The card line with its trailing #D and #E tags replaced by #D<d> and #E<e> (None: no tag)."""
    base = TRAIL_TAGS_RE.sub("", line.rstrip())
    return base + (f" #D{d}" if d else "") + (f" #E{e}" if e else "")


def set_box(line, box):
    if CHECK_RE.match(line):
        return CHECK_RE.sub(f"- {box}", line, count=1)
    return f"- {box} " + line[2:]


def _body_end(lines):
    """Index of the settings block: lanes end there."""
    for i, line in enumerate(lines):
        if SETTINGS_RE.match(line):
            return i
    return len(lines)


def parse(text):
    """{lanes: [{name, line}], cards: [...], stray: [...]}.

    A card is {num, lane, line, end, title, box, d, e, tags, from, decision, subs, text}:
    line and end are 0-based indexes into text.split("\\n") (the list line and the indented
    lines under it); title has no tags; d and e are the highest #D and #E numbers or None;
    tags lists every tag token of the title line; from is an old from tag or None; decision is
    the highest old 'Decision: D<n>' sub-bullet or None. stray lists top-level list items with
    no **Q<n>** token, as (line index, text). Lanes after a '***' line are lanes too."""
    lines = text.split("\n")
    stop = _body_end(lines)
    lanes, cards, stray = [], [], []
    in_front = bool(lines) and lines[0].strip() == "---"
    lane = None
    i = 1 if in_front else 0
    if in_front:
        while i < stop and lines[i].strip() != "---":
            i += 1
        i += 1
    while i < stop:
        line = lines[i]
        m = LANE_RE.match(line)
        if m:
            lane = m.group(1)
            lanes.append({"name": lane, "line": i})
            i += 1
            continue
        if line.startswith("- ") and lane is not None:
            j = i + 1
            while j < stop and lines[j].strip() and lines[j][:1] in ("\t", " "):
                j += 1
            idm = ID_RE.search(line)
            if idm:
                body = CARD_RE.match(line).group(1)
                tags = tags_of(body)
                nums = {"D": [], "E": []}
                for t in tags:
                    tm = CARD_TAG_RE.match(t)
                    if tm:
                        nums[tm.group(1)].append(int(tm.group(2)))
                fm = FROM_RE.search(body)
                title = ID_RE.sub("", body, count=1)
                title = FROM_RE.sub("", TRAIL_TAGS_RE.sub("", title)).strip()
                subs = lines[i + 1:j]
                decs = [int(dm.group(1)) for s in subs if (dm := DECISION_RE.match(s))]
                bm = CHECK_RE.match(line)
                cards.append({"num": int(idm.group(1)), "lane": lane, "line": i, "end": j,
                              "title": title, "box": bm.group(1).strip().lower() if bm else "",
                              "d": max(nums["D"]) if nums["D"] else None,
                              "e": max(nums["E"]) if nums["E"] else None, "tags": tags,
                              "from": fm.group(1) if fm else None,
                              "decision": max(decs) if decs else None,
                              "subs": subs, "text": "\n".join(lines[i:j])})
            else:
                stray.append((i, line))
            i = j
            continue
        i += 1
    return {"lanes": lanes, "cards": cards, "stray": stray}


def is_old(text):
    """True when a card still has a from tag or a 'Decision: D<n>' sub-bullet."""
    return any(c["from"] or c["decision"] for c in parse(text)["cards"])


def find(text, num):
    return next((c for c in parse(text)["cards"] if c["num"] == num), None)


DEFERRED_RE = re.compile(r"^\s*-\s*Deferred to\b")
D_HEAD_RE = re.compile(r"^###\s+D(\d+)\b")


def decision_tags(own, folder):
    """{D: {epic, done, closed, line}}: ownership.read_tags plus closed, true for a superseded
    decision or one with a "- Deferred to" bullet."""
    tags = own.read_tags(folder)
    heads, bullets = own.supersedes(folder)
    closed = set(heads) | set(bullets)
    path = folder / "decisions.md"
    cur = None
    if path.is_file():
        for _, line in own.outside_fences(path.read_text(encoding="utf-8")):
            m = D_HEAD_RE.match(line)
            if m:
                cur = int(m.group(1))
            elif line.startswith("#"):
                cur = None
            elif cur is not None and DEFERRED_RE.match(line):
                closed.add(cur)
    for n, t in tags.items():
        t["closed"] = n in closed
    return tags


def want(card, tags):
    """(box, epic) a Decided card should show for decision_tags(), or None when its #D tag is
    missing or names no decision."""
    t = tags.get(card["d"]) if card["d"] else None
    if t is None:
        return None
    return ("[x]" if t["epic"] or t["done"] or t.get("closed") else "[ ]"), t["epic"]


def sync(text, tags):
    """Set every Decided card's tick and #E tag from decision_tags(), touching only the card
    lines that differ. Returns (text, [Q numbers changed])."""
    lines = text.split("\n")
    changed = []
    for c in parse(text)["cards"]:
        if c["lane"] != "Decided":
            continue
        w = want(c, tags)
        if w is None:
            continue
        new = set_tags(set_box(lines[c["line"]], w[0]), c["d"], w[1])
        if new != lines[c["line"]]:
            lines[c["line"]] = new
            changed.append(c["num"])
    return "\n".join(lines), changed


def sync_file(path, tags, lock_path=None):
    """sync() on queue.md at path under an exclusive lock on lock_path (when given): the file is
    re-read inside the lock and written only when a card changed. Returns the Q numbers changed."""
    if not path.is_file():
        return []
    lock = open(lock_path, "a") if lock_path else None
    try:
        if lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
        text = path.read_text(encoding="utf-8")
        if not is_board(text) or is_old(text):
            return []
        new, changed = sync(text, tags)
        if changed:
            write(path, new)
        return changed
    finally:
        if lock:
            fcntl.flock(lock, fcntl.LOCK_UN)
            lock.close()


def _lane_insert_at(lines, board, lane):
    """Index where a card is appended at the end of lane, and whether a blank line must follow."""
    stop = _body_end(lines)
    heads = board["lanes"]
    k = next((n for n, l in enumerate(heads) if l["name"] == lane), None)
    if k is None:
        raise KeyError(lane)
    start = heads[k]["line"]
    end = heads[k + 1]["line"] if k + 1 < len(heads) else stop
    in_lane = [c for c in board["cards"] if start < c["line"] < end]
    if in_lane:
        return in_lane[-1]["end"], False
    p = start + 1
    if p < end and MARKER_RE.match(lines[p]):
        p += 1
    if p < end and not lines[p].strip():
        p += 1
    return p, not (p < len(lines) and not lines[p].strip())


def _insert(lines, at, block, blank_after):
    lines[at:at] = block + ([""] if blank_after else [])


def append_card(text, lane, block):
    """Append the block (card line plus sub-bullets) at the end of lane."""
    lines = text.split("\n")
    at, blank = _lane_insert_at(lines, parse(text), lane)
    _insert(lines, at, block, blank)
    return "\n".join(lines)


def move(text, num, lane, d=None):
    """Move card Q<num> with its sub-bullets to the end of lane. Into Decided: d is the card's
    #D number, its #E tag is dropped and the card is unticked (sync() then sets both). Into any
    other lane: the lane's checkbox; a card leaving Decided loses its #D and #E tags."""
    card = find(text, num)
    if card is None:
        raise KeyError(num)
    lines = text.split("\n")
    block = lines[card["line"]:card["end"]]
    head = set_box(block[0], box_for(lane))
    if lane == "Decided":
        head = set_tags(head, d)
    elif card["lane"] == "Decided":
        head = set_tags(head)
    block[0] = head
    if card["lane"] == lane:
        lines[card["line"]:card["end"]] = block
        return "\n".join(lines)
    del lines[card["line"]:card["end"]]
    rest = "\n".join(lines)
    return append_card(rest, lane, block)


def add_fact(text, num, fact):
    """Append one tab-indented fact sub-bullet at the end of card Q<num>; outside Decided the
    checkbox is set to the lane's."""
    card = find(text, num)
    if card is None:
        raise KeyError(num)
    lines = text.split("\n")
    if card["lane"] != "Decided":
        lines[card["line"]] = set_box(lines[card["line"]], box_for(card["lane"]))
    lines.insert(card["end"], fact_line(fact))
    return "\n".join(lines)


def render(cards_by_lane, settings=SETTINGS):
    """A whole board: cards_by_lane maps a lane to a list of blocks (lists of lines)."""
    out = list(FRONT)
    for lane in LANES:
        out += [f"## {lane}", ""]
        for block in cards_by_lane.get(lane, []):
            out += block
        if cards_by_lane.get(lane):
            out.append("")
    out += [settings, ""]
    return "\n".join(out)
