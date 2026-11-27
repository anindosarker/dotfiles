# Changelog

One section per version of the skill, newest first. The version is `metadata.version` in the front matter of `SKILL.md`. A release folder states the format it has in `status/data/status.json` (`format`); a release with no status file is format 1.0.

## 2.0

What is new:

- One kind of spec, always a folder: `plan/specs/NN-<slug>/NN-<slug>.md` with its task files in `tasks/`. A spec has modules (what is wanted, with the decision cite), tasks (one file each: Goals and a Verification checklist) and numbered milestones (the tasks built and merged together).
- A spec in work grows: a new piece of work is the next module, its task files and its own milestone, added with `plan/milestone.py add`. `plan/task.py add` adds one more task. A spec that is done takes nothing; later work is a new spec.
- One status file, `status/data/status.json`, holds the status of every epic, spec, milestone and task in five words: not started, in progress, blocked, done, skipped. One command reads and writes it, `status/status.py`. The sprint grid and the `status:` line of each file are copies it writes.
- A task whose only open check is the owner's own look is blocked with that reason, and shows as such.
- A release in format 2.0 has the task board at `status/index.html`, in place of the swimlane page. It reads `status/data/status.data.js`, written from the status file on every change, and reloads every 30 seconds.
- The process file starts from a short template and carries `updated`, the time its facts were last checked.
- `templates/` holds the shape of every authored file, `example/` one small release with every kind of file filled in, and `board/` the status pages.
- `SKILL.md` is short; the detail of each stage is in its own file under `reference/` (`discuss.md`, `plan.md`, `run.md`, `triage.md`), the commands in `reference/scripts.md`. `reference/planning-guidelines.md` describes the 2.0 plan file; the 1.0 text is in `reference/old-form/`.
- `plan/new_cycle.py` is now `plan/new_release.py`; the old name still runs it.
- Migrations sit in `scripts/migrate/`, one folder per version step, each with a guide.

What changes for a release in work:

- Nothing has to change at once. A release in format 1.0 is read as before, and `plan/new_spec.py` and `plan/new_fix.py` still write the earlier form there.
- To use task files and the status command, migrate the release when no milestone is running. The migration is one commit and the reports print the same before and after.
- A session that read the skill before this version re-reads it before it creates a release or migrates one.

What stops working:

- Nothing that a 1.0 release used is removed.
- In a migrated or new release, a status is no longer written into a tracker or the grid by hand or by a prompt: `sprints/mark.py` needs `--reason` for a wait or a stop and `--commit` for a merge.

Changed after the tag `expedition-v2.0`, same format:

- The runner no longer starts a Workflow for every milestone. It judges each one: a Workflow only for several builders at the same time, a second opinion, the release milestone, or a word from the lead or the owner. Every other milestone is built by one agent and merged by the runner.
- A failed Workflow stage is resumed when that is possible; a plain agent may do it otherwise.
- In discuss, the lead fills the module and the task file of a milestone it adds to a spec in progress.
- `queue/item.py` refuses a second `--bullet`.
- Owner words: `delegate` and `epic delegate` replace `go` and `epic go`, which stay accepted as old names.
- New owner word `iterate`: the open item is decided, planned by the regular steps and sent to the runner at once, as the next module of its spec or as a new spec with its own epic. The runner chooses the moment it starts.

Migration: [scripts/migrate/v1.0-v2.0/README.md](scripts/migrate/v1.0-v2.0/README.md).

## 1.0

The skill before versions were kept. Folders older than that: [scripts/migrate/pre-v1.0/README.md](scripts/migrate/pre-v1.0/README.md).
