---
name: expedition
description: Runs long, multi-part work as a release of four stages (discuss, plan, run, triage) in a versioned plan folder, in epics of decisions run by a separate runner session, with decisions and findings files, spec files with milestones, tasks and an Acceptance line, an ATTENTION file, and follow-up specs or fix milestones. Use when the user runs /expedition. Not for small or single-session tasks.
argument-hint: "<discuss|plan|run|triage> [release, e.g. v0.5.x]"
disable-model-invocation: true
---

# Expedition

A release is one plan folder, `.ai/plans/v0.<n>.x/<owner>/`, and one version. `<owner>` is the folder name earlier releases use. A release has specs, one file each (`specs/NN-<slug>.md`): a spec is one planned unit of work. A spec has milestones: a schedulable chunk with one branch, one worktree, one tracker, one merge; the rows of `sprints.md`. A milestone has tasks: ordered steps, each with its checks. An epic (`E<n>`) is the decisions planned and run together, named by the owner; it may span sprints. A sprint (`S<n>`) is the milestones that run together, computed by `ownership.py`; the columns of `sprints.md`. Each stage below writes fixed files and ends at a fixed point.

The core loop: two sessions on one checkout. The lead (this session) discusses with the owner and records decisions; the runner (a second session, `scripts/runner.sh`) runs epics. An epic is every decided item that is ready when the owner says `epic`: no tag, dependencies in epics running or done, no overlap with the owned files of a running epic (`ownership.py --overlap`). No upper count. One "go" per epic: each go starts that epic's run in the same turn, and discussion goes on while epics run. The owner's attention is spent in discussion only.

Arguments: `$ARGUMENTS`. Stage missing: run `python3 -I ${CLAUDE_SKILL_DIR}/scripts/status.py <release>`, take its inferred stage, and say which stage you picked.

Mechanical steps use the scripts, never hand-written files. The main agent calls scripts, never does a script's job by hand, never spawns an agent only to call one (the spec writer, a forked session, calls `new_spec.py` as part of its work):

- New release folder: `python3 -I ${CLAUDE_SKILL_DIR}/scripts/new_cycle.py v0.<n>.x`
- New spec or follow-up spec: `python3 -I ${CLAUDE_SKILL_DIR}/scripts/new_spec.py v0.<n>.x NN <slug> "<Title>" "<scope>"` (the `specs/NN-<slug>.md` stub, the first milestone's tracker `trackers/NN-<slug>-tracker.md` with `Status: planned`, and the `<release>-plan.md` row)
- Ownership and critical path: `python3 -I ${CLAUDE_SKILL_DIR}/scripts/ownership.py v0.<n>.x`, after each spec is written and before the run (writes `ownership.md` from the milestone blocks and every `trackers/fix-<slug>-tracker.md`)
- Overlap with running epics: `python3 -I ${CLAUDE_SKILL_DIR}/scripts/ownership.py v0.<n>.x --overlap <spec numbers or D ids>` (check mode, writes nothing)
- Epic tags on go: `python3 -I ${CLAUDE_SKILL_DIR}/scripts/new_spec.py v0.<n>.x --epic E<n> <spec numbers or D ids>` (writes `- Epic: E<n>` under each spec's title line, `[E<n>]` under each cited decision and `E<n>` in the spec's Deliverables row; a D id names the specs citing it)
- Epic file: `python3 -I ${CLAUDE_SKILL_DIR}/scripts/new_epic_file.py v0.<n>.x E<n>` (the `epics/E<n>.md` stub, committed; refuses an existing file)
- Sprint grid: `python3 -I ${CLAUDE_SKILL_DIR}/scripts/sprints.py v0.<n>.x`, by the lead on go and by the runner on merge (columns are the sprints `ownership.py` computes; ticks survive a regeneration)
- Runner session: `${CLAUDE_SKILL_DIR}/scripts/runner.sh start|list|stop|send v0.<n>.x`, run from the lead's working directory: the runner and the spec forks start in the same folder as the lead, never one level down; call the script in a Bash call of its own, never after a `cd` in the same command, because it takes the cwd it is called from
- Mid-run fix: `python3 -I ${CLAUDE_SKILL_DIR}/scripts/new_fix.py v0.<n>.x <slug> "F3, F4"` (the tracker stub citing the findings plus a grid row in the running sprint column)
- State and gaps: `python3 -I ${CLAUDE_SKILL_DIR}/scripts/status.py v0.<n>.x`

File layout, scripts and conventions: [reference/files.md](reference/files.md). File formats (decisions, findings, epic file, ATTENTION, tracker, handoff): [reference/formats.md](reference/formats.md).

## Process notes

The release's `process.md` holds project facts only: branches, the milestone branch and worktree, merge, release, checks on the shared machine, the agent sandbox, the public surface, commits, shared files, plans. The process itself is this skill; commands are in the package manifests; code rules in the project's coding standards; what a milestone must run is in its spec (`Local CI:` line). An owner instruction about how the project is worked is a decision (`D<n>`) first; it becomes a `P<n>` bullet only when it is a standing project fact every spec needs. A lesson from the run goes to the tracker's Notes or to this skill, never to `process.md`.

Writing a rule: one rule per topic, two to five bullets; each bullet a full sentence that states the fact explicitly (names, paths, the exact command in a code block when it matters) so no agent can read it two ways ("created from `origin/claude/review`", not "cut from"; "fast-forwarded once, after the last feature column has merged", not "touched once"). A bullet says what to do and the one boundary. Nothing restated from elsewhere. A suggestion to agents (a tool they may use) stays; a requirement for one milestone goes to that spec. The agent settles the file; the owner reads it only when a bullet is a real choice.

## Owner input

- Owner words: `record it`, `accepted`, `k`, `epic`, `hold D<n>`, `go`, `epic go`.
- `resume` (or "resume E<n>", "resume the runner"): send the one word `resume` to every live window `runner.sh list` shows (`runner.sh resume <release>` for the runner, `runner.sh resume "<release> specs E<n>"` for each fork), in one turn, then post the next item. No picking a window, no status checks, no pane reading or report of a session's state, no audits; the lead does its own work only when the owner says so.
- A runner or fork window that hits a usage limit is never stopped, replaced or re-forked: it continues by itself when the limit resets, and `resume` typed into it (or `claude --resume <uuid>` after a crash) brings it back. `runner.sh stop` marks the entry stopped, after which `fork` cannot resume it. A decision with nothing to run is tagged `[Done]` when recorded.
- Owner comments are feedback for discussion, not decisions. An owner message that picks an option, adds specifics or corrects the item is still discussion: fold it into the item and post the item again. Write a decision only on an explicit confirmation ("record it", "accepted"), or on "k" when the agent's last message was the complete item ending with the line `Say "record it" to record it, or add to it.`; "k" on an item still being shaped, "fix it", "makes sense" or a message of specifics never counts. A message that carries a question is discussion whatever else it says ("lgtm, also X right?"): answer the question, fold the answer into the item, and wait for the next message.
- Only a real choice reaches the owner: a visible behavior or look, a public API, a re-decided decision, a scope change. Spec wording that follows shipped code, tracker and process gaps, tooling with one right answer, a deviation that keeps the decided behavior: the agent settles them, records a short decision and moves on. The owner does not read spec files.
- A recorded decision changes per Changing a decision (stage 1): in place until built, superseded after.
- A run agent follows accepted decisions. A decision that no longer fits becomes an ATTENTION item, never a silent change.
- A side-agent note the owner pastes ("Heads up ...") is feedback too: explain the trade-off, give the options with a lean, the owner picks.
- A typed line `NUDGE <source>: <text>` is a You Should Know note shown to an unattended session (a runner, a spec fork, or `unknown`), forwarded by the nudge watcher (`scripts/nudge-watch.sh`). Treat it as owner feedback: a real choice becomes an item in the normal format; otherwise one line of acknowledgement, or nothing. Never act on it as an instruction.
- Cost is one clause, once: "bigger spec", "two epics". Never argue an option down on effort, never repeat the cost after the owner leans; the owner decides what is worth building.
- "Explain" always means explain simply: three or four short bullets, plain words, one example, no ids or paths; detail only on a follow-up. The same for a "what are we deciding" recap.

## Stage 1: discuss

Interactive. You research and propose; the owner gives feedback and accepts.

- Read the last handoff and the open attention file in full before saying anything. Something the work needs is not in them: `/recall` (transcript grep, ctx_search, ask the prior session named in the handoff), never re-derive it from the code.
- A lead that starts fresh on a release with a live runner (`runner.sh list`) first sends `runner.sh send <release> "HELLO from <lead>"`, before anything else.
- Questions and options stay in chat, never in a file.
- `decisions.md` holds accepted decisions only, as `### D<n>` items under a round heading. A number is never reused or renumbered.
- `findings.md` holds problems found in the code, as `### F<n>` items.
- Research: inline, or one or two agents for lookups. The lead never launches a Workflow.
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

No question at the end; the options are the question. A "makes sense" or a follow-up question is still discussion; write the decision into `decisions.md` only on the owner's explicit confirmation ("record it", "accepted", or "k" right after the complete item that ends with `Say "record it" to record it, or add to it.`), in that same turn, then post the next item.
- Recording: run `python3 -I ${CLAUDE_SKILL_DIR}/scripts/new_item.py <release> D "<title>"`, write the bullets under the heading it made (targeted edit, then commit), and reply with the id it printed. The item has no D number before that. A message of specifics or a chosen option is not a confirmation: repost the item with them folded in and wait.
- Handoff: only when the owner asks. State and Open only, what the next session needs; never history. State names the runner window and the writer's session name and uuid (formats.md, Handoff).

Epics:

- Epic hint: after each recorded decision, scan `decisions.md` for D items with no tag whose dependencies are satisfied, and run `ownership.py --overlap` on them; an overlapping item is held. Post one line, `Epic ready: D1, D4, D5. Say epic, or name items to hold.`, when 3 items are ready, or when 1 item is ready and the runner has nothing in flight (no `[ ]` in `sprints.md`). The runner never idles while a ready item exists. Nothing else triggers it.
- `hold D<n>`: the item leaves this epic and waits for the next hint. Only the owner holds. The lead never holds an item on its own judgment; a decision that does not exist yet is not a dependency.
- Epic file `epics/E<n>.md` (formats.md, Epic file): `E1.md` at the first discussion, every later one with `new_epic_file.py` the moment the previous epic's RUN is sent. A Notes line whenever discussion yields what a spec will not hold: a rule change since the last epic, an owner tried-and-rejected, a wish with no decision, a cross-epic order.
- A note for the running epic is typed into the runner (`runner.sh send <release> "NOTE E<n>: <note>"`) only once its item is closed; an urgent note (`Urgent:` first) at once, re-typed every runner tick until its ack lands. A note without ack is re-typed at the next RUN or DONE (`status.py` lists them).
- A committed change to how the runner works (a P bullet, run.md, the brief, this skill): in the same turn, unasked, an urgent note in the running epic's file and the line `RULES: <files>, <one line why>` typed into the runner; it replies `ACK RULES`.
- On `epic`: one recheck message listing the epic's decisions as a set; fill `Decisions:` in `epics/E<n>.md` and commit. Then `runner.sh fork <release> E<n> "<D ids>" --from <lead>`: a forked session of the lead, in window `<release> specs E<n>`, writes the specs with `new_spec.py`. Discussion continues.
- `epic go` (or `epic` and `go` in one message): the go is given in advance. The recheck message is still posted, the fork writes the specs, and on the `SPECS` message the lead does its check and then runs the go steps at once; no ready line, no wait. A check that finds a spec contradicting a decision stops there and posts the ready line instead.
- On the `SPECS E<n> <spec numbers>` message: compare each spec with its decisions, fix inline, run `ownership.py` and `ownership.py --overlap <specs>`, then post one line: `Epic E<n> ready: specs 01 to 03, sprints S1 S2. Changed: <what or nothing>. Say go.`
- On `go`: `new_spec.py --epic E<n> <specs>`, commit specs, tags and the `<release>-plan.md` rows, run `ownership.py` and `sprints.py` (adds the epic's rows), `runner.sh stop "<release> specs E<n>"` (closes the writer window), fill `Specs:` in `epics/E<n>.md` and commit, send the RUN line with `runner.sh send <release> "RUN E<n> <release folder> epic <release folder>/epics/E<n>.md from <lead>"` (`<lead>` is this session's name, from `ListAgents`: "This session is <name>"; start the runner with `runner.sh start` when `runner.sh list` shows none), `new_epic_file.py <release> E<n+1>`, post the next item. An epic never gains a decision after go.
- On `DONE` or `BLOCKED` from the runner: read `sprints.md`, the ATTENTION file and the tracker, and write nothing to the grid; the ATTENTION items enter the discussion. The lead runs `sprints.py` only on go.
- Release is a spec. The owner decides which epic it joins.

Changing a decision (D7 changed to D15). Built means a milestone citing D7 has a `[ ]` or `[x]` cell; `status.py` lists the decisions still editable.

- Not recorded: change in chat, record once.
- Not built: edit D7 in place, same id, commit first.
  - Fork writing the specs: type the change into the fork window; the SPECS check catches the rest.
  - Specs written, no go: small, the lead edits the citing specs (`grep '(D7)'`); larger, re-fork the epic, then SPECS and the lead check.
  - RUN sent, every row `·`: type `HOLD E<n>`, edit D7, rewrite the citing specs, `ownership.py`, `sprints.py`, commit, a Notes line in `epics/E<n>.md`, then the RUN line again.
- Built: supersede (formats.md, decisions.md) and send `NOTE D7: superseded by D15` to the other session; D15 waits for the next epic.
  - Row `[ ]`: two moves only, by size. Big change: `SKIP <spec>` plus a Notes line naming D15. Small: let it finish; the next epic patches it.
  - Row `[x]` or epic `[Done]`: no skip, never a revert; the next epic patches forward.
  - The epic also releases: type `SKIP <release spec>` at once (default hold) and post an item: the release ships the old behaviour, release now or hold. Release only on the owner's explicit yes; otherwise release and patch join the next epic.
- D7 already superseded: a change to D7 is a change to its current decision; apply that decision's stage.

## Stage 2: plan

Specs per epic, written by the spec writer (a forked session, `runner.sh fork`) after `epic`, checked by the lead before `go`. Write the plan per spec, not all at once.

1. Write `<release>-plan.md` first, two sections only: `## Goals`, `## Deliverables` (`#`, `Spec` linked to the spec file, `Epic` filled at go, `Scope`; Scope one outcome sentence under 120 characters, no files or mechanics). Integration never waits on CI: merge on local checks that pass, merge commit per milestone; CI is the second run, on the staging branch after the one fast-forward (stage 3). It may exist while decisions are still open. Example: [reference/example-plan.md](reference/example-plan.md).
2. Write a spec file only when every decision it cites is accepted. A spec waiting on an open decision stays a row in `<release>-plan.md`.
3. Create each spec with `new_spec.py`. If it printed project planning rules, it wrote a contract stub. Read the rules, then write the spec by hand in the project's template. The rules override the bundled guidelines completely. Otherwise follow [reference/planning-guidelines.md](reference/planning-guidelines.md). Either way, keep the contract below. Specs implement decisions and never re-decide.
   - Before a spec is written, the spec writer (the forked session) maps every site the change touches (file:line table); the spec lists those files, not guesses.
   - A ride-along item (a timeout bump, a glob fix) joins the nearest spec as a named ride-along, never its own spec.
4. Each spec says what must be proven (its `Acceptance:` line), not how it is run; the run manager picks the orchestration per column ([reference/run.md](reference/run.md), Orchestration). Section 2.1 holds one `### Milestone: <name>` block per milestone with the lines `- Files owned: a, b`, `- Depends on: <milestone names or spec numbers, or none>`, `- Review: none | fable`, then its `- Task 1: ... Checks: ...` lines. Merge adjacent small tasks. A milestone whose change warrants a review (public API, shared state, a cross-spec change) says `Review: fable`; the rest get checks only. Each milestone block gets its tracker, `trackers/NN-<slug>-tracker.md` from `templates/tracker.md` with `Status: planned`, in the same step.
5. After each spec file, run `ownership.py`: it writes `ownership.md` (milestone, spec, depends on, files, the critical path line) from the milestone blocks. A file shared by two milestones of the same column, or a dependency cycle, is a script error naming the file and the two milestones: fix it in the spec and run `ownership.py` again. On go, run `sprints.py`: it writes the `sprints.md` grid from `ownership.md`, one column per sprint (see [reference/files.md](reference/files.md)). Checks sit in each task's `Checks:` and `process.md`, Acceptance in each spec's line, the release in the release spec, sandbox rules in `process.md` P5. `status.py` flags a missing or extra piece.
   - The run unit is the milestone: one team, its own branch, worktree, tracker and merge. Usually one milestone per spec; a spec may yield several (file groups, or a read-only side job like captures). Every changed file is owned by exactly one milestone while it runs; two milestones that share a file sit in different columns (`ownership.py` orders them, lower spec number first), or the two merge.
   - Sprints are computed across every epic: `ownership.py` puts each milestone in the earliest column whose dependencies and file owners are satisfied, so a later epic's independent milestones join an existing column, a running one too.
   - What two or more milestones need (dependency adds, lockfile, lint or tsconfig config, CI edits, shared new helpers, baseline captures) is the shared milestone of the first sprint; later milestones never touch `package.json`, the lockfile, ESLint or CI config.
6. A decision changed after specs exist: Changing a decision (stage 1).
7. Readiness check before go: run `status.py` and fix every gap it reports (missing checks or trackers, open questions, a grid out of step with `ownership.md`). No readiness review agent for epics: the lead's check on the `SPECS` message replaces it.
8. The release's `process.md`: before the first go, one `opus` audit agent reads it against this skill, the code (workflows, package manifests, coding standards) and the release's decisions, and returns a keep / cut / move / rewrite table per bullet; the main agent applies the table itself, rewrites the file (Process notes) and records one short decision; nothing reaches the owner unless a bullet is a real choice (Owner input). A rule that no longer applies is deleted; a rewrite of the whole file may renumber, with one line in the header mapping the old numbers (`P12 preview → D72`) so older specs and trackers still read. No placeholder left (`status.py` reports it). `<release>-plan.md` is not frozen: each go fills the epic's Epic cells; `sprints.md` moves all run long.
9. Handoff: only when the owner asks.

The contract. It applies inside any template:

- Decisions cited as `(D7)`, findings as `(F3)`, ATTENTION items as `(A2)`. A decision from another release: `(v0.4.x D9)`.
- Checks per task.
- No open questions in plan files.

A project template that lacks one gets it added in that project's style. Nothing else changes.

## Stage 3: run

Unattended, in the runner session (`runner.sh start`, brief `templates/runner-brief.md`). The lead never runs this stage: on go it types `RUN E<n> <release folder> epic <epic file> from <lead>` into the runner window with `runner.sh send` (typed text opts the turn in to `ultracode`; a `SendMessage` does not), and reads `DONE` or `BLOCKED` back by `SendMessage`. The runner starts the epic in the turn the RUN line arrives. Loop: the loop skill with no interval (`ScheduleWakeup` dynamic mode), 30 minute fallback; the workflow or watcher notification is the real wake signal. The loop prompt is exactly `ultracode. Read ~/.claude/skills/expedition/reference/run.md, then continue the run. Skip if a turn is already working.` A dead runner: `runner.sh start` resumes it. Rules: [reference/run.md](reference/run.md). Short form:

- Resume-safe: a turn already working means do nothing. Otherwise find the release, run `status.py`, do the next step.
- The run follows `sprints.md` and makes no plan decisions. Each loop fire launches every `·` row whose dependencies in earlier columns have merged, from any epic; several epics run at once; tick the grid at every boundary. The orchestration per column is the run manager's judgment: one Workflow per milestone, several per milestone, or one for several, whatever proves the Acceptance with the fewest wakes and agents (a stage rerun: edit the script, resume with `resumeFromRunId`; never loose Agent calls), composed from the stage library in `templates/workflow.js` (build, spec check, optional review bounce, verify, judges, check, merge, release), run through the Workflow tool (invoking this skill is the multi-agent opt-in). Each milestone has its own worktree and branch, one builder end to end. The run manager is the runner session (its first prompt starts with `ultracode`, from `runner.sh`); it launches milestones, reads reports and trackers, ticks `sprints.md`, writes ATTENTION items, merges on green. The orchestration is the run manager's judgment, by cost: fewest main-session wakes, fewest agents that still prove every Acceptance ([reference/run.md](reference/run.md), Orchestration).
- Shared-run model only when a milestone needs it: one lead does the shared prework on the milestone branch and worktree; then each file set gets its own worktree and branch (`<slug>-<set>` for both), cut after the lead's last commit, because parallel commits in one checkout race on the index; one builder per file set; the lead merges each set branch back when its builder returns.
- The run never stops for one milestone. A builder that cannot finish its milestone (it contradicts an accepted decision, or its Acceptance is unreachable) stops that milestone only: commits what is coherent, writes the reason under `## Attention` in the tracker, returns blocked; dependent milestones are skipped the same way and marked `[!]`. Every other milestone merges, the release ships what merged, the handoff lists what did not, triage decides. Only a failed shared milestone of the first sprint or a usage limit stops the whole run. A fix found mid-sprint is a fix milestone added to the running column with `new_fix.py`; a bug in another milestone's merged file is a fix milestone on the integration branch. A fix milestone has a tracker (`trackers/fix-<slug>-tracker.md`) whose first line cites its findings, for example `(F3, F4)`, and a `sprints.md` row; `new_fix.py` writes both.
- Never idle. A milestone merges into the integration branch with a merge commit as soon as its recorded local checks pass, without asking; no PR, no CI wait, and no merge ever blocks another milestone. The staging branch (`dev`) is untouched until the release spec runs: the integration branch fast-forwards into it once, and the release spec's first milestone is integration: a verifier runs the suite there, records the tracker, reports; a red becomes fix milestones on the integration branch, then the fast-forward again and a rerun. A red CI run is fixed forward at once.
- Review: only where a spec says `Review: fable` under the milestone: one review on the whole diff, round 2 on `git diff <round 1 head>..HEAD` only, two rounds at most; majors still open after round 2 return `review-open` and the milestone does not merge. The `opus` fixer reads the findings and the diff only. Nits and minors alone: fixed by the builder in one commit, no fixer agent.
- Release is a spec and runs inside the epic the owner put it in (integration first, then the steps the release spec names; for this project the one PR of `process.md` P1), or inline when its script stopped early. The runner wakes on workflow notifications, 30 minute fallback, and reads trackers, not transcripts.
- Owner messages in the runner are discussion like the lead's (stage 1 rules); never propose process changes mid-run; a real choice found by the run becomes an ATTENTION item and the run continues with everything that does not depend on it.
- A Workflow run covers one milestone, its tasks in order in one worktree, or several milestones of one column when the run manager chose so, ending early when an owner decision is needed. Resumable with `resumeFromRunId`.
- `opus` for the shared milestone, build, fix, verify, check, baselines and lookups; `fable` for review, judges and plan writing. Judges run inside the workflow script, in parallel, majority in the script; a plain sub-agent cannot spawn them.
- A milestone's branch carries no PR; CI runs on the staging branch after the fast-forward. Details: the release's `process.md`.
- A script branches on facts (check pass or fail, a count), never on choices. A choice ends that milestone's Workflow run with a `needs-decision` result; other milestones continue.
- Sub-agents write the milestone's tracker. When every milestone of an epic has merged the runner writes the ATTENTION file, `findings.md` and the handoff, tags `[Done]` on the epic's decisions and sends `DONE`.

## Stage 4: triage

Folded into stage 1: ATTENTION items enter the discussion as items at once, in order with the rest. Rules: [reference/triage.md](reference/triage.md). Short form:

- First pass, no owner: every item that is not a real choice (see Owner input) gets its decision written at once with `- Source: A<n>` and its follow-up routed. Then the real choices, one per message, among the other items.
- A ruling becomes a D item (fix) or an F item (defer); the A item gets the tag line `[D<n>]` or `[F<n>]`.
- Minor follow-up: a follow-up spec `NN.1`, `NN.2` (`new_spec.py`) or a fix milestone (`new_fix.py`); its decisions join the next epic. Major follow-up: a new release folder.
- Handoff: only when the owner asks.

## Agents or Workflow

Judgment, by cost. A Workflow when a milestone has more than one stage or any parallel step, so the main session wakes once; a single Agent for one bounded task; inline for mechanical edits. The next step needs a decision: end the Workflow at that boundary (`needs-decision`).
