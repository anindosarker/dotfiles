#!/usr/bin/env python3
"""Move a release folder to queue.md as a kanban board in the current card format (board.py
has the format: tags #D<n> and #E<n> only, the tick in Decided mirrors decisions.md).

Usage: python3 -I migrate_queue.py <release> [--dry-run] [--owner X] [--root PATH]

Three inputs, one output:

(c) A board in the old card format (a from tag "#owner", "#lead", "#lookup", "#run" or
"#run-E<n>" on a title line, or a "Decision: D<n>" sub-bullet) is converted in place: from tags
removed from title lines; each "Decision: D<n>" sub-bullet removed and "#D<n>" appended to its
card's title (the highest when several; a card outside Decided keeps its #D tag too); Open and
Later cards "[ ]", Dropped and Autofix "[x]", Decided cards ticked and tagged #E<n> by
board.sync; card order, facts and lanes unchanged; the frontmatter restored when missing; the
settings block kept byte for byte, with "tag-action":"kanban" added only when that key is
absent. A board already in the current format gets the same pass, which changes nothing.
Prints cards per lane, Decided cards ready / in an epic / done without epic / superseded or
deferred without a tag, the ready cards with their D ids, and the from tags removed.

(b) A queue.md in the heading format ("### Q<n> <title>", then "- Tags: <value>" and
"- From: <who>.") is converted in place: ids and titles kept, the Tags value picks the lane
(empty Open, D<n> Decided with "#D<n>" on the title, Later, Dropped, Autofix), From is dropped,
the other bullets become tab-indented sub-bullets with their nesting kept, entry order kept
inside each lane, Decided cards synced as in (c). An entry with any other Tags value goes to
Open and is listed as not placed.

(a) A folder that still has findings.md (### F<n> items) or run/attentions/ (also a flat
attentions/) with ATTENTION-<YYYY-MM-DD>.md files (## A<n> items) is first turned into the
heading format below, then converted as in (b):

- Entries: every F item in file order and every A item in file-date then file order,
  numbered Q1.. in that order; the old bullets follow as they are (blank lines inside an
  item dropped).
- Tags value, one word: an A item tagged [D<n>] gets D<n>. An A item tagged [F<n>] is the same
  item as that finding: it maps to that finding's Q id, gets no entry of its own, and its D
  tags and bullets join that entry. An F item whose first bullet is "- Same as F<n>." maps the
  same way. An F item a decision cites with "- Source: F<n>" or a first bullet "- Fixes F<n>"
  gets D<n>. An F item cited on the first line of a fix tracker gets Autofix. An F item with a
  "Deferred to" bullet, or one an A item deferred into, gets Later. When several apply, the
  first of D (the highest number when several decisions name the entry), Autofix, Later wins.
  Everything else stays empty (open).
- Rewrites every reference in the release folder (decisions.md, specs, trackers, epic files,
  handoffs, the plan file, process.md, status/*.md; never reference/): "(F3)", "(A2)", id lists
  inside parentheses such as "(F3, F4)" or "(milestone 24, A20)", "Source: A2", "Fixes F5 and
  F7", "[F40]", "Same as F<n>". A parenthesis that names another release ("(v0.4.x F9)") is
  never touched. Mentions of findings.md and of the ATTENTION files become queue.md.
- Deletes findings.md and the attentions folder with git rm. Commits nothing.
- Prints the old-id to Q-id mapping, the entries left untagged, and every bare F<digits> or
  A<digits> token it did not rewrite as "path:line: text", for a person to settle.

Prints the count of cards per lane and any entry it could not place. --dry-run prints the same
and writes nothing. Commits nothing. Refuses a folder that has both queue.md and an old file.

refusal(folder, release) is also used by the other scripts to refuse an unmigrated folder: old
queue files, a queue.md that is not a board, or a board in the old card format.
"""
import argparse
import collections
import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path

RELEASE_RE = re.compile(r"^v\d+\.\d+\.x$")
HERE = Path(__file__).resolve().parent
FINDINGS = "findings.md"
ATT_DIRS = ("run/attentions", "attentions")
QUEUE = "queue.md"
F_HEAD_RE = re.compile(r"^###\s+F(\d+)\b\s*(.*?)\s*$")
A_HEAD_RE = re.compile(r"^#{2,3}\s+A(\d+)\b\s*(.*?)\s*$")
D_HEAD_RE = re.compile(r"^###\s+D(\d+)\b")
TAG_LINE_RE = re.compile(r"^\s*(?:\[[^\]\n]+\]\s*)+$")
TAG_RE = re.compile(r"\[([^\]\n]+)\]")
ID = r"[DFAPQ]\d+"
ID_LIST = ID + r"(?:\s*(?:,|and|to)\s*" + ID + r")*"
ID_LIST_RE = re.compile(r"^\s*(" + ID_LIST + r")\s*$")
LEAD_LIST_RE = re.compile(r"^(\s*)(" + ID_LIST + r")")
OTHER_RELEASE_RE = re.compile(r"\bv\d+\.\d+\.x\b")
PAREN_RE = re.compile(r"\(([^()\n]*)\)")
SOURCE_RE = re.compile(r"(Source:\s*)(" + ID_LIST + r")")
FIXES_RE = re.compile(r"^(\s*-\s*Fixes\s+)(" + ID_LIST + r")")
SAME_RE = re.compile(r"\bSame as ([FA]\d+)\b")
BRACKET_RE = re.compile(r"\[([FA]\d+)\]")
FA_RE = re.compile(r"\b([FA]\d+)\b")
ATT_NAME_RE = re.compile(r"(?:(?:run/)?attentions/)?ATTENTION-\d{4}-\d{2}-\d{2}\.md")
FINDINGS_NAME_RE = re.compile(r"([\w./-]*?)\bfindings\.md\b")
BARE_SKIP_RE = re.compile(r"\bv\d+\.\d+\.x\s+$")
FIX_TRACKER_RE = re.compile(r"^fix-(.+)-tracker\.md$")


def old_files(folder):
    """The old queue files a folder still has, as names for a message: [] when migrated."""
    out = [FINDINGS] if (Path(folder) / FINDINGS).is_file() else []
    out += [d + "/" for d in ATT_DIRS if (Path(folder) / d).is_dir()]
    return out


def refusal(folder, release):
    """One line for the other scripts: the folder still has the old files and no queue.md, or a
    queue.md that is not a kanban board yet."""
    old = old_files(folder)
    queue = Path(folder) / QUEUE
    run = f"run python3 -I {HERE / 'migrate_queue.py'} {release}"
    if old and not queue.is_file():
        return f"{folder} has {' and '.join(old)} and no {QUEUE}: {run}"
    if queue.is_file():
        bd = load("board")
        text = read(queue)
        if not bd.is_board(text):
            return f"{queue} is not a kanban board yet: {run}"
        if bd.is_old(text):
            return f"{queue} has cards in the old format (from tags or Decision: sub-bullets): {run}"
    return None


HQ_HEAD_RE = re.compile(r"^###\s+Q(\d+)\b\s*(.*?)\s*$")
HQ_TAGS_RE = re.compile(r"^\s*-\s*Tags:\s*(.*?)\s*$")
HQ_FROM_RE = re.compile(r"^\s*-\s*From:\s*(.*?)\s*$")
BULLET_RE = re.compile(r"^( *)- (.*)$")


def convert(text, tags):
    """Heading-format queue text to a board: (board text, {lane: count}, [not placed])."""
    bd = load("board")
    entries, cur = [], None
    for line, inside in fenced(text.split("\n")):
        m = None if inside else HQ_HEAD_RE.match(line)
        if m:
            cur = {"num": int(m.group(1)), "title": m.group(2), "tag": None, "from": None, "body": []}
            entries.append(cur)
            continue
        if cur is None or (not line.strip() and not inside):
            continue
        t = HQ_TAGS_RE.match(line) if cur["tag"] is None and not cur["body"] else None
        if t:
            cur["tag"] = t.group(1)
            continue
        f = HQ_FROM_RE.match(line) if cur["from"] is None and not cur["body"] else None
        if f:
            cur["from"] = f.group(1)
            continue
        cur["body"].append(line.rstrip())
    lanes, unplaced = {}, []
    for e in entries:
        tag = e["tag"] or ""
        lane = {"": "Open", "Later": "Later", "Dropped": "Dropped", "Autofix": "Autofix"}.get(tag)
        if re.fullmatch(r"D\d+", tag):
            lane = "Decided"
        if lane is None:
            lane = "Open"
            unplaced.append(f"Q{e['num']}: Tags '{tag}'")
        block = [bd.card_line(e["num"], e["title"], lane)]
        if lane == "Decided":
            block[0] = bd.set_tags(block[0], int(tag[1:]))
        for line in e["body"]:
            b = BULLET_RE.match(line)
            if b:
                block.append(bd.fact_line(b.group(2), len(b.group(1)) // 2 + 1))
            else:
                block.append("\t" + bd.escape_tags(line.strip()))
        lanes.setdefault(lane, []).append(block)
    counts = {lane: len(lanes.get(lane, [])) for lane in bd.LANES}
    return bd.sync(bd.render(lanes), tags)[0], counts, unplaced


FROM_STRIP_RE = re.compile(r"[ \t]*(?<![\w`])#(?:owner|lead|lookup|run(?:-E\d+)?)(?![\w-])")
TAG_ACTION = '"tag-action":"kanban"'


def add_tag_action(lines):
    """Add "tag-action":"kanban" to the settings JSON line when the key is absent; every other
    byte of the block stays. Returns True when it added the key."""
    start = next((i for i, l in enumerate(lines) if re.match(r"^%%\s*kanban:settings", l)), None)
    if start is None:
        return False
    for i in range(start, len(lines)):
        line = lines[i]
        if '"tag-action"' in line:
            return False
        if i > start and line.strip() == "%%":
            return False
        k = line.rfind("}")
        if line.lstrip().startswith("{") and k >= 0:
            inner = line[:k].rstrip()
            sep = "" if inner.endswith("{") else ","
            lines[i] = inner + sep + TAG_ACTION + line[k:]
            return True
    return False


def recard(text, tags):
    """A board in the old card format to the current one, in place (mode c).
    Returns (text, {"from": n, "decision": n, "tag_action": bool})."""
    bd = load("board")
    lines = text.split("\n")
    stats = {"from": 0, "decision": 0, "tag_action": False}
    for c in reversed(bd.parse(text)["cards"]):
        head = lines[c["line"]]
        stats["from"] += len(FROM_STRIP_RE.findall(head))
        head = FROM_STRIP_RE.sub("", head).rstrip()
        subs = lines[c["line"] + 1:c["end"]]
        decs = [int(m.group(1)) for l in subs if (m := bd.DECISION_RE.match(l))]
        if decs:
            stats["decision"] += len(decs)
            subs = [l for l in subs if not bd.DECISION_RE.match(l)]
        d = max(decs + ([c["d"]] if c["d"] else [])) if decs or c["d"] else None
        if d:
            head = bd.set_tags(head, d, c["e"] if c["lane"] == "Decided" else None)
        if c["lane"] != "Decided":
            head = bd.set_box(head, bd.box_for(c["lane"]))
        lines[c["line"]:c["end"]] = [head] + subs
    stats["tag_action"] = add_tag_action(lines)
    new, _ = bd.sync(bd.with_front("\n".join(lines)), tags)
    return new, stats


def decided_counts(text, tags):
    """(ready [(Q, D)], in an epic, done without epic, closed without a tag) of the Decided cards,
    from decision_tags()."""
    bd = load("board")
    ready, epic, done, closed = [], 0, 0, 0
    for c in bd.parse(text)["cards"]:
        if c["lane"] != "Decided":
            continue
        t = tags.get(c["d"]) if c["d"] else None
        if t is None:
            continue
        if t["epic"]:
            epic += 1
        elif t["done"]:
            done += 1
        elif t["closed"]:
            closed += 1
        else:
            ready.append((c["num"], c["d"]))
    return ready, epic, done, closed


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def load(name):
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read(p):
    return p.read_text(encoding="utf-8", errors="replace")


def fenced(lines):
    """Yield (line, inside a code fence) for every line."""
    fence = None
    for line in lines:
        s = line.lstrip()
        m = re.match(r"^(`{3,}|~{3,})", s)
        if m:
            if fence is None:
                fence = m.group(1)
            elif m.group(1)[0] == fence[0] and s.strip() == m.group(1):
                fence = None
            yield line, True
            continue
        yield line, fence is not None


def parse_items(path, head_re):
    """[{num, title, tags, body, round}] of one file; body keeps fenced blank lines only."""
    items, cur, round_head = [], None, ""
    for line, inside in fenced(read(path).splitlines()):
        m = None if inside else head_re.match(line)
        if m:
            cur = {"num": int(m.group(1)), "title": m.group(2), "tags": [], "body": [],
                   "round": round_head, "tagline": True}
            items.append(cur)
            continue
        if not inside and re.match(r"^#{1,3}\s", line):
            if line.startswith("## "):
                round_head = line[3:].strip()
            cur = None
            continue
        if cur is None:
            continue
        if cur["tagline"]:
            cur["tagline"] = False
            if not inside and TAG_LINE_RE.match(line):
                cur["tags"] = TAG_RE.findall(line)
                continue
        if not line.strip() and not inside:
            continue
        cur["body"].append(line.rstrip())
    return items


def attention_files(folder):
    out = []
    for d in ATT_DIRS:
        if (folder / d).is_dir():
            out += sorted((folder / d).glob("ATTENTION-*.md"))
    return sorted(out, key=lambda p: p.name)


def ids_in(text):
    return re.findall(r"[FA]\d+", text)


def decision_cites(folder):
    """{old id: {D numbers}} from Source: lines and first-bullet Fixes lines of decisions.md."""
    out = collections.defaultdict(set)
    path = folder / "decisions.md"
    if not path.is_file():
        return out
    d, first = None, False
    for line, inside in fenced(read(path).splitlines()):
        if inside:
            continue
        m = D_HEAD_RE.match(line)
        if m:
            d, first = int(m.group(1)), True
            continue
        if line.startswith("#"):
            d = None
            continue
        if d is None:
            continue
        for s in SOURCE_RE.finditer(line):
            for i in ids_in(s.group(2)):
                out[i].add(d)
        if first and line.lstrip().startswith("- "):
            f = FIXES_RE.match(line)
            if f:
                for i in ids_in(f.group(2)):
                    out[i].add(d)
            first = False
    return out


def fix_cites(folder):
    """{old id: [fix slugs]} from the first line of each fix tracker."""
    out = collections.defaultdict(list)
    for p in sorted(folder.glob("run/trackers/fix-*-tracker.md")) + sorted(folder.glob("trackers/fix-*-tracker.md")):
        lines = read(p).splitlines()
        slug = FIX_TRACKER_RE.match(p.name).group(1)
        for g in PAREN_RE.finditer(lines[0] if lines else ""):
            for i in ids_in(g.group(1)):
                if slug not in out[i]:
                    out[i].append(slug)
    return out


def build(folder):
    """Return (entries, mapping, notes): entries [{q, title, tags, body}], mapping {old: Q id}."""
    f_items = parse_items(folder / FINDINGS, F_HEAD_RE) if (folder / FINDINGS).is_file() else []
    a_items = []
    for p in attention_files(folder):
        for it in parse_items(p, A_HEAD_RE):
            it["file"] = p.name
            a_items.append(it)
    f_nums = {it["num"] for it in f_items}
    later = set()
    order = []
    for it in f_items:
        it["old"] = f"F{it['num']}"
        first = it["body"][0] if it["body"] else ""
        same = re.match(r"^\s*-\s*Same as F(\d+)\b", first)
        it["merge"] = f"F{same.group(1)}" if same and int(same.group(1)) in f_nums else None
        if any(re.match(r"^\s*-\s*Deferred to\b", l) for l in it["body"]):
            later.add(it["old"])
        order.append(it)
    for it in a_items:
        it["old"] = f"A{it['num']}"
        fs = [t for t in it["tags"] if re.fullmatch(r"F\d+", t) and int(t[1:]) in f_nums]
        it["merge"] = fs[0] if fs else None
        if fs:
            later.add(fs[0])
        order.append(it)

    mapping, entries, by_old = {}, [], {}
    for it in order:
        if it["merge"]:
            continue
        q = f"Q{len(entries) + 1}"
        e = {"q": q, "title": it["title"], "body": list(it["body"]),
             "d": set(), "fix": [], "later": False, "olds": [it["old"]]}
        entries.append(e)
        mapping[it["old"]] = q
        by_old[it["old"]] = e
    for it in order:
        if it["merge"]:
            if it["merge"] not in mapping:
                die(f"{it['old']} merges into {it['merge']}, which has no entry yet: fix the old file")
            e = by_old[mapping_owner(it["merge"], mapping, by_old)]
            mapping[it["old"]] = e["q"]
            e["olds"].append(it["old"])
            if it["old"].startswith("A"):
                e["body"] += [l for l in it["body"] if not re.match(r"^\s*-\s*Same as\b", l)]
    for it in order:
        e = by_old[mapping_owner(it["old"], mapping, by_old)]
        e["d"] |= {int(t[1:]) for t in it["tags"] if re.fullmatch(r"D\d+", t)}
    for old, ds in decision_cites(folder).items():
        if old in mapping:
            by_old[mapping_owner(old, mapping, by_old)]["d"] |= ds
    for old, slugs in fix_cites(folder).items():
        if old in mapping:
            e = by_old[mapping_owner(old, mapping, by_old)]
            e["fix"] += [s for s in slugs if s not in e["fix"]]
    for old in later:
        if old in mapping:
            by_old[mapping_owner(old, mapping, by_old)]["later"] = True
    for e in entries:
        e["tag"] = (f"D{max(e['d'])}" if e["d"] else "Autofix" if e["fix"]
                    else "Later" if e["later"] else "")
    return entries, mapping


def mapping_owner(old, mapping, by_old):
    """The old id whose entry holds old's Q id."""
    if old in by_old:
        return old
    q = mapping[old]
    return next(o for o, e in by_old.items() if e["q"] == q)


def rewrite_ids(text, mapping):
    """Rewrite the F and A ids of an id list."""
    return FA_RE.sub(lambda m: mapping.get(m.group(1), m.group(1)), text)


def rewrite_paren(m, mapping):
    inner = m.group(1)
    if OTHER_RELEASE_RE.search(inner):
        return m.group(0)
    lead = LEAD_LIST_RE.match(inner)
    if lead:
        inner = lead.group(1) + rewrite_ids(lead.group(2), mapping) + inner[lead.end():]
    parts = re.split(r"([,;])", inner)
    parts = [rewrite_ids(p, mapping) if ID_LIST_RE.match(p) else p for p in parts]
    return "(" + "".join(parts) + ")"


def rewrite_line(line, mapping, prefix):
    line = PAREN_RE.sub(lambda m: rewrite_paren(m, mapping), line)
    line = SOURCE_RE.sub(lambda m: m.group(1) + rewrite_ids(m.group(2), mapping), line)
    line = FIXES_RE.sub(lambda m: m.group(1) + rewrite_ids(m.group(2), mapping), line)
    line = SAME_RE.sub(lambda m: "Same as " + mapping.get(m.group(1), m.group(1)), line)
    line = BRACKET_RE.sub(lambda m: "[" + mapping.get(m.group(1), m.group(1)) + "]", line)
    line = ATT_NAME_RE.sub(QUEUE, line)

    def findings_name(m):
        pre = m.group(1)
        if pre and pre != "./" and not pre.endswith(prefix):
            return m.group(0)
        return pre + QUEUE
    return FINDINGS_NAME_RE.sub(findings_name, line)


def rewrite_text(text, mapping, prefix):
    out = []
    for line, inside in fenced(text.split("\n")):
        out.append(line if inside else rewrite_line(line, mapping, prefix))
    return "\n".join(out)


def bare_tokens(rel, text):
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        for m in FA_RE.finditer(line):
            if BARE_SKIP_RE.search(line[: m.start()]):
                continue
            if re.search(r"\bof\s+v\d+\.\d+\.x\b", line[m.end(): m.end() + 12]):
                continue
            out.append(f"{rel}:{i}: {line.strip()[:160]}")
            break
    return out


def queue_text(release, entries):
    out = [f"# {release} queue"]
    for e in entries:
        out += ["", f"### {e['q']} {e['title']}", f"- Tags: {e['tag']}".rstrip()]
        out += e["body"]
    return "\n".join(out) + "\n"


def report(counts, unplaced):
    print("Cards per lane: " + ", ".join(f"{k} {v}" for k, v in counts.items())
          + f"; {sum(counts.values())} cards")
    print(f"Not placed: {'; '.join(unplaced) or 'none'}")


def targets(folder):
    """Every Markdown file of the release folder the rewrite covers."""
    skip_dirs = ("reference", "status/data") + ATT_DIRS
    out = []
    for p in sorted(folder.rglob("*.md")):
        rel = p.relative_to(folder).as_posix()
        if rel in (FINDINGS, QUEUE) or any(rel.startswith(d + "/") for d in skip_dirs):
            continue
        out.append(p)
    return out


def git_rm(root, path):
    r = subprocess.run(["git", "-C", str(root), "rm", "-r", "-q", "--", str(path)],
                       capture_output=True, text=True)
    if r.returncode:
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()


def main():
    ap = argparse.ArgumentParser(usage="migrate_queue.py <release> [--dry-run] [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    own = load("ownership")
    root = own.repo_root(a.root, a.release)
    owner = own.detect_owner(root, a.owner)
    folder = root / ".ai" / "plans" / a.release / owner
    if not folder.is_dir():
        die(f"release folder missing: {folder}")
    old = old_files(folder)
    has_queue = (folder / QUEUE).is_file()
    if has_queue and old:
        die(f"{folder} has both {QUEUE} and {' and '.join(old)}: merge them by hand")
    tags = load("board").decision_tags(own, folder)
    if has_queue:
        text = read(folder / QUEUE)
        bd = load("board")
        if bd.is_board(text):
            board_text, stats = recard(text, tags)
            parsed = bd.parse(board_text)
            n = collections.Counter(c["lane"] for c in parsed["cards"])
            report({lane: n[lane] for lane in bd.LANES} | {k: v for k, v in n.items() if k not in bd.LANES}, [])
            print(f"From tags removed: {stats['from']}; Decision: sub-bullets turned into #D tags: "
                  f"{stats['decision']}; tag-action added: {'yes' if stats['tag_action'] else 'no'}")
        else:
            board_text, counts, unplaced = convert(text, tags)
            report(counts, unplaced)
        ready, epic, done, closed = decided_counts(board_text, tags)
        print(f"Decided: {len(ready)} ready, {epic} in an epic, {done} done without epic, "
              f"{closed} superseded or deferred without a tag")
        print(f"Ready: {', '.join(f'Q{q} (D{d})' for q, d in ready) or 'none'}")
        if a.dry_run:
            print("dry run; nothing written")
            return
        if board_text == text:
            print(f"{folder / QUEUE} already in the current format; nothing changed")
            return
        (folder / QUEUE).write_text(board_text, encoding="utf-8")
        print(f"converted {folder / QUEUE}; nothing committed")
        return

    entries, mapping = build(folder)
    prefix = f"{a.release}/{owner}/"
    queue = rewrite_text(queue_text(a.release, entries), mapping, prefix)
    changed, leftovers = [], []
    for p in targets(folder):
        text = read(p)
        new = rewrite_text(text, mapping, prefix)
        rel = p.relative_to(folder).as_posix()
        if new != text:
            changed.append((p, new))
        leftovers += bare_tokens(rel, new)
    leftovers = bare_tokens(QUEUE, queue) + leftovers

    print("Mapping:")
    for o, q in mapping.items():
        print(f"  {o} -> {q}")
    counts = collections.Counter(e["tag"].rstrip("0123456789") for e in entries if e["tag"])
    several = [f"{e['q']} ({', '.join(f'D{n}' for n in sorted(e['d']))})" for e in entries if len(e["d"]) > 1]
    f_count = sum(1 for o in mapping if o.startswith("F"))
    a_count = sum(1 for o in mapping if o.startswith("A"))
    print(f"Counts: {f_count} F items, {a_count} A items, {f_count + a_count - len(entries)} merged, "
          f"{len(entries)} entries; tags: "
          + (", ".join(f"{k} {v}" for k, v in sorted(counts.items())) or "none"))
    untagged = [e["q"] for e in entries if not e["tag"]]
    print(f"Untagged: {', '.join(untagged) or 'none'}")
    if several:
        print(f"Several decisions, highest kept: {'; '.join(several)}")
    print(f"Files rewritten: {len(changed)}")
    for p, _ in changed:
        print(f"  {p.relative_to(folder).as_posix()}")
    print(f"Bare F or A tokens left ({len(leftovers)} lines):")
    for l in leftovers:
        print(f"  {l}")
    board_text, lane_counts, unplaced = convert(queue, tags)
    report(lane_counts, unplaced)
    if a.dry_run:
        print("dry run; nothing written")
        return
    (folder / QUEUE).write_text(board_text, encoding="utf-8")
    for p, new in changed:
        p.write_text(new, encoding="utf-8")
    if (folder / FINDINGS).exists():
        git_rm(root, folder / FINDINGS)
    for d in ATT_DIRS:
        if (folder / d).exists():
            git_rm(root, folder / d)
    print(f"wrote {folder / QUEUE}; removed {' and '.join(old)}; nothing committed")


if __name__ == "__main__":
    main()
