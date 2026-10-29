# Stage 3: run

## Contents
- Starting the run
- Each loop fire
- Lanes
- Workflow per phase
- Facts and choices
- Results, trackers and the ATTENTION file
- Handoff and end of run

## Starting the run

1. Run `python3 -I <skill>/scripts/status.py <cycle>` and fix every gap it reports.
2. Confirm the stage 2 readiness check passed.
3. The owner types `/expedition run <cycle>`, then `/autopilot`.
4. The autopilot loop prompt is exactly `/expedition run`. Nothing else goes in it.

Release and merge sequences (merge commit names, labels, release checks) belong in the release part's phases or in the project rules. Never in the loop prompt.

## Each loop fire

`/expedition run` must be safe to fire at any time.

1. A turn is already working: do nothing.
2. Find the cycle: the argument, else the cycle this session runs, else the `Next:` line of the newest handoff (`.ai/plans/v*.x/<owner>/handoffs/handoff-*.md`, newest by the date in the file name).
3. Run `status.py <cycle>`.
4. Do the next step.

## Lanes

Every phase in a part file names its lane under its heading: `Lane: workflow`, `Lane: agent` or `Lane: inline`. The plan stage picks the lane. The readiness check confirms it fits.

| Lane | Use when | Runs as |
|---|---|---|
| `workflow` | 3 or more agents, or any loop, bounce or verify step; parallel work across files | one Workflow run, worktree per part |
| `agent` | one bounded change, 1 to 5 files, no review loop needed | one Agent on `opus`, then the gates |
| `inline` | mechanical: a rename, a version bump, a changelog line, a file move | the main session, then the gates |

Rules that keep runs fast:

- Pick the lightest lane that fits. A phase does not get a Workflow because the part has one.
- Merge adjacent small phases of one part into one phase before the run starts.
- Parts with no dependency between them run at the same time, each in its own worktree.
- A sub-part (`NN.1`) made only of `inline` and `agent` phases needs no worktree; it runs on the base branch.
- Review depth matches risk: one `fable` verify for public API, shared state or a cross-part change. Mechanical changes get the gates only.

## Workflow per phase

- One Workflow run per `workflow` phase. Keep its run id on the phase line of the tracker.
- A run that stops (usage limit, crash, edited script): relaunch with `resumeFromRunId`. Finished agents come back from cache.
- Models: `opus` for coder, fix and mechanical stages. `fable` only for a review or verify stage that needs judgment.
- Worktrees: one per part, at the project's worktree location. Keep them clean (no build output, no ignore-file churn).
- Between phases the main session reads the result and decides what comes next. Judgment lives there, not in the script.

## Facts and choices

A script may branch on facts. It must not branch on choices.

- Fact branches, kept in the script: gate fails, so fix and rerun the gate, at most 3 times; 0 findings, so skip verify; reviewer rejects, so bounce to the coder.
- Choice branches, which end the run: a finding contradicts an accepted decision; two valid API shapes and the plan names neither; revert or keep a deviation; a scope change.

On a choice the script returns early:

```js
if (review.contradictsDecision) {
  return {
    status: 'needs-decision',
    phase: '02',
    notes: [],
    attention: [`${review.item}: contradicts D7. Options: ${review.options.join('; ')}`],
  }
}
```

The main session then adds an ATTENTION item and continues with work that does not depend on the choice.

## Results, trackers and the ATTENTION file

- Every workflow script's result schema has a `notes` array and an `attention` array. A plain `agent` lane returns the same two lists in its final text.
- `attention`: what needs the owner. `notes`: what a later phase, a resume or the owner would otherwise rediscover. Both are usually empty.
- Sub-agents write the tracker: the builder fills it and sets `Status: running`, the fixer and the verifier update it. They stage owner items in its `## Attention` section.
- The main agent writes the ATTENTION file at each phase boundary. It condenses the trackers' `## Attention` sections and the results, and merges duplicates.
- The run reports; it does not solve. Do not research solutions for an ATTENTION item.
- An accepted decision that no longer fits: an ATTENTION item, never a silent change.
- Nothing needs the owner: no ATTENTION file.
- Formats: [formats.md](formats.md).

## Handoff and end of run

- One handoff per run, `handoffs/handoff-<run start YYYY-MM-DD-HHMM>.md`. Create it with the `write-handoff` skill at the first part boundary. Rewrite it in place at each later part boundary and at the end. Its State section starts with the `Stage:` and `Next:` bullets ([formats.md](formats.md)).
- All parts done: rewrite the handoff, then autopilot section 4 (commit, stop the loop, report).
