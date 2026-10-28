#!/usr/bin/env python3
"""Read-only status report for an expedition cycle folder.

Usage: python3 -I status.py <cycle> [--owner X]
"""
import argparse
import collections
import re
import subprocess
import sys
from pathlib import Path

CYCLE_RE = re.compile(r"^v\d+\.\d+\.x$")
PART_RE = re.compile(r"^(\d{2}(?:\.\d+)?)-.+\.md$")
ROW_RE = re.compile(r"^\|\s*(\d{2}(?:\.\d+)?)\s*\|(.*)$")
LINK_RE = re.compile(r"\]\(([^)\s]+\.md)\)")
ITEM_RE = re.compile(r"^(\d+)\. ")
LIST = r"(\d+(?:\s*(?:,|and|to)\s*\d+)*)"
DEC_PAREN_RE = re.compile(r"\(decisions? " + LIST + r"\)")
DEC_BARE_RE = re.compile(r"\bdecision (\d+)(?![\d-])")
RUL_PAREN_RE = re.compile(r"\(rulings? " + LIST + r"\)")
RUL_BARE_RE = re.compile(r"\bruling (\d+)(?![\d-])")
TAGS = ("[revert?]", "[blocked]", "[ruling]")


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def repo_root():
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


def num_key(num):
    return tuple(int(x) for x in num.split("."))


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


def cites(text, paren_re, bare_re):
    nums = set()
    for m in paren_re.finditer(text):
        nums |= expand(m.group(1))
    for m in bare_re.finditer(text):
        nums.add(int(m.group(1)))
    return nums


def items(path):
    if not path.is_file():
        return []
    return [int(m.group(1)) for l in read(path).splitlines() if (m := ITEM_RE.match(l))]


def fmt(nums):
    return ", ".join(str(n) for n in sorted(nums)) if nums else "none"


def outside_fences(text):
    fence = None
    for i, line in enumerate(text.splitlines(), 1):
        s = line.lstrip()
        m = re.match(r"^(`{3,}|~{3,})", s)
        if m:
            mark = m.group(1)
            if fence is None:
                fence = mark
            elif mark[0] == fence[0] and len(mark) >= len(fence) and s.strip() == mark:
                fence = None
            continue
        if fence is None:
            yield i, line


def cite_report(label, source, defined, parts, paren_re, bare_re):
    cited = set()
    for p in parts:
        cited |= cites(read(p), paren_re, bare_re)
    print(f"{label}: {len(defined)} in {source}")
    print(f"  uncited: {fmt(set(defined) - cited)}")
    print(f"  cited but undefined: {fmt(cited - set(defined))}")
    dups = [n for n, c in collections.Counter(defined).items() if c > 1]
    if dups:
        print(f"  duplicate numbers: {fmt(dups)}")


def main():
    ap = argparse.ArgumentParser(usage="status.py <cycle> [--owner X]")
    ap.add_argument("cycle")
    ap.add_argument("--owner")
    a = ap.parse_args()
    if not CYCLE_RE.match(a.cycle):
        die(f"bad cycle '{a.cycle}', expected like v0.7.x")
    root = repo_root()
    owner = detect_owner(root, a.owner)
    folder = root / ".ai" / "plans" / a.cycle / owner
    if not folder.is_dir():
        die(f"cycle folder missing: {folder}")
    rel = folder.relative_to(root)
    print(f"Cycle {a.cycle} ({rel})")

    index = folder / f"{a.cycle}-plan.md"
    decisions = folder / "decisions.md"
    findings = folder / "findings.md"
    print("Files:")
    for p in (index, decisions, findings):
        print(f"  {p.name}: {'present' if p.is_file() else 'missing'}")

    parts = sorted(
        (p for p in folder.iterdir()
         if p.is_file() and PART_RE.match(p.name) and not p.name.endswith("-tracker.md")),
        key=lambda p: (num_key(PART_RE.match(p.name).group(1)), p.name),
    )
    trackers = {PART_RE.match(p.name).group(1) for p in folder.glob("*-tracker.md")
                if PART_RE.match(p.name)}

    dec_items = items(decisions)
    cite_report("Decisions", "decisions.md", dec_items, parts, DEC_PAREN_RE, DEC_BARE_RE)
    review = folder / "decisions-review.md"
    if review.is_file():
        cite_report("Rulings", "decisions-review.md", items(review), parts,
                    RUL_PAREN_RE, RUL_BARE_RE)

    print("Parts:")
    rows = []
    if index.is_file():
        text = read(index)
        m = re.search(r"^## Parts\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
        if m:
            for line in m.group(1).splitlines():
                r = ROW_RE.match(line.strip())
                if r:
                    link = LINK_RE.search(r.group(2))
                    rows.append((r.group(1), link.group(1) if link else None))
        else:
            print("  index has no ## Parts section")
    part_names = {p.name for p in parts}
    linked = {f for _, f in rows if f}
    print(f"  index rows: {len(rows)}, part files: {len(parts)}")
    for num, f in rows:
        if not f:
            print(f"  row {num}: no linked file")
        elif not (folder / f).is_file():
            print(f"  row {num}: {f} missing (waiting on decisions)")
    for name in sorted(part_names - linked):
        print(f"  not in index: {name}")
    nums = sorted({PART_RE.match(n).group(1) for n in part_names}, key=num_key)
    for n in nums:
        if n not in trackers:
            print(f"  no tracker: part {n}")

    print("Part checks:")
    quiet = True
    for p in parts:
        text = read(p)
        if not re.search(r"^### 2\.2 Gates", text, re.M):
            print(f"  {p.name}: no ### 2.2 Gates")
            quiet = False
        for i, line in outside_fences(text):
            if line.rstrip().endswith("?"):
                print(f"  {p.name}:{i}: open question? {line.strip()[:80]}")
                quiet = False
    if quiet:
        print("  ok")

    print("ATTENTION:")
    reviews = [read(p) for p in folder.glob("decisions-review*.md")]
    attention = sorted(folder.glob("ATTENTION-*.md"))
    untriaged = False
    if not attention:
        print("  none")
    for p in attention:
        bullets = [l for l in read(p).splitlines() if l.startswith("- ")]
        untagged = [l for l in bullets if not l[2:].startswith(TAGS)]
        triaged = any(p.name in t for t in reviews)
        untriaged |= not triaged
        print(f"  {p.name}: {len(bullets)} bullets, {len(untagged)} untagged, "
              f"{'triaged' if triaged else 'untriaged'}")

    if not decisions.is_file() or not dec_items:
        stage = "discuss"
    elif not parts:
        stage = "plan"
    elif untriaged:
        stage = "triage"
    else:
        stage = "run"
    print(f"Stage: {stage}")


if __name__ == "__main__":
    main()
