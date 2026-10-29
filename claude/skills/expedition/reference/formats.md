# File formats

## Contents
- Shared rule
- ATTENTION file
- decisions.md
- findings.md
- Tracker
- Handoff

## Shared rule

Every item has an ID heading. Its first bullet is required and self-explanatory: a reader understands the item from it alone. Everything after it is open-ended, but in bullets. Templates: [../templates/](../templates/).

## ATTENTION file

`ATTENTION-<YYYY-MM-DD>.md`, template [../templates/attention.md](../templates/attention.md).

```md
# Attention, 2026-10-28

## A2 Setters hand on*Change a function updater

- One line, no jargon: the situation and why it needs the owner.
- More lines only when needed: clarification, example, path:line.

- Options (optional):
  - a) Recommended: ...
  - b) ...
```

- First bullet: one line, no jargon. It explains the situation and why it needs the owner. More lines are discouraged, but allowed.
- No tags, no outcome line. Never edited after the run.
- A-numbers continue across the whole cycle. A second ATTENTION file starts after the last A of the previous one.
- The run reports; it does not solve. Do not research solutions for an item.
- Only the main agent writes it. It condenses the trackers' `## Attention` sections and the workflow and agent results, merges duplicates, and appends at each phase boundary, not in one batch at the end.
- An item is triaged when a decision cites it (`- Source: A2`) or a part file cites it (`(A2)`).

## decisions.md

One file per cycle, template [../templates/decisions.md](../templates/decisions.md). Triage decisions continue the numbering.

```md
# v0.4.x decisions

## Round 1: discussion, 2026-10-21

### D1 Rewrite internals on TanStack v9 primitives

- First bullet, required: explains the decision.
- Then anything: bullets, code blocks, examples, sub-bullets.

## Round 2: triage of ATTENTION-2026-10-28

### D9 Setters pass on*Change a function updater, like core

- ...
- Source: A2
```

- Accepted decisions only. Questions stay in chat.
- Superseded: the heading becomes `### D7 (superseded by D15) ...`. The text stays.
- Small wording fixes: in place.
- Deferred to another cycle: add the bullet `- Deferred to v0.5.x`. That cycle's parts cite it as `(v0.4.x D9)`.
- Parts cite a decision as `(D7)`.

## findings.md

One file per cycle, template [../templates/findings.md](../templates/findings.md). Same round headings as `decisions.md`.

```md
### F3 Row pinning drops hand-pinned rows on unselect all

- `features/stRowPinning.ts:42`: what goes wrong and when.
- Then anything.
```

- The heading names the problem, not the file.
- The first bullet names the path and explains.
- Parts cite a finding as `(F3)`.

## Tracker

`<num>-tracker.md`, one per part, template [../templates/tracker.md](../templates/tracker.md).

```md
# 01: examples per edition, tracker

Status: done (3361e3e8)
Branch `v0.6/examples-per-edition`, worktree 07, PR #49
Gates:
- `pnpm lint` at 60434a81: green
- `pnpm check:bases` at 60434a81: green
- CI run 123456: green

- Phase 01 layout: done (c3bcf345)
- Phase 02 edition copies: done (8286e7a2, wf_abc123)

## Attention

- Staging for the ATTENTION file, one bullet per item, self-explanatory first line.

## Notes

- Only what a later phase, a resume or the owner would otherwise rediscover.
```

- `Status:` is `planned`, `running` or `done (<commit>)`.
- Required: the header lines and one line per phase, with the last commit and the workflow run id for a `workflow` phase.
- `Gates:` is followed by one bullet per gate: command, commit, result. The CI run gets its own bullet.
- `## Attention` and `## Notes` are optional. Empty is the normal case. Do not spend tokens on notes.
- Never: review-round narration, gate output, commit lists.
- Writers: `new_part.py` creates it with `Status: planned`. In the run, the builder fills it, the fixer and the verifier update it. One worktree per part, so no conflicts. An `inline` phase: the main agent updates it.
- The main agent writes the ATTENTION file, `decisions.md`, `findings.md` and handoffs.

## Handoff

Written with the `write-handoff` skill.

- Attended stages (discuss, plan, triage): never written on your own. Only when the owner asks.
- Unattended run: one file per run, `handoffs/handoff-<run start YYYY-MM-DD-HHMM>.md`. Create it with `write-handoff` at the first part boundary. Rewrite it in place at each later part boundary and at the end.
- Every expedition handoff starts its State section with these two bullets:

  ```
  - Stage: <discuss | plan | run | triage>
  - Next: `/expedition <stage> <cycle>`, <where to start, e.g. A1 or part 04.1>
  ```

- No cycle line: the folder gives the cycle.
