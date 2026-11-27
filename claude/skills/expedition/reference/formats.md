# File formats

## Contents
- Shared rule
- Shared files
- queue.md
- Settled list
- decisions.md
- Epic file
- status/sprints.md
- Milestone status
- Tracker
- Status
- process.md
- Handoff

## Shared rule

Every item has an ID: the `**Q<n>**` or `**D<n>**` token of its card, a heading elsewhere. Its first bullet is required and self-explanatory: a reader understands the item from it alone. Everything after it is open-ended, but in bullets. Templates: [../templates/](../templates/).

## Shared files

`decisions.md`, `queue.md` and the epic files are written by both sessions, lead and runner.

- The lane, tick and tags of a `decisions.md` card are written by the scripts only: `queue/item.py` (a new card in To do), `epics/tag.py` through `run/go.py` (`#E<n>`, In progress), the sync in `sprints/refresh.py`, `sprints/mark.py`, `status/status.py`, `plan/milestone.py` and every `queue/item.py` call (the lanes of the Done rule), `decisions/close.py` (Done, nothing to run) and `decisions/supersede.py`. A session writes only a decision's bullets.
- Re-read the file right before every write, make a targeted edit, commit at once. No held edits.
- The next D or Q number is read from the file at write time, never from memory.
- Ids come only from `python3 -I <skill>/scripts/queue/item.py <release> D|Q "<title>"`, never typed. It locks, appends the card, commits and prints the id; the session then writes a decision's bullets under its card, each indented with one tab.
- No id is mentioned in chat or a tracker before it is allocated: refer to the item by its title.
- An id never changes after allocation.
- A duplicate filed twice keeps both ids. The later card gets the fact `Same as Q<n>.` and moves to Dropped.
- Fallback rule: a session that finds its own id taken renumbers its own item only, never the other's. With `queue/item.py` this no longer happens.
- Agents on milestone branches never edit `decisions.md`.

## queue.md

One file per release, in the release folder root, template [../templates/queue.md](../templates/queue.md): a kanban board in the obsidian-kanban Markdown format, which the owner may view and drag in the VS Code extension Unified Kanban. It holds every card filed in the release: every owner remark, and every other item that passes the bar at filing, filed in the turn it is raised. The Open lane is the queue; the other lanes are the history.

```md
---
kanban-plugin: basic
---

## Open

- [ ] **Q30** Home title is too technical
- [ ] **Q31** Sidebar link does not match the theme
	- `components/sidebar.tsx:88`: the link uses the default colour, not the muted one.

## Decided

- [ ] **Q21** Change the button color #D85
- [ ] **Q23** Example intros in the short style #D83
	- One or two plain sentences per example, no option names.
- [x] **Q15** Comparison page moves to the end of Getting Started #D71 #E12
- [x] **Q5** Process file audited #D40

## Later

- [ ] **Q7** Row pinning drops hand-pinned rows on unselect all
	- `features/stRowPinning.ts:42`.

## Dropped

## Autofix

- [x] **Q9** Typo in the pinning guide

%% kanban:settings
{"kanban-plugin":"basic","lane-width":300,"date-format":"YYYY-MM-DD","time-format":"HH:mm","tag-action":"kanban"}
%%
```

- Sessions change the file only through the scripts: `queue/item.py` (`Q`, `D --source`, `--move`, `--fact`), `plan/milestone.py` (a cited card to Autofix), and the tag sync in `epics/tag.py` and `sprints/refresh.py`. They re-read it inside the lock, find a card by its `**Q<n>**` token and its lane by the `## ` heading above it, and leave every other byte as found, the `%% kanban:settings` block included. The extension may drop the frontmatter when it saves its settings; the next script write puts it back.
- Five lanes, always all present, in this order. The lane is the card's state:

  | Lane | Meaning |
  |---|---|
  | Open | Waiting to be discussed |
  | Decided | Decided; `#D<n>` names the decision |
  | Later | Parked; reopened by moving it back to Open |
  | Dropped | Will not be done |
  | Autofix | Fixed without a decision |

- A card is one top-level list item: `- [ ] **Q<n>** <title>`, then its tags. The title is a plain sentence naming the problem or idea. Two tags exist, at the end of the title line, space separated, decision before epic:

  | Tag | Meaning |
  |---|---|
  | `#D<n>` | The decision that settled the card |
  | `#E<n>` | The epic that decision is in |

  An open card usually has no tag. No other tag is written, and never a sub-bullet that holds only tags.
- **Bar at filing.** A card's first fact line says what goes wrong for a user of the library or a reader of the docs if the card is ignored. A raiser (the lead, a lookup, the runner, a builder, a verifier) that cannot say it files no card: it writes the point in its tracker's `## Notes`, or leaves it out when it has no tracker. The owner's remarks are exempt: every one is filed.
- The checkbox:

  | Lane | Box | Meaning |
  |---|---|---|
  | Open, Later | `[ ]` | Not decided |
  | Decided | `[ ]` | Ready for an epic: the decision is in To do |
  | Decided | `[x]` with `#E<n>` | In an epic: the decision is In progress |
  | Decided | `[x]`, no `#E` tag | Closed: the decision is Done (merged, nothing to run, superseded or deferred) |
  | Dropped, Autofix | `[x]` | Closed |

  `decisions.md` is the record. The tick and `#E<n>` of a Decided card mirror the lane of its decision; `epics/tag.py`, `sprints/refresh.py` and every `queue/item.py` call sync them, and `status/report.py` flags a card that disagrees.
- Facts are sub-bullets indented with one tab: path:line, measurement, lookup result. Every sub-bullet is a fact. Options are never written in the file. A `#word` that is not a tag is written in backticks, so the extension shows no tag badge.
- New cards go to the end of Open. A moved card goes, with its facts, to the end of its lane. Decided only through `queue/item.py <release> D "<title>" --source Q<n>`, which adds `#D<n>` to the title and leaves the card unticked; a card already in Decided keeps the highest decision number. A card leaving Decided loses its `#D` and `#E` tags.
- `plan/milestone.py add` moves each card it cites (`--cites`) to Autofix, ticked and without tags; the fix is traced through its module heading and its tracker's first line, for example `(Q9)`.
- A lookup agent adds its facts to the card it was given with `queue/item.py <release> --fact Q<n> "<text>"`.
- Citations elsewhere: `(Q3)` in specs and trackers; a decision that came from a card ends with `- Source: Q3`; a fix's tracker cites `(Q3, Q4)` on its first line.
- The run reports; it does not solve. Do not research solutions for a run card.
- Not a queue card: a point that fails the bar at filing, spec text that lags shipped code, a tracker gap, a process lesson, a tooling fact with one right answer. Those go to the tracker Notes, a decision or the spec file directly (`process.md` holds project facts only); the owner sees choices only.

## Settled list

What the lead settled or closed without the owner (SKILL.md, Weight test, Screen and Lead-side close), one plain line per item: its id, what it is in words anyone gets, what was done. No paths or commit ids.

```
Settled without you:
- D133 Filter chips keep their order after a reset: kept as built.
- Q118 Select all with pinned rows drops virtualization: fix sent to the runner.
- Q120 Same as Q84: dropped.
Name one to reopen it.
```

- Posted before the first real item of a round, and with every report of run cards that settled something. Each item is listed once.
- One line per item, never a grouped sentence ("seven kept as built (D133 to D139)").
- The owner naming a line reopens it as a normal item: a dropped card goes back with `queue/item.py <release> --move Q<n> Open`; a settled decision is discussed as a re-decided decision (SKILL.md, Changing a decision).

## decisions.md

One file per release, template [../templates/decisions.md](../templates/decisions.md): a kanban board in the card grammar of `queue.md`. Triage decisions continue the numbering.

```md
---
kanban-plugin: basic
---

## To do

- [ ] **D96** A click in a date filter box starts typing at its first part #R4
	- Native date inputs put the caret on the segment under the click, so typed digits fill only the year.
	- Source: Q80

## In progress

- [ ] **D89** Release 0.9.4 ships E12 #E12 #R4
	- Spec 48 ships E12 as 0.9.4.

## Done

- [x] **D9** Process file audited #R1
	- First bullet, required: explains the decision.
- [x] **D15** Release 0.9.0 after E2 (superseded by D28) #superseded #E3 #R2
	- ...
- [x] **D28** The 0.9.0 release waits for the owner's approval #E7 #R3
	- Supersedes D15.
	- Then anything: bullets, code blocks, examples, sub-bullets.

%% kanban:settings
{"kanban-plugin":"basic","lane-width":600,"date-format":"YYYY-MM-DD","time-format":"HH:mm","tag-action":"kanban","set-view":"list","full-list-lane-width":true,"show-add-list":false,"show-archive-all":false,"custom-title":"v0.9.x decisions"}
%%
```

- Accepted decisions only. Questions stay in chat.
- Three lanes, always all present, in this order. The lane is the decision's state, and the checkbox is `[x]` only in Done:

  | Lane | Meaning |
  |---|---|
  | To do | Decided, in no epic |
  | In progress | In an epic, its own work not all merged |
  | Done | Its own work merged, closed with nothing to run, superseded, or deferred to another release |

- A card is `- [ ] **D<n>** <title> <tags>`; the decision's bullets follow, each indented with one tab. A bullet's nested lines and a fenced code block keep their own indentation after that tab; a blank line inside a fence is a lone tab, so the card stays one card. Cards are ordered by D number inside each lane. A number is never reused; the next is the highest in the file plus one.
- Tags, at the end of the title line only, space separated, in this order: `#superseded` or `#deferred` when it applies, `#E<n>` when the decision is in an epic, `#R<n>` the round it was recorded in. No other tag. A new decision takes the highest round in the file; `queue/item.py <release> D "<title>" --new-round` starts the next one.
- The Done rule, computed by `lib/decisions.py` for every script:
  1. A `(superseded by D<n>)` mark or a `- Deferred to` bullet: Done.
  2. Rows with a Spec cell in the Ownership table of an epic that has gone (a `Starts: S<n>` value): its own specs are the row specs that cite it `(D<n>)` in a heading line (the title line, a `### Milestone:` heading or any `#` heading), else every row spec. Done when every milestone tracker of every own spec is `done` or `stopped`, else In progress. In a new-form spec only the milestones count that hold a task of a module citing it: the decision is Done when each of them is `done` or `skipped`, also while other milestones of the spec run; a citing module with no task in a milestone keeps it In progress.
  3. No such row: Done when it is closed by hand (a ticked card in Done: `decisions/close.py <release> D<n>` for a decision with nothing to run) or when any spec citing it has merged; In progress when it carries `#E<n>`; else To do.
  A release spec that only names a decision in its text does not keep that decision open.
- The board may be viewed in the Unified Kanban extension, but a drag or a tick there is not a state change: `status/report.py` flags a card whose lane disagrees with the Done rule or whose tick disagrees with its lane, and the next sync moves it back.
- Built: a milestone citing the decision has a `[ ]`, `[~]` or `[x]` cell in `status/sprints.md`; a `[~]` row never launched does not count (Milestone status). Before that, a change is an edit of its bullets, same id; from then on, a supersede.
- Supersede: `decisions/supersede.py <release> D7 D15` marks both sides: D7 gets `(superseded by D15)` at the end of its title and `#superseded`, and moves to Done; D15's first bullet is `- Supersedes D7.` The mark is the only edit an old decision ever gets.
- Deferred to another release: add the bullet `- Deferred to v0.5.x`; the sync adds `#deferred` and moves the card to Done. That release's specs cite it as `(v0.4.x D9)`.
- A decision that came from a card ends with `- Source: Q<n>`, the last bullet.
- Specs cite a decision as `(D7)`.

## Epic file

`plan/epics/E<n>.md`, one per epic, started by `epics/new.py`. In a release with `status/data/status.json` the three lines are front matter, with the epic's status first (`status:`, `decisions:`, `specs:`, `starts:`), as in [../templates/epic.md](../templates/epic.md); the line form below is the one of earlier releases, and the scripts read both; lifecycle in SKILL.md stage 1, reading and ack in [run.md](run.md), Epics.

```md
# E12

Decisions: D81, D82, D83, D86, D88, D90
Specs: 39, 40, 41, 42, 49
Starts: S17

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

- `Decisions:` and the Decision cells (`D<n> <decision title>`): `epics/new.py`, on `epic`. One row per decision until the specs exist.
- Files: the spec writer, before it writes specs: the files the decision changes, paths as the project writes them, several separated by `, `.
- Spec, Milestone and Sprint: `epics/table.py E<n>`, from the specs. One row per decision and spec of the epic citing it (`(D82)`); a spec of the epic citing none of its decisions gets a row with an empty Decision cell. Milestone is the spec's milestone name, several joined by `; `. Sprint is that milestone's sprint, a range `S17 to S19` when the spec's milestones span several. Before go the sprints are provisional (the current sprint as the epic's start); go writes the real ones, and every later `sprints/refresh.py` run keeps the Sprint column of an unfinished epic in step with the grid. Rows are ordered by sprint, then spec number, then decision number.
- `Specs:` and `Starts:`: `run/go.py`, on go. `Starts: S<n>` is the epic's start sprint, written once and never changed: no milestone of the epic sits in an earlier column.
- The table shows the plan; it does not pass or fail it. `epics/table.py` lists the Files paths that do not exist yet (a new file and a typo look the same); `status/report.py` does not. `status/report.py` flags a decision or spec with no row, a row file no milestone of its spec owns, and a Sprint cell that disagrees with the grid.
- `## Notes` exists only when something the specs cannot hold must be said: a rule changed since the last epic, owner context such as a tried-and-rejected option, a cross-epic order, the lead's moves during the run (SKIP, HOLD). Written with `epics/new.py <release> E<n> --note "<text>"`, which creates the section. Nothing restates a decision, a spec or a tracker.
- An urgent note starts with `Urgent:`; a RULES line is one.
- ` [ack HH:MM]` is appended by the runner when it has read the note; a note without it is unread.

## status/sprints.md

Columns are the sprints `S1`, `S2`, ... that `lib/ownership.py` computes. Rows are the milestones of specs that carry a `- Epic: E<n>` line (written under the title line by `epics/tag.py`); row text is the epic label, the spec number and the milestone name; rows sorted by epic, then spec number, then milestone order in the spec.

```md
| Milestone | S1 | S2 |
|---|---|---|
| E1 01 Row virtualizer | [x] |  |
| E1 02 Sticky footer | [x] |  |
| E2 03 Resize handle |  | [ ] |
```

## Milestone status

This section is for a release made before `status/data/status.json`; a release that has the file follows Status below. A milestone has one of five statuses. The grid cell, the tracker `Status:` line and the swimlane page use the same set.

| Status | Grid cell | Tracker `Status:` | Page color | Meaning |
|---|---|---|---|---|
| planned | `·` | `planned` | grey | not started |
| running | `[ ]` | `running` | blue | work is happening |
| waiting | `[~]` | `waiting (lead: <what>)` or `waiting (owner: <what>)` | amber | paused, resumes when the lead or the owner acts |
| stopped | `[!]` | `stopped (D<n>)` or `stopped (<reason in a few words>)` | red | ended without merge (blocked or skipped) |
| done | `[x]` | `done (<commit>)` | green | merged |

- `sprints/mark.py` sets the cell: `launch` `[ ]`, `wait` `[~]` (from `·` only for a lead hold), `merge` `[x]`, `stop` `[!]`. `launch` on a `[~]` cell resumes the milestone. The reason stays in the tracker: the `Status:` brackets and `## Attention`.
- `resume` ends a hold: on a `[~]` cell it sets `[ ]` when the milestone was launched before and `·` when it never was. Launched before means a commit `docs(plan): <release> <milestone> launch` of `mark.py` is in the history of `status/sprints.md`; the tracker cannot tell, since the main checkout's copy may lack the `Branch` line until the merge.
- A `[~]` row counts as started and unfinished, like `[ ]`: it keeps its column and its epic is not finished. A `[~]` row never launched moves like a `·` row and does not make its spec built. Only `[x]` meets a dependency, so the dependents of a waiting milestone are not launched and not stopped.
- Trackers written before this set say `merged (<commit>)` or `skipped (D<n>)`. The scripts read them as done and stopped; nothing writes them. `migrate/statuses.py <release>` converts a folder.

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

- Staging for queue.md, one bullet per item, self-explanatory first line.

## Notes

- Only what a later task, a resume or the owner would otherwise rediscover.
```

- `Status:` is one of the five of Milestone status, its detail in brackets. `stopped (D<n>)` is a SKIP, `D<n>` the superseding decision. `waiting` is a milestone that is built and stopped until the lead or the owner acts, `<what>` in a few words (`waiting (lead: comparison table check)`); the scripts count it as running for a decision's state, and the progress reply lists it under Blocked. Whoever stops the milestone writes it, in the tracker copy it already writes: the builder or the verifier in the milestone worktree, or the runner; the runner writes a hold on a milestone that has not started in the main checkout's copy ([run.md](run.md), Milestones and sprints).
- Required: the header lines. A tracker of an old-form spec keeps its lines `- Task 1 <name>: done (<commit>, <workflow run id>)`; in a release with `status.json` the tracker holds no status and no task list (Status). While the milestone runs, its run id is in `status/data/runs.json`, written at launch by `run/runs.py` (git-ignored, in the main checkout, the newest id wins), not in the tracker.
- A fix's tracker cites its queue cards on its first line, for example `# 41: Range field blur (Q3, Q4), tracker`.
- `Checks:` is followed by one bullet per check: command, commit, result. The integration milestone's suite run on the staging branch gets its own bullet.
- `## Attention` and `## Notes` are optional. Empty is the normal case. Do not spend tokens on notes.
- Never: review-round narration, check output, commit lists.
- Writers: `plan/milestone.py add` creates the milestone's tracker, `run/trackers/NN-<name slug>-tracker.md`, for every milestone, the first of a spec included; `plan/new_spec.py` creates no tracker. In a release made before `status.json` the tracker starts with `Status: planned`, `plan/new_spec.py` creates the tracker of the spec's first milestone (`NN-<spec slug>-tracker.md`) and the spec writer creates every further one from the template. In the run, the builder fills it, the fixer and the verifier update it. One worktree per milestone, so no conflicts. In an earlier release the merger sets `done (<commit>)` in the main checkout, whose copy stays `planned` until the merge, apart from a hold before launch; `status/progress.py` reads the most advanced copy across the worktrees.
- The runner writes handoffs. Both sessions write `decisions.md` and `queue.md` (Shared files).

## Status

For a release with `status/data/status.json` (every release `plan/new_cycle.py` makes now).

- Five words everywhere: `not started`, `in progress`, `blocked`, `done`, `skipped`. `blocked` and `skipped` carry a short reason; its full text is in the milestone's tracker under `## Attention`.
- `status/data/status.json` is the only store, for every epic, spec, milestone and task, and it is committed. Writers: `status/status.py <release> set <id> "<status>" [--reason "<text>"]` for a task or a milestone, and `sprints/mark.py` for a milestone by the run's verbs: `launch` and `resume` in progress, `merge --commit <sha>` done, `wait --reason` and `stop --reason` blocked, `stop --reason "D<n> ..."` skipped. Nobody edits a status by hand.
- Stored: the status, reason, changed time and merge commit of a milestone; the status, reason and changed time of a task. Counted on every write: a sprint from its milestones, a spec from its milestones and its tasks together (a spec with no milestone is `not started`), an epic from its specs. `done` when everything inside is done or skipped (`skipped` when all of it is skipped), `in progress` when something inside is in work or part of it is done, `blocked` when nothing is in work and something is blocked, `not started` otherwise. `skipped` is closed, never started: skipped and not started items together are `not started`.
- A task change rolls up into its milestone the same way, with one difference: a milestone becomes `done` only by its merge, `sprints/mark.py <release> <milestone> merge --commit <sha>` (a commit hash, 7 to 40 hex characters). The merge is refused while a task of the milestone is `not started`, `in progress` or blocked for another reason than the owner's look; a milestone whose tasks are all done stays `in progress` until then.
- A task whose only open Verification boxes are `Owner:` lines is `blocked` with the reason "waits for the owner's look": `status/status.py set <task> done` stores that by itself, and the page data marks the task `ownerCheck`. Its milestone may merge; its spec then stays `blocked`, not `done`, and still takes new work. The owner reports the look to the lead, who ticks the box and sets the task done. With any other open box, done is refused.
- Copies, written on every change and never read back as the truth: the `status:` front matter line of the task, spec and epic file; the grid `status/sprints.md` (`·` not started, `[ ]` in progress, `[~]` blocked, `[x]` done, `[!]` skipped); the page data. `status/report.py` flags a `status:` line that differs from the JSON file.
- Ids: a task is `<spec>-<number>` (`27-03`), a milestone its tracker file name without `-tracker.md` (`27-collapse-shortcut`), a spec its number, an epic `E11`. `status/status.py <release> list --status blocked` lists what waits. A stored status is never thrown away: when a milestone or task with a status is renamed or removed, or a spec loses its Deliverables link, every script stops and names the entries until the spec is restored or each entry is removed with `status/status.py <release> drop <id>`. A set that changes nothing writes nothing.
- The file is also the data of the status board: `release`, `updated`, `statuses`, `sprints`, `epics`, `specs`, `milestones`, `tasks`. A milestone entry holds `number` (its position in its spec), `section` (`2.2.<number>`) and `ref` (`<spec>.<number>`, for example `27.1`) after its name. `status/data/status.data.js` (`window.STATUS_DATA`, git-ignored) is the same data plus `root`, the release folder on this machine, after `updated`: a machine path is never committed. A filled file: [../example/v1.0.x/owner/status/data/status.json](../example/v1.0.x/owner/status/data/status.json).
- The tracker of a milestone has no `Status:` line and no task list: branch, Checks, `## Attention`, `## Notes` ([../templates/tracker.md](../templates/tracker.md)).
- The process file has `updated:` in its front matter, the time its facts were last checked or changed. No other file has a timestamp.

## process.md

One rule per topic, two to five bullets, each a full sentence with the explicit fact; a code block only when the exact command matters; a header line that maps renumbered rules. Example (v0.8.x after D88):

```markdown
# Process, v0.8.x

Project facts only. The process itself is the expedition skill; commands are in `package.json`; code rules in `docs/code-of-conduct/`; what a milestone must run is in its spec.

## P1 Branches

- `claude/review`: the integration branch. Every worktree starts from it (branch `v<major>.<minor>/<slug>` created from `origin/claude/review`), and every finished milestone merges back into it.
- `dev`: the staging branch. Fast-forwarded from `claude/review` once, after the last feature column has merged; never pushed to otherwise.
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
