#!/usr/bin/env python3
"""queue.md as a kanban board in the obsidian-kanban Markdown format (the owner views and
drags it with the VS Code extension Unified Kanban). Library for the other scripts, no CLI.

File shape: a frontmatter with "kanban-plugin: basic", then one "## <Lane>" heading per lane,
in this order: Open, Decided, Later, Dropped, Autofix. A card is one top-level list item,
"- [ ] **Q<n>** <title> #<from>", with <from> owner, lead, lookup or run-E<n>; its facts are
sub-bullets indented with one TAB per level. A card in Decided has "\\t- Decision: D<n>" as its
first sub-bullet. The checkbox is [x] in Decided, Dropped and Autofix, [ ] in Open and Later.
The file ends with the "%% kanban:settings ... %%" block.

The extension rewrites the file between script calls, so every edit here is surgical: the
caller re-reads the file inside its lock, a card is found by its **Q<n>** token and its lane by
the "## " heading above it, the checkbox is ignored on read and normalised on the card being
written, and every other byte (frontmatter, settings block, other cards) stays as it was.
"""
import re

LANES = ("Open", "Decided", "Later", "Dropped", "Autofix")
DONE_LANES = ("Decided", "Dropped", "Autofix")
LANE_RE = re.compile(r"^##\s+(.*?)\s*$")
CARD_RE = re.compile(r"^- (?:\[[^\]\n]?\]\s*)?(.*)$")
CHECK_RE = re.compile(r"^- \[[^\]\n]?\]")
ID_RE = re.compile(r"\*\*Q(\d+)\*\*")
FROM_RE = re.compile(r"(?<![\w`])#(owner|lead|lookup|run(?:-E\d+)?)(?![\w-])")
DECISION_RE = re.compile(r"^\t-\s*Decision:\s*D(\d+)\s*$")
MARKER_RE = re.compile(r"^\*\*Complete\*\*\s*$")
SETTINGS_RE = re.compile(r"^%%\s*kanban:settings")
FRONT_KEY = "kanban-plugin:"
SETTINGS = ('%% kanban:settings\n'
            '{"kanban-plugin":"basic","lane-width":300,"date-format":"YYYY-MM-DD","time-format":"HH:mm"}\n'
            '%%')
TAG_TOKEN_RE = re.compile(r"(?<![\w`#])#([\w][\w/-]*)")


def is_board(text):
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


def from_tag(who):
    """'run E10' or 'run E10.' -> 'run-E10'; owner, lead, lookup unchanged."""
    return re.sub(r"\s+", "-", who.strip().rstrip(".").strip())


def escape_tags(text):
    """Wrap each #token outside code spans in backticks, so the extension shows no tag badge."""
    parts = re.split(r"(`+[^`]*`+)", text)
    return "".join(p if i % 2 else TAG_TOKEN_RE.sub(lambda m: f"`{m.group(0)}`", p)
                   for i, p in enumerate(parts))


def card_line(num, title, who, lane):
    box = "[x]" if lane in DONE_LANES else "[ ]"
    tag = f" #{from_tag(who)}" if who else ""
    return f"- {box} **Q{num}** {escape_tags(title)}{tag}"


def fact_line(text, depth=1):
    text = text.strip()
    if text.startswith("- "):
        text = text[2:]
    return "\t" * depth + "- " + escape_tags(text)


def _body_end(lines):
    """Index of the settings block or of a '***' archive line: lanes end there."""
    for i, line in enumerate(lines):
        if SETTINGS_RE.match(line):
            return i
    return len(lines)


def parse(text):
    """{lanes: [{name, line}], cards: [{num, lane, line, end, text, title, from}], stray: [...]}.

    line and end are 0-based indexes into text.split("\\n"); a card spans its list line and the
    indented lines under it. stray lists top-level list items with no **Q<n>** token, as
    (line index, text). Lanes after a '***' line (the extension's archive) are lanes too."""
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
                title = ID_RE.sub("", body, count=1)
                fm = FROM_RE.search(title)
                title = FROM_RE.sub("", title).strip()
                cards.append({"num": int(idm.group(1)), "lane": lane, "line": i, "end": j,
                              "title": title, "from": fm.group(1) if fm else None,
                              "subs": lines[i + 1:j], "text": "\n".join(lines[i:j])})
            else:
                stray.append((i, line))
            i = j
            continue
        i += 1
    return {"lanes": lanes, "cards": cards, "stray": stray}


def decision(card):
    """The D number of the card's first sub-bullet 'Decision: D<n>', else None."""
    if card["subs"]:
        m = DECISION_RE.match(card["subs"][0])
        if m:
            return int(m.group(1))
    return None


def find(text, num):
    return next((c for c in parse(text)["cards"] if c["num"] == num), None)


def normalise(line, lane):
    box = "[x]" if lane in DONE_LANES else "[ ]"
    if CHECK_RE.match(line):
        return CHECK_RE.sub(f"- {box}", line, count=1)
    return f"- {box} " + line[2:]


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


def move(text, num, lane, first_sub=None):
    """Move card Q<num> with its sub-bullets to the end of lane, checkbox normalised.
    first_sub, when given, becomes the card's first sub-bullet (a Decision line replaces one)."""
    card = find(text, num)
    if card is None:
        raise KeyError(num)
    lines = text.split("\n")
    block = lines[card["line"]:card["end"]]
    block[0] = normalise(block[0], lane)
    if first_sub is not None:
        subs = block[1:]
        if subs and DECISION_RE.match(subs[0]):
            subs = subs[1:]
        block = [block[0], first_sub] + subs
    if card["lane"] == lane:
        lines[card["line"]:card["end"]] = block
        return "\n".join(lines)
    del lines[card["line"]:card["end"]]
    rest = "\n".join(lines)
    return append_card(rest, lane, block)


def add_fact(text, num, fact):
    """Append one tab-indented fact sub-bullet at the end of card Q<num>, checkbox normalised."""
    card = find(text, num)
    if card is None:
        raise KeyError(num)
    lines = text.split("\n")
    lines[card["line"]] = normalise(lines[card["line"]], card["lane"])
    lines.insert(card["end"], fact_line(fact))
    return "\n".join(lines)


def render(cards_by_lane, settings=SETTINGS):
    """A whole board: cards_by_lane maps a lane to a list of blocks (lists of lines)."""
    out = ["---", "kanban-plugin: basic", "---", ""]
    for lane in LANES:
        out += [f"## {lane}", ""]
        for block in cards_by_lane.get(lane, []):
            out += block
        if cards_by_lane.get(lane):
            out.append("")
    out += [settings, ""]
    return "\n".join(out)
