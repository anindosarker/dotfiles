# Migration v2.1 to v2.2

Moves one release to the status words of format 2.2: the queue items, the decisions, the epics, the specs, the milestones and the tasks. Each decision gets a file of its own in `decisions/`, and `decisions.md` becomes their list. The epic file loses its `decisions:` and `specs:` lines, `status/sprints.md` is removed, and the release gets the dashboard page.

## Who needs it

- A release whose `status/data/status.json` says `"format": "2.1"`. A release in format `2.0` runs [../v2.0-v2.1/README.md](../v2.0-v2.1/README.md) first, and one in format `1.0` runs [../v1.0-v2.0/README.md](../v1.0-v2.0/README.md) before that. A release that stays in format 2.1 keeps working: every script reads it as before.
- A release that says `"format": "2.2"` and whose `decisions.md` is still the board with the lanes To do, In progress and Done. The same command moves only its decisions to files (see "A release of format 2.2 with the board").

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

- One file per decision: `decisions/D<n>-<slug>.md`. Its front matter holds `status`, `decider`, `source`, `epic` and `replaced_by` (each line only when it has a value), then the title line `# D<n>. <title>`, then a free body. The approved example is [../../../example/v1.0.x/owner/decisions/D58-the-sidebar-has-a-collapse-shortcut.md](../../../example/v1.0.x/owner/decisions/D58-the-sidebar-has-a-collapse-shortcut.md).
- `decisions.md` is a list, one line per decision file, which the scripts write again after each change. Nobody edits it by hand.
- The status of a decision is one of six words, set by the scripts only:

  | Board | Decision file |
  |---|---|
  | lane To do | `to-do`, or `blocked` when it shares a file with a running epic and is in no epic |
  | lane In progress | `in progress` |
  | lane Done | `done` |
  | lane Done, with a `- Deferred to` bullet | `backlog` |
  | the mark `(superseded by D<m>)` | `archived`, with `replaced_by: D<m>` |

- Every `queue/item.py <release> D` call takes `--decider you`, `lead` or `agent`: who made the call. The line goes into the new decision file.
- `decisions/close.py <release> D<n> --backlog` sets a decision to `backlog`. Without `--backlog` it sets `done`, as before.
- `epics/overlap.py <release> D<n> --files "a, b"` stores the files of a decision that no spec cites yet, so the scripts can tell when it waits for a running epic (`blocked`).
- `decisions/supersede.py` sets `status: archived` and `replaced_by: D<new>` in the old file. It no longer writes a `- Supersedes` line into the new decision: `replaced_by` of the old file holds the link.
- The status of an epic, a spec, a milestone and a task, in `status/data/status.json` and in each `status:` line: `not started` is `to-do`, `skipped` is `archived`. `in progress`, `blocked` and `done` stay. An epic whose specs are ready and that waits for your `delegate` is `blocked`, with the reason `waits for delegate`.
- `decider: you`, `lead` or `agent` on a closed queue item: who made the call. A command that closes an item (`--move` to Dropped or Autofix, `D --source`) takes `--decider`. The status file also gives a `decider` for each epic, spec, milestone and task; it is worked out on every write, and no plan file holds it.
- `depends_on: Q14, Q15` on a queue item: the items it waits for. Set it with `queue/item.py <release> --depends Q<n> "Q14, Q15"`. The scripts set `blocked`, and `to-do` again when every item it names is `done`.
- `plan/epics/E<n>.md` has no `decisions:` and no `specs:` line. Its `## Ownership` table is the one copy of both.
- There is no `status/sprints.md`. The status file holds the sprint of each milestone. To see the grid, run `python3 -I <skill>/scripts/sprints/grid.py <release>`: it prints the grid and writes nothing.
- `status/index.html` is the dashboard page in place of the task board: the task board with one more view, Dashboard. Its six views are Dashboard, Epics, Tasks, Sprints, Milestones and Queue (keys 1 to 6). The page loads its scripts and styles from `status/src/`, copies of `board/src/` of the skill. Its reference is [../../../board/README.md](../../../board/README.md).
- `status/data/` gets `dashboard.data.js`, read by the Dashboard and the Queue view, and `dashboard.json`, the same rows for an agent. `queue.data.js` is no longer written: the Queue view reads its rows from `dashboard.data.js`. All of them are renders: every command writes them again.
- The repository's `.gitignore` gets one line, `.ai/plans/*/*/status/src/`, in the commit of the migration.

## What stays

- Every command and every flag. A command takes the words of both formats, and writes the words of format 2.2.
- Every line of every decision card is in its file: each bullet, with its nested lines, tables and code blocks, without its one leading tab. A `- Source: Q<n>` bullet that holds only that id becomes the `source` line; a `- Source:` bullet with more words stays in the body, and its first Q id is also the `source` line.
- The round of each decision, its old tag `#R<n>`, is kept in the status file as `decisions.D<n>.round`; a card with no such tag gets round 1. `queue/item.py D` gives a new decision the highest round, and one more with `--new-round`, as before.
- Only the tick and the tags `#superseded` and `#deferred` are dropped: `status` and `replaced_by` hold what they said. The tag `#E<n>` is the `epic` line.
- The `## Notes`, `## Details` and `## Options:` of every item file, and the `decision` and `option` lines.
- The specs, the task files and the trackers. Only their `status:` line gets the new word.
- Every id: each queue item, decision, epic, spec, milestone and task keeps its number.

The migration writes `decider` only on an item that a run agent fixed (`autofix`). A migrated `decided` or `dropped` item has no `decider` line, because the files of format 2.1 do not say whether you or the lead made the call. This is the one case of a closed item without a `decider` line, and `status/report.py` does not count it as a gap.

A migrated decision file has no `decider` line either, for the same reason. This is no gap. Every page and report shows such a decision with no decider, and `status/report.py` prints one line that counts them. Set the line of each one, when you know who made the call:

```
python3 -I <skill>/scripts/decisions/decider.py <release> D<n> you|lead|agent
```

## Before you start

- `queue.md`, `queue/`, `decisions.md`, `plan/`, `<release>-plan.md`, `status/sprints.md` and `status/data/status.json` have no uncommitted change, nor has the repository's `.gitignore` when it lacks the `status/src/` line.
- The release has no `decisions/` folder.
- Every line of `decisions.md` is in a card, a lane heading, the front matter or the settings block. A loose line is named by the command, which writes nothing: move it under its card or remove it, and commit.
- Each row of `status/sprints.md` has the sprint and the mark of the status file. When they differ, the command names the rows and writes nothing: run `sprints/refresh.py <release>`, commit, and run it again.
- A milestone may be in progress: the migration does not stop a run.

## The commands

`<skill>` is the skill's folder. Run from the project folder.

```
python3 -I <skill>/scripts/migrate/v2.1-v2.2/format.py <release> --check
python3 -I <skill>/scripts/migrate/v2.1-v2.2/format.py <release>
```

The first line, on stderr, tells the session to read the skill again. `--check` prints one line per file it would change, one line per decision file it would write, and the counts, and writes nothing. The run writes the item files, the decision files and the list, the epic files, the `status:` lines of the task and spec files, the plan file, the status file with `"format": "2.2"` and the round of each decision, removes `status/sprints.md`, installs the dashboard page with `status/src/` and its data, adds the `.gitignore` line, and makes one commit: `docs(plan): <release> moved to format 2.2`.

An epic file whose `decisions:` or `specs:` line names a decision or a spec that no row of its table has gets a row for it first. The command prints one line for each row it adds. A part in parentheses on either line, such as `(D50)`, is an id the epic cites and does not run: it gets no row, and the command keeps it as a bullet at the end of the file's `## Notes` section (made when missing) and prints one line for the epic file.

The command refuses, and writes nothing, when the release is not in format 2.1 or a format 2.2 release with the board, when a file it rewrites has an uncommitted change, when the release has a `decisions/` folder, when a line of `decisions.md` is in no card, when an item file has a status that is not a word of format 2.1, when an epic table cannot be read, when `status/sprints.md` differs from the status file, or when a spec has an error that stops the status chain (a `Depends on` name that no milestone has, for example; the command prints each one). A step that fails after the first write restores the files from git and commits nothing.

### A release of format 2.2 with the board

The same two commands. The run writes only the decision files, the list and the round of each decision in the status file, and makes one commit: `docs(plan): <release> decisions moved to decision files`. It changes no item file, no epic file and no other plan file. A release of format 2.2 whose decisions are files already is refused: there is nothing to change.

## How to check it worked

- The command prints the counts before and after: queue items per status, decision cards before and decision files after, epics, specs, milestones and tasks. They are equal, or it commits nothing and restores the files from git. It also prints each status the status file changed beyond the two renamed words.
- The decision step prints its own counts, compared before the commit: decision cards read and decision files written; body lines read, and body lines written plus the `Source` bullets moved to the `source` line; decisions per lane on the board and by the status of their files; rounds read and rounds written. A count that differs stops the run, restores the files and commits nothing. After them it prints each decision status the status rule changed, and the count per status word.
- `python3 -I <skill>/scripts/status/report.py <release>` exits 0. Its `Decisions:` line counts as many decisions in `decisions/` as the board had cards, and its `Queue:` line counts the items in the words of format 2.2.
- Open `status/index.html` of the release in a browser, from disk. The six views draw, and the Queue view shows as many items as the `Queue:` line counts.

## How to undo it

It is one commit in the repository that holds the plan folder: `git revert <that commit>`. The decisions are the board of `decisions.md` again and `decisions/` is gone. After a migration from format 2.1 the release is in format 2.1 again, with its `status/sprints.md`, and the `.gitignore` line for `status/src/` is gone. The next command that writes the page (`sprints/refresh.py <release>`, for example) writes the task board as `status/index.html` again, and `queue.data.js`. `status/src/` is left over and can be deleted.

## Prompt for a lead session

```
The expedition skill stores the status words of format 2.2, keeps each decision in a file of decisions/ with decisions.md as their list, and keeps no status/sprints.md from that format on. Read its CHANGELOG.md and scripts/migrate/v2.1-v2.2/README.md, then re-read SKILL.md whole.
For release <release>: run migrate/v2.1-v2.2/format.py <release> --check, read its lines, then run it without --check. Then run status/report.py <release>, and set the decider of each decision it lists with decisions/decider.py <release> D<n> you|lead|agent.
Do not stop, replace or restart any session or Workflow for this.
Report in under five lines.
```
