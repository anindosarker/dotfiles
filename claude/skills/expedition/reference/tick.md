# One tick

The loop prompt names this file, so every tick reads it and nothing more. It holds what one fire needs; the full run rules are in [run.md](run.md). Re-read [run.md](run.md) and [formats.md](formats.md) before step 4 when this session has not read them since its last compaction, handoff or start; when unsure, re-read.

The loop prompt must be safe to fire at any time. Loop: the loop skill with no interval (`ScheduleWakeup` dynamic mode), 30 minute fallback; the workflow or watcher notification is the real wake signal. The exact loop prompt: [run.md](run.md), Starting the run, step 5. The tick reads the status file (through `status/report.py` and `sprints/grid.py`; in a release of format 2.1, 2.0 or 1.0 it reads `status/sprints.md` in place of the output of `sprints/grid.py`) and the trackers of the milestones in progress, not transcripts.

## Steps

1. A turn is already working: do nothing.
2. Find the release: the argument, else the release this session runs, else the `Next:` line of the newest handoff (`.ai/plans/v*.x/<owner>/run/handoffs/handoff-*.md`, newest by the date in the file name).
3. Wake check. As a new runner's first step, on a typed `resume`, on any message saying the usage limit has reset, and on any wake after a gap longer than the loop interval, this step comes before every other step below: `python3 -I <skill>/scripts/run/check.py <release>`. It prints one line per milestone that is `in progress` (a row): the milestone, its run id, the session that owns the run and one state word. Then per row:
   - `alive` or `paused`: leave it. A paused run continues by itself after the reset.
   - `silent`: stop it with `TaskStop`, then call Workflow with `resumeFromRunId` set to the same run id; finished agents come back from cache. Stop first: while the hung run is not stopped, Workflow answers `Workflow wf_... is still running (task ...). Stop it first with TaskStop`. A run that already ended (`ended killed`) needs no `TaskStop`. A run that `resumeFromRunId` refuses (one from before the session restarted) counts as `no run`.
   - `finished`: read its result and do the boundary step it missed (the mark, the merge fallback, a `wait`).
   - `no run`, or a run whose owner is a session that is gone (`(stopped)` or `(not in registry)`): when one of your running Workflows covers the milestone, record its id with `run/runs.py`; else launch a fresh Workflow on the existing branch, the builder continuing from the tracker, and record the new id.
   - A row owned by another live runner: leave it to that runner.

   Then re-arm the loop wakeup. Then one line to the lead per row restarted or relaunched, `NOTE <milestone>: resumed`; nothing when every row was alive. A loop that died on a limit is woken by `scripts/run/nudge-watch.sh`: it types `ultracode resume` into a runner that owns a `silent`, `finished` or `no run` row and has been quiet for 20 minutes.
4. Run `status/report.py <release>` and `sprints/grid.py <release>`, and read the trackers of the milestones in progress. In a release of format 2.1, 2.0 or 1.0, read `status/sprints.md` instead; there `sprints/grid.py` writes that file.
5. Do the next step: a milestone launched, waiting, resumed, merged or stopped gets its mark (`sprints/mark.py <release> <milestone> launch|wait|resume|merge|stop` (`<milestone>`: the tracker file name without `-tracker.md`, for example `47-comparison-page`); [run.md](run.md), Epics); launch every `to-do` milestone whose dependencies in earlier sprints have merged, from any epic that has been RUN; an epic whose every milestone is `done` or `archived` gets the closing steps of [run.md](run.md), Epics. A run whose tracker has not changed since the previous tick: ask the builder "what is blocking you" and fix the environment (a port, a server, a fixture, compute); do not read its code. A launch: [run.md](run.md), Orchestration and Workflow per milestone (record the run id with `run/runs.py`). A wait, a hold or a stop: run.md, Milestones and sprints. A merge: run.md, Results, trackers and the queue, and Handoff and end of run. In a release of format 2.2, each task of a milestone it runs that is `blocked` with the reason "waits for the owner's look" (`status/status.py <release> list --status blocked --kind task`) gets one line to the lead, once per task: `NOTE <task id>: waits for the owner's look` ([run.md](run.md), Epics).
6. Tick economy:
   - Read the output of `status/report.py` and `sprints/grid.py`, and the trackers only. No `git status`, `diff` or `log` in worktrees; no pull unless a merge is due this tick.
   - A tick with work (a mark, a merge, a launch) reports one line per action.
   - A tick that marks or merges nothing ends with exactly one line: `tick <HH:MM>: <milestone> <stage>, ..., <milestone> waiting on <dep>. Next <HH:MM>.` No table, no per-milestone bullets, no restating what was read.
   - Messages to the lead are DONE, BLOCKED, NOTE, ACK RULES (with the first words of the RULES line), ACK LEAD, and the reply to a HELLO only. Never a status line.

## Environment blockers

Environment blockers are the runner's to fix, never to wait on: a stopped Docker daemon (`open -a Docker`, then poll `docker info`), a busy port, a missing image or dependency. The run nudges the owner only when the fix fails after one attempt. An environment or tooling problem (a build that runs out of memory, a timeout, a flaky check, a tool setting) is fixed by the run at its cause, through `plan/milestone.py add` against the spec it blocks, like any other fix, not worked around per command and not filed as a queue item for the owner; an item is filed only for a real choice.

## Waiting on CI

Waiting on CI or a release run is never a foreground wait and never blocks the next milestone. Arm a background watcher: a shell loop over `gh pr checks <N> --json name,state` (or `gh run watch <id> --exit-status`) every 60 s that exits on any `FAILURE`, `ERROR` or `CANCELLED` and when nothing is `IN_PROGRESS`, `PENDING` or `QUEUED`. `SKIPPED` entries from a `labeled` event run are normal. Its completion notification wakes the loop; the fallback wakeup stays at 30 min. A milestone merges on local checks that pass; CI on the staging branch, after the one fast-forward, is the backstop, read in the integration milestone (`process.md` P1, P4).
