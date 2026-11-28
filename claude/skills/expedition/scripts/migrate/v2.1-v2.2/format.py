#!/usr/bin/env python3
"""Move a release from format 2.1 to 2.2: the status words of the queue item and of epics, specs,
milestones and tasks, the epic file without its decisions and specs lines, and no status/sprints.md.

Usage: python3 -I migrate/v2.1-v2.2/format.py <release> [--check] [--owner X] [--root PATH]

Its first line, on stderr, tells the session that runs it to read the skill again: the commands
of a release of format 2.2 store and print other words and read no grid file.

In the release folder, in one run and one commit ("docs(plan): <release> moved to format 2.2"):
- Each item file queue/Q<n>-<slug>.md: "status: open" becomes to-do, later backlog, dropped
  archived, decided done (decision and option kept), autofix done with "decider: agent"
  (lib/queue.py move_status). No other item gets a decider line: the files of format 2.1 do not
  say whether the owner or the lead made a call. An item with no status line keeps none.
- status/data/status.json: "format" 2.2; "launched": true on each milestone that a
  "docs(plan): <release> <milestone> launch" commit names in the history of status/sprints.md,
  and on each one that is in progress or done; then the status chain once (lib/status.py sync:
  the words to-do and archived, the "statuses" list of format 2.2, the reason and decider of each
  epic, the decider of each spec, milestone and task, the blocked check of the queue, the page
  data). The epic status of format 2.2 is worked out there (lib/status.py epic_state); a status
  the chain changes beyond the two renamed words is printed.
- The "status:" line of each task, spec and epic file: to-do for not started, archived for skipped.
- plan/epics/E<n>.md: the "decisions:" and "specs:" lines removed. Before that, a decision or a
  spec the lines name and no Ownership table row has gets a row (lib/ownership.py build_table),
  with one printed line per row added.
- status/sprints.md removed, after a check that the sprint and the mark of each of its rows equal
  the status file. A difference stops the run before it writes anything and names the rows.
- <release>-plan.md: the link to status/sprints.md in the lines above its first "## " heading
  removed; the rest of the line stays.

Prints one line per file it changes and the counts: queue items per old and new status, decision
cards, epics, specs, milestones and tasks before and after, statuses changed in the status file,
epic files changed, whether the grid file was removed. A count that differs, or a decisions.md that
changed, stops it before the commit and restores the files from git. --check prints the files and
the counts it can know before the status chain runs, and writes nothing.

Refuses, writing nothing: a release that is not in format 2.1 (for 2.0 it names migrate/v2.0-v2.1,
for 1.0 migrate/v1.0-v2.0, for 2.2 or higher it says there is nothing to change); an uncommitted
change in a file it rewrites; an item file with a status that is not a word of format 2.1; an
epic file whose Ownership table cannot be read.
"""
import argparse
import contextlib
import fcntl
import importlib.util
import io
import json
import re
import subprocess
import sys
from pathlib import Path


def _common():
    name = "expedition_lib_common"
    if name not in sys.modules:
        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent.parent.parent / "lib" / "common.py")
        sys.modules[name] = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sys.modules[name])
    return sys.modules[name]


C = _common()
FROM, TO = (2, 1), "2.2"
REREAD = ("The expedition skill stores the status words of format 2.2 and reads no status/sprints.md in a "
          "release of that format: read SKILL.md and scripts/migrate/v2.1-v2.2/README.md again before the next command.")
GRID = "status/sprints.md"
EPIC_LINE_RE = re.compile(r"^(decisions|specs):", re.I)
SPEC_NUM_RE = re.compile(r"\b\d{2}(?:\.\d+)?\b")
GRID_LINK_RE = re.compile(r"[ \t]*Sprints:[ \t]*\[[^\]]*\]\(status/sprints\.md\)\.?|\[[^\]]*\]\(status/sprints\.md\)")
FRONT_STATUS_RE = re.compile(r"^status:[ \t]*(.*?)[ \t]*$")


def plural(n, word):
    return f"{n} {word}" + ("" if n == 1 else "s")


def tally(words):
    """"open 2, decided 4" of a list of words, in first-seen order."""
    out = {}
    for w in words:
        out[w] = out.get(w, 0) + 1
    return ", ".join(f"{w or '(no status line)'} {n}" for w, n in out.items()) or "none"


def head_end(lines):
    """The index of the first "## " heading line, or the line count."""
    return next((i for i, l in enumerate(lines) if l.startswith("## ")), len(lines))


def front_span(lines):
    """(first, last) line indexes inside the front matter block; None when the file has none."""
    if not lines or lines[0].strip() != "---":
        return None
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    return (1, end) if end else None


def new_status_line(text, words):
    """text with its front matter "status:" line in the words of format 2.2; text itself when
    there is nothing to change."""
    lines = text.split("\n")
    span = front_span(lines)
    if not span:
        return text
    for i in range(*span):
        m = FRONT_STATUS_RE.match(lines[i])
        if m and m.group(1) in words:
            lines[i] = f"status: {words[m.group(1)]}"
    return "\n".join(lines)


# --- the queue ---

def item_plan(q, folder):
    """[(path, old status, new status, new text)] of every item file; dies on a word that is not
    one of format 2.1."""
    out = []
    for it in q.items(folder):
        old = it["status"]
        if old and old not in q.STATUSES:
            C.die(f"{it['path']}: status '{old}' is not one of {', '.join(q.STATUSES)}: "
                  "set a word of format 2.1, commit, then run again; nothing written")
        if not old:
            out.append((it["path"], old, old, it["text"]))
            continue
        # decided is the one word of format 2.1 no command takes: done, its decision line kept
        new = "done" if old == "decided" else q.move_status(old, new=True)
        fields = {"status": new}
        if old == "autofix":
            fields["decider"] = "agent"
        out.append((it["path"], old, new, q.set_front(it["text"], **fields)))
    return out


# --- the grid file ---

def grid_differences(o, st, data, folder):
    """The rows of status/sprints.md whose sprint or mark differs from the status file, and the
    milestones of an epic with a sprint in the status file and no row, as printable lines."""
    _, rows = o.grid(folder)
    by_label = {f"{m['epic']} {m['spec']} {m['name']}": m for m in data["milestones"] if m.get("epic")}
    out, seen = [], set()
    for label, cells in rows:
        at = next((i + 1 for i, c in enumerate(cells) if c), None)
        m = by_label.get(label)
        if m is None:
            out.append(f"row '{label}': no milestone of the status file has it")
            continue
        seen.add(label)
        want = (m.get("sprint") or "", st.MARKS.get(m["status"], "?"))
        have = (f"S{at}" if at else "", cells[at - 1] if at else "")
        if have != want:
            out.append(f"row '{label}': {have[0] or 'no sprint'} {have[1]} in {GRID}, "
                       f"{want[0] or 'no sprint'} {want[1]} in {st.FILE}")
    for label, m in by_label.items():
        if label not in seen and m.get("sprint"):
            out.append(f"milestone '{label}': {m['sprint']} in {st.FILE}, no row in {GRID}")
    return out


# --- the epic files ---

def epic_plan(o, folder):
    """[(path, new text, [added row labels])] of each epic file the migration changes; dies on a
    table it cannot read."""
    out, comp, gcols = [], None, None
    for n in o.epic_numbers(folder):
        p = o.epic_path(folder, n)
        text = C.read(p)
        rows, err = o.read_table(text)
        if err:
            C.die(f"{p}: {err}: fix the table, commit, then run again; nothing written")
        rows = rows or []
        named_d = o.epic_decisions(text)
        m = o.SPECS_LINE_RE.search(text)
        named_s = list(dict.fromkeys(SPEC_NUM_RE.findall(re.sub(r"\([^)]*\)", "", m.group(1))))) if m else []
        have_d = {r["decision"] for r in rows if r["decision"] is not None}
        have_s = {r["spec"] for r in rows if r["spec"]}
        miss_d = [d for d in named_d if d not in have_d]
        miss_s = [s for s in named_s if s not in have_s]
        added = []
        if miss_d or miss_s:
            if comp is None:
                comp = o.compute(folder)
                if comp["errors"]:
                    o.print_errors(comp["errors"])
                gcols = o.grid_columns(folder)
            known = dict(o.spec_files(folder))
            specs = [s for s in dict.fromkeys(named_s + sorted(have_s, key=o.num_key)) if s in known]
            keys = set()
            for d in miss_d:
                new = [r for r in o.build_table(folder, [d], specs, [], comp, gcols, from_specs=True)
                       if r["decision"] == d]
                for r in new:
                    if (r["decision"], r["spec"]) not in keys:
                        keys.add((r["decision"], r["spec"]))
                        added.append(r)
            for s in miss_s:
                if s not in known:
                    added.append({"decision": None, "title": "", "files": [], "spec": s, "milestone": "", "sprint": ""})
                    continue
                for r in o.build_table(folder, named_d + sorted(have_d), [s], [], comp, gcols, from_specs=True):
                    if r["spec"] == s and (r["decision"], r["spec"]) not in keys:
                        keys.add((r["decision"], r["spec"]))
                        added.append(r)
        new = add_rows(o, text, added)
        lines = new.split("\n")
        stop = head_end(lines)
        lines = [l for i, l in enumerate(lines) if not (i < stop and EPIC_LINE_RE.match(l))]
        new = "\n".join(lines)
        if new != text:
            out.append((p, new, [o.row_label(r) for r in added]))
    return out


def add_rows(o, text, rows):
    """text with the rows put after the last line of its Ownership table, each row as
    lib/ownership.py renders it; the rows above keep every byte. A file with no table gets one."""
    if not rows:
        return text
    lines = text.split("\n")
    span = o.section(lines, o.OWN_HEAD)
    tl = [i for i in range(span[0] + 1, span[1]) if lines[i].strip().startswith("|")] if span else []
    if not tl:
        return o.put_table(text, rows)
    return "\n".join(lines[:tl[-1] + 1] + o.render_table(rows)[2:] + lines[tl[-1] + 1:])


# --- the plan file ---

def plan_text(folder, release):
    """(path, new text) of the plan file without its link to status/sprints.md in the lines above
    its first "## " heading; None when there is nothing to change."""
    p = folder / f"{release}-plan.md"
    if not p.is_file():
        return None
    lines = C.read(p).split("\n")
    stop = head_end(lines)
    new = [GRID_LINK_RE.sub("", l) if i < stop else l for i, l in enumerate(lines)]
    return (p, "\n".join(new)) if new != lines else None


# --- the counts ---

def counts(q, st, dec, folder):
    """(queue statuses, decision cards, {kind: entry count}) as the stores read them now."""
    data = st.load(folder)
    return ([it["status"] for it in q.items(folder)], len(dec.read_cards(folder)["cards"]),
            {k: len(data.get(k) or []) for k in ("epics", "specs", "milestones", "tasks")})


def count_line(before, after):
    (qb, db, kb), (qa, da, ka) = before, after
    kinds = "; ".join(f"{k} {kb[k]} before, {ka[k]} after" for k in kb)
    return (f"queue items {len(qb)} before ({tally(qb)}), {len(qa)} after ({tally(qa)}); "
            f"decision cards {db} before, {da} after; {kinds}")


def commit(root, paths, message):
    """One commit of paths, a removed file among them (lib/common.py commit names only files that
    exist, so it cannot commit the removal of status/sprints.md); pushed as lib/common.py pushes."""
    repo, paths = C.plan_repo(root, paths)
    git = lambda *args: subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    r = git("add", "-A", "--", *paths)
    if r.returncode:
        C.die(f"git add failed: {(r.stderr or r.stdout).strip()}")
    r = git("commit", "-q", "-m", message, "--only", "--", *paths)
    if r.returncode:
        C.die(f"git commit failed: {(r.stderr or r.stdout).strip()}")
    C.push_plans(root, repo)


def main():
    ap = argparse.ArgumentParser(usage="migrate/v2.1-v2.2/format.py <release> [--check] [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("--check", action="store_true", help="print the files and the counts; write nothing")
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    print(REREAD, file=sys.stderr)
    if not C.RELEASE_RE.match(a.release):
        C.die(f"bad release '{a.release}', expected like v0.9.x")
    root, folder = C.find_folder(a.release, a.owner, a.root)
    st, q, o, dec = C.load("lib/status"), C.load("lib/queue"), C.load("lib/ownership"), C.load("lib/decisions")
    fmt = st.release_format(folder)
    v = st.version(fmt)
    if v < (2, 0):
        C.die(f"{a.release} is in format {fmt}: run migrate/v1.0-v2.0/format.py first (scripts/migrate/v1.0-v2.0/README.md)")
    if v < FROM:
        C.die(f"{a.release} is in format {fmt}: run migrate/v2.0-v2.1/format.py first (scripts/migrate/v2.0-v2.1/README.md)")
    if v > FROM:
        C.die(f"{a.release} is in format {fmt}, not 2.1: it has the words of format 2.2 already; nothing to change")
    real = folder.resolve()
    git = lambda *args: subprocess.run(["git", "-C", str(real), *args], capture_output=True, text=True)
    plan_md = f"{a.release}-plan.md"
    rewrites = [C.QUEUE_MD, q.QUEUE_DIR, "plan", plan_md, GRID, st.FILE]
    r = git("status", "--porcelain", "--", *rewrites)
    if r.returncode:
        C.die(f"{folder} is not in a git repository: {(r.stderr or r.stdout).strip()}")
    if r.stdout.strip():
        first = r.stdout.splitlines()[0][3:]
        C.die(f"{first} has uncommitted changes ({plural(len(r.stdout.splitlines()), 'path')} in all): "
              "commit them first; nothing written")

    lock = None if a.check else open(C.lock_file(folder), "a")
    if lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
    data = st.load(folder)
    before = counts(q, st, dec, folder)
    decisions_before = C.read(dec.path_of(folder)) if dec.path_of(folder).is_file() else None

    items = item_plan(q, folder)
    grid_on = (folder / GRID).is_file()
    differ = grid_differences(o, st, data, folder) if grid_on else []
    if differ:
        for line in differ:
            print(line)
        C.die(f"{GRID} and {st.FILE} differ in {plural(len(differ), 'row')}: run sprints/refresh.py {a.release}, "
              "commit, then run again; nothing written")
    keys = o.launched_keys(folder) or set()
    launched = [m["id"] for m in data["milestones"] if m["id"] in keys or m["status"] in ("in progress", "done")]
    epics = epic_plan(o, folder)
    words = st.WORDS_22
    plain = []  # the task and spec files whose status line changes
    for p in sorted((folder / "plan" / "specs").rglob("*.md")) if (folder / "plan" / "specs").is_dir() else []:
        text = C.read(p)
        new = new_status_line(text, words)
        if new != text:
            plain.append((p, new))
    epics = [(p, new_status_line(t, words), added) for p, t, added in epics]
    have = {p for p, _, _ in epics}
    for n in o.epic_numbers(folder):
        p = o.epic_path(folder, n)
        if p not in have:
            new = new_status_line(C.read(p), words)
            if new != C.read(p):
                epics.append((p, new, []))
    plan = plan_text(folder, a.release)
    renamed = sum(1 for k in st.KINDS for e in data.get(k) or [] if e.get("status") in words)

    pre = "would write " if a.check else ""
    rel = lambda p: p.relative_to(folder).as_posix()
    for p, old, new, text in items:
        if old:
            print(f"{pre}{rel(p)}: {old} to {new}" + (", decider agent" if old == "autofix" else ""))
    for p, _, added in epics:
        print(f"{pre}{rel(p)}: no decisions and specs lines" + (f", {plural(len(added), 'row')} added" if added else ""))
        for label in added:
            print(f"{pre}{rel(p)}: row added for {label}")
    for p, _ in plain:
        print(f"{pre}{rel(p)}: status line in the words of format 2.2")
    if plan:
        print(f"{pre}{rel(plan[0])}: link to {GRID} removed")
    print(f"{'would remove ' if a.check else 'remove '}{GRID}" if grid_on else f"{GRID}: none")
    print(f"{pre}{st.FILE}: format {TO}, {plural(renamed, 'word')} renamed (not started to to-do, skipped to archived), "
          f"launched true on {plural(len(launched), 'milestone')}")
    if a.check:
        print(f"queue items {len(before[0])} ({tally(before[0])}) become ({tally(n for _, _, n, _ in items)}); "
              f"decision cards {before[1]}; " + "; ".join(f"{k} {n}" for k, n in before[2].items()))
        print(f"epic files changed {len(epics)}; grid file removed: {'yes' if grid_on else 'none to remove'}")
        print("check; nothing written. The run then rebuilds the status file and prints each status it changes")
        return

    for p, _, _, text in items:
        q.write_item(p, text)
    for p, text, _ in epics:
        p.write_text(text, encoding="utf-8")
    for p, text in plain:
        p.write_text(text, encoding="utf-8")
    if plan:
        plan[0].write_text(plan[1], encoding="utf-8")
    if grid_on:
        (folder / GRID).unlink()
    old_words = {e["id"]: e["status"] for k in st.KINDS for e in data.get(k) or [] if "id" in e}
    old_sprint = {m["id"]: m.get("sprint") or "" for m in data["milestones"]}
    for m in data["milestones"]:
        m["launched"] = m["id"] in launched
    data["format"] = TO
    st.write_json(st.path(folder), st.dump(data))
    with contextlib.redirect_stdout(io.StringIO()):
        new_data = st.sync(folder, a.release)
        C.load("sprints/swimlanes").write(folder, a.release, quiet=True)
    after = counts(q, st, dec, folder)
    print(count_line(before, after))
    changed = [f"{e['id']} from {st.say(folder, old_words[e['id']])} to {st.say(folder, e['status'])}"
               for k in st.KINDS for e in new_data.get(k) or []
               if e.get("id") in old_words and old_words[e["id"]] != e.get("status")]
    moved = [f"{m['id']} from {old_sprint[m['id']] or 'no sprint'} to {m.get('sprint') or 'no sprint'}"
             for m in new_data["milestones"] if m["id"] in old_sprint and old_sprint[m["id"]] != (m.get("sprint") or "")]
    print(f"statuses changed in the status file: {len(changed)}" + (f" ({'; '.join(changed)})" if changed else "")
          + f"; {plural(renamed, 'word')} renamed")
    if moved:
        print(f"sprints changed in the status file: {'; '.join(moved)}")
    print(f"epic files changed {len(epics)}; grid file removed: {'yes' if grid_on else 'none to remove'}")
    want = sorted(n for _, _, n, _ in items)
    stop = []
    if (len(before[0]), before[1], before[2]) != (len(after[0]), after[1], after[2]):
        stop.append("a count differs")
    if sorted(after[0]) != want:
        stop.append(f"the queue statuses are ({tally(after[0])}), not ({tally(want)})")
    if decisions_before is not None and C.read(dec.path_of(folder)) != decisions_before:
        stop.append("decisions.md changed")
    if (folder / GRID).exists():
        stop.append(f"{GRID} exists again")
    if stop:
        for x in rewrites:  # one path at a time: a path HEAD does not have would stop a joint checkout
            git("checkout", "HEAD", "--", x)
        left = git("status", "--porcelain", "--", *rewrites).stdout.strip()
        if left:
            C.die(f"{'; '.join(stop)}, and git could not restore every file ({left.splitlines()[0][3:]}): "
                  f"run `git checkout HEAD -- {' '.join(rewrites)}` in the release folder; nothing is committed")
        st.write_page_data(folder)
        C.die(f"{'; '.join(stop)}: the files are restored from git and nothing is committed")
    commit(root, [folder / x for x in rewrites if x != GRID or grid_on], f"docs(plan): {a.release} moved to format {TO}")
    q.write_data(folder)  # again after the commit: the "changed" time of each item is its commit
    fcntl.flock(lock, fcntl.LOCK_UN)
    lock.close()
    print("committed")


if __name__ == "__main__":
    main()
