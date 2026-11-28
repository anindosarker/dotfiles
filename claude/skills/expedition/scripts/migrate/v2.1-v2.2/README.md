# Migration v2.1 to v2.2

Moves one release to the status words of format 2.2: the queue items, the epics, the specs, the milestones and the tasks. The epic file loses its `decisions:` and `specs:` lines, and `status/sprints.md` is removed.

## Who needs it

A release whose `status/data/status.json` says `"format": "2.1"`. A release in format `2.0` runs [../v2.0-v2.1/README.md](../v2.0-v2.1/README.md) first, and one in format `1.0` runs [../v1.0-v2.0/README.md](../v1.0-v2.0/README.md) before that. A release that stays in format 2.1 keeps working: every script reads it as before.

## What changes for you

- The status of a queue item, in its `status:` line:

  | Format 2.1 | Format 2.2 |
  |---|---|
  | `open` | `to-do` |
  | `decided` | `done`, with its `decision` line |
  | `autofix` | `done`, with `decider: agent` |
  | `later` | `backlog` |
  | `dropped` | `archived` |
  | (none) | `blocked`: it waits for an item that is not `done` |

- The status of an epic, a spec, a milestone and a task, in `status/data/status.json` and in each `status:` line: `not started` is `to-do`, `skipped` is `archived`. `in progress`, `blocked` and `done` stay. An epic whose specs are ready and that waits for your `delegate` is `blocked`, with the reason `waits for delegate`.
- `decider: you`, `lead` or `agent` on a closed queue item: who made the call. A command that closes an item (`--move` to Dropped or Autofix, `D --source`) takes `--decider`. The status file also gives a `decider` for each epic, spec, milestone and task; it is worked out on every write, and no plan file holds it.
- `depends_on: Q14, Q15` on a queue item: the items it waits for. Set it with `queue/item.py <release> --depends Q<n> "Q14, Q15"`. The scripts set `blocked`, and `to-do` again when every item it names is `done`.
- `plan/epics/E<n>.md` has no `decisions:` and no `specs:` line. Its `## Ownership` table is the one copy of both.
- There is no `status/sprints.md`. The status file holds the sprint of each milestone. To see the grid, run `python3 -I <skill>/scripts/sprints/grid.py <release>`: it prints the grid and writes nothing.

## What stays

- Every command and every flag. A command takes the words of both formats, and writes the words of format 2.2.
- The `## Notes`, `## Details` and `## Options:` of every item file, and the `decision` and `option` lines.
- `decisions.md`, with its three lanes. The migration does not change it.
- The specs, the task files and the trackers. Only their `status:` line gets the new word.
- Every id: each queue item, decision, epic, spec, milestone and task keeps its number.

The migration writes `decider` only on an item that a run agent fixed (`autofix`). A migrated `decided` or `dropped` item has no `decider` line, because the files of format 2.1 do not say whether you or the lead made the call. This is the one case of a closed item without a `decider` line, and `status/report.py` does not count it as a gap.

## Before you start

- `queue.md`, `queue/`, `plan/`, `<release>-plan.md`, `status/sprints.md` and `status/data/status.json` have no uncommitted change.
- Each row of `status/sprints.md` has the sprint and the mark of the status file. When they differ, the command names the rows and writes nothing: run `sprints/refresh.py <release>`, commit, and run it again.
- A milestone may be in progress: the migration does not stop a run.

## The commands

`<skill>` is the skill's folder. Run from the project folder.

```
python3 -I <skill>/scripts/migrate/v2.1-v2.2/format.py <release> --check
python3 -I <skill>/scripts/migrate/v2.1-v2.2/format.py <release>
```

The first line, on stderr, tells the session to read the skill again. `--check` prints one line per file it would change and the counts, and writes nothing. The run writes the item files, the epic files, the `status:` lines of the task and spec files, the plan file, the status file with `"format": "2.2"`, removes `status/sprints.md`, writes the page data, and makes one commit: `docs(plan): <release> moved to format 2.2`.

An epic file whose `decisions:` or `specs:` line names a decision or a spec that no row of its table has gets a row for it first. The command prints one line for each row it adds.

The command refuses, and writes nothing, when the release is not in format 2.1, when a file it rewrites has an uncommitted change, when an item file has a status that is not a word of format 2.1, when an epic table cannot be read, or when `status/sprints.md` differs from the status file.

## How to check it worked

- The command prints the counts before and after: queue items per status, decision cards, epics, specs, milestones and tasks. They are equal, or it commits nothing and restores the files from git. It also prints each status the status file changed beyond the two renamed words.
- `python3 -I <skill>/scripts/status/report.py <release>` exits 0, and its `Queue:` line counts the items in the words of format 2.2.

## How to undo it

It is one commit in the repository that holds the plan folder: `git revert <that commit>`. The release is in format 2.1 again, with its `status/sprints.md`.

## Prompt for a lead session

```
The expedition skill stores the status words of format 2.2 and keeps no status/sprints.md from that format on. Read its CHANGELOG.md and scripts/migrate/v2.1-v2.2/README.md, then re-read SKILL.md whole.
For release <release>: run migrate/v2.1-v2.2/format.py <release> --check, read its lines, then run it without --check. Then run status/report.py <release>.
Do not stop, replace or restart any session or Workflow for this.
Report in under five lines.
```
