# Specs

What expedition adds on top of a plan file. The planning guidelines ([planning-guidelines.md](planning-guidelines.md), or the project's own planning rules) say how to write one plan file and know nothing about expedition. This file holds the expedition-only rules for a spec. The contract a spec must keep is in [SKILL.md](../SKILL.md), Stage 2, The contract, and is not repeated here.

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

The three aims to weigh, and what to do when they pull against each other: [SKILL.md](../SKILL.md), Stage 2, Cutting an epic into specs.

## Milestones

- A milestone is one branch, one worktree, one tracker and one merge, and it sits in one sprint column. The guidelines call it a named group of tasks; under expedition it is also the run unit.
- `lib/ownership.py` reads the `#### 2.2.N Milestone: <name>` blocks and computes the dependency edges and the run order. An edge exists for a listed dependency or a shared file, the lower spec number first. Milestones without such a reason run at the same time.
- A file shared by two milestones of one sprint column is a script error, fixed in the spec. The full rules: [files.md](files.md), Ownership.
- `- Depends on:` takes exact milestone names, spec numbers (`03` or `spec 03`), or `none`.
- A task's Verification list names its checks per base where the repository has bases.
- A milestone or a task added after the spec was written: `plan/milestone.py add`, `plan/task.py add`. They take the next number; a number is never reused.

## Lines the spec writer adds

These lines are expedition's own. The contract in [SKILL.md](../SKILL.md) says which of them a script needs.

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
