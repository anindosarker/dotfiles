#!/usr/bin/env python3
"""Read-only status report for an expedition cycle folder.

Usage: python3 -I status.py <cycle> [--owner X]

Decisions (### D<n>) and findings (### F<n>) get a derived state table from the
part files that cite them and those parts' tracker Status lines. ATTENTION items
(## A<n>) are untriaged until a decision (Source: A<n>) or a part cites them.
"""
import argparse
import collections
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

CYCLE_RE = re.compile(r"^v\d+\.\d+\.x$")
PART_RE = re.compile(r"^(\d{2}(?:\.\d+)?)-.+\.md$")
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
STATUS_VALUE_RE = re.compile(r"^(planned|running|done)\b\s*(?:\(([^)]*)\))?")
A_HEAD_RE = re.compile(r"^##\s+A(\d+)\b")
SOURCE_RE = re.compile(r"Source:\s*(A\d+(?:\s*(?:,|and)\s*A\d+)*)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.*)$")
GATES_LINE_RE = re.compile(r"^\s*-\s*Gates:")
PHASE_RE = re.compile(r"\bphase\b", re.I)
LANE_RE = re.compile(r"^Lane:\s*(workflow|agent|inline)\b")


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


def find_rules(root):
    sys.dont_write_bytecode = True
    path = Path(__file__).resolve().parent / "find_rules.py"
    spec = importlib.util.spec_from_file_location("find_rules", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.find_rules(root)


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


def tracker_status(folder, num):
    """Return (state, sha) from the tracker's Status line, or None."""
    p = folder / f"{num}-tracker.md"
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
    states = {s[0] for s in st}
    if states == {"done"}:
        shas = [s[1] for s in st if s[1]]
        return f"done ({', '.join(shas)})" if shas else "done"
    if states & {"running", "done"}:
        return "running"
    return "planned"


def state_table(label, letter, path, parts, statuses, legacy_cites):
    fmt, items = parse_items(path, letter)
    note = {"ids": "", "legacy": ", legacy numbered list", "none": ""}[fmt]
    print(f"{label}: {len(items)} in {path.name}{note}")
    if fmt == "none" and path.is_file():
        heads = sum(1 for _, l in outside_fences(read(path)) if l.startswith("### "))
        if heads:
            print(f"  legacy format, {heads} headings")
    texts = {num: read(p) for num, p in parts}
    cited = {num: cites(t, letter, legacy_cites)
             for num, t in texts.items()}
    rows = []
    for n, heading, body in items:
        citing = sorted((num for num, c in cited.items() if n in c), key=num_key)
        rows.append((f"{letter}{n}", ", ".join(citing) or "-",
                     item_state(heading, body, citing, statuses)))
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
    return items


def a_cites(text, source_only):
    nums = set()
    for m in SOURCE_RE.finditer(text):
        nums |= {int(n) for n in re.findall(r"A(\d+)", m.group(1))}
    if not source_only:
        nums |= cites(text, "A", False)
    return nums


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
    rules = find_rules(root)
    print(f"Planning rules: {', '.join(rules) if rules else 'none, bundled default'}")
    print(f"Cycle {a.cycle} ({rel})")

    index = folder / f"{a.cycle}-plan.md"
    decisions = folder / "decisions.md"
    findings = folder / "findings.md"
    print("Files:")
    for p in (index, decisions, findings):
        print(f"  {p.name}: {'present' if p.is_file() else 'missing'}")
    for name in ("decisions-review.md", "findings-review.md"):
        if (folder / name).is_file():
            print(f"  legacy: {name}")

    rows = []
    if index.is_file():
        m = re.search(r"^## Parts\s*$(.*?)(?=^## |\Z)", read(index), re.M | re.S)
        if m:
            for line in m.group(1).splitlines():
                r = ROW_RE.match(line.strip())
                if r:
                    link = LINK_RE.search(r.group(2))
                    rows.append((r.group(1), link.group(1) if link else None))
    parts = [(num, folder / f) for num, f in rows if f and (folder / f).is_file()]
    statuses = {num: tracker_status(folder, num) for num, _ in parts}

    dec_items = state_table("Decisions", "D", decisions, parts, statuses, True)
    state_table("Findings", "F", findings, parts, statuses, False)

    print("Parts:")
    if index.is_file() and not rows and "## Parts" not in read(index):
        print("  index has no ## Parts section")
    print(f"  index rows: {len(rows)}, linked part files: {len(parts)}")
    for num, f in rows:
        if not f:
            print(f"  row {num}: no linked file")
        elif not (folder / f).is_file():
            print(f"  row {num}: {f} missing (waiting on decisions)")
    linked = {p.name for _, p in parts}
    for p in sorted(folder.iterdir(), key=lambda p: p.name):
        if (p.is_file() and PART_RE.match(p.name)
                and not p.name.endswith("-tracker.md") and p.name not in linked):
            print(f"  supporting: {p.name}")
    for num, _ in parts:
        t = folder / f"{num}-tracker.md"
        if not t.is_file():
            print(f"  no tracker: part {num}")
        elif statuses[num] is None:
            print(f"  no Status line: {t.name}")

    print("Part checks:")
    quiet = True
    for _, p in parts:
        text = read(p)
        has_gates = False
        phase = None
        for i, line in outside_fences(text):
            h = HEADING_RE.match(line)
            if h:
                if phase is not None:
                    print(f"  {p.name}:{phase}: phase heading without Lane")
                    quiet = False
                title = h.group(1)
                if re.search(r"\bGates\b", title):
                    has_gates = True
                phase = i if PHASE_RE.search(title) else None
                continue
            if GATES_LINE_RE.match(line):
                has_gates = True
            if phase is not None and LANE_RE.match(line):
                phase = None
        if phase is not None:
            print(f"  {p.name}:{phase}: phase heading without Lane")
            quiet = False
        if not has_gates:
            print(f"  {p.name}: no gates")
            quiet = False
        for i, line in outside_fences(text):
            if line.rstrip().endswith("?"):
                print(f"  {p.name}:{i}: open question? {line.strip()[:80]}")
                quiet = False
    if quiet:
        print("  ok")

    print("ATTENTION:")
    attention = sorted(folder.glob("ATTENTION-*.md"))
    a_ids = []
    if not attention:
        print("  none")
    for p in attention:
        lines = [l for _, l in outside_fences(read(p))]
        ids = [int(m.group(1)) for l in lines if (m := A_HEAD_RE.match(l))]
        if ids:
            a_ids += ids
            print(f"  {p.name}: {len(ids)} items, A{min(ids)} to A{max(ids)}")
        else:
            bullets = sum(1 for l in lines if l.startswith("- "))
            print(f"  {p.name}: legacy format, {bullets} bullets")
    cited_a = a_cites(read(decisions), True) if decisions.is_file() else set()
    for _, p in parts:
        cited_a |= a_cites(read(p), False)
    uncited = sorted(set(a_ids) - cited_a)
    if a_ids:
        print(f"  untriaged: {', '.join(f'A{n}' for n in uncited) or 'none'}")
    dups = sorted(n for n, c in collections.Counter(a_ids).items() if c > 1)
    if dups:
        print(f"  duplicate numbers: {', '.join(f'A{n}' for n in dups)}")

    if not dec_items:
        stage = "discuss"
    elif not parts:
        stage = "plan"
    elif uncited:
        stage = "triage"
    else:
        stage = "run"
    print(f"Stage: {stage}")


if __name__ == "__main__":
    main()
