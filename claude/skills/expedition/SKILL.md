---
name: expedition
description: Runs long, multi-part work as a cycle of four stages (discuss, plan, run, triage) in a versioned plan folder, with decisions and findings files, part files with phases, one Workflow run per phase, an ATTENTION file, and follow-up parts. Use when the user runs /expedition. Not for small or single-session tasks.
argument-hint: "<discuss|plan|run|triage> [cycle, e.g. v0.5.x]"
disable-model-invocation: true
---

# Expedition

A cycle is one plan folder, `.ai/plans/v0.<n>.x/<owner>/`. `<owner>` is the folder name earlier cycles use. A cycle has parts (`NN-<name>.md`). A part has phases. Each stage below writes fixed files and ends at a fixed point.

Arguments: `$ARGUMENTS`. Stage missing: run `python3 -I ${CLAUDE_SKILL_DIR}/scripts/status.py <cycle>`, take its inferred stage, and say which stage you picked.

Mechanical steps use the scripts, never hand-written files:

- New cycle folder: `python3 -I ${CLAUDE_SKILL_DIR}/scripts/new_cycle.py v0.<n>.x`
- New part or sub-part: `python3 -I ${CLAUDE_SKILL_DIR}/scripts/new_part.py v0.<n>.x NN <slug> "<Title>" "<scope>"`
- State and gaps: `python3 -I ${CLAUDE_SKILL_DIR}/scripts/status.py v0.<n>.x`

File layout, scripts and conventions: [reference/files.md](reference/files.md). File formats (decisions, findings, ATTENTION, tracker, handoff): [reference/formats.md](reference/formats.md).

## Owner input

- Owner comments are feedback for discussion, not decisions. Discuss, propose, and record a decision only when the owner accepts it.
- A decision can be revisited. A new decision supersedes it; the old one stays in the file, marked.
- A run agent follows accepted decisions. A decision that no longer fits becomes an ATTENTION item, never a silent change.

## Stage 1: discuss

Interactive. You research and propose; the owner gives feedback and accepts.

- Questions and options stay in chat, never in a file.
- `decisions.md` holds accepted decisions only, as `### D<n>` items under a round heading. A number is never reused or renumbered.
- `findings.md` holds problems found in the code, as `### F<n>` items.
- Research: inline, or one or two agents for lookups. No Workflow in this stage.
- Handoff: only when the owner asks.

## Stage 2: plan

Write the plan per part, not all at once.

1. Write the plan index `v0.<n>.x-plan.md` first: parts table (`#`, `Part`, `Scope`), dependency graph, integration, process rules. It may exist while decisions are still open. Example: [reference/example-plan-index.md](reference/example-plan-index.md).
2. Write a part file only when every decision it cites is accepted. A part waiting on an open decision stays a row in the index.
3. Create each part with `new_part.py`. If it printed project planning rules, read them and follow them. They override the bundled guidelines completely. Otherwise follow [reference/planning-guidelines.md](reference/planning-guidelines.md). Either way, keep the contract below. Parts implement decisions and never re-decide.
4. Each phase names its lane: `workflow`, `agent` or `inline` ([reference/run.md](reference/run.md)). Pick the lightest lane that fits. Merge adjacent small phases.
5. A decision superseded after parts exist: `grep` its citation, for example `(D7)`, across the part files and rewrite only those parts.
6. Readiness check before stage 3:
   1. Run `status.py`. Fix every gap it reports (unplanned decisions, missing gates or trackers, open questions).
   2. One review agent on the `fable` model, prompted to refute readiness. It checks that no part contradicts a decision, that each phase fits its lane, and that each `workflow` phase fits one Workflow run.
   3. Fix what it finds and repeat from step 1. Proceed only when both pass.
7. Handoff: only when the owner asks.

The contract. It applies inside any template:

- Decisions cited as `(D7)`, findings as `(F3)`, ATTENTION items as `(A2)`. A decision from another cycle: `(v0.4.x D9)`.
- A `Lane: workflow|agent|inline` line under each phase heading.
- Gates per phase.
- No open questions in plan files.

A project template that lacks one gets it added in that project's style. Nothing else changes.

## Stage 3: run

Unattended through `/autopilot`. The owner types `/expedition run <cycle>`, then `/autopilot`. The autopilot loop prompt is exactly `/expedition run`. Rules: [reference/run.md](reference/run.md). Short form:

- Resume-safe: a turn already working means do nothing. Otherwise find the cycle, run `status.py`, do the next step.
- Each phase runs in its lane. Independent parts run at the same time.
- One Workflow run per `workflow` phase, resumable with `resumeFromRunId`.
- `opus` for coder and mechanical stages; `fable` only where a review or verify stage needs judgment.
- A script branches on facts (gate pass or fail, a count), never on choices. A choice ends the run with a `needs-decision` result.
- Sub-agents write `<num>-tracker.md`. The main agent writes the ATTENTION file at each phase boundary, and one handoff per run at each part boundary.

## Stage 4: triage

Interactive. Go through the ATTENTION file with the owner one item at a time. Rules: [reference/triage.md](reference/triage.md). Short form:

- Accepted decisions go to `decisions.md` under a new triage round, with `- Source: A<n>`. Bugs found on the way go to `findings.md`.
- Minor follow-up: a sub-part `NN.1`, `NN.2`, placed before the next part that depends on it.
- Major follow-up: a new cycle folder.
- Then return to stage 2 for the new parts.
- Handoff: only when the owner asks.

## Agents or Workflow

- 3 or more agents, or any loop, bounce or verify step: Workflow.
- 1 or 2 one-shot tasks: a single Agent.
- Mechanical edits: inline.
- The next step needs a decision: inline, or end the Workflow at that boundary.
