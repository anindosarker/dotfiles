#!/usr/bin/env python3
"""Convert a decisions.md in the heading format ("## Round <n>: ..." headings, "### D<n> <title>"
items, a tag line "[E<n>]", "[Done]  [E<n>]" or "[Done]" under a heading) in place into the
kanban board of lib/decisions.py.

Usage: python3 -I migrate/decisions.py <release> [--dry-run] [--owner X] [--root PATH]

Lossless: every decision becomes one card "- [ ] **D<n>** <title> <tags>" with its title (a
"(superseded by D<n>)" mark moved to the end of the title) and every non-blank line of its body,
in order, indented with one TAB; inside a fenced code block every line is kept, a blank one as a
lone TAB. The tag line becomes "#E<n>"; the round heading the decision sat under becomes "#R<n>";
"#superseded" or "#deferred" when it applies. The lane comes from the Done rule (lib/decisions.py);
a "[Done]" tag line is read as closed by hand (a ticked card in Done), so a decision with no row
in an epic that has gone keeps the Done the old file gave it. The file title, the round headings and blank lines between bullets are
dropped; any other line outside a decision is printed as not placed and dropped.

Prints the cards per lane, the ids in To do and In progress, and the lines not placed. --dry-run
writes nothing. Commits nothing. A board is left as it is ("already a board"), so a second run
changes nothing. refusal(folder, release) is the one line every other script prints for a folder
whose decisions.md is still in the heading format.
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
HERE = Path(__file__).resolve().parent
ROUND_RE = re.compile(r"^##\s+Round\s+(\d+)\b")
HEAD_RE = re.compile(r"^###\s+D(\d+)\b\s*(.*?)\s*$")
SECTION_RE = re.compile(r"^#{1,3}\s")
TAG_LINE_RE = re.compile(r"^\s*(?:\[(?:Done|E\d+)\]\s*)+$")
die = C.die


def refusal(folder, release):
    """One line for the other scripts when decisions.md is not a board yet, else None."""
    path = Path(folder) / "decisions.md"
    if not path.is_file():
        return None
    if C.load("lib/decisions").is_board(C.read(path)):
        return None
    return (f"{path} is in the old heading format, not a kanban board: run python3 -I "
            f"{HERE / 'decisions.py'} {release}")


def flags(lines):
    """Inside-fence flag of each line, as common.fence_flags decides it (a fence line counts as
    inside), one flag per element of lines."""
    out, fence = [], None
    for line in lines:
        s = line.lstrip()
        m = re.match(r"^(`{3,}|~{3,})", s)
        if m:
            mark = m.group(1)
            if fence is None:
                fence = mark
            elif mark[0] == fence[0] and len(mark) >= len(fence) and s.strip() == mark:
                fence = None
            out.append(True)
            continue
        out.append(fence is not None)
    return out


def read_old(text):
    """(decisions, not placed): each decision {num, title, round, epic, done, body}; body holds
    the non-blank lines outside fences and every line inside one; not placed [(line no, text)]."""
    lines = text.split("\n")
    inside = flags(lines)
    out, unplaced = [], []
    rnd, cur, titled = None, None, False
    for i, line in enumerate(lines):
        fenced = inside[i]
        if not fenced:
            m = ROUND_RE.match(line)
            if m:
                rnd, cur = int(m.group(1)), None
                continue
            m = HEAD_RE.match(line)
            if m:
                cur = {"num": int(m.group(1)), "title": m.group(2), "round": rnd, "epic": None,
                       "done": False, "tagged": False, "body": []}
                out.append(cur)
                continue
            if SECTION_RE.match(line):
                cur = None
                if line.startswith("# ") and not titled:
                    titled = True
                    continue
                unplaced.append((i + 1, line))
                continue
        if cur is None:
            if line.strip():
                unplaced.append((i + 1, line))
            continue
        if not fenced and not cur["tagged"] and not cur["body"] and TAG_LINE_RE.match(line):
            e = re.search(r"\[E(\d+)\]", line)
            cur["epic"] = int(e.group(1)) if e else None
            cur["done"] = "[Done]" in line
            cur["tagged"] = True
            continue
        if fenced or line.strip():
            cur["body"].append(line)
    return out, unplaced


def to_card(dc, d, lane):
    """The card block of an old decision in lane."""
    marks = [int(n) for n in dc.MARK_RE.findall(d["title"])]
    body = d["body"]
    card = {"num": d["num"], "base": dc.MARK_RE.sub("", d["title"]).strip(), "sup_by": marks,
            "deferred": any(dc.DEFERRED_RE.match(l) for l in dc.outside(body)),
            "epic": d["epic"], "round": d["round"]}
    return [dc.head_line(card, lane)] + ["\t" + l for l in body]


def convert(folder, release, text):
    """(board text, lanes {D: lane}, not placed)."""
    dc = C.load("lib/decisions")
    olds, unplaced = read_old(text)
    first = collections.defaultdict(list)
    for d in sorted(olds, key=lambda d: d["num"]):
        lane = dc.DONE if d["done"] else dc.TODO
        first[lane].append(to_card(dc, d, lane))
    draft = dc.render(release, first)
    want = dc.rule_lanes(folder, dc.parse(draft)["cards"])
    by_lane = collections.defaultdict(list)
    for d in sorted(olds, key=lambda d: d["num"]):
        by_lane[want[d["num"]]].append(to_card(dc, d, want[d["num"]]))
    return dc.render(release, by_lane), want, unplaced, olds


def main():
    ap = argparse.ArgumentParser(usage="migrate/decisions.py <release> [--dry-run] [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    root = C.repo_root(a.root, a.release)
    folder = root / ".ai" / "plans" / a.release / C.detect_owner(root, a.owner)
    if not folder.is_dir():
        die(f"release folder missing: {folder}")
    if not (folder / "plan").is_dir():
        die(f"{folder} has the old layout (no plan/): run python3 -I {HERE / 'layout.py'} {a.release}")
    path = folder / "decisions.md"
    if not path.is_file():
        die(f"missing: {path}")
    dc = C.load("lib/decisions")
    text = C.read(path)
    if dc.is_board(text):
        cards = dc.parse(text)["cards"]
        n = collections.Counter(c["lane"] for c in cards)
        print(f"{path} is already a board: " + ", ".join(f"{lane} {n[lane]}" for lane in dc.LANES)
              + "; nothing changed")
        return
    board, want, unplaced, olds = convert(folder, a.release, text)
    n = collections.Counter(want.values())
    print(f"Cards: {len(olds)}; " + ", ".join(f"{lane} {n[lane]}" for lane in dc.LANES))
    for lane in (dc.TODO, dc.PROGRESS):
        ids = sorted(k for k, v in want.items() if v == lane)
        print(f"{lane}: {', '.join(f'D{k}' for k in ids) or 'none'}")
    dups = sorted(k for k, v in collections.Counter(d["num"] for d in olds).items() if v > 1)
    if dups:
        print(f"Duplicate numbers, both kept: {', '.join(f'D{k}' for k in dups)}")
    print(f"Not placed ({len(unplaced)} lines):")
    for i, line in unplaced:
        print(f"  decisions.md:{i}: {line[:100]}")
    if a.dry_run:
        print("dry run; nothing written")
        return
    path.write_text(board, encoding="utf-8")
    print(f"converted {path}; nothing committed")


if __name__ == "__main__":
    main()
