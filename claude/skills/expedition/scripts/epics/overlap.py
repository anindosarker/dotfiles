#!/usr/bin/env python3
"""Check mode, writes nothing: every file the named specs' milestones own (for a D id: the specs
citing it) that a milestone of a running epic also owns.

Usage: python3 -I epics/overlap.py <release> <spec numbers or D ids> [--owner X] [--root PATH]
       python3 -I epics/overlap.py <release> D<n> --files "a, b"   (decisions in files only)
       python3 -I epics/overlap.py <release>                       (decisions in files only)

A running epic is the #E<n> tag of a decisions.md card not in the Done lane; a spec's epic is
its own "- Epic: E<n>" line (epics/tag.py). Exit code 1 when a file is shared, 0 otherwise.

In a release whose decisions are files (lib/decisions.py file_form, spec 07 module 1.6.2) a
running epic is the "epic" line of a decision that is in progress, and a D id that no spec cites
is checked with the files the lead gave for it. Two more forms, both refused or a usage error on
a decisions.md board:
- D<n> --files "a, b": stores the files of a decision that no spec cites yet (it replaces the
  list; "" removes it) in status/data/status.json, runs the status rule, commits, writes the
  dashboard data, and prints "D14: blocked. Waits for E2, same file: <files>" or
  "D14: to-do, no shared file".
- no id: prints the decisions that are ready and the ones that are blocked, in the lines of the
  Epic ready message, and writes nothing.
"""
import argparse
import fcntl
import importlib.util
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
# The usage line of a board release, as it was before the file form: its usage error stays the same.
BOARD_USAGE = "epics/overlap.py <release> <spec numbers or D ids> [--owner X] [--root PATH]"
USAGE = ('epics/overlap.py <release> [<spec numbers or D ids>] [--files "a, b"] [--owner X] '
         '[--root PATH]')
TODO = "to-do"


def running_epics(tags):
    """Epics with at least one decision not in Done."""
    return sorted({t["epic"] for t in tags.values() if t["epic"] and not t["done"]})


def overlap(own, folder, items, dc=None):
    """Print files the named specs (or the specs citing the named D ids) share with
    milestones of running epics. Returns the number of shared files. dc (lib/decisions) is
    given for a release in the file form: the running epics from the decision files, and a D id
    no spec cites checked with its given files."""
    epics = own.spec_epics(folder)
    files = dict(own.spec_files(folder))
    targets = set()
    given = {}
    entries = C.load("lib/status").decision_entries(folder) if dc else {}
    for item in items:
        d = own.D_ID_RE.match(item)
        if d:
            hit = [num for num, (_, cited) in epics.items() if int(d.group(1)) in cited]
            mine = (entries.get(f"D{int(d.group(1))}") or {}).get("files") if not hit else None
            if mine:
                given[f"D{int(d.group(1))}"] = (mine, int(d.group(1)))
            elif not hit:
                print(f"{item}: no spec cites it yet, files unknown")
            targets.update(hit)
        elif own.SPEC_NUM_RE.match(item) and item in files:
            targets.add(item)
        else:
            own.die(f"'{item}' is neither a spec number with a file nor a D id")
    running = set(dc.running_epics(folder) if dc else running_epics(own.read_tags(folder)))
    owned = {}
    for num, (epic, _) in epics.items():
        if num in targets or epic not in running:
            continue
        for b in own.parse_spec(files[num]):
            for f in b["files"] or []:
                owned.setdefault(f, []).append(f"{b['name']} (E{epic})")
    shared = 0
    for num in sorted(targets, key=own.num_key):
        for b in own.parse_spec(files[num]):
            for f in b["files"] or []:
                if f in owned:
                    shared += 1
                    print(f"{num} {b['name']}: `{f}` shared with {', '.join(owned[f])}")
    for ident, (mine, _) in sorted(given.items(), key=lambda x: x[1][1]):
        for f in mine:
            if f in owned:
                shared += 1
                print(f"{ident} given files: `{f}` shared with {', '.join(owned[f])}")
    print(f"running epics: {', '.join(f'E{n}' for n in sorted(running)) or 'none'}; "
          f"checked specs: {', '.join(sorted(targets, key=own.num_key)) or 'none'}; shared files: {shared}")
    return shared


def ready_list(dc, folder):
    """The Ready and Blocked blocks of the Epic ready message (spec 09, module 1.6.2): Ready, each
    decision that is to-do with no "epic" line and no row in an epic file ("Ready: none" when
    there is none); Blocked, each blocked decision with its reason (no block when none)."""
    cards = dc.file_cards(folder)
    word, waits = dc.status_and_waits(folder, cards)
    rows = dc.row_epics(folder)
    ready = [c for c in cards if word[c["num"]] == TODO and not c["epic"] and c["num"] not in rows]
    blocked = [c for c in cards if word[c["num"]] == "blocked"]
    print("Ready:" if ready else "Ready: none")
    for c in ready:
        print(f"- D{c['num']}: {c['title']}")
    if blocked:
        print("Blocked:")
    for c in blocked:
        reason, _ = dc.blocked_reason(waits[c["num"]])
        print(f"- D{c['num']}: {c['title'].rstrip('.')}. {reason}.")


def give_files(own, dc, root, folder, release, items, text):
    """--files: store the files of one decision no spec cites, the status rule, one commit, the
    dashboard data; print the outcome line."""
    st = C.load("lib/status")
    m = own.D_ID_RE.match(items[0]) if len(items) == 1 else None
    if not m:
        C.die(f'--files takes one D id, like: epics/overlap.py {release} D14 --files "path/a.py, path/b.py"')
    num = int(m.group(1))
    ident = f"D{num}"
    files = list(dict.fromkeys(f.strip().strip("`").strip() for f in text.split(",") if f.strip().strip("`").strip()))
    with open(C.lock_file(folder), "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        cards = dc.file_cards(folder)
        if num not in {c["num"] for c in cards}:
            C.die(f"{ident} has no file in {dc.DECISIONS_DIR}/: record it first with queue/item.py {release} D")
        word = dc.rule_status(folder, cards)[num]
        if word not in (TODO, "blocked"):
            C.die(f"{ident} is {word}: --files is only for a decision that is to-do or blocked")
        rows = dc.row_epics(folder)
        if num in rows:
            C.die(f"{ident} is in E{rows[num]}: its files are in the Ownership table of plan/epics/E{rows[num]}.md")
        cites = [s for s, (_, cited) in own.spec_epics(folder).items() if num in cited]
        if cites:
            C.die(f"{ident}: its files are in spec {', '.join(cites)}; --files is only for a decision no spec cites")
        st.set_decision(folder, ident, files=files or None)
        dc.sync_files(folder)
        cards = dc.file_cards(folder)
        word, waits = dc.status_and_waits(folder, cards)
        stored = next(c["stored"] for c in cards if c["num"] == num)
        kept = (st.decision_entries(folder).get(ident) or {}).get("files")
        if (kept or []) != files or stored != word[num]:
            C.die(f"{ident}: the files or the status line were not stored as expected "
                  f"(files {kept}, status {stored}, want {files} and {word[num]}); run the call again")
        what = "files given" if files else "files removed"
        st.commit(root, folder, dc.commit_paths(folder), f"docs(plan): {release} {ident} {what}")
        fcntl.flock(lock, fcntl.LOCK_UN)
    st.write_page_data(folder)
    if word[num] == "blocked":
        reason, shared = dc.blocked_reason(waits[num])
        print(f"{ident}: blocked. {reason}: {', '.join(shared)}")
    else:
        print(f"{ident}: {word[num]}, no shared file")


def main():
    ap = argparse.ArgumentParser(usage=USAGE)
    ap.add_argument("release")
    ap.add_argument("items", nargs="*", metavar="ID")
    ap.add_argument("--files", help='file form: the files of one decision no spec cites yet, "a, b"; "" removes them')
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    items = [s.strip() for x in a.items for s in x.split(",") if s.strip()]

    def usage_error():
        ap.usage = BOARD_USAGE
        ap.error("the following arguments are required: ID")

    if not C.RELEASE_RE.match(a.release):
        if not a.items:
            usage_error()
        C.die(f"bad release '{a.release}', expected like v0.9.x")
    own = C.load("lib/ownership")
    root = own.repo_root(a.root, a.release)
    folder = own.release_folder(root, own.detect_owner(root, a.owner), a.release)
    dc = C.load("lib/decisions")
    form = dc.file_form(folder)
    if a.files is not None:
        if not form:
            dc.board_refusal(folder, "epics/overlap.py --files")
        give_files(own, dc, root, folder, a.release, items, a.files)
        return
    if not a.items:
        if not form:
            usage_error()
        ready_list(dc, folder)
        return
    sys.exit(1 if overlap(own, folder, items, dc if form else None) else 0)


if __name__ == "__main__":
    main()
