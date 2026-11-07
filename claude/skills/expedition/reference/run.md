# Stage 3: run

## Contents
- Starting the run
- Epics
- Each loop fire
- Milestones and sprints
- Orchestration
- Workflow per milestone
- Facts and choices
- Results, trackers and the ATTENTION file
- Handoff and end of run

## Starting the run

1. Run `python3 -I <skill>/scripts/status.py <release>` and fix every gap it reports.
2. Confirm the stage 2 readiness check passed.
3. The runner session runs every epic: started by `scripts/runner.sh start <release>` from the talker's working directory (the runner and every spec fork run from the same folder as the talker, never from a subfolder or the repo root the script could infer; the script takes the cwd it is called from, so call it in a Bash call of its own, never after a `cd`) as a window `<release> runner1` (also its session name) in the talker's own tmux session (outside tmux the script prints the command), brief from `templates/runner-brief.md`. Its first prompt starts with `ultracode`, so the Workflow tool is opted in from the first turn. Each go sends one RUN line; the turn it arrives in starts the epic: autopilot start script, loop scheduled, worktrees assigned, the epic's ready milestones launched. Loop: the loop skill with no interval (`ScheduleWakeup` dynamic mode), 30 minute fallback; the workflow or watcher notification is the real wake signal. The owner never has to type a command.
4. A runner that died: `runner.sh start` finds its entry in `~/.claude/expedition-runners.json` and resumes it with `claude --resume <uuid>`. `runner.sh list` shows each runner busy or idle (Stop and UserPromptSubmit hooks of `templates/runner-settings.json`).
5. The autopilot loop prompt is exactly `ultracode. Read ~/.claude/skills/expedition/reference/run.md, then continue the run. Skip if a turn is already working.` Nothing else goes in it. A loop fire cannot load a skill marked `disable-model-invocation`, and after compaction the session may no longer hold the run rules, so the prompt names the file.

The release's `process.md` (`.ai/plans/<release>/<owner>/process.md`) holds the project facts P1 to P<n> (branches and worktrees, merge, release, checks, agent sandbox, plans); every sub-agent prompt names it by path. `new_cycle.py` copies it from the previous release; the plan stage trims it before the run. Never in the loop prompt.

## Epics

- Messages, one line each, nothing else in a message:
  - Talker to runner: `HELLO from <talker session name>`, typed by `runner.sh send` from a talker that starts fresh on a release with a live runner. No work starts.
  - Talker to runner: `RUN E<n> <release folder> from <talker session name>`, typed into the runner window by `runner.sh send` (as `ultracode RUN ...`, so the turn is opted in to the Workflow tool)
  - Runner to talker, by `SendMessage` to the name after `from`: `DONE E<n> <merge sha> attention <A ids or none>`, when every milestone of the epic has merged
  - Runner to talker, the same way: `BLOCKED E<n> <tracker path>`, when a bounce loop or a gate cannot be resolved
  - Spec writer to talker, by `SendMessage`: `SPECS E<n> <spec numbers>`, from the forked session `runner.sh fork` opened
- Reply target: the name after `from` in the latest RUN or HELLO line; DONE and BLOCKED go there from then on.
- RUN is idempotent: an epic whose `sprints.md` rows are already running or done is not started again; the runner replies with the current state.
- Several epics run at once, no slot limit. One worktree per milestone from the pool. Machine load as today: `process.md` P5, `SERIAL_GATES` when loaded.
- On each merge the runner ticks the row and reruns `sprints.py`. When every milestone of an epic has merged it writes ATTENTION, `findings.md` and the handoff, tags `[Done]` on the epic's decisions, sends DONE.
- Shared files (`decisions.md`, ATTENTION): the rules in [formats.md](formats.md), Shared files.

## Each loop fire

The loop prompt must be safe to fire at any time. Each fire reads this file, about 2k tokens. That is the cost of surviving compaction. Loop: the loop skill with no interval (`ScheduleWakeup` dynamic mode), 30 minute fallback; the workflow or watcher notification is the real wake signal. The tick reads `sprints.md` and the trackers of its `[ ]` rows, not transcripts.

1. A turn is already working: do nothing.
2. Find the release: the argument, else the release this session runs, else the `Next:` line of the newest handoff (`.ai/plans/v*.x/<owner>/handoffs/handoff-*.md`, newest by the date in the file name).
3. Run `status.py <release>`, read `sprints.md` and the trackers of its `[ ]` rows.
4. Do the next step: a milestone merged or stopped ticks its cell; launch every `·` row whose dependencies in earlier columns have merged, from any epic that has been RUN; an epic whose every milestone is `[x]` or `[!]` gets the closing steps of Epics. A run whose tracker has not changed since the previous tick: ask the builder "what is blocking you" and fix the environment (a port, a server, a fixture, compute); do not read its code.
5. Tick economy:
   - Read `sprints.md` and the trackers only. No `git status`, `diff` or `log` in worktrees; no pull unless a merge is due this tick.
   - A tick with work (tick a cell, merge, launch) reports one line per action.
   - A tick that ticks or merges nothing ends with exactly one line: `tick <HH:MM>: <milestone> <stage>, ..., <milestone> waiting on <dep>. Next <HH:MM>.` No table, no per-milestone bullets, no restating what was read.
   - Messages to the talker are DONE, BLOCKED and the reply to a HELLO only. Never a status line.

Waiting on CI or a release run is never a foreground wait and never blocks the next milestone. Arm a background watcher: a shell loop over `gh pr checks <N> --json name,state` (or `gh run watch <id> --exit-status`) every 60 s that exits on any `FAILURE`, `ERROR` or `CANCELLED` and when nothing is `IN_PROGRESS`, `PENDING` or `QUEUED`. `SKIPPED` entries from a `labeled` event run are normal. Its completion notification wakes the loop; the fallback wakeup stays at 30 min. A milestone merges on local checks that pass; CI on the staging branch, after the one fast-forward, is the backstop, read in the integration milestone (`process.md` P1, P4).

## Milestones and sprints

The run follows `sprints.md` and `ownership.md` ([files.md](files.md)) and decides nothing the plan left out.

- The run unit is the milestone, not the spec: one team, its own worktree, branch and tracker, one builder end to end. It edits only its files while it runs. The orchestration per column is the run manager's judgment: one Workflow per milestone, several per milestone, or one for several, whatever proves the Acceptance with the fewest wakes and agents.
- A sprint is one column of the grid, computed by `ownership.py` across every epic. A running column accepts new `·` rows from a later epic. A milestone branches from the integration branch after the milestones it depends on have merged. The critical path is the `Critical path:` line of `ownership.md`, the longest chain ending at the release milestone.
- The runner ticks `sprints.md` at each boundary: `[ ]` at launch, `[x]` at merge, `[!]` at a stop (the reason in the tracker's `## Attention`), and the `Updated:` line. A fix milestone added mid-run gets its row from `new_fix.py`.
- The first sprint's shared milestone: everything two or more milestones need (dependency adds, lockfile, lint or tsconfig config, CI edits, shared new helpers, baseline captures). Later milestones never touch `package.json`, the lockfile, ESLint or CI config.
- A fix found mid-sprint is a fix milestone added to the running column (`new_fix.py <release> <slug> "F3, F4"`). A bug in another milestone's merged file is a fix milestone on the integration branch, never an edit by the running milestone.
- Shared files: per the release's `process.md`. Generated outputs (registry json, installed docs copies) are regenerated by whoever merges, never hand-merged. A comment-only hunk in conflict yields to the code change.
- Check pyramid: per task, tsc and lint on the milestone's own files only; at milestone end, unit tests plus one base of the long per-base checks; at verify, every base concurrently, once; CI is the second run. A long check (pages check, Storybook build, browser tests) never runs per task.
- Acceptance: programmatic checks run by the `opus` builder and verifier. Judged checks (visual) only where the spec's `Acceptance:` line names them: baseline captured in the first sprint, its reference path in that line and the tracker, three `fable` judges inside the workflow script, majority passes.
- Merge each milestone when its recorded checks pass. The staging branch stays untouched until the release spec runs; then the integration branch fast-forwards into it once. Release is a spec, run inside the epic the owner put it in: its first milestone is integration (a verifier runs the suite on the staging branch, records the tracker, reports; a red becomes fix milestones on the integration branch, then the fast-forward again and a rerun), then the steps the release spec names; for this project the one PR of `process.md` P1.
- The run never stops for one milestone. A builder that cannot finish its milestone (it contradicts an accepted decision, or its Acceptance is unreachable) stops that milestone only: commits what is coherent, writes the reason under `## Attention` in the tracker, returns blocked. Milestones that depend on it are skipped the same way. Every other milestone merges, the release ships what merged, the handoff lists what did not, the triage round decides. Only a failed shared milestone of the first sprint (nothing can start) or a usage limit stops the whole run. `needs-decision` and `review-open` results stop their own milestone only.

## Orchestration

The spec says what must be proven (`Acceptance:`); the run manager decides how, per column, by cost: fewest main-session wakes, fewest agents that still prove every Acceptance. No lane line in specs.

- The orchestration per column is the run manager's judgment: one Workflow per milestone, several per milestone, or one for several, whatever proves the Acceptance with the fewest wakes and agents. A stage rerun: edit the script, resume with `resumeFromRunId`; never loose Agent calls. Composed from the stage library in [../templates/workflow.js](../templates/workflow.js): build, spec check, review bounce (only when the milestone says `Review: fable`), verify, judges, check, merge on green, release steps. The milestones of a sprint with no dependency between them run at the same time. The main session wakes at each milestone's end, or at a `needs-decision`.
- A single Agent for one bounded task with nothing after it; inline for mechanical edits (a rename, a version bump, a changelog line).
- Milestones with no dependency between them run at the same time, each in its own worktree.
- Review depth matches risk: a review only where the milestone asks for one (public API, shared state, a cross-spec change); mechanical changes get the checks only. Nits and minors alone are fixed by the builder in one commit, no fixer agent.
- Every spec has an `Acceptance:` check the builder runs itself and loops on (programmatic, or captures judged against a named reference by three `fable` judges inside the script, majority). The readiness check refuses a spec without one.
- Checks run once. The builder records each check as one tracker line: command, commit, result. Baselines a check diffs against (a built tree, captures) live in the session scratchpad, never in the repo.
- Checks that run once per base run the bases concurrently, unless the release's `process.md` says the machine is loaded.
- The verifier reruns only the checks that have no valid line for the current HEAD. A line stays valid when `git diff --name-only <recorded commit>..HEAD` touches only the paths the release's `process.md` names (default `.ai/` and the changelog). Any other changed file means rerun.
- CI is the second run. It never blocks: a milestone merges into the integration branch with a merge commit the moment its local checks pass, no PR. CI runs on the staging branch after the one fast-forward, read in the integration milestone. A red run is fixed forward by a fix milestone on the integration branch, then the fast-forward again.
- The next milestone never waits: the merge lands at once, so it branches from the integration branch.
- Shared-run model, only when a milestone needs it: one lead agent does the shared prework on the run branch and worktree; then each file set gets its own worktree and branch (`<slug>-<set>` for both), cut from the run branch after the lead's last commit, because parallel commits in one checkout race on the index; one builder per file set (each file, in every base, owned by one builder); the lead merges each set branch into the run branch when its builder returns; one review bounce, one verify, one merge for the run. Their trackers cite the shared commits and the one run id. `templates/workflow.js` takes this as a `MILESTONES` entry with `lead` and `fileSets`.
- Owner messages in the runner are discussion under the stage 1 rules; no process proposals; a real choice the run finds is an ATTENTION item.
- A milestone slower than the previous ones: measure per-agent durations from the workflow transcript before changing the script.

## Workflow per milestone

- Start from [../templates/workflow.js](../templates/workflow.js): the agent-rules reference, the stage functions (build, spec check, review bounce, verify, judges, check, merge, release), the result schemas, `MILESTONES` and `SPECIFICS` slots. Edit `meta`, `MILESTONES`, `BASE_SHA`, `SPECIFICS` and the composition at the bottom per milestone; keep the rest.
- A Workflow run covers one milestone: its tasks in order in its worktree, then its merge; or several milestones of one column when the run manager chose so. The release spec's milestones run the integration, check, judges and release. A step whose result needs the owner's judgment ends the run there.
- A choice found mid-run still ends that Workflow run early ([Facts and choices](#facts-and-choices)); other milestones continue.
- Keep the run id on the tracker line of each task it covers.
- A run that stops (usage limit, crash, edited script): relaunch with `resumeFromRunId`. Finished agents come back from cache.
- Models: `opus` for the shared milestone, build, fix, verify, check, baselines, lookups. `fable` for review, judges, plan writing. Judges run inside the script (`agent()` calls in parallel, majority in the script); a plain sub-agent has no agent tool, so a judged clause outside a workflow falls to the main session.
- The loop tick reads the trackers; where they fall short, which stage runs and the commits so far come from `<transcriptDir>/journal.jsonl` through a sandboxed read, never from a raw transcript. A run whose tracker has not changed since the previous tick gets "what is blocking you". Pause with the loop's stop; resume a workflow with `resumeFromRunId`.
- Worktrees: one per milestone, assigned at launch and recorded in its tracker, as `process.md` P1 says. A project with a worktree pool (numbered, clean, dependencies installed) reuses it: `git -C <wt> fetch origin && git -C <wt> checkout -B <branch> origin/<integration branch> && git -C <wt> push -u origin <branch>`, create a new numbered one only when every pool worktree is in use, and it joins the pool; never remove one. Without a pool: create one per milestone, install dependencies per P5, remove it after the merge. Keep them clean (no build output, no ignore-file churn).
- Between tasks the main session reads the result and decides what comes next. Judgment lives there, not in the script.

## Facts and choices

A script may branch on facts. It must not branch on choices.

- Fact branches, kept in the script: check fails, so fix and rerun the check, at most 3 times; 0 findings, so skip verify; reviewer rejects, so bounce to the coder; a test `process.md` names as a known flake fails once, so rerun that job once (`gh run rerun --failed <id>`) before treating it as red.
- Choice branches, which end that milestone's Workflow run (`needs-decision`), never the whole run: a finding contradicts an accepted decision; two valid API shapes and the plan names neither; revert or keep a deviation; a scope change.

On a choice the script returns early:

```js
if (review.contradictsDecision) {
  return {
    status: 'needs-decision',
    task: '02',
    notes: [],
    attention: [`${review.item}: contradicts D7. Options: ${review.options.join('; ')}`],
  }
}
```

The runner then adds an ATTENTION item and continues with work that does not depend on the choice.

## Results, trackers and the ATTENTION file

- Every workflow script's result schema has a `notes` array and an `attention` array. A plain Agent returns the same two lists in its final text.
- `attention`: what needs the owner. `notes`: what a later task, a resume or the owner would otherwise rediscover. Both are usually empty.
- Sub-agents write the tracker: the builder fills it and sets `Status: running`, the fixer and the verifier update it. They stage owner items in its `## Attention` section.
- The runner writes the ATTENTION file at each milestone boundary and when an epic has merged. It condenses the trackers' `## Attention` sections and the results, and merges duplicates.
- The run reports; it does not solve. Do not research solutions for an ATTENTION item. A deviation is reported as keep or revert with the exact strings, never as an implementation question.
- An accepted decision that no longer fits: an ATTENTION item, never a silent change.
- Nothing needs the owner: no ATTENTION file.
- Formats: [formats.md](formats.md).

## Handoff and end of run

- One handoff per run, `handoffs/handoff-<run start YYYY-MM-DD-HHMM>.md`. Create it with the `write-handoff` skill at the first milestone boundary. Rewrite it in place at each later milestone boundary and at the end. Its State section starts with the `Stage:` and `Next:` bullets ([formats.md](formats.md)).
- Every epic merged or stopped and no RUN pending: rewrite the handoff, release resources (stop every server, watcher and browser the run started, remove worktrees only where `process.md` has no pool, delete throwaway apps, end finished sub-agents), then autopilot section 4 (commit, stop the loop, report).
