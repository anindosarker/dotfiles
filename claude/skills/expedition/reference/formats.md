# File formats

## Contents
- Shared rule
- Shared files
- queue.md
- Item file
- Settled list
- Progress reply and reports
- Waits for you line
- decisions.md
- Decision file
- Epic file
- The grid
- Milestone status
- Tracker
- Status
- process.md
- Handoff

## Shared rule

Every item has an ID: the `# Q<n>.` title of an item file, the `# D<n>.` title of a decision file, a heading elsewhere. Its first bullet is required and self-explanatory: a reader understands the item from it alone. A decision file is the one exception: its body is free, and no bullet is required (Decision file). Everything after it is open-ended, but in bullets. Templates: [../templates/](../templates/).

## Shared files

The decisions (`decisions.md` and the decision files in `decisions/`), the queue (`queue.md` and the item files in `queue/`) and the epic files are written by both sessions, lead and runner.

- The front matter of a decision file and the list `decisions.md` are written by the scripts only: `queue/item.py` (a new file), `epics/tag.py` through `run/go.py` (`epic`), the status rule in every status chain (`sprints/refresh.py`, `sprints/mark.py`, `status/status.py`, `plan/milestone.py`) and every call that writes a decision, `decisions/close.py` (`done` or `backlog`), `decisions/supersede.py` (`archived`, `replaced_by`) and `decisions/decider.py` (`decider`). A session writes only the body of a decision file.
- Re-read the file right before every write, make a targeted edit, commit at once. No held edits.
- The next D or Q number is read from the file at write time, never from memory.
- Ids come only from `python3 -I <skill>/scripts/queue/item.py <release> D|Q "<title>"`, never typed. It locks, writes the decision file or the item file, commits and prints the id; the session then writes the body of the decision file.
- No id is mentioned in chat or a tracker before it is allocated: refer to the item by its title.
- An id never changes after allocation.
- A duplicate filed twice keeps both ids. The later item gets the fact `Same as Q<n>.` and is closed with `queue/item.py <release> --move Q<n> Dropped --decider lead` (`status: archived`).
- Fallback rule: a session that finds its own id taken renumbers its own item only, never the other's. With `queue/item.py` this no longer happens.
- Agents on milestone branches never edit `decisions.md` or a decision file.

## queue.md

One file per release, in the release folder root, template [../templates/queue-list.md](../templates/queue-list.md), filled in [../example/v1.0.x/owner/queue.md](../example/v1.0.x/owner/queue.md): the list of every item filed in the release, one line per item file. Every owner remark, and every other item that passes the bar at filing (Item file), is filed in the turn it is raised. A release of format 2.0 or 1.0 keeps its queue as a kanban board: [old-form/queue-board.md](old-form/queue-board.md).

```md
# Queue, <release>

- [Q1](queue/Q1-<slug>.md): <title>
- [Q2](queue/Q2-<slug>.md): <title>
```

- One line per item file, in the order of the numbers, linked to the file. No status, no decision, no tag: those are in the item file.
- The scripts write the whole file again after each change of an item (`queue/item.py`, `plan/milestone.py`). Nobody edits it by hand; `status/report.py` flags a `queue.md` out of step with the item files.
- The owner sees the queue in the Queue view of the dashboard page (Status).

## Item file

`queue/Q<n>-<slug>.md`, one per item, in the folder `queue/` of the release folder, template [../templates/queue-item.md](../templates/queue-item.md). A filled one, shown below: [../example/v1.0.x/owner/queue/Q49-a-select-menu-in-the-sidebar-turns-translucent-after-a.md](../example/v1.0.x/owner/queue/Q49-a-select-menu-in-the-sidebar-turns-translucent-after-a.md).

```md
---
status: done
decision: D62
option: 1
decider: you
---
# Q49. A select menu in the sidebar turns translucent after a short scroll

## Notes

- `styles/menu.css:1447`: the blur is inside the scroll container.

## Details

- To see it: open the layout menu in the sidebar and scroll down.
- Likely cause: `styles/menu.css:1447` puts the blur inside the scroll container.

## Options:

1. Recommended: fix the blur in the app's own styles
   - A translucent menu opened from the sidebar keeps its blur while its content scrolls.
   - `components/ui/` stays unchanged.
2. Fix the blur in `components/ui/`
   - The change is in `components/ui/`, not in the app's own styles.
```

| Part | Written by | Notes |
|---|---|---|
| front matter `status` | scripts only | `to-do`, `blocked`, `done`, `backlog` or `archived` |
| front matter `decision` | scripts only | `D<n>`; present on an item that a decision closed, absent on every other item |
| front matter `option` | scripts only | the number of the picked option; absent when none was given |
| front matter `decider` | scripts only | `you`, `lead` or `agent`: who closed the item; present on a `done` or `archived` item only |
| front matter `depends_on` | scripts only | the item ids this item waits for, `Q14, Q15`; absent when there are none |
| `# Q<n>. <title>` | script at filing | one plain sentence naming the problem or idea; the number is never reused |
| `## Notes` | script (`--bullet`, `--fact`) | the owner's remark and the first findings, raw, one bullet each; nested bullets allowed; not shown in chat |
| `## Details` | the lead, by a targeted edit | the facts the decision needs; absent until the lead writes the item out |
| `## Options:` | the lead, by a targeted edit | numbered, `Recommended:` on the first; inside an option bullets by default, a table or a code block only where bullets do not work; absent until the lead writes the item out |

- Five of the six status words are the item's state; a queue item is never `in progress`:

  | `status` | Meaning | `decider` |
  |---|---|---|
  | `to-do` | Waiting to be discussed: the queue | none |
  | `blocked` | Waits for the items of its `depends_on` line that are not `done`; set by the scripts only | none |
  | `done` with a `decision` line | Decided; `decision` names the decision | `you`, or `lead` when the lead settled it alone |
  | `done` with no `decision` line | Fixed by the run without a decision | `agent` |
  | `backlog` | Parked; reopened by moving it back to `to-do` | none |
  | `archived` | Will not be done | `you`, or `lead` for a Lead-side close |

- The status changes only through the scripts, and a call that closes an item names its decider, or it is refused before anything is written:
  - `queue/item.py <release> D "<title>" --source Q<n> [--option <n>] --decider you|lead` sets `done`, `decision`, `option` and `decider` (it refuses an option number the item does not have).
  - `queue/item.py <release> --move Q<n> <word>` takes the lane words `Open`, `Later`, `Dropped`, `Autofix` or the status words `to-do`, `backlog`, `archived`, `done`, which mean the same in that order. `Dropped` needs `--decider you` or `--decider lead`; `Autofix` needs `--decider agent`; `Open` and `Later` take no decider. Every move first removes `decision`, `option` and `decider`.
  - `plan/milestone.py add --cites` sets `done` and `decider: agent` on each item it cites and removes its `decision` and `option` lines. The fix is traced through its module heading and its tracker's first line, for example `(Q9)`.
  - `queue/item.py <release> --depends Q<n> "Q14, Q15"` writes the `depends_on` line (`""` removes it). It refuses an id with no item file, the item itself and a ring of items that wait for each other. After every write of an item, of `queue.md` and of the page data the blocked check runs: a `to-do` or `blocked` item becomes `blocked` while a named item is not `done`, and `to-do` when every named item is `done`. After a hand edit of an item file, `sprints/refresh.py <release>` runs the check.
- A closed item always has a `decider`, with one case that has none: an item that was decided or dropped before its release moved to format 2.2. The migration writes `decider: agent` on an `autofix` item only, because the files of format 2.1 do not say whether the owner or the lead made the other calls. `status/report.py` does not flag that case.
- The decision file is the record. A `done` item holds its decision id only: the status and the epic of that decision are read from its decision file, and nothing is synced into the item file. `status/report.py` flags a `done` item whose decision has no decision file.
- `<slug>` is made from the title at filing, as a task file's slug is, and never changes after. A new file has the front matter, the title and `## Notes`.
- **Bar at filing.** An item's first `## Notes` bullet says what goes wrong for a user of the library or a reader of the docs if the item is ignored. A raiser (the lead, a lookup, the runner, a builder, a verifier) that cannot say it files no item: it writes the point in its tracker's `## Notes`, or leaves it out when it has no tracker. The owner's remarks are exempt: every one is filed.
- `## Notes` bullets are facts and remarks as found: path:line, measurement, lookup result, what the owner said. A lookup agent adds its facts to the item it was given with `queue/item.py <release> --fact Q<n> "<text>"`.
- `## Details` and `## Options:` hold the item as the owner reads it in chat, word for word; the lead writes them when the item settles ([discuss.md](discuss.md), Item format, Storing).
- Citations elsewhere: `(Q3)` in specs and trackers; a decision file that came from an item has the line `source: Q3`; a fix's tracker cites `(Q3, Q4)` on its first line.
- The run reports; it does not solve. Do not research solutions for a run item.
- Not a queue item: a point that fails the bar at filing, spec text that lags shipped code, a tracker gap, a process lesson, a tooling fact with one right answer. Those go to the tracker Notes, a decision or the spec file directly (`process.md` holds project facts only); the owner sees choices only.

## Settled list

What the lead settled or closed without the owner (SKILL.md, Weight test; discuss.md, Screen and Lead-side close), one plain line per item: its id, what it is in words anyone gets, what was done. No paths or commit ids.

```
Settled without you:
- D133 Filter chips keep their order after a reset: kept as built.
- Q118 Select all with pinned rows drops virtualization: fix sent to the runner.
- Q120 Same as Q84: dropped.
Name one to reopen it.
```

- Posted before the first real item of a round, and with every report of run items that settled something. Each item is listed once.
- One line per item, never a grouped sentence ("seven kept as built (D133 to D139)").
- The owner naming a line reopens it as a normal item: an `archived` item goes back with `queue/item.py <release> --move Q<n> Open`; a settled decision is discussed as a re-decided decision (discuss.md, Changing a decision).

## Progress reply and reports

- On `progress` (or "status") the session, lead or runner, runs `status/progress.py <release>`. No warning and nothing the session knows to be wrong: it replies with the output unchanged and nothing else. Otherwise it checks, corrects the source (`status/status.py` or `sprints/mark.py`; in a format 1.0 release, `sprints/mark.py` for a mark and the tracker `Status:` line for waiting), runs the script again and replies with that output. Only when no file field can hold the truth does it correct the block text itself, in the same format. The owner sees one block, no added line, apart from the Waits for you line under it in a release of format 2.2 (Waits for you line). When the block says a milestone waits on the lead, the lead does that work in the same turn, after the block. Example output:

  ```
  **E12** · Specs 6/12
  - **Running**
    - 44 Range filter editor
  - **Blocked**
    - 47 Comparison page: the table names a feature tablecn dropped; keep or remove the row.
  ```

  `Running` lists each spec with a milestone running, including a spec that is being retried or fixed. `Blocked` lists only work that has stopped, with the run's own reason and who it waits on (`waits on the owner: ...` or `waits on the lead: ...`).
- Reporting on epic work (after a regroup, an added fix, a note to the runner, a release check): the default report is that same progress block, followed by the settled list (Settled list, above) when run items were settled. Add a plain sentence only when the block cannot show what was done or what the owner has to do. No commit id, sprint number, file path or script leftover; a leftover is fixed, or filed as a queue item when it needs a decision. A reply to a skill-update prompt keeps the form that prompt asks for.

## Waits for you line

In a release of format 2.2, the last line of every message of the lead to the owner: `status/waits.py <release>` prints it from the rows of the dashboard data, built at each call, so it is never older than the files. When the lead calls it and when it pushes: [discuss.md](discuss.md), Discussing items, Waits for you line, and Epics, Push. A release of format 2.1 or lower has no line.

```
Waits for you: E3 planned: delegate · D14 ready: compose · 05-04: your look · Held: D9
```

- The line is `Waits for you: `, then one entry per row that waits, joined by ` · `: epics, decisions, tasks, milestones, queue items, and inside a kind in the order of the numbers.

  | Row | Entry |
  |---|---|
  | epic, `blocked`, turn `you` (planned, waits for `delegate`) | `E3 planned: delegate` |
  | decision, ready, no hold | `D14 ready: compose` |
  | decision, ready, a hold that is over | `D14: hold over, ready: compose` |
  | task, turn `you` (waits for the owner's look) | `05-04: your look` |
  | milestone, turn `you`, and none of its tasks has an entry | `<label>: <the reason>`, without a leading `owner: ` |
  | queue item, turn `you` (its options are written, it waits for the owner's word) | `Q18: record it` |

- Ready: the decision is `to-do`, has no `epic` line and no row in the table of an epic file, and has no hold or a hold that is over ([../board/README.md](../board/README.md), the field `ready`).
- The last part is `Held: D9, D14`: each decision with a hold that is not over, ids only, in the order of the numbers. Absent when no decision is held. A held decision has no entry of its own.
- No entry and nothing held: the command prints nothing, and the message has no line.
- `--skip Q19` leaves out the entries of that id: the item the same message posts.
- `--new` prints the line, then one line `new: <entry>` for each entry that was not in the line of the call before. A held decision is never a `new:` line. The keys of what each call printed are in `status/data/waits.json` (git-ignored); an entry that leaves the line loses its key, so a thing that waits a second time is new again.
- A hold is the entry of the decision in the status file (Status): `hold` is `yes`, or `until <id>` (a queue item, a decision or an epic), and `hold_reason` holds the owner's reason in words, with `hold: yes` only. A hold `until <id>` is over when `<id>` is `done` or `archived`; every other hold ends only on the owner's word. `decisions/hold.py` writes both keys; `epics/new.py` removes them from each decision it takes into an epic, and the refresh chain removes them from a decision that is no longer `to-do` or `blocked`.

The held block, `status/waits.py <release> --held`: one line per held decision, its id, its title, and after a colon `until <id>` or the reason in words when there is one. A hold that is over is not in it. Nothing held: nothing printed.

```
Held:
- D9 Decision: six status words and decider: first the trial of the page
- D14 The skill's own scripts build the dashboard data: until Q8
- D21 The report names the migration folder
```

## decisions.md

The list of the decisions of the release, template [../templates/decisions-list.md](../templates/decisions-list.md): the title `# Decisions, <release>`, then one line per decision file, in the order of the numbers, linked to the file. The scripts write it again after each change of a decision; nobody edits it by hand. It holds no status, decider or epic: those are in the decision files. A filled list: [../example/v1.0.x/owner/decisions.md](../example/v1.0.x/owner/decisions.md).

```md
# Decisions, v0.9.x

- [D9](decisions/D9-process-file-audited.md): Process file audited
- [D96](decisions/D96-a-click-in-a-date-filter-box-starts-typing-at-its-first-part.md): A click in a date filter box starts typing at its first part
```

A release that keeps its decisions on a board (format 2.1 or lower, or format 2.2 before its decisions moved to files): [old-form/format-2.1.md](old-form/format-2.1.md), Decision board.

## Decision file

`decisions/D<n>-<slug>.md`, one accepted decision, template [../templates/decision.md](../templates/decision.md). Read the approved example before the first decision file is written: [../example/v1.0.x/owner/decisions/D58-the-sidebar-has-a-collapse-shortcut.md](../example/v1.0.x/owner/decisions/D58-the-sidebar-has-a-collapse-shortcut.md). More examples: [../example/v1.0.x/owner/decisions.md](../example/v1.0.x/owner/decisions.md).

```md
---
status: to-do
decider: you
source: Q80
---
# D96. A click in a date filter box starts typing at its first part

- Native date inputs put the caret on the segment under the click, so typed digits fill only the year.
- The click puts the caret on the first part.
```

The front matter, in this order, each line only when it has a value:

| Line | Value | Written by |
|---|---|---|
| `status` | one of the six status words, below | the scripts only |
| `decider` | `you`, `lead` or `agent`: who made the call | `queue/item.py D --decider`; `decisions/decider.py` for a file that has none |
| `source` | `Q<n>`, the queue item it came from | `queue/item.py D --source` |
| `epic` | `E<n>`, the epic it runs in | `epics/tag.py`, through `run/go.py` on `delegate` |
| `replaced_by` | `D<n>`, the decision that replaces it; on an `archived` decision only | `decisions/supersede.py` |

Then the title line `# D<n>. <title>`, one plain sentence, written by `queue/item.py`. `<slug>` is made from the first title, as a queue item file's slug is, and the file is never renamed. A number is never reused; the next is one above the highest decision file.

The rules of the file:

- Fixed: the front matter and the title line. Only the scripts write the front matter.
- The body is free. Bullets are the default, one rule per bullet.
- No bullet is required: there is no fixed list of bullets and no fixed section.
- A table, a code block or other formatting where it reads better. All of that is optional.

How the scripts treat it:

- `queue/item.py <release> D "<title>" --decider you|lead|agent` writes the file with `status: to-do`, the front matter it has and the `--bullet` line as the first body line. No script reads the body, and no script writes into it after that line. The session that recorded the decision writes the body by a targeted edit, then commits ([discuss.md](discuss.md), Item format, Recording). No `- Source:` line: `source` is in the front matter.
- The round of a decision is not in its file: it is `decisions.D<n>.round` in the status file. A new decision takes the highest round; `queue/item.py <release> D "<title>" --new-round` starts the next one.
- The six status words of a decision:

  | `status` | Meaning | Set by |
  |---|---|---|
  | `to-do` | Decided, in no epic | `queue/item.py D`, then the status rule |
  | `in progress` | In an epic, its work not all merged | the status rule, from the `epic` line |
  | `blocked` | In no epic, and it shares a file with a running epic | the status rule |
  | `done` | Its work merged, or closed with nothing to run | the status rule; `decisions/close.py <release> D<n>` |
  | `backlog` | Moved to another release | `decisions/close.py <release> D<n> --backlog` |
  | `archived` | Replaced by a later decision | `decisions/supersede.py <release> D<old> D<new>`, with `replaced_by` |

- Nobody sets a status by hand: `backlog` and `archived` come from a command, the others from the status rule (`lib/decisions.py`), which runs after every command that writes a decision and in every status chain (`sprints/refresh.py`, `sprints/mark.py`, `status/status.py`). A decision with rows in the Ownership table of an epic that has gone is `done` when every milestone that holds a task of a module citing it is `done` or `archived`, else `in progress`.
- `blocked`: the files of a decision are the files owned by the milestones of the specs that cite it; when no spec cites it, the files the lead gave with `epics/overlap.py <release> D<n> --files "<files>"`. A decision with no `epic` line and no row in the table of any epic file, one of whose files a running epic owns, is `blocked` with the reason `Waits for E11, same file`. It is `to-do` again by itself when that epic has merged. The owner may still put it into an epic (`compose delegate with D<n>`).
- One case of a file with no `decider` line: a decision recorded before its release moved to decision files. Every reader shows it with no decider, `status/report.py` counts such files in one line, and `decisions/decider.py <release> D<n> you|lead|agent` writes the line once.
- Built: a milestone citing the decision is `in progress`, `blocked` after its launch, or `done`. Before that, a change is an edit of its body, same id; from then on, a supersede ([discuss.md](discuss.md), Changing a decision). `decisions/supersede.py` writes nothing into the new decision: `replaced_by` of the old file holds the link.
- A decision that moves to another release is `backlog`; that release's specs cite it as `(v0.4.x D9)`.
- Specs cite a decision as `(D7)`.

## Epic file

`plan/epics/E<n>.md`, one per epic, started by `epics/new.py`, template [../templates/epic.md](../templates/epic.md); lifecycle in [discuss.md](discuss.md), Epics, reading and ack in [run.md](run.md), Epics. The front matter holds `status` and `starts` only; the Ownership table is the one copy of the epic's decisions and specs. A release of format 2.1, 2.0 or 1.0 keeps its `decisions:` and `specs:` lines: [old-form/format-2.1.md](old-form/format-2.1.md), Epic file.

```md
---
status: in progress
starts: S17
---
# E12

## Ownership

| Decision | Files | Spec | Milestone | Sprint |
|---|---|---|---|---|
| D88 One debounce hook | useDebouncedFilter.ts | 39 | Filter debounce hook | S17 |
| D90 Home hero wording | page.tsx | 49 | Home hero wording | S17 |
| D82 Multi-select opens on click | ST_FilterTextField.tsx | 41 | Filter editor fixes | S17 |
| D83 Escape closes the editor | ST_FilterTextField.tsx | 41 | Filter editor fixes | S17 |
| D81 Date filters compare dates | filterFns.ts | 40 | Date filter compare | S18 |
| D86 Range editors show both inputs | ST_FilterRangeFields.tsx | 42 | Range filter editor | S18 |

## Notes

- process.md P3, P4 changed since E11: re-read before the first launch. [ack 14:05]
- SKIP 41: D82 superseded by D95, rebuilt next epic.
```

- `status`: a copy of the epic's status in the status file (Status), written by the scripts.
- The Decision cells (`D<n> <decision title>`): `epics/new.py`, on `compose`. One row per decision until the specs exist; a rerun adds only the missing rows. The decisions of the epic are the D ids of the Decision column.
- Files: the spec writer, before it writes specs: the files the decision changes, paths as the project writes them, several separated by `, `.
- Spec, Milestone and Sprint: `epics/table.py <release> E<n>`, from the specs. One row per decision and spec of the epic citing it (`(D82)`); a spec of the epic citing none of its decisions gets a row with an empty Decision cell. Milestone is the spec's milestone name, several joined by `; `. Sprint is that milestone's sprint, a range `S17 to S19` when the spec's milestones span several. Before go the sprints are provisional (the current sprint as the epic's start); go writes the real ones, and every later `sprints/refresh.py` run keeps the Sprint column of an unfinished epic in step with the status file. Rows are ordered by sprint, then spec number, then decision number. The specs of the epic are the Spec column and the specs with its `- Epic: E<n>` line.
- `starts`: `run/go.py` (through `epics/tag.py`), on go. `starts: S<n>` is the epic's start sprint, written once and never changed: no milestone of the epic sits in an earlier sprint. An epic that has not gone has the line with no value.
- The table shows the plan; it does not pass or fail it. `epics/table.py` lists the Files paths that do not exist yet (a new file and a typo look the same); `status/report.py` does not. `status/report.py` flags a row file no milestone of its spec owns and a Sprint cell that disagrees with the status file. The go fails when a decision of the table is cited by no spec of the epic.
- `## Notes` exists only when something the specs cannot hold must be said: a rule changed since the last epic, owner context such as a tried-and-rejected option, a cross-epic order, the lead's moves during the run (SKIP, HOLD). Written with `epics/new.py <release> E<n> --note "<text>"`, which creates the section. Nothing restates a decision, a spec or a tracker.
- An urgent note starts with `Urgent:`; a RULES line is one.
- ` [ack HH:MM]` is appended by the runner when it has read the note; a note without it is unread.

## The grid

The grid is a view of the status file: `sprints/grid.py <release>` prints it on stdout and writes nothing. No file holds it. Columns are the sprints `S1`, `S2`, ... that `lib/ownership.py` computes and the status file stores. Rows are the milestones of specs that carry a `- Epic: E<n>` line (written under the title line by `epics/tag.py`); row text is the epic label, the spec number and the milestone name; rows sorted by epic, then spec number, then milestone order in the spec. Each milestone has one mark, in the column of its sprint:

```md
# v0.9.x sprints

Updated: 2026-11-28 12:10

| Milestone | S1 | S2 |
|---|---|---|
| E1 01 Row virtualizer | [x] |  |
| E1 02 Sticky footer | [ ] |  |
| E2 03 Resize handle |  | · |
| E2 04 Footer typo fix |  | [~] |

Marks: `·` to-do, `[ ]` in progress, `[~]` blocked, `[x]` done, `[!]` archived.
```

A release of format 2.1, 2.0 or 1.0 keeps the grid in the file `status/sprints.md`: [old-form/format-2.1.md](old-form/format-2.1.md), The grid file.

## Milestone status

A milestone has one of five statuses, stored in the status file (Status): `to-do`, `in progress`, `blocked`, `done`, `archived`. The grid mark, the page and the progress reply show the same status.

| Status | Grid mark | Meaning |
|---|---|---|
| `to-do` | `·` | nothing of it is in work |
| `in progress` | `[ ]` | work is happening |
| `blocked` | `[~]` | paused, with a reason: it resumes when the lead or the owner acts |
| `done` | `[x]` | merged |
| `archived` | `[!]` | ended without merge, stopped by a decision |

- `sprints/mark.py <release> <milestone> <verb>` sets it: `launch` `in progress`, `wait --reason` `blocked` (from `to-do` only for a lead hold), `merge --commit <sha>` `done`, `stop --reason` `blocked`, `stop --reason "D<n> ..."` `archived`. `launch` on a `blocked` milestone resumes it. The reason stays in the status file and in the tracker's `## Attention`.
- `launched` in the milestone's entry of the status file is `true` from its first `launch`, and stays `true`.
- `resume` ends a hold: on a `blocked` milestone it sets `in progress` when `launched` is `true` and `to-do` when it is not.
- A `blocked` milestone counts as started and unfinished, like `in progress`: it keeps its sprint and its epic is not finished. A `blocked` milestone never launched is placed again like a `to-do` one and does not make its spec built. Only `done` meets a dependency, so the dependents of a blocked milestone are not launched and not stopped.
- In a release of format 1.0 the status of a milestone is its grid mark and the `Status:` line of its tracker: [old-form/format-2.1.md](old-form/format-2.1.md), The grid file.

## Tracker

One per milestone: `run/trackers/NN-<slug>-tracker.md` for a milestone of spec NN (the first milestone may use the spec's slug, a later one the slug of its name). A milestone added later (`plan/milestone.py add`) follows the spec it belongs to: `NN-<name slug>-tracker.md`. Template [../templates/tracker.md](../templates/tracker.md).

```md
# 01: examples per edition, tracker

Status: done (3361e3e8)
Branch `v0.6/examples-per-edition`, worktree 07
Checks:
- Check: lint, `pnpm lint` at 60434a81: pass
- Check: check:bases, `pnpm check:bases` at 60434a81: pass

- Task 1 layout: done (c3bcf345)
- Task 2 edition copies: done (8286e7a2, wf_abc123)

## Attention

- Staging for the queue, one bullet per item, self-explanatory first line.

## Notes

- Only what a later task, a resume or the owner would otherwise rediscover.
```

- `Status:` (format 1.0 only) is one of the five of [old-form/format-2.1.md](old-form/format-2.1.md), The grid file, its detail in brackets. `stopped (D<n>)` is a SKIP, `D<n>` the superseding decision. `waiting` is a milestone that is built and stopped until the lead or the owner acts, `<what>` in a few words (`waiting (lead: comparison table check)`); the scripts count it as running for a decision's state, and the progress reply lists it under Blocked. Whoever stops the milestone writes it, in the tracker copy it already writes: the builder or the verifier in the milestone worktree, or the runner; the runner writes a hold on a milestone that has not started in the main checkout's copy ([run.md](run.md), Milestones and sprints).
- Required: the header lines. A tracker of an old-form spec keeps its lines `- Task 1 <name>: done (<commit>, <workflow run id>)`; in a release with `status.json` the tracker holds no status and no task list (Status). While the milestone runs, its run id is in `status/data/runs.json`, written at launch by `run/runs.py` (git-ignored, in the main checkout, the newest id wins), not in the tracker.
- A fix's tracker cites its queue items on its first line, for example `# 41: Range field blur (Q3, Q4), tracker`.
- `Checks:` is followed by one bullet per check: command, commit, result. The integration milestone's suite run on the staging branch gets its own bullet.
- `## Attention` and `## Notes` are optional. Empty is the normal case. Do not spend tokens on notes.
- Never: review-round narration, check output, commit lists.
- Writers: `plan/milestone.py add` creates the milestone's tracker, `run/trackers/NN-<name slug>-tracker.md`, for every milestone, the first of a spec included; `plan/new_spec.py` creates no tracker. In a format 1.0 release the tracker starts with `Status: planned`, `plan/new_spec.py` creates the tracker of the spec's first milestone (`NN-<spec slug>-tracker.md`) and the spec writer creates every further one from the template. In the run, the builder fills it, the fixer and the verifier update it. One worktree per milestone, so no conflicts. In a format 1.0 release the merger sets `done (<commit>)` in the main checkout, whose copy stays `planned` until the merge, apart from a hold before launch; `status/progress.py` reads the most advanced copy across the worktrees.
- The runner writes handoffs. Both sessions write the decisions and the queue (Shared files).

## Status

For a release with `status/data/status.json`. These are the words of format 2.2; a release of format 2.1 or 2.0 keeps the words of [old-form/format-2.1.md](old-form/format-2.1.md), Status words.

- Every epic, spec, milestone and task has one of five of the six status words: `to-do`, `in progress`, `blocked`, `done`, `archived`. `backlog` is for a queue item only. `blocked` and `archived` carry a short reason; its full text is in the milestone's tracker under `## Attention`. Every command takes the words of format 2.1 too (`not started` is `to-do`, `skipped` is `archived`) and stores the word of the release's format.
- `status/data/status.json` is the only store, for every epic, spec, milestone and task, and it is committed by the sync: a status change writes the files and makes no commit, and `status/sync.py <release>` commits every change under the release folder in one commit (at a milestone merge and when an epic becomes `done` by itself, before a handoff and a roll over by the session). The release folder can have uncommitted changes between two syncs. A release of format 2.1 or lower commits each status change at once. Writers: `status/status.py <release> set <id> "<status>" [--reason "<text>"]` for a task or a milestone, and `sprints/mark.py` for a milestone by the run's verbs (Milestone status). Nobody edits a status by hand.
- Stored: the status, reason, changed time, merge commit, sprint and `launched` of a milestone; the status, reason and changed time of a task. Counted on every write: a sprint from its milestones, a spec from its milestones and its tasks together (a spec with no milestone is `to-do`), an epic from its specs. `done` when everything inside is done or archived (`archived` when all of it is archived), `in progress` when something inside is in work or part of it is done, `blocked` when nothing is in work and something is blocked, `to-do` otherwise. `archived` is closed, never started: archived and to-do items together are `to-do`.
- The status of an epic is worked out on every build and never set (`status/status.py` refuses it):

  | The epic file says | Status | Reason |
  |---|---|---|
  | no `starts` value; a row of the table has no Spec cell (the specs are being written) | `to-do` | |
  | no `starts` value; every row has a Spec cell (the specs are ready, it waits for the owner's `delegate`) | `blocked` | `waits for delegate` |
  | a `starts` value | counted from its specs, as above | the reason of what blocks it |

  `epics/table.py` and `epics/new.py` run the status chain after their write, so the epic shows `blocked` as soon as its table is complete.
- A task change rolls up into its milestone the same way, with one difference: a milestone becomes `done` only by its merge, `sprints/mark.py <release> <milestone> merge --commit <sha>` (a commit hash, 7 to 40 hex characters). The merge is refused while a task of the milestone is `to-do`, `in progress` or blocked for another reason than the owner's look; a milestone whose tasks are all done stays `in progress` until then.
- A task whose only open Verification boxes are `Owner:` lines is `blocked` with the reason "waits for the owner's look": `status/status.py <release> set <task> done` stores that by itself, and the page data marks the task `ownerCheck`. Its milestone may merge; its spec then stays `blocked`, not `done`, and still takes new work. The owner reports the look to the lead, who ticks the box and sets the task done. With any other open box, done is refused.
- `decider`, worked out on every build of the status file, never stored in a plan file: `you` for an epic; for a task, the decider of the decision its module cites; for a spec, the decider of the first decision a module of it cites; for a milestone, the decider of the decision of its first task that has one, `agent` when none has one. The decider of a decision is the `decider` line of its decision file; a file with no `decider` line gives `""`, and so does a task or a spec that cites no decision. A release with a decision board takes the `decider` line of the queue item whose `decision` line names the decision.
- Copies, written on every change and never read back as the truth: the `status:` front matter line of the task, spec and epic file; the page data. `status/report.py` flags a `status:` line that differs from the JSON file. The grid is printed from the store (The grid).
- Ids: a task is `<spec>-<number>` (`27-03`), a milestone its tracker file name without `-tracker.md` (`27-collapse-shortcut`), a spec its number, an epic `E11`. `status/status.py <release> list --status blocked` lists what waits. A stored status is never thrown away: when a milestone or task with a status is renamed or removed, or a spec loses its Deliverables link, every script stops and names the entries until the spec is restored or each entry is removed with `status/status.py <release> drop <id>`. A set that changes nothing writes nothing.
- The file is also the data of the dashboard page: `release`, `format` (the skill version whose form the release has, written by `plan/new_release.py` and by a migration; a release with no status file is format `1.0`), `updated`, `statuses` (the six words, in the order above), `sprints`, `epics`, `specs`, `milestones`, `tasks`. An epic entry holds `reason` and `decider`; a milestone entry holds `number` (its position in its spec), `section` (`2.2.<number>`) and `ref` (`<spec>.<number>`, for example `27.1`) after its name, and `sprint`, `launched` and `decider`. A filled file: [../example/v1.0.x/owner/status/data/status.json](../example/v1.0.x/owner/status/data/status.json).
- `decisions`: one entry per decision, `D<n>`, with `round` (Decision file), `files` (the files the lead gave with `epics/overlap.py <release> D<n> --files`, kept while no spec cites the decision), and `hold` and `hold_reason` while the owner holds it (Waits for you line).
- The page is the dashboard page, `status/index.html`, a copy of `board/dashboard.html`, with its scripts in `status/src/` (copies of `board/src/`). It has six views: Dashboard, Queue, Epics, Milestones, Tasks and Sprints. Its data, all in `status/data/`, git-ignored and written by the scripts:
  - `status.data.js` (`window.STATUS_DATA`): the status file plus `root`, the release folder on this machine, after `updated`; read by Epics, Milestones, Tasks and Sprints, and reloaded every 2 seconds while the tab is visible. A machine path is never committed.
  - `dashboard.data.js` (`window.DASHBOARD_DATA`): one row for every queue item, decision, epic, milestone and task, with `release`, `updated`, `roots`, `sources` and `rows`; read by Dashboard and Queue. A decision row takes its status and its decider from its decision file; a `blocked` decision has the reason `Waits for E11, same file`. With a decision board the row takes its status from the lane and has no decider.
  - `dashboard.json`: the same rows, indented, without `roots`: the file an agent reads.

  The three files are written together, by every command that changes a status or an item (`status/status.py`, `sprints/mark.py`, `queue/item.py`, `sprints/refresh.py` and the other commands of the status chain). A release of format 2.2 has no `queue.data.js`. The page of a release of format 2.1 or 2.0 is the task board: [old-form/format-2.1.md](old-form/format-2.1.md), Files and pages.
- The tracker of a milestone has no `Status:` line and no task list: branch, Checks, `## Attention`, `## Notes` ([../templates/tracker.md](../templates/tracker.md)).
- The process file has `updated:` in its front matter, the time its facts were last checked or changed. No other file has a timestamp.

## process.md

One rule per topic, two to five bullets, each a full sentence with the explicit fact; a code block only when the exact command matters; a header line that maps renumbered rules. Example (v0.8.x after D88):

```markdown
# Process, v0.8.x

Project facts only. The process itself is the expedition skill; commands are in `package.json`; code rules in `docs/code-of-conduct/`; what a milestone must run is in its spec.

## P1 Branches

- `claude/review`: the integration branch. Every worktree starts from it (branch `v<major>.<minor>/<slug>` created from `origin/claude/review`), and every finished milestone merges back into it.
- `dev`: the staging branch. Fast-forwarded from `claude/review` once, after the last feature sprint has merged; never pushed to otherwise.
- `master`: the release branch. Changes only by merging the release PR from `dev`; no other source branch, no direct push.

## P3 Merge

- A milestone merges into `claude/review` the moment its recorded checks pass: `merge: <milestone> (<spec>)`, then the branch is deleted local and remote. No PR, no CI wait; the next milestone starts at once.
- A small fix (a constant, a copy change, a one-file docs fix) skips the verifier and is merged from the main session.
- `act pull_request` runs `pr.yml` locally on Linux: any agent may use it when it helps; never required, never forbidden.
```

Not in this file: commands (`package.json`), code rules (coding standards), orchestration, models, attention and triage rules (this skill), anything one decision already says (cite it).

## Handoff

Written with the `write-handoff` skill.

- Attended stages (discuss, plan, triage): never written on your own. Only when the owner asks.
- Unattended run: one file per run, `run/handoffs/handoff-<run start YYYY-MM-DD-HHMM>.md`. Create it with `write-handoff` at the first milestone boundary. Rewrite it in place at each later milestone boundary and at the end.
- Every expedition handoff starts its State section with these four bullets:

  ```
  - Stage: <the Stage line of status/report.py, e.g. discuss, run (S2)>
  - Next: `/expedition <stage> <release>`, <where to start, e.g. Q1 or spec 04.1>
  - Runner: window `<runner name>` in tmux session <name>, or none; registry `~/.claude/expedition-runners.json`
  - Writer: session `<name>` `<uuid from $CLAUDE_CODE_SESSION_ID>`, so the next session can ask it or grep its transcript (`/recall`).
  ```

- No release line: the folder gives the release.
- A handoff that a new lead session starts from ends with `## Starter prompt`: two lines, each typed as its own prompt, the voice line and then the stage command:

  ```
  /caveman:ultracave
  /expedition discuss <release> Read <handoff path> and continue.
  ```

  The `roll-over` skill types each line as its own message; a person pastes them one at a time. The handoff of a roll over: [run.md](run.md), Roll over.
