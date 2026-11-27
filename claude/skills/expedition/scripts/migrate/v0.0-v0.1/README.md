# Migrations up to v0.1

Scripts for release folders made before the skill kept versions. Each one runs once per release. A current script that refuses a folder names the script to run.

## Who needs it

A release folder that a script refuses with one line naming a script of this folder, or one of the cases below. A release made with v0.1 or later needs none of them.

## Before you start

- The plan folder has no uncommitted change.
- No milestone is running.

## The commands, in this order

`<skill>` is the skill's folder. Run from the project folder. Every script but `layout.py` takes `--dry-run`: use it first.

| Order | Command | For a folder that |
|---|---|---|
| 1 | `python3 -I <skill>/scripts/migrate/v0.0-v0.1/layout.py <release>` | has the flat layout, no `plan/` folder. It then runs steps 2 to 4 itself when they are needed |
| 2 | `.../decisions.py <release>` | has a `decisions.md` in the heading format (`## Round`, `### D<n>`) |
| 3 | `.../queue.py <release>` | has `findings.md` or `run/attentions/`, or a `queue.md` in the old card format |
| 4 | `.../epics.py <release>` | still has `status/ownership.md` |
| 5 | `.../fixes.py <release> --dry-run`, then without | has trackers `run/trackers/fix-<slug>-tracker.md` with no spec; `--map <slug>=E<n>:<NN>` for a choice it cannot make |
| 6 | `.../backfill_starts.py <release>` | has epics with grid rows and no `Starts:` line; then `sprints/check.py` and `sprints/refresh.py` |
| 7 | `.../statuses.py <release>` | has trackers that say `merged` or `skipped`, or a waiting milestone whose cell is `[ ]` |

## What they change

- `layout.py` moves the files into `plan/`, `run/` and `status/` with `git mv`.
- `decisions.py` and `queue.py` rewrite the two files as boards, every card and line kept.
- `epics.py` fills each epic file's Ownership table and removes `status/ownership.md`.
- `fixes.py` turns each free-standing fix into a follow-up spec of an epic.
- `backfill_starts.py` and `statuses.py` write the start sprint of old epics and the five tracker statuses.

## How to check it worked

Run `status/report.py <release>` and `sprints/check.py <release>`: no script refuses the folder, and the report lists no gap that names one of these scripts. A second run of any script changes nothing.

## How to undo it

Each script writes one commit, or leaves its changes for you to commit: `git revert` that commit, or `git checkout` the release folder before you commit.

## Prompt for a lead session

```
Release <release> was made before the expedition skill kept versions. Read scripts/migrate/v0.0-v0.1/README.md.
Run status/report.py <release>. For each line that names a script of that folder, run the script with --dry-run, read its lines, then run it without. Follow the order of the README.
If the sprint grid has a running milestone, do nothing and tell me which ones run.
Do not stop, replace or restart any session or Workflow for this.
Report in under five lines.
```
