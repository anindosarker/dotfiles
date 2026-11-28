# Dashboard page (v2.1)

The task board with a Dashboard view: one page that opens from disk (`file://`), no framework, no build step. The expedition skill keeps this README; it is not copied into releases.

A release of format 2.2 gets the page as `status/index.html` and the files of `src/` as `status/src/` (`scripts/sprints/swimlanes.py`, `scripts/plan/new_release.py`). Its data is in `status/data/`. Script paths in this README are relative to the skill folder; the paths of release files are relative to the release folder.

## Files

```
board/
  dashboard.html   top bar, board and panel mount points, the <link> and <script> tags
  README.md        this page reference
  src/style.css    all styles
  src/core.js      data loading and the 30 s reload, state and saved settings, filters, search, sort, keys, side panel, render
  src/parts.js     shared parts: icon sprite, id chips and pills, shared board (move, resize, hide columns, View menu, keys),
                   shared foldable list sections, swimlanes (Epics and Milestones), sprint folding
  src/views.js     the six views built from the parts: Dashboard, Epics and Milestones (swimlanes), Tasks, Sprints, Queue,
                   with the Queue and Dashboard side panels
  task-board.html  the page of a release of format 2.0 and 2.1
  swimlanes.html   the page of a release of format 1.0
  swimlanes.tw.css the styles of swimlanes.html
```

## Keys

One handler (`core.js`) and one cursor per view (`parts.js`, `navStep`). The cursor is kept when the view changes.

- An open menu owns the keys: arrows, Enter and Esc act in the menu only. The cursor behind it does not move.
- Lists (Dashboard, Sprints, Queue): `j` / `k` or the down / up arrows move row by row and skip folded sections. With no cursor, `j` goes to the first row and `k` to the last. `h` / `l` do nothing.
- Boards (Dashboard, Tasks, Sprints, Queue): `j` / `k` move in a column, `h` / `l` move between columns in the shown order. With no cursor, the first key goes to the first card of the first column.
- `Enter` opens the side panel on the cursor item; with no cursor it does nothing. `Esc` closes the panel, the next `Esc` clears the cursor. `/` focuses the search box. `1` to `6` change the view.
- A clicked card or row becomes the cursor. The mark shows from the next redraw.
- The swimlanes (Epics, Milestones) have no cursor.

Scripts are classic `<script src>` files that share one global scope, loaded in the order core, parts, views; `core.js` starts the page on `DOMContentLoaded`, after all three ran.

## Data

`dashboard.html` is the task board with one more view, Dashboard, picked from the view menu with the other five (keys 1 to 6). Dashboard shows one card per item of every kind, in every status, in six columns: a board, or a list grouped the same way (list / board toggle). Nothing is left out by a rule: the filter menu (Status, Kind, Turn, each multi-select) is the only way to hide cards, and by default every card shows. The title shows "N need you" (items with `turn: you`).

`data/dashboard.json` and `data/dashboard.data.js` are generated output of `scripts/lib/dashboard.py`: never edit them by hand. `turn` and `ready` are computed at build time from the sources (rules below), never set by hand. An agent can read `dashboard.json` to find the items with `turn: "you"`. All data files are in `data/` (`DATA_DIR = "data/"` in `src/core.js`): Dashboard and Queue read `dashboard.data.js` (sets `window.DASHBOARD_DATA`), the other views read `status.data.js`; without `dashboard.data.js` the two views show an empty state. `dashboard.json` is the same data, indented, without `roots`. The release badge shows the dashboard data's `release` in this view.

```
{
  release: "v2.1.x",
  updated: "2026-11-28 07:00",                                          local time, YYYY-MM-DD HH:MM
  roots:   { plan: "/abs/plan/folder", status: "/abs/status/root" },   only in dashboard.data.js
  sources: { ... },                                                     for people, not shown
  rows: [{ kind, id, label, title, status, turn, ready, command, hold, depends_on, decider, decision, reason, progress, root, file, notes, details, options, option_list }]
}
```

The skill's Python scripts write both files from this section (v2.1.x D14), in the step that writes `status.data.js`. The Queue view reads its rows (`kind: queue`) from the same file, so the page needs no `queue.data.js`. Every item of every kind is one row. The builder maps no status word: it copies the stored one. It never reads `status/sprints.md` (D13). The writer is `scripts/lib/dashboard.py`; `scripts/lib/status.py` writes `status.data.js`. `scripts/sprints/refresh.py` writes both again after a hand edit.

A decision row copies the `status` line and the `decider` line of its decision file `decisions/D<n>-<slug>.md` (D9, D16); a file with no `decider` line gives `decider: ""` (a decision moved from a board has none until `scripts/decisions/decider.py` sets it). The rows are in the order of the numbers, and `sources` names the folder `decisions/`.

Format 2.2 releases with the board: a release whose `decisions.md` is still a board (not yet moved by `scripts/migrate/v2.1-v2.2/`) takes a decision row's `status` from the lane of its card (To do `to-do`, In progress `in progress`, Done `done`; Done with the tag `#deferred` `backlog`, with `#superseded` `archived`). Such a row is never `blocked`, has `decider: ""`, and its file is `decisions.md`. It has no `hold` field (a hold needs decision files); `ready` is `true` for a decision that is `to-do` with no epic tag, and its `turn` is `lead` while it is `to-do`.

Fields of every row. A text field with no value is `""`; `ready` is always `true` or `false`; `progress` is present on epics only, `decision`, `notes`, `options` and `option_list` on queue rows only, `hold` on the decision rows of a release whose decisions are files only.

| Field | Stored or worked out | Meaning |
|---|---|---|
| `kind` | | `queue`, `decision`, `epic`, `milestone` or `task`; the id chip has the kind's color |
| `id` | stored | unique key: `Q8`, `D4`, `E32`, the milestone id, the task id |
| `label` | worked out | the text on the id chip: the id; a milestone's ref (`93.3`); a task's `<spec>-<number>` |
| `title` | stored | the item's title |
| `status` | stored | the column: `to-do`, `in progress`, `blocked`, `done`, `backlog`, `archived` (Status, below); cards have no status pill |
| `turn` | worked out | whose move: `you` (person icon, marker color), `lead` (compass, muted), `agent` (bot, muted); `""` on an item that is `done`, `archived` or `backlog`, and on a held decision |
| `ready` | worked out | `true` only for a decision that is `to-do`, has no `epic` line, has no row in the Ownership table of an epic file, and has no hold or a hold that is over: it waits for the owner's go. The rule is `is_ready` of `scripts/lib/decisions.py`, the same rule as the `Ready:` list of `scripts/epics/overlap.py`. The side panel shows "Ready: waits for your go (compose D<n>)" |
| `command` | worked out | `compose` when `ready`, else `""` |
| `hold` | stored | decisions only: the owner's hold, `yes` or `until <id>` (a queue item, a decision or an epic), from `decisions.D<n>.hold` of `data/status.json` (`scripts/decisions/hold.py`); `""` when there is none. A hold `until <id>` is over when `<id>` is `done` or `archived`. The page does not show it |
| `depends_on` | stored | queue items: the ids the item waits for, as written (`Q14, Q15`); shown in the side panel |
| `decider` | stored or worked out | `you`, `lead` or `agent`: who made the call (Decider, below). Shown as "decided by ..." on a closed queue card and on a decision card, and in the side panel of every kind |
| `decision` | stored | queue rows only: the id of the decision made from the item (`D8`), else `""`; a chip in the Queue view |
| `reason` | stored or worked out | a `blocked` item's reason, the muted line on the card (Reason, below); on a decision that is not `blocked`, the id of its epic (`E<n>`) |
| `progress` | worked out | epics only: `{ done, total }`, the epic's tasks; `done` counts `done` and `archived`. Shown as "8/16 done" |
| `root`, `file` | worked out | key into `roots` (`plan` or `status`) and the path relative to it, for the VS Code / Browser buttons; `file: ""` for no file |
| `notes` | stored | queue rows only: the text under `## Notes` of the item file, as it is (D21) |
| `details` | stored | optional Markdown for the side panel; on a queue row the text under `## Details` of the item file |
| `options` | stored | queue rows only: the text under `## Options:` of the item file, as it is, numbers and nested bullets kept (D21) |
| `option_list` | stored | queue rows only: the same options as option cards, `[{ number, title, recommended, picked, body }]`, one per top-level `<n>.` line of `## Options:` (Q30). `title` without the `Recommended:` prefix; `recommended` is `true` when the line had it; `picked` is `true` on the option whose number is the `option` line of the item file; `body` the indented lines below, as Markdown. `[]` when the section has no option |

The side panel of a queue card, in the Queue view and in the Dashboard view, shows `notes`, `details` and the options in that order. Notes and Details are Markdown under their own heading. The options are the option cards of `option_list` under the heading Options (n): each card shows its number, its title, the tag recommended and, on the picked option, the mark picked; the other cards are faded when one is picked. When `option_list` is `[]` and `options` is not `""`, the panel shows `options` as Markdown under the heading Options. A part with no text gets no heading. The panel of every other kind shows `details` only.

Status: one list for every kind (D8, D9, D11). The stored word is copied.

| Kind | `to-do` | `in progress` | `blocked` | `done` | `backlog` | `archived` |
|---|---|---|---|---|---|---|
| queue | waits to be discussed; also during the discussion and a lookup | not used | a `depends_on` id is not `done` | a decision was made from it, or it was fixed without one | parked | will not be done |
| decision | decided, in no epic | in an epic, its work not all merged | shares a file with a running epic | its work merged, or closed with nothing to run | moved to another release | replaced by a later decision |
| epic | specs are being written, or delegated and no builder has started | a builder works | specs are ready, it waits for the owner's `delegate` | everything inside is done | not used | stopped by a decision |
| milestone, task | nothing inside is in work | something inside is in work, or part is done | nothing is in work and something is blocked; also a task that waits for the owner's look | merged, or everything inside is done | not used | stopped by a decision |

Rules that are worked out, in this order:

1. Queue item, `blocked`: an item that is `to-do` and has a `depends_on` id that is not `done` is `blocked`, with `reason: "Waits for <the ids that are not done>"`. An id that is not in the queue counts as not done. When every id is `done` the item is `to-do` again. (In the new format the script `scripts/queue/item.py --depends` stores this status; the builder then only copies it and writes the reason.)
2. Epic, `blocked` (a planned epic): the epic's stored status is `to-do`, its file `plan/epics/E<n>.md` has an Ownership table with at least one row, every row has a value in the Spec column and in the Milestone column ("the specs are ready"), and the front matter has no `starts:` value (the owner has not said `delegate`). Then `status: blocked`. In a release of format 2.2 the status file stores this status with the reason `waits for delegate`, and the row copies that reason. The lines `decisions:` and `specs:` of the front matter are not read (D12).
3. Decision, `blocked`: stored in the `status` line of the decision file by the status rule of `scripts/lib/decisions.py`, which every refresh runs. `reason` is "Waits for E<n>, same file" (`blocked_reason` of `scripts/lib/decisions.py`), the words `scripts/epics/overlap.py` prints for it and the `Blocked:` block of the `Epic ready` message (D10).

Turn. An item that is `done`, `archived` or `backlog` has `turn: ""`. For every other item, the first rule that fits:

| Kind | Condition | `turn` |
|---|---|---|
| queue | `to-do`, its item file has an `## Options:` section | `you` |
| queue | `to-do`, no `## Options:` section, or no item file | `lead` |
| queue | `blocked` | `lead` |
| decision | `ready: true` (`command: compose`) | `you` |
| decision | `to-do` or `blocked`, with a hold that is not over | `""`: the owner chose to wait, so it is not in "N need you" |
| decision | `to-do`, not ready and not held (an epic file names it and the owner has not said `delegate`) | `lead` |
| decision | `in progress`, or `blocked` and not held | `agent` |
| epic | `blocked` (planned, rule 2) | `you` |
| epic | `to-do` or `in progress` | `agent` |
| milestone | `blocked`, the reason is "waits for the owner's look" or starts with `owner:` | `you` |
| milestone | `blocked`, the reason starts with `lead:` | `lead` |
| milestone | every other case | `agent` |
| task | `blocked`, and `ownerCheck` is set or the reason is "waits for the owner's look" | `you` |
| task | every other case | `agent` |

The title's "N need you" counts the rows with `turn: you`.

Decider:

| Kind | `decider` |
|---|---|
| queue | stored; written when the item is closed (`done` or `archived`); `""` on every other item. `agent` means it was fixed without a decision |
| decision | stored: the `decider` line of its decision file, `you` (the owner said "record it"), `lead` (the lead settled it alone), `agent` (a run agent recorded a deviation); `""` when the file has no such line. A queue item that names the decision is not read for it |
| epic | `you` |
| milestone | stored in the status file by `scripts/lib/status.py`: the decider of the decision of its tasks, the first task that has one; `agent` when none has one |
| task | stored in the status file by `scripts/lib/status.py`: the decider of the decision its module cites; `""` when the module cites none or the decision has no decider |

Reason: a queue item's comes from rule 1, an epic's from rule 2, a decision's from rule 3; a milestone's and a task's blocked reason is stored. No other item has a reason, except the epic id on a decision that is not `blocked`.

Item files: a queue item's file is `<plan>/queue/Q<n>-*.md` (`root: plan`); a decision's is its decision file `decisions/D<n>-<slug>.md` (`root: plan`; `decisions.md` with the board); an epic's is `plan/epics/E<n>.md` and a task's is its task file (`root: status`); a milestone has none.
