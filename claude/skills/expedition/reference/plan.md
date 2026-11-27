# Stage 2: plan

For the spec writer, and for the lead's check of the specs before go: read this file whole before writing or checking a spec. How to write one plan file: [planning-guidelines.md](planning-guidelines.md). The filled shape: [../example/](../example/README.md).

## Contents
- Writing the specs of an epic
- The contract
- Plan file and spec
- Modules, tasks, milestones
- Cutting an epic into specs
- Milestones
- Lines the spec writer adds
- Integration never waits on CI

## Writing the specs of an epic

Specs per epic, written by the spec writer (the session `run/runner.sh fork` opens) after `epic`, checked by the lead before `go`. Write the plan per spec, not all at once.

The spec writer's order: fill the Files column of the epic's Ownership table (the files each decision changes, paths as the project writes them); cut the epic into specs by the three aims below; write the specs; run `epics/table.py <release> E<n>` to complete the table; check the plan with that output and its own judgment, and regroup when a clearly better cut exists; send `SPECS`.

Cutting an epic into specs: weigh three aims.

- As much as possible runs side by side. Specs that do not share files can be built at the same time.
- No spec is bloated. One spec is a piece of work one builder can hold and one review can cover.
- Work is not split so finely that agents repeat each other. Changes to the same area are cheaper in one spec: a filter look change and a filter bug fix go to the same builder, who already has that code in context.

These are aims, not rules. They pull against each other, and the right cut depends on the epic. Choose the plan that is best overall, and do not bend a good plan to satisfy one aim. The ownership table and its Sprint column show the result; they do not pass or fail it. The reason for a deliberate choice (two specs sharing a file, or one larger spec) goes in the spec, in one line.

1. Write `<release>-plan.md` first, two sections only: `## Goals`, `## Deliverables` (`#`, `Spec` linked to the spec file, `Epic` filled at go, `Scope`; Scope one outcome sentence under 120 characters, no files or mechanics). Integration never waits on CI: merge on local checks that pass, merge commit per milestone; CI is the second run, on the staging branch after the one fast-forward ([run.md](run.md)). It may exist while decisions are still open. Example: [../example/v1.0.x/owner/v1.0.x-plan.md](../example/v1.0.x/owner/v1.0.x-plan.md).
2. Write a spec file only when every decision it cites is accepted. A spec waiting on an open decision stays a row in `<release>-plan.md`.
3. Create each spec with `plan/new_spec.py`. If it printed project planning rules, it wrote a contract stub. Read the rules, then write the spec by hand in the project's template. The rules override the bundled guidelines completely. Otherwise follow [planning-guidelines.md](planning-guidelines.md), which say how to write one plan file and do not mention expedition. Either way, keep the contract below and add expedition's own lines (Lines the spec writer adds, below). Specs implement decisions and never re-decide.
   - Before a spec is written, the spec writer maps every site the change touches (file:line table); the spec lists those files, not guesses.
   - A ride-along item (a timeout bump, a glob fix) joins the nearest spec as a named ride-along, never its own spec.
4. Each spec says what must be proven (its `Acceptance:` line), not how it is run; the runner picks the orchestration per sprint ([run.md](run.md), Orchestration). The spec writer writes section 1 by hand, then adds each piece of work with `plan/milestone.py add`: it writes the module heading in 1.6, the task files, their pointer lines in 2.1, the milestone block in 2.2 and the milestone's tracker. The writer then fills each module and each task file (Goals, Verification). Merge adjacent small tasks. The lines are in the contract below; the filled shape is in the example release.
5. After each spec file, run `sprints/check.py`: it computes, in memory, each milestone's sprint and each epic's critical path from the milestone blocks, and writes nothing. A file shared by two milestones of the same sprint, or a dependency cycle, is a script error naming the file and the two milestones: fix it in the spec and run `sprints/check.py` again. When the epic's specs are written, `epics/table.py <release> E<n>` completes the epic file's table. On go, `run/go.py` runs `sprints/refresh.py` then `sprints/swimlanes.py`: they write the `status/sprints.md` grid, one column per sprint, and the page data for `status/index.html` (format 2.0: `status.data.js` for the task board, `board/task-board.html`; format 1.0: the swimlane data) (see [files.md](files.md)). Checks sit in each task's Verification list and `process.md`, Acceptance in each spec's line, the release in the release spec, sandbox rules in `process.md` P5. `status/report.py` flags a missing or extra piece.
   - The run unit is the milestone: one team, its own branch, worktree, tracker and merge. Usually one milestone per spec; a spec may yield several (file groups, or a read-only side job like captures). Every changed file is owned by exactly one milestone while it runs; two milestones that share a file sit in different sprints (`lib/ownership.py` orders them, lower spec number first), or the two merge.
   - Sprints are computed across every epic: `lib/ownership.py` puts each milestone in the first sprint at or after its epic's start sprint (`Starts:` in the epic file, the current sprint at go) whose dependencies and file owners are satisfied. A milestone with a running or finished grid row keeps its sprint. A new epic never lands in a finished sprint, and a milestone added after go (`plan/milestone.py add`) starts at the current sprint ([files.md](files.md), Ownership).
   - What two or more milestones need (dependency adds, lockfile, lint or tsconfig config, CI edits, shared new helpers, baseline captures) is the shared milestone of the first sprint; later milestones never touch `package.json`, the lockfile, ESLint or CI config.
6. A decision changed after specs exist: Changing a decision ([discuss.md](discuss.md)).
7. Readiness check before go: run `status/report.py` and fix every gap it reports (missing checks or trackers, open questions, a grid out of step with the specs, an epic table out of step with its specs or the grid). No readiness review agent for epics: the lead's check on the `SPECS` message replaces it.
8. The release's `process.md`: before the first go, one `opus` audit agent reads it against this skill, the code (workflows, package manifests, coding standards) and the release's decisions, and returns a keep / cut / move / rewrite table per bullet; the main agent applies the table itself, rewrites the file (SKILL.md, Process notes: template and example first, `updated` set in the same edit) and records one short decision; nothing reaches the owner unless a bullet is a real choice (SKILL.md, Owner input). A rule that no longer applies is deleted; a rewrite of the whole file may renumber, with one line in the header mapping the old numbers (`P12 preview → D72`) so older specs and trackers still read. No placeholder left (`status/report.py` reports it). `<release>-plan.md` is not frozen: each go fills the epic's Epic cells; `status/sprints.md` moves all run long.
9. Handoff: only when the owner asks.

## The contract

The contract. It applies inside any template, and it is stated here only. Under expedition the root `<release>-plan.md` is the index with `## Goals` and `## Deliverables`, and each spec is one plan file written by the guidelines.

Part 1, what the plan file must carry. A plan written by the bundled guidelines already has all of it but the file name, which `plan/new_spec.py` sets:

- Hard, a script stops or schedules wrong without it:
  - The spec is a folder with a file of the same name and its task files beside it: `plan/specs/NN-<slug>/NN-<slug>.md` and `tasks/`. `lib/ownership.py` does not see a file with another name.
  - Section `### 1.6 Modules`: one `#### 1.6.N <title>` heading per module, what is wanted.
  - Section `### 2.1 Tasks`: one pointer line per task, `- 03 <Task title> · module 1.6.2 · tasks/03-<slug>.md`, written by `plan/milestone.py` and `plan/task.py`. Task numbers run across the spec and equal the number of the task file.
  - Section `### 2.2 Milestones`: one `#### 2.2.N Milestone: <name>` block per milestone, with `- Tasks: 01, 02`. Milestone names are unique across the release and hold no `|`; a repeat is a `sprints/check.py` error. Trackers, the grid and `Depends on` use the name.
  - A name on a `- Depends on:` line exists: exact milestone names, spec numbers, or `none`. An unknown name is a `sprints/check.py` error.
  - A task file: front matter `status` and `type` (`feat` or `bug`), the title, `## Goals`, and a `## Verification` checklist. A line of it may start with `Browser:` (the builder checks it in a browser) or `Owner:` (the owner checks it himself). The quote of the owner's words and `## Instructions` are optional; an agent never writes the quote.
- Suggestions. A script reads the line when it is there and reports nothing when it is not:
  - `- Files owned: a, b` in a milestone block, when it could clash with other running work. A milestone without the line is not part of the overlap check.
  - `- Depends on:` in a milestone block, only where two pieces of work touch the same thing. With no line, a milestone is built at the same time as the others.
  - Sections 1.3, 1.4, 1.5 and 1.7 of the spec: left out when empty.
- Shown only as `status/report.py` warnings, fixed in the readiness check (step 7):
  - A pointer whose task file is missing, and a task file with no Verification box.
  - One `- Acceptance:` line per spec.
  - No open question in a plan file. The report flags each line that ends in `?`.
  - A `status:` front matter line that differs from `status/data/status.json`: a status edited by hand.
- Growth: a spec whose status is not `done` takes a new module, task files and a milestone at any time (`plan/milestone.py add`). Each new piece of work is its own milestone; a task joins an existing milestone only while that milestone is `not started`. A spec that is `done` takes nothing: work on the same subject is a new spec.
- Status: five words, `not started`, `in progress`, `blocked`, `done`, `skipped`; `blocked` and `skipped` carry a short reason. `status/data/status.json` is the only store, for every epic, spec, milestone and task; `status/status.py` and `sprints/mark.py` are its only writers. A milestone is `done` only by its merge (`sprints/mark.py ... merge --commit <sha>`); a spec is counted from its milestones and its tasks, an epic from its specs. The `status:` line of a task, spec or epic file and the grid `status/sprints.md` are copies it writes. Nobody edits a status by hand. The rules: [formats.md](formats.md), Status.
- A format 1.0 release keeps its form and is read unchanged; no release is converted by itself. There a spec is one flat file `plan/specs/NN-<slug>.md` (follow-up specs `NN.M-<slug>.md`) with `### Milestone: <name>` blocks and `- Task N: ... Checks: ...` lines, `- Files owned:` is required in each block, and statuses are the grid marks and the tracker `Status:` lines ([SKILL.md](../SKILL.md), Format 1.0 releases).

Part 2, what the spec writer adds on top. No planning guidelines need to mention these:

- Hard: `(D7)` on the heading of the module that carries decision D7 (`#### 1.6.2 <title> (D7)`), outside code fences. `epics/tag.py`, `epics/table.py` and `run/go.py` find an epic's specs by these cites; the Done rule and the status file find a decision's milestones through the tasks of that module.
- `(Q3)` for a queue card, `(v0.4.x D9)` for a decision of another release.
- `- Review: none | fable` in each milestone block. No script acts on it; the runner reads it when it writes the workflow script.
- `- Local CI:` in each milestone block (SKILL.md, Process notes).
- The reference and the judges on the `- Acceptance:` line, when the Acceptance is judged ([run.md](run.md), Milestones and sprints, the Acceptance bullet).
- `- Epic: E<n>` and `- Starts: S<n>` are written by `epics/tag.py` and `plan/milestone.py`, never by hand.

When to use each line of part 2, with an example block: Lines the spec writer adds, below.

Project planning rules override the bundled guidelines completely. A project template that lacks a line of part 1 gets it added in that project's style. The lines of part 2 are added to every spec, whatever template it follows. Nothing else in the template changes.

## Plan file and spec

- Under expedition the root plan file `<release>-plan.md` is an index with two sections only, `## Goals` and `## Deliverables` ([files.md](files.md), `<release>-plan.md` sections).
- Each spec, `plan/specs/NN-<slug>/NN-<slug>.md`, is one plan file written by the guidelines. Where the guidelines say "plan", read "spec". Its task files are in `tasks/` of the same folder.
- The plan folder of the guidelines is the release folder `.ai/plans/v0.<n>.x/<owner>/`. `<owner>` is the folder name the scripts find, the most common folder name under `.ai/plans/v*.x/`, or the value of `--owner`; it is not read from `git config`. Its other files and folders belong to expedition: [files.md](files.md), Layout.
- A scope agreed in discussion is recorded in `decisions.md` before the spec is written. The spec implements the decision and never re-decides it.
- A question is asked in chat. Once the owner has answered it and said the explicit word, the answer goes to `decisions.md`, never into a spec.

## Modules, tasks, milestones

One kind of spec, three levels, one home each. The filled shape: [../example/v1.0.x/owner/plan/specs/27-sidebar/](../example/v1.0.x/owner/plan/specs/27-sidebar/27-sidebar.md).

- **Module**, section `1.6.N` of the spec: what is wanted and how it should behave. Its heading carries the decision cite, `#### 1.6.2 Collapse shortcut (D58)`.
- **Task**, a file in `tasks/`: the work. Front matter `status` and `type`, the title, an optional quote of the owner's own words (never written by an agent), `## Goals`, optional `## Instructions`, and a `## Verification` checklist. Template: [../templates/task.md](../templates/task.md).
- **Milestone**, section `2.2.N` of the spec: the tasks that are built and merged together. One branch, one worktree, one tracker.
- `2.1 Tasks` is a list of one-line pointers, `- 03 <Task title> · module 1.6.2 · tasks/03-<slug>.md`, written by the scripts.
- New work is always the same three additions, made by one command, `plan/milestone.py add`: the next module, one or more task files, a milestone. Numbers only go up.
- Each piece of work is its own milestone and is built at the same time as the others. `Depends on` is written only where two of them touch the same thing.
- A Verification line is a fact that can be seen when the task is done. A plain line: the builder checks it. `Browser:` the builder checks it in a browser. `Owner:` the owner checks it himself, and no agent opens a browser for it. Lint, type-check and build are never listed.
- A spec that is not `done` takes new modules, tasks and milestones. A spec that is `done` is finished; later work on the same subject is a new spec.

## Cutting an epic into specs

The three aims to weigh, and what to do when they pull against each other: Writing the specs of an epic, above.

## Milestones

- A milestone is one branch, one worktree, one tracker and one merge, and it sits in one sprint. The guidelines call it a named group of tasks; under expedition it is also the run unit.
- `lib/ownership.py` reads the `#### 2.2.N Milestone: <name>` blocks and computes the dependency edges and the run order. An edge exists for a listed dependency or a shared file, the lower spec number first. Milestones without such a reason run at the same time.
- A file shared by two milestones of one sprint is a script error, fixed in the spec. The full rules: [files.md](files.md), Ownership.
- `- Depends on:` takes exact milestone names, spec numbers (`03` or `spec 03`), or `none`.
- A task's Verification list names its checks per base where the repository has bases.
- A milestone or a task added after the spec was written: `plan/milestone.py add`, `plan/task.py add`. They take the next number; a number is never reused.

## Lines the spec writer adds

These lines are expedition's own. The contract, above, says which of them a script needs.

- Decision cites: `(D7)` on the heading of the module that carries decision D7, outside code fences (the scripts count every cite in the file outside a fence), `(Q3)` for a queue card, `(v0.4.x D9)` for a decision of another release.
- `- Review: none | fable` in each milestone block. `Review: fable` only where the change warrants a review: a public API, shared state, or a change across specs. Every other milestone says `Review: none` and gets its checks only. The runner picks the orchestration.
- `- Local CI:` in each milestone block: what runs on the merged tree before the merge, beyond the task checks, or `none`. Examples: `pnpm test --changed`, `act pull_request -j <job>`.
- A judged Acceptance: the `- Acceptance:` line names the reference path and the points the three judges rule on ([run.md](run.md), Milestones and sprints, the Acceptance bullet). A programmatic Acceptance needs no judges.
- `- Epic: E<n>` under the spec title and `- Starts: S<n>` in a milestone block are written by `epics/tag.py` and `plan/milestone.py`. No session writes them by hand.

Sections 1.6 and 2 with the added lines:

```markdown
### 1.6 Modules

#### 1.6.1 Docs weight (D7)

- `ExplorerFile` renders `DynamicCodeBlock`; the `highlight` imports are gone.

## 2. Instructions for AI

### 2.1 Tasks

- 01 Render `DynamicCodeBlock` in `ExplorerFile` · module 1.6.1 · tasks/01-render-dynamic-code-block.md
- 02 Remove the `highlight` imports · module 1.6.1 · tasks/02-remove-highlight-imports.md

### 2.2 Milestones

#### 2.2.1 Milestone: Docs weight
- Tasks: 01, 02
- Files owned: `apps/docs/components/code-explorer.tsx`, `apps/docs/components/mdx/example-snippet.tsx`
- Review: none
- Local CI: none
```

The bundled template is [../templates/spec.md](../templates/spec.md).

## Integration never waits on CI

- A milestone merges on local checks that pass, with one merge commit per milestone.
- CI is the second run. It runs on the staging branch after the one fast-forward, in the release spec's integration milestone.
