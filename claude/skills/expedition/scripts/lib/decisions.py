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
   every milestone tracker of every own spec is done or stopped, else In progress. In a
   new-form spec (modules, task pointers, numbered milestones) only the milestones count that
   hold a task of a module citing it; a citing module with no task in a milestone keeps it In
   progress, except in a spec migrate/v1.0-v2.0/format.py marked "migrated: true".
3. No such row: Done when it is closed by hand (a ticked card in Done: decisions/close.py writes
   it for a decision with nothing to run, migrate/pre-v1.0/decisions.py for an old "[Done]" tag line) or
   when any spec citing it has merged; In progress when it carries "#E<n>"; else To do.
The checkbox is [x] only in Done. sync() moves every card whose lane disagrees with the rule,
sets every card's tick to its lane and writes its tags in the order above; the scripts are the
only writers of lanes, ticks and tags (a drag or tick in the extension is not a state change).

The file form (spec 07, D9 and D16). A release of format 2.2 or higher whose decisions.md is not
a board keeps each decision in a file of its own, decisions/D<n>-<slug>.md (file_form is the one
test; a release of format 2.2 with a board stays in the board form until scripts/migrate/v2.1-v2.2
has moved it). A decision file is front matter, the title line "# D<n>. <title>", an empty line
and a free body. The front matter lines, in this order, each absent when it has no value:
"status" (STATUS_WORDS, written by the scripts only), "decider" (you, lead or agent: who made the
call), "source" (Q<n>), "epic" (E<n>, written by epics/tag.py), "replaced_by" (D<n>, written by
decisions/supersede.py). The slug is made once from the first title (the rule of a queue item
file) and the file is never renamed. No script reads the body, and no script writes into it
after the --bullet line of a new decision. The round of a decision is "decisions.D<n>.round" in
status/data/status.json (lib/status.py). decisions.md is then a list the scripts write again
(write_list): "# Decisions, <release>", an empty line, one line per decision file in the order of
the numbers, "- [D<n>](decisions/D<n>-<slug>.md): <title>".

The status of a decision file, from the status rule (rule_status), the first row that holds:
1. a "replaced_by" line: archived.
2. the stored status is backlog (decisions/close.py --backlog): backlog.
3. rows with a Spec cell in an epic file that has gone: done when the Done rule above says Done,
   else in progress.
4. no such row, and the stored status is done (decisions/close.py, or a rule of an earlier run),
   or a spec that cites it has merged: done.
5. an "epic" line: in progress.
6. in no epic (no "epic" line, no row in the Ownership table of any epic file, gone or planned)
   and sharing a file with a running epic: blocked (the blocked check below).
7. else to-do.
The blocked check (module 1.6.2 of spec 07). The files of a decision are the Files owned of every
milestone of the specs that cite it; when no spec cites it, the files the lead gave with
epics/overlap.py --files ("decisions.D<n>.files" in status/data/status.json). A running epic is
the "epic" line of a decision that is in progress by rows 1 to 5; its files are the Files owned of
every milestone of the specs with "- Epic: E<n>", except the specs that cite the decision checked.
The reason of a blocked decision is "Waits for E11, same file" (reason_words). The refresh chain
removes the given files of a decision (kept_entries, called by lib/status.py build) when a spec
cites it, when it has a row in an epic file, or when it is no longer to-do or blocked.
The readers of the board form (read_cards, rule_lanes, sync_file, highest) answer from the files
in the file form: a card keeps its keys, each worked out from the file and the status file (the
lane from the status: to-do and blocked give To do, in progress gives In progress, done, backlog
and archived give Done; sup_by and the tag superseded from "replaced_by"; deferred and the tag
deferred from backlog), and gains status, decider, source, path and file.
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
# Tracker states that end a milestone; lib/ownership.py reads the old merged and skipped as these.
MERGED = ("done", "stopped")
# The file form.
DECISIONS_DIR = "decisions"
FILE_FORMAT = (2, 2)  # the first release format that can keep its decisions in files (D16)
STATUS_WORDS = ("to-do", "in progress", "blocked", "done", "backlog", "archived")
DECIDERS = ("you", "lead", "agent")
FRONT_KEYS = ("status", "decider", "source", "epic", "replaced_by")
LANE_OF = {"to-do": TODO, "blocked": TODO, "in progress": PROGRESS, "done": DONE, "backlog": DONE,
           "archived": DONE}
MIGRATE = "scripts/migrate/v2.1-v2.2"
FILE_RE = re.compile(r"^D(\d+)-.*\.md$")
FRONT_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)
TITLE_RE = re.compile(r"^#\s+D\d+\.\s*(.*?)\s*$")
LIST_TITLE_RE = re.compile(r"\A# Decisions, ")


def bd():
    return C.load("lib/board")


def own():
    return C.load("lib/ownership")


def path_of(folder):
    return Path(folder) / DECISIONS_MD


def settings(release):
    return SETTINGS.replace("[release]", release)


def is_kanban(text):
    """True when the text is the decisions board (lane "## To do" first)."""
    return bd().is_board(text, "To do")


def is_list(text):
    """True when the text is decisions.md of the file form: it starts with "# Decisions,"."""
    return bool(LIST_TITLE_RE.match(text))


def is_board(text):
    """True when decisions.md is in a form the scripts read, not in the old heading format: the
    board, or the list of the file form. migrate/pre-v1.0/decisions.py refusal and the release
    lookup of lib/common.py ask this; is_kanban asks for the board alone."""
    return is_kanban(text) or is_list(text)


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
    """parse() of the release's decisions.md; empty when the file is missing or not a board. In
    the file form the cards of the decision files (file_cards)."""
    if file_form(folder):
        return {"lanes": [], "cards": file_cards(folder), "stray": []}
    path = path_of(folder)
    if not path.is_file():
        return {"lanes": [], "cards": [], "stray": []}
    text = C.read(path)
    if not is_kanban(text):
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


def next_round(cards, new_round):
    """The round of a new decision: the highest round of the release, 1 when there is none, one
    more with --new-round when there is one."""
    top = highest_round(cards)
    return max(top, 1) + (1 if new_round and top else 0)


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


def spec_state(folder, num, path):
    """(merged, {D number: done}): merged is True when every milestone of the spec is done or
    stopped; the second holds, for a new-form spec, each decision a module heading cites: True
    when every milestone that holds a task of such a module is done or stopped, and each such
    module has a task in a milestone."""
    o = own()
    m = re.match(r"^\d{2}(?:\.\d+)?-(.+)\.md$", path.name)
    slug = m.group(1) if m else ""
    doc = o.read_spec(path)
    blocks = doc["blocks"]
    if blocks:
        trackers = [o.milestone_tracker(folder, num, slug, i, b["name"]) for i, b in enumerate(blocks)]
    else:
        trackers = [folder / o.TRACKERS_DIR / f"{num}-tracker.md"]
    states = [o.tracker_status(folder, num, t) for t in trackers]
    ok = [s is not None and s[0] in MERGED for s in states]
    per, placed = {}, set()
    for b, done in zip(blocks, ok):
        for t in b["tasks"] if b["id"] is not None else []:
            placed.add(t["module"])
            for d in t["cites"]:
                per[d] = per.get(d, True) and done
    pure = bool(doc["tasks"]) and "migrated" not in doc["front"]  # migrate/v1.0-v2.0/format.py: modules older than the tasks
    for mod, cites in (doc["modules"].items() if pure else ()):
        if mod not in placed:
            for d in cites:
                per[d] = False
    return all(ok), per


def spec_facts(folder):
    """{spec number: (D numbers cited in a heading line, D numbers cited anywhere, merged,
    {D number: done} of spec_state)}."""
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
        out[num] = (head, every) + spec_state(folder, num, p)
    return out


def hand_closed(card):
    """Closed by hand: a ticked card in Done (rule 3 asks it only of a card with no row)."""
    return card["lane"] == DONE and card["ticked"]


def rows_done(n, rows, facts):
    """Rule 2 of the Done rule: True when every own spec of decision n (rows[n]) is done for it."""
    mine = [s for s in rows[n] if s in facts and n in facts[s][0]] or rows[n]
    return all(s in facts and facts[s][3].get(n, facts[s][2]) for s in mine)


def cited_merged(n, facts):
    """True when a spec that cites decision n has merged (for n)."""
    return any(n in f[1] and f[3].get(n, f[2]) for f in facts.values())


def rule_lanes(folder, cards):
    """{D: lane} of every card by the Done rule (module docstring); in the file form the lane of
    the status rule."""
    if file_form(folder):
        return {n: LANE_OF[w] for n, w in rule_status(folder, cards).items()}
    rows = started_rows(folder)
    facts = spec_facts(folder)
    out = {}
    for c in cards:
        n = c["num"]
        if c["sup_by"] or c["deferred"]:
            out[n] = DONE
        elif rows.get(n):
            out[n] = DONE if rows_done(n, rows, facts) else PROGRESS
        elif hand_closed(c) or cited_merged(n, facts):
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
    re-read inside the lock, written only when it changed. Returns the cards moved. In the file
    form sync_files: the status rule on every decision file, and the list."""
    path = path_of(folder)
    form = file_form(folder)
    if not form and not path.is_file():
        return []
    lock = open(lock_path, "a") if lock_path else None
    try:
        if lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
        if form:
            return sync_files(folder)
        text = path.read_text(encoding="utf-8")
        if not is_kanban(text):
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


# The file form (module docstring).
def status_lib():
    return C.load("lib/status")


def file_form(folder):
    """True for a release of format FILE_FORMAT or higher whose decisions.md is not a board: its
    decisions are files in decisions/. The one test of the form; no script tests it by itself."""
    s = status_lib()
    if s.version(s.release_format(Path(folder))) < FILE_FORMAT:
        return False
    path = path_of(folder)
    return not (path.is_file() and is_kanban(C.read(path)))


def board_refusal(folder, what):
    """End the script with one line: what needs the file form, and the migration that makes it."""
    C.die(f"{what} needs a release whose decisions are files; {Path(folder).parent.name} keeps "
          f"them on the decisions.md board: move it first with {MIGRATE}")


def dir_of(folder):
    return Path(folder) / DECISIONS_DIR


def commit_paths(folder):
    """The paths a commit of a decision change names: decisions.md, and in the file form the
    folder decisions/."""
    return [path_of(folder)] + ([dir_of(folder)] if file_form(folder) else [])


def front_of(text):
    """The front matter of a decision file as an ordered dict of its "key: value" lines."""
    m = FRONT_RE.match(text)
    out = {}
    for line in m.group(1).split("\n") if m else []:
        k, sep, v = line.partition(":")
        if sep and k.strip():
            out[k.strip()] = v.strip()
    return out


def rest_of(text):
    """The text after the front matter: the title line and the body, byte for byte."""
    m = FRONT_RE.match(text)
    return text[m.end():] if m else text


def front_text(fields):
    """The front matter block: the keys of FRONT_KEYS in that order, then any other key as it
    was; a key with no value has no line."""
    keys = [k for k in FRONT_KEYS if fields.get(k)] + [k for k in fields if k not in FRONT_KEYS and fields[k]]
    return "---\n" + "".join(f"{k}: {fields[k]}\n" for k in keys) + "---\n"


def set_front(text, **fields):
    """text with the front matter keys set (None or "" removes a line); the title line and the
    body stay byte for byte."""
    have = front_of(text)
    for k, v in fields.items():
        if v is None or v == "":
            have.pop(k, None)
        else:
            have[k] = str(v)
    return front_text(have) + rest_of(text)


def decision_files(folder):
    """[(D number, path)] of the decision files, in the order of the numbers. Two files with one
    number end the script with one line."""
    d = dir_of(folder)
    seen = {}
    for p in sorted(d.glob("D*.md")) if d.is_dir() else []:
        m = FILE_RE.match(p.name)
        if not m:
            continue
        n = int(m.group(1))
        if n in seen:
            C.die(f"two files for D{n}: {seen[n].name} and {p.name}; keep one, a D number is never used twice")
        seen[n] = p
    return sorted(seen.items())


def file_path(folder, num):
    """The file of decision num, or None."""
    return dict(decision_files(folder)).get(num)


def new_path(folder, num, title):
    """decisions/D<num>-<slug>.md, the slug by the rule of a queue item file (lib/queue.py)."""
    slug = C.load("lib/specs").file_slug(title) or "decision"
    return dir_of(folder) / f"D{num}-{slug}.md"


def new_text(num, title, decider, source=None, bullet=None):
    """A new decision file: status to-do, the decider, the source when given; the title line; the
    --bullet line as the body when given."""
    body = ("\n" + (bullet if bullet.startswith("- ") else f"- {bullet}") + "\n") if bullet else ""
    return front_text({"status": STATUS_WORDS[0], "decider": decider, "source": source or ""}) + \
        f"# D{num}. {title.strip()}\n" + body


def file_cards(folder):
    """The cards of the decision files: the keys of a parse() card, worked out from each file and
    the status file, plus status, decider, source, front, path and file."""
    rounds = status_lib().decision_entries(folder)
    out = []
    for n, p in decision_files(folder):
        text = C.read(p)
        front = front_of(text)
        word = front.get("status") if front.get("status") in STATUS_WORDS else STATUS_WORDS[0]
        lines = rest_of(text).split("\n")
        t = TITLE_RE.match(lines[0]) if lines else None
        title = t.group(1) if t else (lines[0].lstrip("#").strip() if lines else "")
        body = lines[1:]
        while body and not body[0].strip():
            body.pop(0)
        while body and not body[-1].strip():
            body.pop()
        rb = re.fullmatch(r"D(\d+)", front.get("replaced_by", ""))
        ep = re.fullmatch(r"E(\d+)", front.get("epic", ""))
        rnd = (rounds.get(f"D{n}") or {}).get("round")
        sup = [int(rb.group(1))] if rb else []
        tags = (["superseded"] if sup else ["deferred"] if word == "backlog" else []) + \
            ([f"E{ep.group(1)}"] if ep else []) + ([f"R{rnd}"] if rnd else [])
        lane = LANE_OF[word]
        out.append({"num": n, "lane": lane, "line": 0, "end": 0, "box": "x" if lane == DONE else " ",
                    "ticked": lane == DONE, "title": title, "base": title, "sup_by": sup, "tags": tags,
                    "epic": int(ep.group(1)) if ep else None, "round": rnd if isinstance(rnd, int) else None,
                    "deferred": word == "backlog", "supersedes": [], "body": body, "subs": body,
                    "status": word, "stored": front.get("status", ""), "decider": front.get("decider", ""),
                    "source": front.get("source", ""), "front": front, "path": p,
                    "file": p.relative_to(folder).as_posix()})
    return out


def rule_status(folder, cards):
    """{D: status word} of every decision file by the status rule (module docstring)."""
    return status_and_waits(folder, cards)[0]


def status_and_waits(folder, cards):
    """({D: status word} by the status rule, {D: {epic: [shared files]}} of each blocked
    decision)."""
    rows = started_rows(folder)
    facts = spec_facts(folder)
    out = {}
    for c in cards:
        n = c["num"]
        if c["sup_by"]:
            out[n] = "archived"
        elif c["status"] == "backlog":
            out[n] = "backlog"
        elif rows.get(n):
            out[n] = "done" if rows_done(n, rows, facts) else "in progress"
        elif c["status"] == "done" or cited_merged(n, facts):
            out[n] = "done"
        elif c["epic"]:
            out[n] = "in progress"
        else:
            out[n] = STATUS_WORDS[0]
    waits = {}
    free = [c for c in cards if out[c["num"]] == STATUS_WORDS[0] and not c["epic"]]
    if free:
        scene = block_scene(folder, cards, out)
        for c in free:
            if c["num"] in scene["rows"]:
                continue
            got = waits_of(scene, c["num"])
            if got:
                out[c["num"]], waits[c["num"]] = "blocked", got
    return out, waits


# The blocked check (module docstring).
def row_epics(folder):
    """{D: the first epic number}: every decision with a row in the Ownership table of an epic
    file, gone or planned."""
    o = own()
    out = {}
    for n in o.epic_numbers(folder):
        rows, _ = o.read_table(o.read(o.epic_path(folder, n)))
        for r in rows or []:
            if r["decision"] is not None:
                out.setdefault(r["decision"], n)
    return out


def running_from(cards, word):
    """Sorted epic numbers of the decisions that have an "epic" line and are in progress, word
    being {D: status word}."""
    return sorted({c["epic"] for c in cards if c["epic"] and word.get(c["num"]) == "in progress"})


def block_scene(folder, cards, word):
    """The facts of the blocked check: specs {spec: (epic or None, cited D numbers)}, owned
    {spec: [files of every milestone]}, running (epic numbers), rows (row_epics) and given
    ({"D<n>": [files]} the lead gave)."""
    o = own()
    owned = {}
    for num, p in o.spec_files(folder):
        files = []
        for b in o.parse_spec(p):
            files += [f for f in b["files"] or [] if f not in files]
        owned[num] = files
    given = {k: v["files"] for k, v in status_lib().decision_entries(folder).items()
             if isinstance(v, dict) and isinstance(v.get("files"), list)}
    return {"specs": o.spec_epics(folder), "owned": owned, "running": running_from(cards, word),
            "rows": row_epics(folder), "given": given}


def citing(scene, num):
    """Spec numbers that cite decision num, in spec order."""
    return [s for s, (_, cited) in scene["specs"].items() if num in cited]


def files_of(scene, num):
    """The files of decision num: the Files owned of the specs that cite it, else the files the
    lead gave, else []."""
    specs = citing(scene, num)
    if specs:
        out = []
        for s in specs:
            out += [f for f in scene["owned"].get(s, []) if f not in out]
        return out
    return list(scene["given"].get(f"D{num}", []))


def waits_of(scene, num):
    """{epic: [files of decision num that a milestone of that running epic owns]}, only the
    epics that share a file. The specs citing num are not counted for any epic."""
    mine = files_of(scene, num)
    skip = set(citing(scene, num))
    out = {}
    for e in scene["running"]:
        theirs = set()
        for s, (epic, _) in scene["specs"].items():
            if epic == e and s not in skip:
                theirs.update(scene["owned"].get(s, []))
        shared = [f for f in mine if f in theirs]
        if shared:
            out[e] = shared
    return out


def reason_words(epics):
    """"Waits for E11, same file", "Waits for E11 and E12, same file", "Waits for E1, E2 and E3,
    same file" for the epic numbers given."""
    names = [f"E{e}" for e in sorted(epics)]
    who = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]
    return f"Waits for {who}, same file"


def blocked_reason(waits):
    """(reason words, shared files) of one entry of status_and_waits()[1]."""
    files = []
    for e in sorted(waits):
        files += [f for f in waits[e] if f not in files]
    return reason_words(waits), files


def running_epics(folder):
    """Sorted epic numbers of the running epics of a release in the file form."""
    cards = file_cards(folder)
    return running_from(cards, status_and_waits(folder, cards)[0])


def kept_entries(folder, entries):
    """The entries of the key "decisions" of the status file without the given files that the
    refresh chain removes: a decision a spec cites, one with a row in an epic file, one that is
    no longer to-do or blocked (or has no file). An entry left empty is dropped."""
    if not any(isinstance(v, dict) and "files" in v for v in entries.values()):
        return entries
    cards = file_cards(folder)
    word = rule_status(folder, cards)
    scene = block_scene(folder, cards, word)
    out = {}
    for k, v in entries.items():
        m = re.fullmatch(r"D(\d+)", k)
        n = int(m.group(1)) if m else None
        if isinstance(v, dict) and "files" in v and (
                n is None or word.get(n) not in (STATUS_WORDS[0], "blocked")
                or citing(scene, n) or n in scene["rows"]):
            v = {x: y for x, y in v.items() if x != "files"}
        if v:
            out[k] = v
    return out


def write_status(card, word):
    """The status line of the card's file set to word; the rest of the file byte for byte."""
    p = card["path"]
    p.write_text(set_front(p.read_text(encoding="utf-8"), status=word), encoding="utf-8")


def sync_files(folder):
    """The status rule on every decision file, then the list when it is not in step. Returns
    [(D number, old status, new status)] of the files changed. The caller holds the lock."""
    cards = file_cards(folder)
    want = rule_status(folder, cards)
    moved = []
    for c in cards:
        w = want[c["num"]]
        if w != c["stored"]:
            write_status(c, w)
            moved.append((c["num"], c["stored"] or "no status", w))
    if not list_in_step(folder):
        write_list(folder)
    return moved


def render_list(release, cards):
    """The text of decisions.md in the file form (templates/decisions-list.md)."""
    lines = [f"- [D{c['num']}]({DECISIONS_DIR}/{c['path'].name}): {c['title']}" for c in cards]
    return f"# Decisions, {release}\n" + ("\n" + "\n".join(lines) + "\n" if lines else "")


def list_text(folder):
    return render_list(Path(folder).parent.name, file_cards(folder))


def list_in_step(folder):
    path = path_of(folder)
    return path.is_file() and C.read(path) == list_text(folder)


def write_list(folder):
    """decisions.md written again from the decision files; returns its path."""
    path = path_of(folder)
    path.write_text(list_text(folder), encoding="utf-8")
    return path


def set_fields(folder, num, **fields):
    """Front matter lines of decision num set (None or "" removes one), then the status rule on
    every file and the list. Returns the path of the file."""
    p = file_path(folder, num)
    if p is None:
        raise KeyError(num)
    p.write_text(set_front(p.read_text(encoding="utf-8"), **fields), encoding="utf-8")
    sync_files(folder)
    return p


def write_data(folder):
    """The dashboard data written again after a change of a decision file (lib/dashboard.py)."""
    C.load("lib/dashboard").write(folder)
