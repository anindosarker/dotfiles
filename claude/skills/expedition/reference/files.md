# Release files

## Contents
- Layout
- <release>-plan.md sections
- Ownership
- The grid
- Scripts
- Template
- Conventions

## Layout

```
.ai/plans/v0.<n>.x/<owner>/
├── <release>-plan.md       ← authored: ## Goals, ## Deliverables
├── decisions.md            ← the list of the accepted decisions, one linked line per decision file; written by the scripts only (in a release of format 2.1 or lower a kanban board of D<n> cards: old-form/format-2.1.md, Decision board)
├── decisions/D<n>-<slug>.md ← one decision file per decision: front matter (status, decider, source, epic, replaced_by), # D<n>. title, a free body (formats.md, Decision file)
├── queue.md                ← the list of every item filed in the release, one linked line per item file; written by the scripts only (in a release of format 2.0 or 1.0 a kanban board of Q<n> cards: old-form/queue-board.md)
├── queue/Q<n>-<slug>.md    ← one item file per item: front matter (status, decision, option, decider, depends_on), # Q<n>. title, ## Notes (scripts), ## Details and ## Options: (the lead, when the item settles); format 2.1 and higher
├── process.md              ← this project's facts for the release, about ten P<n> rules, two to five explicit bullets each (branches, milestone branch and worktree, merge, release, checks on the shared machine, agent sandbox, public surface, commits, shared files, plans); copied from the previous release by plan/new_release.py, audited and rewritten rule by rule with the owner before the run (SKILL.md, Process notes)
├── plan/specs/NN-<slug>/   ← authored: one spec, NN-<slug>.md: modules in 1.6, task pointers in 2.1, one #### 2.2.N Milestone: <name> block per milestone in 2.2; tasks/NN-<slug>.md its task files
├── plan/epics/E<n>.md     ← one per epic, started by epics/new.py: front matter status and starts, the Ownership table (the one copy of its decisions and specs), Notes only when the specs cannot hold something, acked by the runner
├── run/trackers/NN-<slug>-tracker.md ← one per milestone: branch, check lines, staged attention items, notes; no status
├── run/handoffs/          ← write-handoff output
├── status/index.html       ← the dashboard page, generated like everything under status/ (never edited by hand), a render, git-ignored, never committed: a copy of board/dashboard.html, made by plan/new_release.py and kept current by sprints/swimlanes.py
├── status/src/             ← the dashboard page's scripts and style, copies of board/src/ (core.js, parts.js, views.js, style.css); git-ignored
├── status/data/status.json ← the store of every status (epic, spec, milestone, task), with the sprint and launched of each milestone, and the data of the dashboard page; written by status/status.py and sprints/mark.py only; committed
├── status/data/status.data.js ← the data of the Epics, Milestones, Tasks and Sprints views, rewritten with every status change; git-ignored, never committed
├── status/data/dashboard.data.js ← the data of the Dashboard and Queue views: one row per queue item, decision, epic, milestone and task, written with status.data.js and by queue/item.py; git-ignored, never committed
├── status/data/dashboard.json ← the same rows, indented, for an agent to read; written with dashboard.data.js; git-ignored, never committed
├── status/data/go.log      ← run/go.py: one line per runner step done (the spec writer's window closed, the RUN line sent) per epic, so a rerun skips it; git-ignored
├── status/data/runs.json   ← run/runs.py: the Workflow run id of each milestone, written by the runner at launch, the newest id wins; read by run/check.py; git-ignored
├── status/data/.ids.lock   ← the write lock every writing script takes (ids, the queue, decisions, the statuses); an empty file, git-ignored with the folder
└── reference/              ← optional supporting material, by hand
```

Where the root folder, the project repo, the worktrees folder and `.ai/plans/` sit, and what the lead asks before a project's first release folder: [first-run.md](first-run.md).

A release folder in an older layout is refused by the scripts with one line naming a `migrate/` script: [migrate.md](migrate.md).

Formats of each file: [formats.md](formats.md). A release of format 2.1, 2.0 or 1.0 has `status/sprints.md` and the page and data files of its format: [old-form/format-2.1.md](old-form/format-2.1.md).

## <release>-plan.md sections

Exactly two, in order: `## Goals`, `## Deliverables`. No other `## ` section. Process rules are cited `(P<n>)`, never repeated.

Deliverables table: columns `#`, `Spec` (linked to the spec file), `Epic` (filled at go), `Scope`. Scope is one outcome sentence under 120 characters: no file lists, no mechanics; the spec file holds them.

Milestones live in the spec files, not in `<release>-plan.md`: each spec holds one `#### 2.2.N Milestone: <name>` block per milestone (a format 1.0 spec: `### Milestone: <name>`), with the lines of the contract ([plan.md](plan.md), The contract). Branch and worktree are assigned at launch and recorded in the milestone's tracker, never in the spec.

Checks live in each task's Verification list and the release's `process.md`; Acceptance in each spec's `Acceptance:` line (programmatic or judged); the release in the release spec; sandbox rules in `process.md`.

`<release>-plan.md` is not frozen: specs add rows, each go fills their Epic cells.

## Ownership

- `lib/ownership.py` computes the ownership facts from those blocks, in memory; no file holds them, and every script that needs them (`sprints/check.py`, the grid chain, `sprints/swimlanes.py`, `status/report.py`, `plan/milestone.py`, `run/go.py`) calls the same code.
- An edge from A to B exists when B lists A under `Depends on` or when A and B share a file (lower spec number first); a milestone with no `Files owned` line shares no file.
- A milestone's sprint is the longest chain ending at it plus one, across every epic, and never before its epic's start sprint: the `starts: S<n>` line of `plan/epics/E<n>.md`, written on go by `epics/tag.py` as the current sprint.
- The start sprint carries along the edges.
- An epic file without a `starts` value means no floor.
- A milestone added after go carries its own `- Starts: S<n>` line (`plan/milestone.py` writes the current sprint), so it never lands in a finished sprint.
- The status file stores the sprint of each milestone. A milestone that is `in progress`, `done` or `archived`, or `blocked` after its launch, keeps the sprint the status file holds, and a finished one never collides on a shared file. Every other milestone is placed again on each refresh.
- The current sprint is the lowest sprint that holds a milestone of an epic that is `to-do`, `in progress` or `blocked`; when there is none, the sprint after the highest one in use (S1 for a release with no sprint).
- For an epic's own start its own rows are ignored.
- An epic's critical path is the longest chain over that epic's milestones and the edges between them, ties by lower spec number; it is computed where it is shown (the `sprints/check.py` printout, `status/report.py`, the swimlane data), never stored.
- Each epic file's Ownership table shows the epic's share of these facts: the files per decision, the spec and milestones that own them and their sprint ([formats.md](formats.md), Epic file).
- A file shared by two milestones of the same sprint, or a dependency cycle, is a script error naming the file and the two milestones, fixed in the spec.

- Every file the release changes has exactly one milestone owner while it runs.
- Two milestones that share a file sit in different sprints, or the two merge.
- Shared files no milestone owns (`<release>-plan.md` appends, changelog blocks, generated registry and docs copies) follow the release's `process.md`.
- What two or more milestones need (dependency adds, lockfile, lint or CI config, shared helpers, baseline captures) lands as the first sprint's shared milestone.

## The grid

A release of format 2.2 has no grid file. `sprints/grid.py <release>` prints the grid from the status file, in the shape of [formats.md](formats.md), The grid, and writes nothing.

- `sprints/refresh.py` places the milestones and stores each sprint in the status file, on go (`run/go.py`) and after every change to the specs or the epics; `sprints/mark.py` sets a milestone's status at a boundary (`launch`, `wait`, `resume`, `merge`, `stop`) and runs the same chain, so nothing under `status/` is edited by hand.
- Then the Sprint column of every unfinished epic's table that has a `starts` value follows the status file; nothing else in those files changes, and finished epics' files are left alone.
- `status/report.py` flags a left-over `status/sprints.md` (delete it) and a milestone of an epic with no sprint in the status file (run `sprints/refresh.py`).
- A release of format 2.1, 2.0 or 1.0 keeps the file `status/sprints.md`: [old-form/format-2.1.md](old-form/format-2.1.md), The grid file.

## Scripts

Every command, its arguments, what it writes and what it refuses: [scripts.md](scripts.md).

## Template

Precedence, highest first:

1. `--template PATH` on `plan/new_spec.py`.
2. Project planning rules, found by `plan/find_rules.py`: files named like `*plan*guide*.md` or `planning*.md`, and `CLAUDE.md` or `AGENTS.md` lines that mention plan files.
   - `plan/new_spec.py` writes a contract stub and prints each path.
   - The agent then writes the spec by hand in the project's template.
   - The project rules override the bundled guidelines completely: structure, headings, rules, template.
3. Bundled default, only when no project rules are found: [planning-guidelines.md](planning-guidelines.md), which are general purpose and do not mention expedition, and the template [../templates/spec.md](../templates/spec.md), which is expedition's own and carries the added lines.

The contract applies in all three: [plan.md](plan.md), The contract. The lines expedition adds to a spec: [plan.md](plan.md), Lines the spec writer adds.

## Conventions

- Citations: `(D7)` for a decision, `(Q3)` for a queue item, `(P2)` for a process rule, `(v0.4.x D9)` for a decision of another release. `status/report.py` also reads the older `(decision N)` form.
- `<release>-plan.md` lists `#`, `Spec`, `Epic`, `Scope` only. No duration or size column.
- No questions in plan files. They stay in chat until answered.
- No em dashes in any release file.
