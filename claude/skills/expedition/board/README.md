# Dashboard page (v2.1)

The task board with a Dashboard view: one page that opens from disk (`file://`), no framework, no build step. The expedition skill keeps this README; it is not copied into releases.

## Files

```
v2.1-dashboard/
  dashboard.html   top bar, board and panel mount points, the <link> and <script> tags
  README.md        this page reference
  src/style.css    all styles
  src/core.js      data loading and the 30 s reload, state and saved settings, filters, search, sort, keys, side panel, render
  src/parts.js     shared parts: icon sprite, id chips and pills, shared board (move, resize, hide columns, View menu, keys),
                   shared foldable list sections, swimlanes (Epics and Milestones), sprint folding
  src/views.js     the six views built from the parts: Dashboard, Epics and Milestones (swimlanes), Tasks, Sprints, Queue,
                   with the Queue and Dashboard side panels
  src/build.js     writes data/dashboard.data.js and data/dashboard.json
  data/            dashboard.data.js + .json, status.data.js
  tests/keys.js    checks the key rules below in every view (Playwright); prints pass or fail per rule
```

## Keys

One handler (`core.js`) and one cursor per view (`parts.js`, `navStep`). The cursor is kept when the view changes.

- An open menu owns the keys: arrows, Enter and Esc act in the menu only. The cursor behind it does not move.
- Lists (Dashboard, Sprints, Queue): `j` / `k` or the down / up arrows move row by row and skip folded sections. With no cursor, `j` goes to the first row and `k` to the last. `h` / `l` do nothing.
- Boards (Dashboard, Tasks, Sprints, Queue): `j` / `k` move in a column, `h` / `l` move between columns in the shown order. With no cursor, the first key goes to the first card of the first column.
- `Enter` opens the side panel on the cursor item; with no cursor it does nothing. `Esc` closes the panel, the next `Esc` clears the cursor. `/` focuses the search box. `1` to `6` change the view.
- A clicked card or row becomes the cursor. The mark shows from the next redraw.
- The swimlanes (Epics, Milestones) have no cursor.

Run the test: `PLAYWRIGHT=<path to the playwright package> node tests/keys.js`

Scripts are classic `<script src>` files that share one global scope, loaded in the order core, parts, views; `core.js` starts the page on `DOMContentLoaded`, after all three ran.

Build the dashboard data, in `status-board/v2.1-dashboard/`:

```
node src/build.js ~/Work/Personal/Expedition/.ai/plans/v2.1.x/anindo-mac data/status.data.js data
```

## Data

`dashboard.html` is the task board with one more view, Dashboard, picked from the view menu with the other five (keys 1 to 6). Dashboard shows one card per item of every kind, in every status, in six columns: a board, or a list grouped the same way (list / board toggle). Nothing is left out by a rule: the filter menu (Status, Kind, Turn, each multi-select) is the only way to hide cards, and by default every card shows. The title shows "N need you" (items with `turn: you`).

`data/dashboard.json` and `data/dashboard.data.js` are generated output of `src/build.js`: never edit them by hand. `turn` and `ready` are computed at build time from the sources (rules below), never set by hand. An agent can read `dashboard.json` to find the items with `turn: "you"`. All data files are in `data/` (`DATA_DIR = "data/"` in `src/core.js`): Dashboard and Queue read `dashboard.data.js` (sets `window.DASHBOARD_DATA`), the other views read `status.data.js`; without `dashboard.data.js` the two views show an empty state. `dashboard.json` is the same data, indented, without `roots`. The release badge shows the dashboard data's `release` in this view.

```
{
  release: "v2.1.x",
  updated: "2026-11-28 07:00",                                          local time, YYYY-MM-DD HH:MM
  roots:   { plan: "/abs/plan/folder", status: "/abs/status/root" },   only in dashboard.data.js
  sources: { ... },                                                     for people, not shown
  rows: [{ kind, id, label, title, status, turn, ready, command, depends_on, decider, decision, reason, progress, root, file, details }]
}
```

The skill's Python scripts write both files from this section (v2.1.x D14), in the step that writes `status.data.js`. The Queue view reads its rows (`kind: queue`) from the same file, so the page needs no `queue.data.js`. Every item of every kind is one row. The builder maps no status word: it copies the stored one. It never reads `status/sprints.md` (D13). `src/build.js` builds only the sample (Sample, below) and is not copied into the skill.

Fields of every row. A text field with no value is `""`; `ready` is always `true` or `false`; `progress` is present on epics only, `decision` on queue rows only.

| Field | Stored or worked out | Meaning |
|---|---|---|
| `kind` | | `queue`, `decision`, `epic`, `milestone` or `task`; the id chip has the kind's color |
| `id` | stored | unique key: `Q8`, `D4`, `E32`, the milestone id, the task id |
| `label` | worked out | the text on the id chip: the id; a milestone's ref (`93.3`); a task's `<spec>-<number>` |
| `title` | stored | the item's title |
| `status` | stored | the column: `to-do`, `in progress`, `blocked`, `done`, `backlog`, `archived` (Status, below); cards have no status pill |
| `turn` | worked out | whose move: `you` (person icon, marker color), `lead` (compass, muted), `agent` (bot, muted); `""` on an item that is `done`, `archived` or `backlog` |
| `ready` | worked out | `true` only for a decision that is `to-do` and in no epic: it waits for the owner's go. No person icon; the side panel shows "Ready: waits for your go (compose D<n>)" |
| `command` | worked out | `compose` when `ready`, else `""` |
| `depends_on` | stored | queue items: the ids the item waits for, as written (`Q14, Q15`); shown in the side panel |
| `decider` | stored or worked out | `you`, `lead` or `agent`: who made the call (Decider, below). Shown as "decided by ..." on a closed queue card and on a decision card, and in the side panel of every kind |
| `decision` | stored | queue rows only: the id of the decision made from the item (`D8`), else `""`; a chip in the Queue view |
| `reason` | stored or worked out | a `blocked` item's reason, the muted line on the card (Reason, below); on a decision that is not `blocked`, the id of its epic (`E<n>`) |
| `progress` | worked out | epics only: `{ done, total }`, the epic's tasks; `done` counts `done` and `archived`. Shown as "8/16 done" |
| `root`, `file` | worked out | key into `roots` (`plan` or `status`) and the path relative to it, for the VS Code / Browser buttons; `file: ""` for no file |
| `details` | stored | optional Markdown for the side panel |

Status: one list for every kind (D8, D9, D11). The stored word is copied.

| Kind | `to-do` | `in progress` | `blocked` | `done` | `backlog` | `archived` |
|---|---|---|---|---|---|---|
| queue | waits to be discussed; also during the discussion and a lookup | not used | a `depends_on` id is not `done` | a decision was made from it, or it was fixed without one | parked | will not be done |
| decision | decided, in no epic | in an epic, its work not all merged | shares a file with a running epic | its work merged, or closed with nothing to run | moved to another release | replaced by a later decision |
| epic | specs are being written, or delegated and no builder has started | a builder works | specs are ready, it waits for the owner's `delegate` | everything inside is done | not used | stopped by a decision |
| milestone, task | nothing inside is in work | something inside is in work, or part is done | nothing is in work and something is blocked; also a task that waits for the owner's look | merged, or everything inside is done | not used | stopped by a decision |

Rules that are worked out, in this order:

1. Queue item, `blocked`: an item that is `to-do` and has a `depends_on` id that is not `done` is `blocked`, with `reason: "Waits for <the ids that are not done>"`. An id that is not in the queue counts as not done. When every id is `done` the item is `to-do` again. (In the new format the script `queue/item.py --depends` stores this status; the builder then only copies it and writes the reason.)
2. Epic, `blocked` (a planned epic): the epic's stored status is `to-do`, its file `plan/epics/E<n>.md` has an Ownership table with at least one row, every row has a value in the Spec column and in the Milestone column ("the specs are ready"), and the front matter has no `starts:` value (the owner has not said `delegate`). Then `status: blocked`, `reason: "Specs are ready; waits for your delegate"`. The lines `decisions:` and `specs:` of the front matter are not read (D12).
3. Decision, `blocked`: stored, worked out by `epics/overlap.py`. `reason` is "Waits for E<n>, same file", the words of the `Blocked:` block of the `Epic ready` message (D10).

Turn. An item that is `done`, `archived` or `backlog` has `turn: ""`. For every other item, the first rule that fits:

| Kind | Condition | `turn` |
|---|---|---|
| queue | `to-do`, its item file has an `## Options:` section | `you` |
| queue | `to-do`, no `## Options:` section, or no item file | `lead` |
| queue | `blocked` | `lead` |
| decision | `to-do` (in no epic: `ready: true`, `command: compose`) | `lead` |
| decision | `in progress` or `blocked` | `agent` |
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
| decision | stored on every decision: `you` (the owner said "record it"), `lead` (the lead settled it alone), `agent` (a run agent recorded a deviation) |
| epic | `you` |
| milestone | the `decider` of its decision: the Decision cell of the Ownership table row that names the milestone. `agent` when that cell is empty or no row names it |
| task | the `decider` of its own decision: the task's `decision` value in the status data. Only a task with no `decision` value takes the `decider` of its milestone |

Reason: a queue item's comes from rule 1, an epic's from rule 2; a decision's, a milestone's and a task's blocked reason is stored. No other item has a reason, except the epic id on a decision.

Item files: a queue item's file is `<plan>/queue/Q<n>-*.md` (`root: plan`); a decision's is `decisions.md` (the storage of a decision's status and decider is not decided, queue item Q21); an epic's is `plan/epics/E<n>.md` and a task's is its task file (`root: status`); a milestone has none.

### Sample

`src/build.js` writes the sample from files that are still in the old form: the v2.1.x `queue.md` and `decisions.md`, `data/status.data.js` (v0.9.x), and the epic files under that status file's `root`. It turns the old words into the new ones:

| Kind | Old | New |
|---|---|---|
| queue | lane Open | `to-do` |
| queue | lane Decided | `done`, `decider` of its decision (`#D<n>`), else `you` |
| queue | lane Autofix | `done`, `decider: agent` |
| queue | lane Later | `backlog` |
| queue | lane Dropped | `archived`, `decider: you` |
| decision | lane To do / In progress / Done | `to-do` / `in progress` / `done` |
| decision | lane Done, tag `#deferred` / `#superseded` | `backlog` / `archived` |
| epic, milestone, task | `not started` / `skipped` | `to-do` / `archived` |

Values the old files do not hold are in the `SAMPLE` table of `src/build.js`, so that the page shows every case: the `decider` of a decision (`you`, but `lead` for D14), one `blocked` decision (D10, "Waits for E2, same file"), one `depends_on` (Q10 waits for Q18). These three are examples, not facts of the release. An old item file's `waits_for:` line is read as `depends_on`. In the sample epic files the `starts` line is `Starts:` in the body text.
