#!/usr/bin/env python3
"""Run every go step of an epic, in order, as one command (SKILL.md stage 1, On go).

Usage: python3 -I run/go.py <release> E<n> --from <lead session name> [--owner X] [--root PATH]

Steps, each skipped when already done, so a rerun after a failure picks up where it stopped:

1. tag: epics/tag.py <release> E<n> <specs>: "- Epic: E<n>" in each spec, "#E<n>" on each
   decision card (moved to In progress), E<n> in the Deliverables rows, "Starts:" in the epic file, the epic's queue
   cards ticked and tagged #E<n>. The epic's specs: its tagged specs, the Spec column of its
   table, and (before the Starts line exists) every untagged spec citing one of its decisions.
   Fails when a decision of the "Decisions:" line is cited by none of them. Done when every
   spec and decision carries E<n> and Starts has a value.
2. commit: the epic's spec files and their trackers, decisions.md, queue.md, <release>-plan.md
   and the epic file, when any of them changed.
3. grid: sprints/refresh.py (the grid, the epic files' Sprint column, the decisions lanes, the
   queue sync, the swimlane data). Done when every milestone of the epic's specs has a row in status/sprints.md.
4. epic file: the "Specs:" line and the final table (the epics/table.py fill, the Sprint column
   from the grid); commits the epic files, status/sprints.md, decisions.md and queue.md when any of
   them changed.
5. close writer: runner.sh stop "<release> specs E<n>". Skipped when runner.sh list shows that
   window stopped; a window runner.sh does not list at all leaves nothing to close.
6. run: runner.sh start <release> --from <lead> when runner.sh list shows no live runner of the
   release, then runner.sh send <release> "RUN E<n> <release folder> epic <release
   folder>/plan/epics/E<n>.md from <lead>" (<release folder> relative to the repository).
7. next epic: epics/new.py <release> E<n+1>, when that file does not exist.

Steps 5 and 6 have no trace in the plan files: each is recorded in status/data/go.log (a
git-ignored script output, like the swimlane data) once it succeeds, and a rerun skips a step
recorded there. On the first failure it prints one line naming the step, runs nothing after it
and exits 1. On success it prints one summary line.

runner.sh is scripts/run/runner.sh beside this file, or the path in the environment variable
EXPEDITION_RUNNER_SH (tests point it at a stub).
"""
import argparse
import datetime
import importlib.util
import os
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
GO_LOG = "status/data/go.log"


class StepFailed(Exception):
    pass


die = C.die


def last_line(r):
    lines = [l for l in (r.stderr or "").splitlines() + (r.stdout or "").splitlines() if l.strip()]
    err = [l for l in lines if l.startswith("error:")]
    return (err or lines or [f"exit {r.returncode}"])[-1].removeprefix("error: ")


class Go:
    def __init__(self, root, folder, release, owner, n, lead):
        self.root, self.folder, self.release, self.owner = root, folder, release, owner
        self.n, self.lead = n, lead
        self.own = C.load("lib/ownership")
        self.path = self.own.epic_path(folder, n)
        self.runner = os.environ.get("EXPEDITION_RUNNER_SH") or str(HERE / "runner.sh")
        self.ran, self.skipped = [], []

    # helpers
    def script(self, name, *args):
        r = subprocess.run([sys.executable, "-I", str(C.SCRIPTS / name), self.release, *args,
                            "--owner", self.owner, "--root", str(self.root)],
                           capture_output=True, text=True)
        if r.returncode:
            raise StepFailed(f"{name}: {last_line(r)}")
        return r.stdout

    def runner_sh(self, *args, check=True):
        cmd = [self.runner, *args] if os.access(self.runner, os.X_OK) else ["bash", self.runner, *args]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if check and r.returncode:
            raise StepFailed(f"runner.sh {args[0]}: {last_line(r)}")
        return r

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], capture_output=True, text=True)

    def commit(self, paths, message):
        """git add and commit the paths when any changed; True when a commit was made."""
        paths = [str(p) for p in paths if Path(p).exists() or self.git("ls-files", "--", str(p)).stdout]
        if not paths:
            return False
        r = self.git("add", "-A", "--", *paths)
        if r.returncode:
            raise StepFailed(f"git add: {last_line(r)}")
        if self.git("diff", "--cached", "--quiet", "--", *paths).returncode == 0:
            return False
        r = self.git("commit", "-q", "-m", message, "--", *paths)
        if r.returncode:
            raise StepFailed(f"git commit: {last_line(r)}")
        return True

    def logged(self, what):
        p = self.folder / GO_LOG
        return p.is_file() and f"E{self.n} {what}" in {" ".join(l.split()[:2]) for l in p.read_text().splitlines()}

    def log(self, what):
        p = self.folder / GO_LOG
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(f"E{self.n} {what} {datetime.datetime.now():%Y-%m-%d %H:%M}\n")

    def runner_list(self):
        rows = []
        for line in self.runner_sh("list").stdout.splitlines():
            cells = line.split("\t")
            if len(cells) >= 3:
                rows.append({"name": cells[0], "state": cells[1], "status": cells[2]})
        return rows

    # state
    def text(self):
        return self.own.read(self.path)

    def specs(self):
        own, text = self.own, self.text()
        decisions = own.epic_decisions(text)
        specs, _ = own.epic_specs(self.folder, self.n, decisions)
        rows, _ = own.read_table(text)
        eps = own.spec_epics(self.folder)
        extra = {r["spec"] for r in rows or [] if r["spec"] in eps and eps[r["spec"]][0] in (None, self.n)}
        return sorted(set(specs) | extra, key=own.num_key), decisions

    def milestones_of(self, specs):
        comp = self.own.compute(self.folder)
        if comp["errors"]:
            raise StepFailed(comp["errors"][0])
        return [m for m in comp["milestones"] if m["spec"] in specs]

    # steps
    def step_tag(self):
        own = self.own
        specs, decisions = self.specs()
        if not decisions:
            raise StepFailed(f"{self.path.name} has no decision on its Decisions line")
        if not specs:
            raise StepFailed("no spec cites a decision of the epic")
        files = dict(own.spec_files(self.folder))
        cited = set().union(*(own.spec_cites(files[s]) for s in specs))
        lost = [d for d in decisions if d not in cited]
        if lost:
            raise StepFailed(f"{', '.join(f'D{d}' for d in lost)} cited by no spec of the epic")
        tags = own.read_tags(self.folder)
        starts = own.epic_starts(self.folder).get(self.n)
        if (all(own.spec_epic(files[s]) == self.n for s in specs)
                and all(tags.get(d, {}).get("epic") == self.n for d in decisions)
                and own.SPRINT_VALUE_RE.match(starts or "")):
            return False
        self.script("epics/tag.py", f"E{self.n}", *specs)
        return True

    def step_commit(self):
        specs, _ = self.specs()
        paths = []
        for s in specs:
            paths += sorted((self.folder / self.own.SPECS_DIR).glob(f"{s}-*.md"))
            paths += sorted((self.folder / self.own.TRACKERS_DIR).glob(f"{s}-*-tracker.md"))
        paths += [self.folder / "decisions.md", self.folder / self.own.QUEUE_MD,
                  self.folder / f"{self.release}-plan.md", self.path]
        return self.commit(paths, f"docs(plan): {self.release} E{self.n} go: specs, tags, plan rows, queue")

    def step_grid(self):
        specs, _ = self.specs()
        have = self.own.grid_columns(self.folder)
        if all(m["name"] in have for m in self.milestones_of(specs)):
            return False
        self.script("sprints/refresh.py")
        return True

    def step_epic_file(self):
        own = self.own
        specs, _ = self.specs()
        text = self.text()
        new = own.set_field(text, "Specs", ", ".join(specs))
        if new != text:
            self.path.write_text(new, encoding="utf-8")
        try:
            own.fill_epic(self.folder, self.n, quiet=True)
        except SystemExit:
            raise StepFailed("epics/table.py failed")
        return self.commit([self.folder / own.EPICS_DIR, self.folder / own.SPRINTS_MD,
                            self.folder / "decisions.md", self.folder / own.QUEUE_MD],
                           f"docs(plan): {self.release} E{self.n} go: grid and epic file")

    def step_close(self):
        if self.logged("stop"):
            return False
        window = f"{self.release} specs E{self.n}"
        entry = next((r for r in self.runner_list() if r["name"] == window), None)
        if entry and entry["state"] == "stopped":
            self.log("stop")
            return False
        r = self.runner_sh("stop", window, check=False)
        if r.returncode and entry:
            raise StepFailed(f"runner.sh stop: {last_line(r)}")
        self.log("stop")
        return True

    def step_run(self):
        if self.logged("run"):
            return False
        pat = re.compile(rf"^(?:{re.escape(self.release)} runner\d+|runner-{re.escape(self.release)})$")
        live = [r for r in self.runner_list()
                if pat.match(r["name"]) and r["state"] != "stopped" and not r["status"].startswith("dead")]
        if not live:
            self.runner_sh("start", self.release, "--from", self.lead)
        rel = self.folder.relative_to(self.root).as_posix()
        line = f"RUN E{self.n} {rel} epic {rel}/{self.own.EPICS_DIR}/E{self.n}.md from {self.lead}"
        self.runner_sh("send", self.release, line)
        self.log("run")
        return True

    def step_next(self):
        if self.own.epic_path(self.folder, self.n + 1).exists():
            return False
        self.script("epics/new.py", f"E{self.n + 1}")
        return True

    STEPS = [("tag", "step_tag"), ("commit", "step_commit"), ("grid", "step_grid"),
             ("epic file", "step_epic_file"), ("close writer", "step_close"),
             ("run", "step_run"), ("next epic", "step_next")]

    def run(self):
        if not self.path.is_file():
            print(f"go E{self.n} stopped at step 1 (tag): {self.path} missing", file=sys.stderr)
            sys.exit(1)
        for i, (name, fn) in enumerate(self.STEPS, 1):
            try:
                did = getattr(self, fn)()
            except StepFailed as e:
                print(f"go E{self.n} stopped at step {i} ({name}): {e}", file=sys.stderr)
                sys.exit(1)
            (self.ran if did else self.skipped).append(name)
        specs, _ = self.specs()
        rows, _ = self.own.read_table(self.text())
        cols = [int(c) for r in rows or [] for c in re.findall(r"S(\d+)", r["sprint"])]
        span = self.own.sprint_text([min(cols), max(cols)]) if cols else "none"
        starts = self.own.epic_starts(self.folder).get(self.n)
        print(f"E{self.n} go: specs {', '.join(specs)}; Starts {starts}; sprints {span}; "
              f"RUN sent; next epic file E{self.n + 1}.md; ran: {', '.join(self.ran) or 'none'}; "
              f"skipped: {', '.join(self.skipped) or 'none'}")


def main():
    ap = argparse.ArgumentParser(usage="run/go.py <release> E<n> --from <lead session name> [--owner X] [--root PATH]")
    ap.add_argument("release")
    ap.add_argument("epic")
    ap.add_argument("--from", dest="lead", required=True)
    ap.add_argument("--owner")
    ap.add_argument("--root", help="repository root (default: found from the cwd)")
    a = ap.parse_args()
    if not C.RELEASE_RE.match(a.release):
        die(f"bad release '{a.release}', expected like v0.9.x")
    m = re.match(r"^E(\d+)$", a.epic)
    if not m:
        die(f"bad epic '{a.epic}', expected like E12")
    own = C.load("lib/ownership")
    root = own.repo_root(a.root, a.release)
    owner = own.detect_owner(root, a.owner)
    folder = own.release_folder(root, owner, a.release)
    Go(root, folder, a.release, owner, int(m.group(1)), a.lead).run()


if __name__ == "__main__":
    main()
