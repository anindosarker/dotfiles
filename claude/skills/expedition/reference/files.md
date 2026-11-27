# Release files

## Contents
- Layout
- <release>-plan.md sections
- Ownership
- status/sprints.md
- Scripts
- Template
- Conventions

## Layout

```
.ai/plans/v0.<n>.x/<owner>/
├── <release>-plan.md       ← authored: ## Goals, ## Deliverables
├── decisions.md            ← accepted decisions, a kanban board: D<n> cards in three lanes (To do, In progress, Done), lane by the Done rule
├── queue.md                ← every card filed in the release, a kanban board: Q<n> cards in five lanes (Open, Decided, Later, Dropped, Autofix)
├── process.md              ← this project's facts for the release, about ten P<n> rules, two to five explicit bullets each (branches, milestone branch and worktree, merge, release, checks on the shared machine, agent sandbox, public surface, commits, shared files, plans); copied from the previous release by plan/new_release.py, audited and rewritten rule by rule with the owner before the run (SKILL.md, Process notes)
├── plan/specs/NN-<slug>/   ← authored: one spec, NN-<slug>.md: modules in 1.6, task pointers in 2.1, one #### 2.2.N Milestone: <name> block per milestone in 2.2; tasks/NN-<slug>.md its task files
├── plan/epics/E<n>.md     ← one per epic, started by epics/new.py: Decisions, Specs and Starts lines, the Ownership table, Notes only when the specs cannot hold something, acked by the runner
├── run/trackers/NN-<slug>-tracker.md ← one per milestone: branch, check lines, staged attention items, notes; no status
├── run/handoffs/          ← write-handoff output
├── status/sprints.md       ← generated, like everything under status/ (never edited by hand); sprints/refresh.py, by run/go.py: the grid, one row per milestone, one column per sprint; its marks set by sprints/mark.py only
├── status/index.html       ← the status page, a render, git-ignored, never committed: in a release of format 2.0 the task board, copied from board/task-board.html by plan/new_release.py and kept current by sprints/swimlanes.py; in a format 1.0 release the swimlane page from board/swimlanes.html
├── status/data/status.json ← the store of every status (epic, spec, milestone, task) and the data of the status board; written by status/status.py and sprints/mark.py only; committed
├── status/data/status.data.js ← the task board's data, rewritten with every status change; git-ignored, never committed. sprints.data.js and sprints.json, the swimlane page's data, are written only in a format 1.0 release
├── status/data/go.log      ← run/go.py: one line per runner step done (the spec writer's window closed, the RUN line sent) per epic, so a rerun skips it; git-ignored
├── status/data/runs.json   ← run/runs.py: the Workflow run id of each milestone, written by the runner at launch, the newest id wins; read by run/check.py; git-ignored
├── status/data/.ids.lock   ← the write lock every writing script takes (ids, the queue, decisions, the grid and its marks); an empty file, git-ignored with the folder
└── reference/              ← optional supporting material, by hand
```

Where the root folder, the project repo, the worktrees folder and `.ai/plans/` sit, and what the lead asks before a project's first release folder: [first-run.md](first-run.md).

A release folder in an older layout is refused by the scripts with one line naming a `migrate/` script: [migrate.md](migrate.md).

Formats of each file: [formats.md](formats.md).

## <release>-plan.md sections

Exactly two, in order: `## Goals`, `## Deliverables`. No other `## ` section. Process rules are cited `(P<n>)`, never repeated.

Deliverables table: columns `#`, `Spec` (linked to the spec file), `Epic` (filled at go), `Scope`. Scope is one outcome sentence under 120 characters: no file lists, no mechanics; the spec file holds them.

Milestones live in the spec files, not in `<release>-plan.md`: each spec holds one `#### 2.2.N Milestone: <name>` block per milestone (a format 1.0 spec: `### Milestone: <name>`), with the lines of the contract ([plan.md](plan.md), The contract). Branch and worktree are assigned at launch and recorded in the milestone's tracker, never in the spec.

Checks live in each task's Verification list and the release's `process.md`; Acceptance in each spec's `Acceptance:` line (programmatic or judged); the release in the release spec; sandbox rules in `process.md`.

`<release>-plan.md` is not frozen: specs add rows, each go fills their Epic cells.

## Ownership

- `lib/ownership.py` computes the ownership facts from those blocks, in memory; no file holds them, and every script that needs them (`sprints/check.py`, the grid chain, `sprints/swimlanes.py`, `status/report.py`, `plan/milestone.py`, `run/go.py`) calls the same code.
- An edge from A to B exists when B lists A under `Depends on` or when A and B share a file (lower spec number first); a milestone with no `Files owned` line shares no file.
- A milestone's sprint is the longest chain ending at it plus one, across every epic, and never before its epic's start sprint: the `Starts: S<n>` line of `plan/epics/E<n>.md`, written on go by `epics/tag.py` as the current sprint.
- The start sprint carries along the edges.
- An epic file without a `Starts:` value means no floor.
- A milestone added after go carries its own `- Starts: S<n>` line (`plan/milestone.py` writes the current sprint), so it never lands in a finished sprint.
- A milestone whose grid row is running or waiting (`[ ]`, `[~]`) or finished (`[x]`, `[!]`) keeps that sprint, and a finished one never collides on a shared file.
- The current sprint is the first column of `status/sprints.md` holding a `[ ]`, `[~]` or `·` cell of an epic row; when there is none, the column after the last column holding an epic row (S1 on an empty grid).
- For an epic's own start its own rows are ignored.
- An epic's critical path is the longest chain over that epic's milestones and the edges between them, ties by lower spec number; it is computed where it is shown (the `sprints/check.py` printout, `status/report.py`, the swimlane data), never stored.
- Each epic file's Ownership table shows the epic's share of these facts: the files per decision, the spec and milestones that own them and their sprint ([formats.md](formats.md), Epic file).
- A file shared by two milestones of the same sprint, or a dependency cycle, is a script error naming the file and the two milestones, fixed in the spec.

- Every file the release changes has exactly one milestone owner while it runs.
- Two milestones that share a file sit in different sprints, or the two merge.
- Shared files no milestone owns (`<release>-plan.md` appends, changelog blocks, generated registry and docs copies) follow the release's `process.md`.
- What two or more milestones need (dependency adds, lockfile, lint or CI config, shared helpers, baseline captures) lands as the first sprint's shared milestone.

## status/sprints.md

In `status/`: a title, an `Updated: <date time>` line, one table `Milestone`, `S1` .. `Sn`. Grid only: one row per milestone of a spec with an Epic line, row text `E1 01 Filtering` ([formats.md](formats.md)). A cell is one of the marks of [formats.md](formats.md), Milestone status. No legend, no prose, nothing under the table.

- `sprints/refresh.py` writes it on go (`run/go.py`, the epic's rows with `·`); `sprints/mark.py` sets each mark at a boundary (`launch`, `wait`, `resume`, `merge`, `stop`) and reruns the same chain, so nothing under `status/` is edited by hand.
- A regeneration keeps every finished cell (`[x]`, `[!]`) where it is; a running or waiting row (`[ ]`, `[~]`) keeps its sprint (`lib/ownership.py` pins it) and a not-started row (`·`, or `[~]` never launched) is placed again.
- Then the Sprint column of every unfinished epic's table that has a `Starts:` value follows the grid; nothing else in those files changes, and finished epics' files are left alone.
- `status/report.py` flags a `status/sprints.md` whose rows differ from the milestones.

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

- Citations: `(D7)` for a decision, `(Q3)` for a queue card, `(P2)` for a process rule, `(v0.4.x D9)` for a decision of another release. `status/report.py` also reads the older `(decision N)` form.
- `<release>-plan.md` lists `#`, `Spec`, `Epic`, `Scope` only. No duration or size column.
- No questions in plan files. They stay in chat until answered.
- No em dashes in any release file.
