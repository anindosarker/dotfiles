# File formats

## Contents
- Shared rule
- Shared files
- ATTENTION file
- decisions.md
- findings.md
- sprints.md
- Tracker
- process.md
- Handoff

## Shared rule

Every item has an ID heading. Its first bullet is required and self-explanatory: a reader understands the item from it alone. Everything after it is open-ended, but in bullets. Templates: [../templates/](../templates/).

## Shared files

`decisions.md` and the ATTENTION files are written by both sessions, lead and runner.

- `[E<n>]` is written by whoever sends RUN. `[Done]` is written by the runner on merge, or by the lead when a decision with nothing to run is recorded.
- Re-read the file right before every write, make a targeted edit, commit at once. No held edits.
- The next D, F or A number is read from the file at write time, never from memory.
- Agents on milestone branches never edit `decisions.md`.

## ATTENTION file

`attentions/ATTENTION-<YYYY-MM-DD>.md`, template [../templates/attention.md](../templates/attention.md).

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
- One tag line once ruled, directly under the heading: `[D107]` (a fix decision) or `[F40]` (deferred as a finding). Nothing else is edited after the run.
- A-numbers continue across the whole release. A second ATTENTION file starts after the last A of the previous one.
- The run reports; it does not solve. Do not research solutions for an item.
- Not an ATTENTION item: spec text that lags shipped code, a tracker gap, a process lesson, a tooling fact with one right answer. Those go to the tracker Notes, a decision or the spec file directly (`process.md` holds project facts only); the owner sees choices only.
- Only the runner writes its items; the tag line is written by whoever records the ruling. It condenses the trackers' `## Attention` sections and the workflow and agent results, merges duplicates, and appends at each milestone boundary, not in one sprint at the end.
- An item is triaged when it has a tag line, a decision cites it (`- Source: A2`) or a spec file cites it (`(A2)`).

## decisions.md

One file per release, template [../templates/decisions.md](../templates/decisions.md). Triage decisions continue the numbering.

```md
# v0.4.x decisions

## Round 1: discussion, 2026-10-21

### D1 Rewrite internals on TanStack v9 primitives

- First bullet, required: explains the decision.
- Then what changes and what stays. A later ruling on the same decision is a dated addendum bullet under it, never a rewrite.
- Then anything: bullets, code blocks, examples, sub-bullets.

## Round 2: triage of ATTENTION-2026-10-28

### D9 Setters pass on*Change a function updater, like core

- ...
- Source: A2
```

- Tag line, directly under the heading: none (deciding), in an epic, done, or done with nothing to run:

  ```
  ### D1 Toolbar above the frame

  ### D1 Toolbar above the frame
  [E1]

  ### D1 Toolbar above the frame
  [Done]  [E1]

  ### D9 Process file audited
  [Done]
  ```

- Accepted decisions only. Questions stay in chat.
- Superseded: the heading becomes `### D7 (superseded by D15) ...`. The text stays.
- Small wording fixes: in place.
- Deferred to another release: add the bullet `- Deferred to v0.5.x`. That release's specs cite it as `(v0.4.x D9)`.
- Specs cite a decision as `(D7)`.

## findings.md

One file per release, template [../templates/findings.md](../templates/findings.md). Same round headings as `decisions.md`.

```md
### F3 Row pinning drops hand-pinned rows on unselect all

- `features/stRowPinning.ts:42`: what goes wrong and when.
- Then anything.
```

- The heading names the problem, not the file.
- The first bullet names the path and explains.
- Specs cite a finding as `(F3)`.

## sprints.md

Columns are the sprints `S1`, `S2`, ... that `ownership.py` computes. Rows are the milestones of specs that carry a `- Epic: E<n>` line (written under the title line by `new_spec.py --epic`), plus fix milestones; row text is the epic label, the spec number and the milestone name; rows sorted by epic, then spec number, then `ownership.md` order.

```md
| Milestone | S1 | S2 |
|---|---|---|
| Row virtualizer  D101 | [x] |  |
| Sticky footer  D102 | [x] |  |
| Resize handle  D104, D105 |  | [ ] |
```

## Tracker

One per milestone: `trackers/NN-<slug>-tracker.md` for a milestone of spec NN, `trackers/fix-<slug>-tracker.md` for a fix milestone. Template [../templates/tracker.md](../templates/tracker.md).

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

- Staging for the ATTENTION file, one bullet per item, self-explanatory first line.

## Notes

- Only what a later task, a resume or the owner would otherwise rediscover.
```

- `Status:` is `planned`, `running` or `merged (<commit>)`.
- Required: the header lines and one line per task, with the last commit and the workflow run id of the run that covered the task.
- A fix milestone's tracker cites its findings on its first line, for example `# Component fixes (F3, F4), tracker`.
- `Checks:` is followed by one bullet per check: command, commit, result. The integration milestone's suite run on the staging branch gets its own bullet.
- `## Attention` and `## Notes` are optional. Empty is the normal case. Do not spend tokens on notes.
- Never: review-round narration, check output, commit lists.
- Writers: `new_fix.py` creates a fix milestone's tracker with `Status: planned`; `new_spec.py` creates the spec's first milestone's tracker with `Status: planned`; the spec writer creates every further milestone's tracker from the template with `Status: planned` in stage 2, when the milestone block is written. In the run, the builder fills it, the fixer and the verifier update it. One worktree per milestone, so no conflicts.
- The runner writes the ATTENTION file and handoffs. Both sessions write `decisions.md` and `findings.md` (Shared files).

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
- Unattended run: one file per run, `handoffs/handoff-<run start YYYY-MM-DD-HHMM>.md`. Create it with `write-handoff` at the first milestone boundary. Rewrite it in place at each later milestone boundary and at the end.
- Every expedition handoff starts its State section with these three bullets:

  ```
  - Stage: <the Stage line of status.py, e.g. discuss, run (S2)>
  - Next: `/expedition <stage> <release>`, <where to start, e.g. A1 or spec 04.1>
  - Runner: window `<release> runner1` in tmux session <name>, or none; registry `~/.claude/expedition-runners.json`
  ```

- No release line: the folder gives the release.
