# Migration v0.1 to v0.2

Moves one release that is in work from flat spec files and tracker statuses to spec folders, task files and the status file.

## Who needs it

A release folder that has no `status/data/status.json`. `status/report.py <release>` says so in its last line. A finished release does not need it: the scripts still read the earlier form.

## Before you start

- The plan folder has no uncommitted change.
- No milestone is running. The command refuses otherwise; a builder in the middle of a milestone holds the earlier text.
- Save the three reports, to compare later: `sprints/check.py`, `status/report.py`, `status/progress.py`, each with the release as its argument.

## The commands

`<skill>` is the skill's folder. Run from the project folder.

```
python3 -I <skill>/scripts/migrate/v0.1-v0.2/format.py <release> --dry-run
python3 -I <skill>/scripts/migrate/v0.1-v0.2/format.py <release>
```

The dry run prints one line per spec and the counts, and writes nothing. `--force` runs it while a milestone is running; use it only when that builder has been told.

## What it changes

- Each spec `plan/specs/NN-<slug>.md` moves to `plan/specs/NN-<slug>/NN-<slug>.md`; every link to it in the release folder follows.
- In each spec, the old milestone blocks become a task list, numbered milestones and one task file per old task line, with its checks as a Verification list.
- `status/data/status.json` is written from the sprint grid and the trackers; the trackers lose their `Status:` line and task lines.
- Epic files get front matter; `process.md` gets `updated`; `.gitignore` keeps `status.json` in git.
- Everything is one commit.

## How to check it worked

- The command prints the counts before and after (specs, milestones, tasks, done milestones). They are equal, or it commits nothing.
- Run the three reports again and compare with the saved ones. `sprints/check.py` and `status/progress.py` print the same; `status/report.py` differs only where a line names a spec file path.
- `python3 -I <skill>/scripts/status/status.py <release> list --status blocked` shows what waits.

## How to undo it

It is one commit in the repository that holds the plan folder: `git revert <that commit>`.

## Prompt for a lead session

```
The expedition skill is now v0.2. Read its CHANGELOG.md and scripts/migrate/v0.1-v0.2/README.md, then re-read SKILL.md whole.
For release <release>: save the output of sprints/check.py, status/report.py and status/progress.py. If the sprint grid has a running milestone, do not migrate now: tell me which ones run and wait for my word.
Otherwise run migrate/v0.1-v0.2/format.py <release> --dry-run, read its lines, then run it without --dry-run. Run the three reports again and compare them with the saved ones.
Do not stop, replace or restart any session or Workflow for this.
Report in under five lines.
```
