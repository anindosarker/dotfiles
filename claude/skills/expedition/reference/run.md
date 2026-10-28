# Stage 3: run

## Contents
- Lanes
- Workflow per phase
- Facts and choices
- Trackers and the ATTENTION file
- Starting the run

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

- One Workflow run per `workflow` phase. Keep its run id in the part tracker.
- A run that stops (usage limit, crash, edited script): relaunch with `resumeFromRunId`. Finished agents come back from cache.
- Models: `opus` for coder, fix and mechanical stages. `fable` only for a review or verify stage that needs judgment.
- Worktrees: one per part, at the project's worktree location. Keep them clean (no build output, no ignore-file churn).
- Between phases the main session reads the result and decides what comes next. Judgment lives there, not in the script.

## Facts and choices

A script may branch on facts. It must not branch on choices.

- Fact branches, kept in the script: gate fails, so fix and rerun the gate, at most 3 times; 0 findings, so skip verify; reviewer rejects, so bounce to the coder.
- Choice branches, which end the run: a finding contradicts `decisions.md`; two valid API shapes and the plan names neither; revert or keep a deviation; a scope change.

On a choice the script returns early:

```js
if (review.contradictsDecision) {
  return { status: 'needs-decision', phase: '02', item: review.item, options: review.options }
}
```

The main session then writes a `[ruling]` bullet in the ATTENTION file and continues with work that does not depend on the choice.

## Trackers and the ATTENTION file

- `<num>-tracker.md`: per phase, the branch, commits, gate results, deviations from the part file and decisions taken during the run. No progress narration.
- `ATTENTION-<YYYY-MM-DD>.md`: only when something needs the owner. One short bullet each, starting with one tag:
  - `[revert?]` a judgment call taken that the owner may want reverted
  - `[blocked]` an item that could not be finished, and why
  - `[ruling]` a choice the run stopped on, with the options
- Nothing needs the owner: no ATTENTION file.

## Starting the run

1. Run `python3 -I <skill>/scripts/status.py <cycle>` and fix every gap it reports.
2. Confirm the stage 2 readiness check passed.
3. The owner types `/expedition run <cycle>`, then `/autopilot` with the parts to run.
4. The autopilot loop prompt includes `Follow ~/.claude/skills/expedition/reference/run.md`. This skill is not model-invocable, so the file path is how later loop fires find these rules.
