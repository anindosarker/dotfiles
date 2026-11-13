# File formats

## Contents
- Shared rule
- Shared files
- queue.md
- decisions.md
- Epic file
- status/sprints.md
- Tracker
- process.md
- Handoff

## Shared rule

Every item has an ID: the `**Q<n>**` or `**D<n>**` token of its card, a heading elsewhere. Its first bullet is required and self-explanatory: a reader understands the item from it alone. Everything after it is open-ended, but in bullets. Templates: [../templates/](../templates/).

## Shared files

`decisions.md`, `queue.md` and the epic files are written by both sessions, lead and runner.

- The lane, tick and tags of a `decisions.md` card are written by the scripts only: `queue/item.py` (a new card in To do), `epics/tag.py` through `run/go.py` (`#E<n>`, In progress), the sync in `sprints/refresh.py`, `sprints/mark.py`, `plan/new_fix.py` and every `queue/item.py` call (the lanes of the Done rule), `decisions/close.py` (Done, nothing to run) and `decisions/supersede.py`. A session writes only a decision's bullets.
- Re-read the file right before every write, make a targeted edit, commit at once. No held edits.
- The next D or Q number is read from the file at write time, never from memory.
- Ids come only from `python3 -I <skill>/scripts/queue/item.py <release> D|Q "<title>"`, never typed. It locks, appends the card, commits and prints the id; the session then writes a decision's bullets under its card, each indented with one tab.
- No id is mentioned in chat or a tracker before it is allocated: refer to the item by its title.
- An id never changes after allocation.
- A duplicate filed twice keeps both ids. The later card gets the fact `Same as Q<n>.` and moves to Dropped.
- Fallback rule: a session that finds its own id taken renumbers its own item only, never the other's. With `queue/item.py` this no longer happens.
- Agents on milestone branches never edit `decisions.md`.

## queue.md

One file per release, in the release folder root, template [../templates/queue.md](../templates/queue.md): a kanban board in the obsidian-kanban Markdown format, which the owner may view and drag in the VS Code extension Unified Kanban. It holds every item raised in the release, filed in the turn it is raised (the only exception: an item raised and ruled in the same owner message goes straight to a decision). The Open lane is the queue; the other lanes are the history.

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

- Sessions change the file only through the scripts: `queue/item.py` (`Q`, `D --source`, `--move`, `--fact`), `plan/new_fix.py`, and the tag sync in `epics/tag.py` and `sprints/refresh.py`. They re-read it inside the lock, find a card by its `**Q<n>**` token and its lane by the `## ` heading above it, and leave every other byte as found, the `%% kanban:settings` block included. The extension may drop the frontmatter when it saves its settings; the next script write puts it back.
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
- `plan/new_fix.py` moves each card a fix cites to Autofix, ticked and without tags; the fix is traced through its task line and its tracker's first line, for example `(Q9)`.
- A lookup agent adds its facts to the card it was given with `queue/item.py <release> --fact Q<n> "<text>"`.
- Citations elsewhere: `(Q3)` in specs and trackers; a decision that came from a card ends with `- Source: Q3`; a fix's tracker cites `(Q3, Q4)` on its first line.
- The run reports; it does not solve. Do not research solutions for a run card.
- Not a queue card: spec text that lags shipped code, a tracker gap, a process lesson, a tooling fact with one right answer. Those go to the tracker Notes, a decision or the spec file directly (`process.md` holds project facts only); the owner sees choices only.

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
  2. Rows with a Spec cell in the Ownership table of an epic that has gone (a `Starts: S<n>` value): its own specs are the row specs that cite it `(D<n>)` in a heading line (the title line, a `### Milestone:` heading or any `#` heading), else every row spec. Done when every milestone tracker of every own spec is `merged` or `skipped`, else In progress.
  3. No such row: Done when it is closed by hand (a ticked card in Done: `decisions/close.py <release> D<n>` for a decision with nothing to run) or when any spec citing it has merged; In progress when it carries `#E<n>`; else To do.
  A release spec that only names a decision in its text does not keep that decision open.
- The board may be viewed in the Unified Kanban extension, but a drag or a tick there is not a state change: `status/report.py` flags a card whose lane disagrees with the Done rule or whose tick disagrees with its lane, and the next sync moves it back.
- Built: a milestone citing the decision has a `[ ]` or `[x]` cell in `status/sprints.md`. Before that, a change is an edit of its bullets, same id; from then on, a supersede.
- Supersede: `decisions/supersede.py <release> D7 D15` marks both sides: D7 gets `(superseded by D15)` at the end of its title and `#superseded`, and moves to Done; D15's first bullet is `- Supersedes D7.` The mark is the only edit an old decision ever gets.
- Deferred to another release: add the bullet `- Deferred to v0.5.x`; the sync adds `#deferred` and moves the card to Done. That release's specs cite it as `(v0.4.x D9)`.
- A decision that came from a card ends with `- Source: Q<n>`, the last bullet.
- Specs cite a decision as `(D7)`.

## Epic file

`plan/epics/E<n>.md`, one per epic, started by `epics/new.py`; lifecycle in SKILL.md stage 1, reading and ack in [run.md](run.md), Epics.

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
| Row virtualizer  D101 | [x] |  |
| Sticky footer  D102 | [x] |  |
| Resize handle  D104, D105 |  | [ ] |
```

## Tracker

One per milestone: `run/trackers/NN-<slug>-tracker.md` for a milestone of spec NN (the first milestone may use the spec's slug, a later one the slug of its name). A fix follows the spec it belongs to: `NN-<title slug>-tracker.md` for a fix milestone of spec NN, `NN.M-<slug>-tracker.md` for a follow-up spec. Template [../templates/tracker.md](../templates/tracker.md).

```md
# 01: examples per edition, tracker

Status: merged (3361e3e8)
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

- `Status:` is `planned`, `running`, `waiting (lead: <what>)` or `waiting (owner: <what>)`, `merged (<commit>)` or `skipped (D<n>)` (a SKIP, `D<n>` the superseding decision). `waiting` is a milestone that is built and stopped until the lead or the owner acts, `<what>` in a few words (`waiting (lead: comparison table check)`); its grid cell stays `[ ]`, the scripts count it as running for a decision's state, and the progress reply lists it under Blocked. Whoever stops the milestone writes it, in the tracker copy it already writes: the builder or the verifier in the milestone worktree, or the runner ([run.md](run.md), Milestones and sprints).
- Required: the header lines and one line per task, with the last commit and the workflow run id of the run that covered the task.
- A fix's tracker cites its queue cards on its first line, for example `# 41: Range field blur (Q3, Q4), tracker`.
- `Checks:` is followed by one bullet per check: command, commit, result. The integration milestone's suite run on the staging branch gets its own bullet.
- `## Attention` and `## Notes` are optional. Empty is the normal case. Do not spend tokens on notes.
- Never: review-round narration, check output, commit lists.
- Writers: `plan/new_fix.py` creates a fix's tracker with `Status: planned`; `plan/new_spec.py` creates the spec's first milestone's tracker with `Status: planned`; the spec writer creates every further milestone's tracker from the template with `Status: planned` in stage 2, when the milestone block is written. In the run, the builder fills it, the fixer and the verifier update it, the merger sets `merged` in the main checkout. One worktree per milestone, so no conflicts. The main checkout's copy stays `planned` until the merge; `status/progress.py` reads the most advanced copy across the worktrees.
- The runner writes handoffs. Both sessions write `decisions.md` and `queue.md` (Shared files).

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
- Every expedition handoff starts its State section with these three bullets:

  ```
  - Stage: <the Stage line of status/report.py, e.g. discuss, run (S2)>
  - Next: `/expedition <stage> <release>`, <where to start, e.g. Q1 or spec 04.1>
  - Runner: window `<release> runner<n>` in tmux session <name>, or none; registry `~/.claude/expedition-runners.json`
- Writer: session `<name>` `<uuid from $CLAUDE_CODE_SESSION_ID>`, so the next session can ask it or grep its transcript (`/recall`).
  ```

- No release line: the folder gives the release.
