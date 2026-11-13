#!/usr/bin/env python3
"""Move the free-standing fix milestones of an older release into epics: every
run/trackers/fix-<slug>-tracker.md (a tracker and a "fix <name>" grid row, no spec, no epic)
becomes a follow-up spec with one milestone inside an epic.

Usage: python3 -I migrate/fixes.py <release> [--dry-run] [--map <slug>=E<n>:<NN>]...
       [--owner X] [--root PATH]

Epic and parent spec of each fix, from the first evidence that decides:
1. The tracker names one spec: a spec or milestone under its "Depends on:" line, or "spec NN"
   (or a plan/specs/NN- path) in its text. The parent is that spec, the epic its Epic line.
2. Its cited ids (the title's "(Q3, D7)") lead to one spec: a spec citing a cited D id, a
   cited Q id, or the decision a cited card is tagged with (#D<n>). Else, when those decisions
   are all tagged with one epic: that epic, the parent its spec sharing a file with the fix,
   else its highest-numbered spec.
3. The grid: the epic with rows in the fix row's sprint column (its Starts at or before that
   column, or its first row there when it has no Starts value, and its last row at or after
   it; with several, the one with the most rows in that column). The parent is its
   highest-numbered spec with a row in that column. Always marked "unsure".
--map <slug>=E<n>:<NN> sets the epic and the parent spec of one fix and skips the rules.

Per fix: the next free NN.M after the parent spec; plan/specs/NN.M-<slug>.md written from the
tracker (title, the cited ids as citations, an Acceptance line pointing at the tracker's
recorded checks, a "### Milestone:" block with the tracker's Files owned and Depends on,
"Review: none", one task line, and "- Starts: S<n>" when the row is not finished, so it keeps
its column); "- Epic: E<n>" under its title; the Deliverables row; when the epic has an epic
file, the spec on its "Specs:" line and its Ownership row (the row of a cited decision, or of
the decision a cited card is tagged with, that has an empty Spec cell is filled, else a row
with an empty Decision cell is added). The
tracker moves by git mv to run/trackers/NN.M-<slug>-tracker.md, its first line and Status
kept. The grid row "fix <name>" becomes "E<n> NN.M <name>" with its cells unchanged; the
milestone name is the tracker title without the cited ids (kept with them when the shorter
name is taken). References to the old tracker path in handoffs, epic files, queue.md, specs
and trackers are rewritten; a `fix-<slug>` mention in queue.md or an epic file becomes
"spec NN.M". Then the refresh chain (lib/grid.py refresh) and sprints/swimlanes.py run.

--dry-run prints one line per fix (slug, epic, parent spec, new spec number, evidence, "unsure"
when rule 3 decided or a tie was broken) and writes nothing. Commits nothing. A second run
changes nothing. Every other script refuses a folder that still has fix trackers, with one
line naming this script.
"""
import argparse
import collections
import importlib.util
import re
import subprocess
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
NUM = r"\d{2}(?:\.\d+)?"
SLUG_RE = re.compile(r"^fix-(.+)-tracker\.md$")
IDS_TAIL_RE = re.compile(r"\s*\(([QD]\d+(?:\s*,\s*[QD]\d+)*)\)\s*$")
SPEC_MENTION_RE = re.compile(r"\b[Ss]pecs?\s+(" + NUM + r"(?:\s*(?:,|and|or)\s*" + NUM + r")*)\b")
SPEC_PATH_RE = re.compile(r"plan/specs/(" + NUM + r")-")
MAP_RE = re.compile(r"^([a-z0-9]+(?:-[a-z0-9]+)*)=E(\d+):(" + NUM + r")$")


die = C.die


def load(name):
    """The scripts this one used under their old names: ownership, board, migrate_queue."""
    return C.load({"ownership": "lib/ownership", "board": "lib/board", "migrate_queue": "migrate/queue"}[name])


def parse_tracker(own, path):
    """{slug, path, text, name, title, ids, files_raw, files, deps}."""
    text = own.read(path)
    lines = text.splitlines()
    name = re.sub(r"^#\s*", "", lines[0] if lines else "").strip()
    name = re.sub(r",\s*tracker\s*$", "", name).strip()
    m = IDS_TAIL_RE.search(name)
    ids = [s.strip() for s in m.group(1).split(",")] if m else []
    title = name[:m.start()].strip() if m else name
    files_raw, deps = "none", "none"
    for line in lines[1:]:
        if line.startswith("## "):
            break
        f = own.FIELD_RE.match(line)
        if f and f.group(1) == "Files owned":
            files_raw = f.group(2) or "none"
        elif f and f.group(1) == "Depends on":
            deps = f.group(2) or "none"
    return {"slug": SLUG_RE.match(path.name).group(1), "path": path, "text": text, "name": name,
            "title": title, "ids": ids, "files_raw": files_raw,
            "files": own.split_files(files_raw), "deps": deps}


def grid_rows(own, folder):
    """[(label, cells)] of status/sprints.md."""
    return own.grid(folder)[1]


def first_col(cells):
    return next((i + 1 for i, c in enumerate(cells) if c), None)


class Facts:
    def __init__(self, own, bd, folder):
        self.own, self.folder = own, folder
        self.files = dict(own.spec_files(folder))
        self.epics = own.spec_epics(folder)
        self.blocks = {num: own.parse_spec(p) for num, p in self.files.items()}
        self.ms_spec = {b["name"]: num for num, bl in self.blocks.items() for b in bl}
        self.tags = own.read_tags(folder)
        self.cards = {c["num"]: c for c in bd.parse(own.read(folder / own.QUEUE_MD))["cards"]}
        self.qcites = {num: set(int(n) for n in re.findall(r"\(\s*Q(\d+)", own.read(p)))
                       for num, p in self.files.items()}
        self.rows = grid_rows(own, folder)
        self.starts = own.epic_starts(folder)

    def epic_of(self, num):
        return self.epics.get(num, (None, []))[0]

    def specs_of_epic(self, e):
        return sorted((n for n, (x, _) in self.epics.items() if x == e), key=self.own.num_key)

    def spec_files_owned(self, num):
        return {f for b in self.blocks.get(num, []) for f in b["files"] or []}


def by_text(f, fx):
    """Rule 1: specs the tracker names."""
    own = f.own
    found = set()
    deps = fx["deps"]
    if deps and deps.lower().rstrip(".") != "none":
        names, _ = own.resolve_deps(deps, list(f.ms_spec), {n: [b["name"] for b in bl]
                                                          for n, bl in f.blocks.items()})
        found |= {f.ms_spec[n] for n in names}
    body = "\n".join(fx["text"].splitlines()[1:])
    for m in SPEC_MENTION_RE.finditer(body):
        found |= {n for n in re.findall(NUM, m.group(1)) if n in f.files}
    found |= {n for n in SPEC_PATH_RE.findall(body) if n in f.files}
    return sorted(found, key=own.num_key)


def by_cites(f, fx):
    """Rule 2: (specs, decisions) the cited ids lead to."""
    ds = {int(i[1:]) for i in fx["ids"] if i.startswith("D")}
    qs = {int(i[1:]) for i in fx["ids"] if i.startswith("Q")}
    for q in qs:
        c = f.cards.get(q)
        if c and c.get("d"):
            ds.add(c["d"])
    specs = {n for n, (_, cited) in f.epics.items() if ds & set(cited)}
    specs |= {n for n, cited in f.qcites.items() if qs & cited}
    return sorted(specs, key=f.own.num_key), sorted(ds)


def by_grid(f, label):
    """Rule 3: (epic, parent, tie) from the fix row's column."""
    cells = dict(f.rows).get(label)
    col = first_col(cells or [])
    if col is None:
        return None, None, False
    span = collections.defaultdict(list)
    in_col = collections.Counter()
    for lab, c in f.rows:
        m = re.match(r"^E(\d+)\s+(" + NUM + r")\s", lab)
        at = first_col(c)
        if m and at:
            e = int(m.group(1))
            span[e].append(at)
            if at == col:
                in_col[e] += 1
    cands = []
    for e, cols in span.items():
        s = f.own.SPRINT_VALUE_RE.match(f.starts.get(e) or "")
        start = int(s.group(1)) if s else min(cols)
        if start <= col <= max(cols):
            cands.append(e)
    if not cands:
        return None, None, False
    cands.sort(key=lambda e: (-in_col[e], e))
    tie = len(cands) > 1 and in_col[cands[0]] == in_col[cands[1]]
    e = cands[0]
    at_col = [m.group(1) for lab, c in f.rows
              if (m := re.match(r"^E" + str(e) + r"\s+(" + NUM + r")\s", lab)) and first_col(c) == col]
    at_col = [n for n in at_col if n in f.files]
    parent = max(at_col, key=f.own.num_key) if at_col else (f.specs_of_epic(e) or [None])[-1]
    return e, parent, tie


def choose(f, fx, label, mapped):
    """(epic, parent, evidence, unsure)."""
    if fx["slug"] in mapped:
        e, p = mapped[fx["slug"]]
        return e, p, "--map", False
    named = [n for n in by_text(f, fx) if f.epic_of(n)]
    if len(named) == 1:
        return f.epic_of(named[0]), named[0], f"tracker names spec {named[0]}", False
    note = f"tracker names specs {', '.join(named)}; " if named else ""
    specs, ds = by_cites(f, fx)
    specs = [n for n in specs if f.epic_of(n)]
    if len(specs) == 1:
        return f.epic_of(specs[0]), specs[0], note + f"cited ids lead to spec {specs[0]}", False
    epics = {f.tags[d]["epic"] for d in ds if d in f.tags and f.tags[d]["epic"]}
    if len(epics) == 1:
        e = epics.pop()
        own_specs = f.specs_of_epic(e)
        sharing = [n for n in own_specs if f.spec_files_owned(n) & set(fx["files"])]
        if len(sharing) == 1:
            parent, why = sharing[0], "its spec sharing a file"
        else:
            parent, why = (own_specs or [None])[-1], "its last spec"
        if parent:
            dl = ", ".join(f"D{d}" for d in ds)
            return e, parent, note + f"cites {dl} of E{e}; parent {why}", False
    if specs:
        note += f"cited ids lead to specs {', '.join(specs)}; "
    e, parent, tie = by_grid(f, label)
    if e is None:
        return None, None, note + "no epic covers its sprint column", True
    return e, parent, note + f"grid column, E{e}" + (" (tie)" if tie else ""), True


def next_number(f, parent, taken):
    used = {n for n in list(f.files) + list(taken) if re.fullmatch(re.escape(parent) + r"\.\d+", n)}
    m = max((int(n.split(".")[-1]) for n in used), default=0)
    return f"{parent}.{m + 1}"


def spec_text(num, title, epic, parent, slug, ids, name, files_raw, deps, tracker_rel, status, starts):
    cite = " ".join(f"({i})" for i in ids)
    lines = [f"# {num}: {title}", f"- Epic: E{epic}", "",
             f"Follow-up of spec {parent}" + (f" {cite}" if cite else "")
             + f", from the free-standing fix milestone `fix-{slug}` of this release.", "",
             f"- Acceptance: the checks recorded in `{tracker_rel}` pass" + (f"; tracker Status: {status}" if status else "") + ".",
             "", "## 2. Instructions for AI", "", "### 2.1 Milestones", "",
             f"### Milestone: {name}", "",
             f"- Files owned: {files_raw}", f"- Depends on: {deps}", "- Review: none"]
    if starts:
        lines.append(f"- Starts: S{starts}")
    lines.append(f"- Task 1: {title}" + (f" {cite}" if cite else "") + ". Checks: the check lines of the tracker.")
    return "\n".join(lines) + "\n"


def add_to_epic_file(own, path, num, name, files, cited, sprint):
    """Specs line and Ownership row of the follow-up spec; returns the new text."""
    text = own.read(path)
    m = own.SPECS_LINE_RE.search(text)
    have = [s.strip() for s in (m.group(1) if m else "").split(",") if s.strip()]
    if num not in have:
        have = sorted(have + [num], key=lambda s: own.num_key(s) if re.fullmatch(NUM, s) else (2,))
        text = own.set_field(text, "Specs", ", ".join(have))
    rows, err = own.read_table(text)
    if err or rows is None:
        return text
    if any(r["spec"] == num for r in rows):
        return text
    hit = [r for r in rows if r["decision"] in cited and not r["spec"]]
    new = {"files": files, "spec": num, "milestone": name, "sprint": sprint}
    if hit:
        for r in hit:
            r.update(new)
    else:
        rows.append(dict(decision=None, title="", **new))
    return own.put_table(text, rows)


def rewrite_refs(text, old_name, new_rel, slug, num, tokens):
    text = text.replace(f"run/trackers/{old_name}", new_rel).replace(old_name, Path(new_rel).name)
    if tokens:
        text = re.sub(r"`fix-" + re.escape(slug) + r"`", f"spec {num}", text)
        text = re.sub(r"(?<![\w/-])fix-" + re.escape(slug) + r"(?![\w-])", f"spec {num}", text)
    return text


def main():
    ap = argparse.ArgumentParser(usage="migrate/fixes.py <release> [--dry-run] [--map <slug>=E<n>:<NN>]... "
                                       "[--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--map", action="append", default=[])
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    own = load("ownership")
    bd = load("board")
    root = own.repo_root(a.root, a.release)
    folder = root / ".ai" / "plans" / a.release / own.detect_owner(root, a.owner)
    if not folder.is_dir():
        die(f"release folder missing: {folder}")
    if not (folder / "plan").is_dir():
        die(f"{folder} has the old layout (no plan/): run python3 -I {HERE / 'layout.py'} {a.release}")
    old = load("migrate_queue").refusal(folder, a.release) or C.load("migrate/decisions").refusal(folder, a.release)
    if old:
        die(old)
    if (folder / own.LEGACY_OWNERSHIP_MD).is_file():
        die(f"{folder} still has {own.LEGACY_OWNERSHIP_MD}: run python3 -I {HERE / 'epics.py'} {a.release}")
    fixes = [parse_tracker(own, p) for p in own.legacy_fixes(folder)]
    if not fixes:
        print("no free-standing fix trackers; nothing to change")
        return
    f = Facts(own, bd, folder)
    slugs = {fx["slug"] for fx in fixes}
    mapped = {}
    for m in a.map:
        g = MAP_RE.match(m)
        if not g:
            die(f"bad --map '{m}', expected like docs-build-memory=E12:47")
        if g.group(1) not in slugs:
            die(f"--map {m}: no run/trackers/fix-{g.group(1)}-tracker.md")
        if g.group(3) not in f.files:
            die(f"--map {m}: spec {g.group(3)} has no file in {own.SPECS_DIR}")
        mapped[g.group(1)] = (int(g.group(2)), g.group(3))
    labels = {sp_name: lab for lab, _ in f.rows
              if (sp_name := re.sub(r"^fix\s+", "", lab)) and lab.startswith("fix ")}
    names = set(f.ms_spec)
    plan = []
    taken = []
    unsure = 0
    for fx in fixes:
        label = labels.get(fx["name"])
        e, parent, why, doubt = choose(f, fx, label, mapped)
        if e is None or parent is None:
            print(f"fix-{fx['slug']}: no epic found ({why}); pass --map {fx['slug']}=E<n>:<NN>")
            unsure += 1
            plan.append(None)
            continue
        num = next_number(f, parent, taken)
        taken.append(num)
        name = fx["title"] if fx["title"] not in names else fx["name"]
        names.add(name)
        unsure += doubt
        plan.append((fx, e, parent, num, name, label))
        cells = dict(f.rows).get(label) or []
        at = first_col(cells)
        mark = cells[at - 1] if at else "no row"
        print(f"fix-{fx['slug']} -> E{e}, parent {parent}, spec {num} '{name}', "
              f"row S{at} {mark}; {why}" + ("; unsure" if doubt else ""))
    print(f"{len(fixes)} fixes, {unsure} unsure")
    if any(p is None for p in plan):
        die("a fix has no epic: pass --map for it; nothing written")
    if a.dry_run:
        print("dry run; nothing written")
        return

    plan_md = folder / f"{a.release}-plan.md"
    plan_text = own.read(plan_md)
    grid_path = folder / own.SPRINTS_MD
    grid_text = own.read(grid_path)
    edits = {}
    for fx, e, parent, num, name, label in plan:
        cells = dict(f.rows).get(label) or []
        at = first_col(cells)
        finished = any(c in ("[x]", "[!]") for c in cells)
        new_tracker = folder / own.TRACKERS_DIR / f"{num}-{fx['slug']}-tracker.md"
        tracker_rel = new_tracker.relative_to(folder).as_posix()
        status = re.search(r"^Status:\s*(.*?)\s*$", fx["text"], re.M)
        spec_path = folder / own.SPECS_DIR / f"{num}-{fx['slug']}.md"
        if spec_path.exists() or new_tracker.exists():
            die(f"{spec_path.name} or {new_tracker.name} exists already")
        spec_path.write_text(spec_text(num, fx["title"], e, parent, fx["slug"], fx["ids"], name,
                                       fx["files_raw"], fx["deps"], tracker_rel,
                                       status.group(1) if status else "",
                                       None if finished or not at else at), encoding="utf-8")
        r = subprocess.run(["git", "-C", str(root), "mv", str(fx["path"]), str(new_tracker)],
                           capture_output=True, text=True)
        if r.returncode:
            fx["path"].rename(new_tracker)
        row = f"| {num} | [{fx['title']}](plan/specs/{spec_path.name}) | E{e} | {fx['title']} |"
        plan_text = C.insert_row(plan_text, num, row)
        if label:
            grid_text = re.sub(r"^\|\s*" + re.escape(label) + r"\s*\|",
                               lambda _: f"| E{e} {num} {name} |", grid_text, count=1, flags=re.M)
        epic_file = own.epic_path(folder, e)
        if epic_file.is_file():
            edits[epic_file] = add_to_epic_file(own, epic_file, num, name, fx["files"],
                                                set(by_cites(f, fx)[1]), f"S{at}" if at else "")
            epic_file.write_text(edits[epic_file], encoding="utf-8")
        refs = [folder / own.QUEUE_MD] + sorted((folder / own.EPICS_DIR).glob("*.md")) \
            + sorted((folder / own.HANDOFFS_DIR).glob("*.md")) + sorted((folder / own.SPECS_DIR).glob("*.md")) \
            + sorted((folder / own.TRACKERS_DIR).glob("*.md"))
        for p in refs:
            text = own.read(p)
            tokens = p.name == own.QUEUE_MD or p.parent.name == "epics"
            new = rewrite_refs(text, fx["path"].name, tracker_rel, fx["slug"], num, tokens)
            if new != text:
                p.write_text(new, encoding="utf-8")
        print(f"fix-{fx['slug']}: {spec_path.relative_to(folder)}, {tracker_rel}")
    plan_md.write_text(plan_text, encoding="utf-8")
    grid_path.write_text(grid_text, encoding="utf-8")
    C.load("lib/grid").refresh(folder, a.release)
    C.load("sprints/swimlanes").write(folder, a.release)
    print(f"{len(plan)} fixes moved into epics; nothing committed")


if __name__ == "__main__":
    main()
