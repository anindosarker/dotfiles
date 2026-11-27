# Specs

What expedition adds on top of a plan file. The planning guidelines ([planning-guidelines.md](planning-guidelines.md), or the project's own planning rules) say how to write one plan file and know nothing about expedition. This file holds the expedition-only rules for a spec. The contract a spec must keep is in [SKILL.md](../SKILL.md), Stage 2, The contract, and is not repeated here.

## Plan file and spec

- Under expedition the root plan file `<release>-plan.md` is an index with two sections only, `## Goals` and `## Deliverables` ([files.md](files.md), `<release>-plan.md` sections).
- Each spec, `plan/specs/NN-<slug>/NN-<slug>.md`, is one plan file written by the guidelines. Where the guidelines say "plan", read "spec". Its task files are in `tasks/` of the same folder.
- The plan folder of the guidelines is the release folder `.ai/plans/v0.<n>.x/<owner>/`. `<owner>` is the folder name the scripts find, the most common folder name under `.ai/plans/v*.x/`, or the value of `--owner`; it is not read from `git config`. Its other files and folders belong to expedition: [files.md](files.md), Layout.
- A scope agreed in discussion is recorded in `decisions.md` before the spec is written. The spec implements the decision and never re-decides it.
- A question is asked in chat. Once the owner has answered it and said the explicit word, the answer goes to `decisions.md`, never into a spec.

## Structured and iterative

- `structured`: a scoped piece of work, planned in full before it runs. Section 1 is the full architecture. A task usually points to a section of the same file (`- Detail: 1.6.1`). It is finished when its milestones are.
- `iterative`: one area the owner gives feedback on, item after item. Section 1 is a short scope. Each feedback item is a task with a task file (`- Plan: tasks/03-<slug>.md`), added with `plan/task.py add`. A milestone is one feedback round; it stays open while tasks are added. The spec stays open, and counts as unfinished, until `plan/close_spec.py` closes it on the owner's word.
- An iterative spec goes through an epic and a go once, like any spec. After that its tasks and rounds are added while it runs ([SKILL.md](../SKILL.md), stage 1, Route).
- A task file has the front matter `task`, `status`, `type`, `decision` and the sections Description (the owner's remark, quoted), Requirements, Plan, Result. A small task uses two of them. Template: [../templates/task.md](../templates/task.md).
- Files owned, Depends on, task files and the sections of a task file are suggestions in both types.

## Cutting an epic into specs

The three aims to weigh, and what to do when they pull against each other: [SKILL.md](../SKILL.md), Stage 2, Cutting an epic into specs.

## Milestones

- A milestone is one branch, one worktree, one tracker and one merge, and it sits in one sprint column. The guidelines call it a named group of tasks; under expedition it is also the run unit.
- `lib/ownership.py` reads the `#### 2.2.N Milestone: <name>` blocks and computes the dependency edges and the run order. An edge exists for a listed dependency or a shared file, the lower spec number first; with no `- Depends on:` line a milestone follows the one listed before it in its spec. Milestones without such a reason run at the same time.
- A file shared by two milestones of one sprint column is a script error, fixed in the spec. The full rules: [files.md](files.md), Ownership.
- `- Depends on:` takes exact milestone names, spec numbers (`03` or `spec 03`), or `none`.
- Each task names its checks per base where the repository has bases.
- A milestone or a task added after the spec was written: `plan/milestone.py add`, `plan/task.py add`. They take the next section number; a number is never reused.

## Lines the spec writer adds

These lines are expedition's own. The contract in [SKILL.md](../SKILL.md) says which of them a script needs.

- Decision cites: `(D7)` at the end of each line that implements decision D7, outside code fences (the scripts count every cite in the file outside a fence), `(Q3)` for a queue card, `(v0.4.x D9)` for a decision of another release.
- `- Review: none | fable` in each milestone block. `Review: fable` only where the change warrants a review: a public API, shared state, or a change across specs. Every other milestone says `Review: none` and gets its checks only. The runner picks the orchestration.
- `- Local CI:` in each milestone block: what runs on the merged tree before the merge, beyond the task checks, or `none`. Examples: `pnpm test --changed`, `act pull_request -j <job>`.
- A judged Acceptance: the `- Acceptance:` line names the reference path and the points the three judges rule on ([run.md](run.md), Milestones and sprints, the Acceptance bullet). A programmatic Acceptance needs no judges.
- `- Epic: E<n>` under the spec title and `- Starts: S<n>` in a milestone block are written by `epics/tag.py` and `plan/milestone.py`. No session writes them by hand.

Section 2 with the added lines:

```markdown
### 2.1 Tasks

#### 2.1.1 Task: Change `ExplorerFile`, render `DynamicCodeBlock` (D7)
- Detail: 1.6.2
- Checks: docs `types:check`

#### 2.1.2 Task: Cleanup, remove the `highlight` imports from `example-snippet.tsx`
- Checks: docs `types:check`, `lint`, `build`

### 2.2 Milestones

#### 2.2.1 Milestone: Docs weight
- Tasks: 2.1.1, 2.1.2
- Files owned: `apps/docs/components/code-explorer.tsx`, `apps/docs/components/mdx/example-snippet.tsx`
- Review: none
- Local CI: none
```

The bundled templates carry these lines already: [../templates/spec.md](../templates/spec.md) for a structured spec, [../templates/spec-iterative.md](../templates/spec-iterative.md) for an iterative one.

## Integration never waits on CI

- A milestone merges on local checks that pass, with one merge commit per milestone.
- CI is the second run. It runs on the staging branch after the one fast-forward, in the release spec's integration milestone.
