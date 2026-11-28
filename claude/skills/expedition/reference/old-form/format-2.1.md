# Format 2.1 releases

For a session that works on a release whose `status/data/status.json` says `"format": "2.1"`. The sections on status words, the epic file and the grid file hold for a release of format 2.0 too, and the grid file for a release of format 1.0, as each section says. The text is the text of the format 2.1 skill, with its links set for this folder. To move a release of format 2.1 to format 2.2: [../../scripts/migrate/v2.1-v2.2/README.md](../../scripts/migrate/v2.1-v2.2/README.md).

## Contents
- What differs
- Status words
- Item file
- Epic file
- The grid file
- Files and pages

## What differs

- A queue item has five words of its own: `open`, `decided`, `later`, `dropped`, `autofix` (Item file).
- An epic, a spec, a milestone and a task have five words: `not started`, `in progress`, `blocked`, `done`, `skipped` (Status words). A planned epic is `not started`, not `blocked`.
- The epic file has the lines `decisions:` and `specs:` beside `status:` and `starts:` (Epic file).
- The grid is the committed file `status/sprints.md`, written by the scripts (The grid file).
- No `decider` is stored: `queue/item.py --decider` is accepted and not stored. `queue/item.py --depends` is refused with one line that names `scripts/migrate/v2.1-v2.2`, so no item has `depends_on` and no item is `blocked`.
- The page `status/index.html` is the task board; its Queue view reads `status/data/queue.data.js` (Files and pages).

## Status words

For a release with `status/data/status.json` (format 2.0 or 2.1).

- Five words everywhere: `not started`, `in progress`, `blocked`, `done`, `skipped`. `blocked` and `skipped` carry a short reason; its full text is in the milestone's tracker under `## Attention`.
- `status/data/status.json` is the only store, for every epic, spec, milestone and task, and it is committed. Writers: `status/status.py <release> set <id> "<status>" [--reason "<text>"]` for a task or a milestone, and `sprints/mark.py` for a milestone by the run's verbs: `launch` in progress, `resume` (a blocked milestone only) in progress when it was launched before and not started when it never was, `merge --commit <sha>` done, `wait --reason` and `stop --reason` blocked, `stop --reason "D<n> ..."` skipped. Nobody edits a status by hand.
- Stored: the status, reason, changed time and merge commit of a milestone; the status, reason and changed time of a task. Counted on every write: a sprint from its milestones, a spec from its milestones and its tasks together (a spec with no milestone is `not started`), an epic from its specs. `done` when everything inside is done or skipped (`skipped` when all of it is skipped), `in progress` when something inside is in work or part of it is done, `blocked` when nothing is in work and something is blocked, `not started` otherwise. `skipped` is closed, never started: skipped and not started items together are `not started`.
- The merge is refused while a task of the milestone is `not started`, `in progress` or blocked for another reason than the owner's look.
- Copies, written on every change and never read back as the truth: the `status:` front matter line of the task, spec and epic file; the grid `status/sprints.md` (`·` not started, `[ ]` in progress, `[~]` blocked, `[x]` done, `[!]` skipped); the page data. `status/report.py` flags a `status:` line that differs from the JSON file.
- Every command takes the words of format 2.2 too (`to-do` is `not started`, `archived` is `skipped`) and stores the word of format 2.1.
- The `status` line of a plan file or a task file is one of `not started`, `in progress`, `blocked`, `done`, `skipped`; a new task file says `status: not started`.

## Item file

A release of format 2.1 keeps one item file per item, `queue/Q<n>-<slug>.md`, and `queue.md` as the list of them, as format 2.2 does. The front matter holds `status`, `decision` and `option` only:

| `status` | Meaning |
|---|---|
| `open` | Waiting to be discussed: the queue |
| `decided` | Decided; `decision` names the decision |
| `later` | Parked; reopened by moving it back to `open` |
| `dropped` | Will not be done |
| `autofix` | Fixed without a decision |

- The status changes only through the scripts: `queue/item.py <release> D "<title>" --source Q<n> [--option <n>]` sets `decided`, `decision` and `option` (it refuses an option number the item does not have); `queue/item.py <release> --move Q<n> Open|Later|Dropped|Autofix` sets the same word in lower case; `plan/milestone.py add --cites` sets `autofix` on each item it cites and drops its `decision` and `option` lines.
- `queue/item.py Q` makes the item file with `status: open`; `queue/next.py` prints the `open` item with the lowest number; `queue/list.py <release> <lane>` selects the items whose `status` is that word in lower case.
- The owner's words: "record it" sets `decided`, "later" sets `later`, "drop it" sets `dropped`. A Lead-side close is `--move Q<n> Dropped`. An item the run fixes, or that the lead settles alone, becomes `autofix` or `decided` without being posted.
- A release of format 2.0 or 1.0 keeps its queue as a board: [queue-board.md](queue-board.md).

## Epic file

`plan/epics/E<n>.md`, one per epic, started by `epics/new.py`. In a release with `status/data/status.json` (format 2.0 or 2.1) the three lines are front matter, with the epic's status first (`status:`, `decisions:`, `specs:`, `starts:`); the line form below is the one of format 1.0 releases, and the scripts read both.

```md
# E12

Decisions: D81, D82, D83, D86, D88, D90
Specs: 39, 40, 41, 42, 49
Starts: S17

## Ownership

| Decision | Files | Spec | Milestone | Sprint |
|---|---|---|---|---|
| D88 One debounce hook | useDebouncedFilter.ts | 39 | Filter debounce hook | S17 |
| D81 Date filters compare dates | filterFns.ts | 40 | Date filter compare | S18 |
```

- `Decisions:` and the Decision cells (`D<n> <decision title>`): `epics/new.py`, on `compose`. One row per decision until the specs exist.
- `Specs:` and `Starts:`: `run/go.py`, on go. `Starts: S<n>` is the epic's start sprint, written once and never changed: no milestone of the epic sits in an earlier sprint. `epics/tag.py` writes it under the `Specs:` line, as the current sprint of the grid file.
- `status/report.py` flags a decision of the `Decisions:` line with no row, a spec with no row, a row file no milestone of its spec owns, and a Sprint cell that disagrees with the grid.
- The Ownership table and `## Notes` are written as in every format: the Files column by the spec writer, the Spec, Milestone and Sprint columns by `epics/table.py`, a note by `epics/new.py --note`.

## The grid file

`status/sprints.md`, in a release of format 2.1, 2.0 or 1.0. Columns are the sprints `S1`, `S2`, ... that `lib/ownership.py` computes. Rows are the milestones of specs that carry a `- Epic: E<n>` line (written under the title line by `epics/tag.py`); row text is the epic label, the spec number and the milestone name; rows sorted by epic, then spec number, then milestone order in the spec.

```md
| Milestone | S1 | S2 |
|---|---|---|
| E1 01 Row virtualizer | [x] |  |
| E1 02 Sticky footer | [x] |  |
| E2 03 Resize handle |  | [ ] |
```

- In `status/`: a title, an `Updated: <date time>` line, one table `Milestone`, `S1` .. `Sn`. Grid only: one row per milestone of a spec with an Epic line, row text `E1 01 Filtering`. A cell is one of the marks below. No legend, no prose, nothing under the table.
- `sprints/refresh.py` writes it on go (`run/go.py`, the epic's rows with `·`); `sprints/mark.py` sets each mark at a boundary (`launch`, `wait`, `resume`, `merge`, `stop`) and reruns the same chain, so nothing under `status/` is edited by hand. `sprints/grid.py <release>` writes the grid alone.
- A regeneration keeps every finished cell (`[x]`, `[!]`) where it is; a running or waiting row (`[ ]`, `[~]`) keeps its sprint (`lib/ownership.py` pins it) and a not-started row (`·`, or `[~]` never launched) is placed again.
- Then the Sprint column of every unfinished epic's table that has a `Starts:` value follows the grid; nothing else in those files changes, and finished epics' files are left alone.
- The current sprint is the first column of `status/sprints.md` holding a `[ ]`, `[~]` or `·` cell of an epic row; when there is none, the column after the last column holding an epic row (S1 on an empty grid).
- `status/report.py` flags a `status/sprints.md` whose rows differ from the milestones.
- Readers: the lead reads `status/sprints.md` on `DONE` or `BLOCKED`; the runner reads it and the trackers of its `[ ]` rows in each tick (step 4 and the tick economy), and `run/check.py` prints one line per `[ ]` row. A RUN for an epic whose rows are already running or done starts nothing.
- In a release of format 2.0 or 2.1 every mark is drawn from the status file (Status words, the copies). Launched before means a commit `docs(plan): <release> <milestone> launch` of `sprints/mark.py` is in the history of `status/sprints.md`.

### Milestone status, format 1.0

A release of format 1.0 has no status file: the grid is its only status. A milestone has one of five statuses. The grid cell, the tracker `Status:` line and the swimlane page use the same set.

| Status | Grid cell | Tracker `Status:` | Page color | Meaning |
|---|---|---|---|---|
| planned | `·` | `planned` | grey | not started |
| running | `[ ]` | `running` | blue | work is happening |
| waiting | `[~]` | `waiting (lead: <what>)` or `waiting (owner: <what>)` | amber | paused, resumes when the lead or the owner acts |
| stopped | `[!]` | `stopped (D<n>)` or `stopped (<reason in a few words>)` | red | ended without merge (blocked or skipped) |
| done | `[x]` | `done (<commit>)` | green | merged |

- `sprints/mark.py` sets the cell: `launch` `[ ]`, `wait` `[~]` (from `·` only for a lead hold), `merge` `[x]`, `stop` `[!]`. `launch` on a `[~]` cell resumes the milestone. The reason stays in the tracker: the `Status:` brackets and `## Attention`.
- `resume` ends a hold: on a `[~]` cell it sets `[ ]` when the milestone was launched before and `·` when it never was. Launched before means a commit `docs(plan): <release> <milestone> launch` of `mark.py` is in the history of `status/sprints.md`; the tracker cannot tell, since the main checkout's copy may lack the `Branch` line until the merge.
- A `[~]` row counts as started and unfinished, like `[ ]`: it keeps its sprint and its epic is not finished. A `[~]` row never launched moves like a `·` row and does not make its spec built. Only `[x]` meets a dependency, so the dependents of a waiting milestone are not launched and not stopped.
- Trackers written before this set say `merged (<commit>)` or `skipped (D<n>)`. The scripts read them as done and stopped; nothing writes them. `migrate/pre-v1.0/statuses.py <release>` converts a folder.
- The tracker `Status:` line is one of the five, its detail in brackets. `stopped (D<n>)` is a SKIP, `D<n>` the superseding decision. `waiting` is a milestone that is built and stopped until the lead or the owner acts; whoever stops the milestone writes it, in the tracker copy it already writes.

## Files and pages

```
├── status/sprints.md       ← generated, like everything under status/ (never edited by hand); sprints/refresh.py, by run/go.py: the grid, one row per milestone, one column per sprint; its marks set by sprints/mark.py only
├── status/index.html       ← the status page, a render, git-ignored, never committed: in a release of format 2.0 or 2.1 the task board (with its Queue view in 2.1), copied from board/task-board.html by plan/new_release.py and kept current by sprints/swimlanes.py; in a format 1.0 release the swimlane page from board/swimlanes.html
├── status/data/status.json ← the store of every status (epic, spec, milestone, task) and the data of the status board; written by status/status.py and sprints/mark.py only; committed
├── status/data/status.data.js ← the task board's data, rewritten with every status change; git-ignored, never committed. sprints.data.js and sprints.json, the swimlane page's data, are written only in a format 1.0 release
├── status/data/queue.data.js ← the data of the task board's Queue view, written from the item files by queue/item.py and the refresh chain; format 2.1 only; git-ignored, never committed
```

- The page is the task board, `status/index.html`, copied from `board/task-board.html`; it reads `status/data/status.data.js` (`window.STATUS_DATA`, git-ignored) and reloads it every 30 seconds. That file is the same data plus `root`, the release folder on this machine, after `updated`: a machine path is never committed.
- In a release of format 2.1 the task board also has a Queue view: every item with its status, notes, details and options. It reads `status/data/queue.data.js` (`window.QUEUE_DATA`, git-ignored, never committed), written from the item files by `queue/item.py` and by the refresh chain of `sprints/refresh.py` and `status/status.py`; it holds `root` like `status.data.js`. A release of a lower format has no queue data.
- The `<release>-plan.md` of a release below format 2.2 links `status/sprints.md` in its first lines.
