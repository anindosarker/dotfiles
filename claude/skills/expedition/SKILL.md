---
name: expedition
description: Runs long, multi-part work as a release of four stages (discuss, plan, run, triage) in a versioned plan folder, in batches of decisions run by a separate runner session, with decisions and findings files, epic files with milestones, tasks and an Acceptance line, an ATTENTION file, and follow-up epics or fix milestones. Use when the user runs /expedition. Not for small or single-session tasks.
argument-hint: "<discuss|plan|run|triage> [release, e.g. v0.5.x]"
disable-model-invocation: true
---

# Expedition

A release is one plan folder, `.ai/plans/v0.<n>.x/<owner>/`, and one version. `<owner>` is the folder name earlier releases use. A release has epics, one file each (`epics/NN-<slug>.md`): an epic is one planned unit of work. An epic has milestones: a schedulable chunk with one branch, one worktree, one tracker, one merge, inside one batch; the rows of `sprints.md`. A milestone has tasks: ordered steps, each with its checks. A batch is the decided items that run together; the columns of `sprints.md`. Each stage below writes fixed files and ends at a fixed point.

The core loop: two sessions on one checkout. The talker (this session) discusses with the owner and records decisions; the runner (a second session, `scripts/runner.sh`) runs batches. A batch is 3 to 5 decided items whose dependencies are all in batches running or done, and whose epic files do not overlap the owned files of a running batch (`ownership.py --overlap`). One "go" per batch: each go starts that batch's run in the same turn, and discussion goes on while batches run. The owner's attention is spent in discussion only.

Arguments: `$ARGUMENTS`. Stage missing: run `python3 -I ${CLAUDE_SKILL_DIR}/scripts/status.py <release>`, take its inferred stage, and say which stage you picked.

Mechanical steps use the scripts, never hand-written files. The main agent calls scripts, never does a script's job by hand, never spawns an agent only to call one (the epic-writing fork calls `new_epic.py` as part of its work):

- New release folder: `python3 -I ${CLAUDE_SKILL_DIR}/scripts/new_cycle.py v0.<n>.x`
- New epic or follow-up epic: `python3 -I ${CLAUDE_SKILL_DIR}/scripts/new_epic.py v0.<n>.x NN <slug> "<Title>" "<scope>"` (the `epics/NN-<slug>.md` stub, the first milestone's tracker `trackers/NN-<slug>-tracker.md` with `Status: planned`, and the `plan.md` row)
- Ownership and critical path: `python3 -I ${CLAUDE_SKILL_DIR}/scripts/ownership.py v0.<n>.x`, after each epic is written and before the run (writes `ownership.md` from the milestone blocks and every `trackers/fix-<slug>-tracker.md`)
- Overlap with running batches: `python3 -I ${CLAUDE_SKILL_DIR}/scripts/ownership.py v0.<n>.x --overlap <epic numbers or D ids>` (check mode, writes nothing)
- Batch tags on go: `python3 -I ${CLAUDE_SKILL_DIR}/scripts/new_epic.py v0.<n>.x --batch B<n> <epic numbers or D ids>` (writes `- Batch: B<n>` under each epic's title line, the epic's batch for `sprints.py`, and `[B<n>]` under each cited decision; a D id names the epics citing it)
- Batch grid: `python3 -I ${CLAUDE_SKILL_DIR}/scripts/sprints.py v0.<n>.x`, by the talker on go and by the runner on merge (one column per batch; ticks survive a regeneration)
- Runner session: `${CLAUDE_SKILL_DIR}/scripts/runner.sh start|list|stop|send v0.<n>.x`
- Mid-run fix: `python3 -I ${CLAUDE_SKILL_DIR}/scripts/new_fix.py v0.<n>.x <slug> "F3, F4"` (the tracker stub citing the findings plus a grid row in the running batch column)
- State and gaps: `python3 -I ${CLAUDE_SKILL_DIR}/scripts/status.py v0.<n>.x`

File layout, scripts and conventions: [reference/files.md](reference/files.md). File formats (decisions, findings, ATTENTION, tracker, handoff): [reference/formats.md](reference/formats.md).

## Process notes

The release's `process.md` holds project facts only: branches, the milestone branch and worktree, merge, release, checks on the shared machine, the agent sandbox, the public surface, commits, shared files, plans. The process itself is this skill; commands are in the package manifests; code rules in the project's coding standards; what a milestone must run is in its epic (`Local CI:` line). An owner instruction about how the project is worked is a decision (`D<n>`) first; it becomes a `P<n>` bullet only when it is a standing project fact every epic needs. A lesson from the run goes to the tracker's Notes or to this skill, never to `process.md`.

Writing a rule: one rule per topic, two to five bullets; each bullet a full sentence that states the fact explicitly (names, paths, the exact command in a code block when it matters) so no agent can read it two ways ("created from `origin/claude/review`", not "cut from"; "fast-forwarded once, after the last feature column has merged", not "touched once"). A bullet says what to do and the one boundary. Nothing restated from elsewhere. A suggestion to agents (a tool they may use) stays; a requirement for one milestone goes to that epic. The owner reviews the file rule by rule, one rule per message, as a decision round.

## Owner input

- Owner words: `record it`, `accepted`, `record D<n>`, `k`, `batch`, `hold D<n>`, `go`.
- Owner comments are feedback for discussion, not decisions. An owner message that picks an option, adds specifics or corrects the item is still discussion: fold it into the item and post the item again. Write a decision only on an explicit confirmation ("record it", "accepted", "record D<n>"), or on "k" when the agent's last message was the complete item ending with the line `Say "record it" to write D<n>, or add to it.`; "k" on an item still being shaped, "fix it", "makes sense" or a message of specifics never counts. A message that carries a question is discussion whatever else it says ("lgtm, also X right?"): answer the question, fold the answer into the item, and wait for the next message.
- Only a real choice reaches the owner: a visible behavior or look, a public API, a re-decided decision, a scope change. Epic wording that follows shipped code, tracker and process gaps, tooling with one right answer, a deviation that keeps the decided behavior: the agent settles them, records a short decision and moves on. The owner does not read epic files.
- A decision can be revisited. A new decision supersedes it; the old one stays in the file, marked.
- A run agent follows accepted decisions. A decision that no longer fits becomes an ATTENTION item, never a silent change.
- A side-agent note the owner pastes ("Heads up ...") is feedback too: explain the trade-off, give the options with a lean, the owner picks.
- Cost is one clause, once: "bigger epic", "two batches". Never argue an option down on effort, never repeat the cost after the owner leans; the owner decides what is worth building.
- An explanation the owner asks for is a short bullet list, one plain sentence per bullet, never prose paragraphs; the same holds for a "what are we deciding" recap of an item.

## Stage 1: discuss

Interactive. You research and propose; the owner gives feedback and accepts.

- Read the last handoff and the open attention file in full before saying anything.
- Questions and options stay in chat, never in a file.
- `decisions.md` holds accepted decisions only, as `### D<n>` items under a round heading. A number is never reused or renumbered.
- `findings.md` holds problems found in the code, as `### F<n>` items.
- Research: inline, or one or two agents for lookups. The talker never launches a Workflow.
- ATTENTION items enter the discussion at once, as items in order with the rest. A ruling becomes a D item (fix) or an F item (defer), and the A item gets its tag line ([reference/formats.md](reference/formats.md)).
- Both sessions may discuss and record decisions, under the shared-file rules in [reference/formats.md](reference/formats.md).
- An item that needs a lookup does not block the round: start the lookup agent, say so in one line, and post the next item whose facts are in hand; the waiting item is posted when the agent reports. Items may therefore be ruled out of order; the numbers stay.
- A finished lookup agent stays idle, not stopped: it costs nothing idle, and a follow-up on the same area goes to it by name (`SendMessage`) so its context is reused. Stop agents only when the owner says so.

Item format, one item per message, the next item only after the owner rules on this one (or while this one waits on a lookup, see above):

```
# <n>. <Title>: one plain sentence that says what is wrong today, where, and what the change is.
- optional bullets: facts, file:line, how the common references do it (measured or read, never assumed)
## Options:
- recommended: ...
- ...
```

No question at the end; the options are the question. A "makes sense" or a follow-up question is still discussion; write the decision into `decisions.md` only on the owner's explicit confirmation ("record it", "accepted", "record D<n>", or "k" right after the complete item that ends with `Say "record it" to write D<n>, or add to it.`), in that same turn, then post the next item. A message of specifics or a chosen option is not a confirmation: repost the item with them folded in and wait.
- Handoff: only when the owner asks.

Batches:

- Batch hint: after each recorded decision, scan `decisions.md` for D items with no `[B]` tag whose dependencies are satisfied, and run `ownership.py --overlap` on them; an overlapping item is held. At 3 to 5, post one line: `Batch ready: D101, D102, D103. Say batch, or name items to hold.` Nothing else triggers it.
- `hold D<n>`: the item leaves this batch and waits for the next hint.
- On `batch`: one recheck message listing the batch's decisions as a set. Then spawn a fork (`Agent`, `subagent_type: fork`) that writes the epics with `new_epic.py`. Discussion continues.
- On fork return: compare each epic with its decisions, fix inline, run `ownership.py` and `ownership.py --overlap <epics>`, then post one line: `Batch <n> epics ready. Changed: <what or nothing>. Say go.`
- On `go`: `new_epic.py --batch B<n> <epics>`, commit epics, tags and the `plan.md` rows `new_epic.py` wrote, run `sprints.py` (adds column B<n>), send the RUN line with `runner.sh send <release> "RUN B<n> <release folder> from <talker>"` (`<talker>` is this session's name, from `ListAgents`: "This session is <name>"; start the runner with `runner.sh start` when `runner.sh list` shows none), post the next item.
- On `DONE` or `BLOCKED` from the runner: read `sprints.md`, the ATTENTION file and the tracker, and write nothing to the grid; the ATTENTION items enter the discussion. The talker runs `sprints.py` only on go.
- Release is an epic. The owner decides which batch it joins.

## Stage 2: plan

Epics per batch, written by the fork after `batch`, checked by the talker before `go`. Write the plan per epic, not all at once.

1. Write `plan.md` first, two sections only: `## Goals`, `## Epics` (`#`, `Epic` linked to the epic file, `Scope`; Scope one outcome sentence under 120 characters, no files or mechanics). Integration never waits on CI: merge on local checks that pass, merge commit per milestone; CI is the second run, on the staging branch after the one fast-forward (stage 3). It may exist while decisions are still open. Example: [reference/example-plan.md](reference/example-plan.md).
2. Write an epic file only when every decision it cites is accepted. An epic waiting on an open decision stays a row in `plan.md`.
3. Create each epic with `new_epic.py`. If it printed project planning rules, it wrote a contract stub. Read the rules, then write the epic by hand in the project's template. The rules override the bundled guidelines completely. Otherwise follow [reference/planning-guidelines.md](reference/planning-guidelines.md). Either way, keep the contract below. Epics implement decisions and never re-decide.
   - Before an epic is written, the epic writer (the fork) maps every site the change touches (file:line table); the epic lists those files, not guesses.
   - A ride-along item (a timeout bump, a glob fix) joins the nearest epic as a named ride-along, never its own epic.
4. Each epic says what must be proven (its `Acceptance:` line), not how it is run; the run manager picks the orchestration per column ([reference/run.md](reference/run.md), Orchestration). Section 2.1 holds one `### Milestone: <name>` block per milestone with the lines `- Files owned: a, b`, `- Depends on: <milestone names or epic numbers, or none>`, `- Review: none | fable`, then its `- Task 1: ... Checks: ...` lines. Merge adjacent small tasks. A milestone whose change warrants a review (public API, shared state, a cross-epic change) says `Review: fable`; the rest get checks only. Each milestone block gets its tracker, `trackers/NN-<slug>-tracker.md` from `templates/tracker.md` with `Status: planned`, in the same step.
5. After each epic file, run `ownership.py`: it writes `ownership.md` (milestone, epic, depends on, files, the critical path line) from the milestone blocks. A file shared by two milestones of the same column, or a dependency cycle, is a script error naming the file and the two milestones: fix it in the epic and run `ownership.py` again. On go, run `sprints.py`: it writes the `sprints.md` grid from `ownership.md`, one column per batch (see [reference/files.md](reference/files.md)). Checks sit in each task's `Checks:` and `process.md`, Acceptance in each epic's line, the release in the release epic, sandbox rules in `process.md` P5. `status.py` flags a missing or extra piece.
   - The run unit is the milestone: one team, one batch, its own branch, worktree, tracker and merge. Usually one milestone per epic; an epic may yield several (file groups, or a read-only side job like captures). Every changed file is owned by exactly one milestone while it runs; two milestones that share a file sit in different columns (`ownership.py` orders them, lower epic number first), or the two merge.
   - Inside a batch the milestones run in `ownership.md` order; the batch column starts with `·` in every cell.
   - What two or more milestones need (dependency adds, lockfile, lint or tsconfig config, CI edits, shared new helpers, baseline captures) is the shared milestone of the first batch; later milestones never touch `package.json`, the lockfile, ESLint or CI config.
6. A decision superseded after epics exist: `grep` its citation, for example `(D7)`, across the epic files and rewrite only those epics, then `ownership.py` again.
7. Readiness check before go: run `status.py` and fix every gap it reports (missing checks or trackers, open questions, a grid out of step with `ownership.md`). No readiness review agent for batches: the talker's check on fork return replaces it.
8. The release's `process.md`: before the first go, one `opus` audit agent reads it against this skill, the code (workflows, package manifests, coding standards) and the release's decisions, and returns a keep / cut / move / rewrite table per bullet; the main agent posts the cut list to the owner as one item and rewrites the file rule by rule (Process notes). A rule that no longer applies is deleted; a rewrite of the whole file may renumber, with one line in the header mapping the old numbers (`P12 preview → D72`) so older epics and trackers still read. No placeholder left (`status.py` reports it). `plan.md` is not frozen: each go appends the batch's epics to it; `sprints.md` moves all run long.
9. Handoff: only when the owner asks.

The contract. It applies inside any template:

- Decisions cited as `(D7)`, findings as `(F3)`, ATTENTION items as `(A2)`. A decision from another release: `(v0.4.x D9)`.
- Checks per task.
- No open questions in plan files.

A project template that lacks one gets it added in that project's style. Nothing else changes.

## Stage 3: run

Unattended, in the runner session (`runner.sh start`, brief `templates/runner-brief.md`). The talker never runs this stage: on go it types `RUN B<n> <release folder> from <talker>` into the runner window with `runner.sh send` (typed text opts the turn in to `ultracode`; a `SendMessage` does not), and reads `DONE` or `BLOCKED` back by `SendMessage`. The runner starts the batch in the turn the RUN line arrives. Loop: the loop skill with no interval (`ScheduleWakeup` dynamic mode), 30 minute fallback; the workflow or watcher notification is the real wake signal. The loop prompt is exactly `ultracode. Read ~/.claude/skills/expedition/reference/run.md, then continue the run. Skip if a turn is already working.` A dead runner: `runner.sh start` resumes it. Rules: [reference/run.md](reference/run.md). Short form:

- Resume-safe: a turn already working means do nothing. Otherwise find the release, run `status.py`, do the next step.
- The run follows `sprints.md` and makes no plan decisions. Each batch column runs on its own, several batches at once; inside a batch the milestones go in `ownership.md` order; tick the grid at every boundary. The orchestration per column is the run manager's judgment: one Workflow per milestone, several per milestone, or one for several, whatever proves the Acceptance with the fewest wakes and agents (a stage rerun: edit the script, resume with `resumeFromRunId`; never loose Agent calls), composed from the stage library in `templates/workflow.js` (build, epic check, optional review bounce, verify, judges, check, merge, release), run through the Workflow tool (invoking this skill is the multi-agent opt-in). Each milestone has its own worktree and branch, one builder end to end. The run manager is the runner session (its first prompt starts with `ultracode`, from `runner.sh`); it launches milestones, reads reports and trackers, ticks `sprints.md`, writes ATTENTION items, merges on green. The orchestration is the run manager's judgment, by cost: fewest main-session wakes, fewest agents that still prove every Acceptance ([reference/run.md](reference/run.md), Orchestration).
- Shared-run model only when a milestone needs it: one lead does the shared prework on the milestone branch and worktree; then each file set gets its own worktree and branch (`<slug>-<set>` for both), cut after the lead's last commit, because parallel commits in one checkout race on the index; one builder per file set; the lead merges each set branch back when its builder returns.
- The run never stops for one milestone. A builder that cannot finish its milestone (it contradicts an accepted decision, or its Acceptance is unreachable) stops that milestone only: commits what is coherent, writes the reason under `## Attention` in the tracker, returns blocked; dependent milestones are skipped the same way and marked `[!]`. Every other milestone merges, the release ships what merged, the handoff lists what did not, triage decides. Only a failed shared milestone of the first batch or a usage limit stops the whole run. A fix found mid-batch is a fix milestone added to the running column with `new_fix.py`; a bug in another milestone's merged file is a fix milestone on the integration branch. A fix milestone has a tracker (`trackers/fix-<slug>-tracker.md`) whose first line cites its findings, for example `(F3, F4)`, and a `sprints.md` row; `new_fix.py` writes both.
- Never idle. A milestone merges into the integration branch with a merge commit as soon as its recorded local checks pass, without asking; no PR, no CI wait, and no merge ever blocks another milestone. The staging branch (`dev`) is untouched until the release epic runs: the integration branch fast-forwards into it once, and the release epic's first milestone is integration: a verifier runs the suite there, records the tracker, reports; a red becomes fix milestones on the integration branch, then the fast-forward again and a rerun. A red CI run is fixed forward at once.
- Review: only where an epic says `Review: fable` under the milestone: one review on the whole diff, round 2 on `git diff <round 1 head>..HEAD` only, two rounds at most; majors still open after round 2 return `review-open` and the milestone does not merge. The `opus` fixer reads the findings and the diff only. Nits and minors alone: fixed by the builder in one commit, no fixer agent.
- Release is an epic and runs inside the batch the owner put it in (integration first, then the steps the release epic names; for this project the one PR of `process.md` P1), or inline when its script stopped early. The runner wakes on workflow notifications, 30 minute fallback, and reads trackers, not transcripts.
- Owner messages in the runner are discussion like the talker's (stage 1 rules); never propose process changes mid-run; a real choice found by the run becomes an ATTENTION item and the run continues with everything that does not depend on it.
- A Workflow run covers one milestone, its tasks in order in one worktree, or several milestones of one column when the run manager chose so, ending early when an owner decision is needed. Resumable with `resumeFromRunId`.
- `opus` for the shared milestone, build, fix, verify, check, baselines and lookups; `fable` for review, judges and plan writing. Judges run inside the workflow script, in parallel, majority in the script; a plain sub-agent cannot spawn them.
- A milestone's branch carries no PR; CI runs on the staging branch after the fast-forward. Details: the release's `process.md`.
- A script branches on facts (check pass or fail, a count), never on choices. A choice ends that milestone's Workflow run with a `needs-decision` result; other milestones continue.
- Sub-agents write the milestone's tracker. On the merge of a batch the runner ticks the column, writes the ATTENTION file, `findings.md` and the handoff, tags `[Done]` on the batch's decisions and sends `DONE`.

## Stage 4: triage

Folded into stage 1: ATTENTION items enter the discussion as items at once, in order with the rest. Rules: [reference/triage.md](reference/triage.md). Short form:

- First pass, no owner: every item that is not a real choice (see Owner input) gets its decision written at once with `- Source: A<n>` and its follow-up routed. Then the real choices, one per message, among the other items.
- A ruling becomes a D item (fix) or an F item (defer); the A item gets the tag line `[D<n>]` or `[F<n>]`.
- Minor follow-up: a follow-up epic `NN.1`, `NN.2` (`new_epic.py`) or a fix milestone (`new_fix.py`); its decisions join the next batch. Major follow-up: a new release folder.
- Handoff: only when the owner asks.

## Agents or Workflow

Judgment, by cost. A Workflow when a milestone has more than one stage or any parallel step, so the main session wakes once; a single Agent for one bounded task; inline for mechanical edits. The next step needs a decision: end the Workflow at that boundary (`needs-decision`).
