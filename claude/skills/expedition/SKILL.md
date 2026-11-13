---
name: expedition
description: Runs long, multi-part work as a release of four stages (discuss, plan, run, triage) in a versioned plan folder, in epics of decisions run by a separate runner session, with a decisions file, one queue file for every item not yet decided, spec files with milestones, tasks and an Acceptance line, and follow-up specs or fix milestones. Use when the user runs /expedition. Not for small or single-session tasks.
argument-hint: "<discuss|plan|run|triage> [release, e.g. v0.5.x]"
disable-model-invocation: true
---

# Expedition

A release is one plan folder, `.ai/plans/v0.<n>.x/<owner>/`, and one version: `plan/` (specs, epics), `queue.md` (every item raised, a kanban board), `run/` (trackers, handoffs), `status/` (generated, never edited by hand; `index.html` and `data/` are swimlanes.py renders, git-ignored, never committed). `<owner>` is the folder name earlier releases use. A release has specs, one file each (`plan/specs/NN-<slug>.md`): a spec is one planned unit of work. A spec has milestones: a schedulable chunk with one branch, one worktree, one tracker, one merge; the rows of `status/sprints.md`. A milestone has tasks: ordered steps, each with its checks. An epic (`E<n>`) is the decisions planned and run together, named by the owner; it may span sprints. A sprint (`S<n>`) is the milestones that run together, computed by `ownership.py`; the columns of `status/sprints.md`. Each stage below writes fixed files and ends at a fixed point.

The core loop: two sessions on one checkout. The lead (this session) discusses with the owner and records decisions; the runner (a second session, `scripts/runner.sh`) runs epics. An epic is every decided item that is ready when the owner says `epic`: no tag, dependencies in epics running or done, no overlap with the owned files of a running epic (`ownership.py --overlap`). No upper count. One "go" per epic: each go starts that epic's run in the same turn, and discussion goes on while epics run. The owner's attention is spent in discussion only. Decisions are the work. An epic is only a grouping of decided items for planning and running. Discussion means taking items from the queue and deciding them.

Arguments: `$ARGUMENTS`. Stage missing: run `python3 -I ${CLAUDE_SKILL_DIR}/scripts/status.py <release>`, take its inferred stage, and say which stage you picked.

Mechanical steps use the scripts, never hand-written files. The scripts find the release folder from the cwd or one level below it, so sessions never `cd` for them and use `git -C <repo>` for git. The main agent calls scripts, never does a script's job by hand, never spawns an agent only to call one (the spec writer, a forked session, calls `new_spec.py` as part of its work):

- New release folder: `python3 -I ${CLAUDE_SKILL_DIR}/scripts/new_cycle.py v0.<n>.x`
- New spec or follow-up spec: `python3 -I ${CLAUDE_SKILL_DIR}/scripts/new_spec.py v0.<n>.x NN <slug> "<Title>" "<scope>"` (the `plan/specs/NN-<slug>.md` stub, the first milestone's tracker `run/trackers/NN-<slug>-tracker.md` with `Status: planned`, and the `<release>-plan.md` row)
- Ownership check: `python3 -I ${CLAUDE_SKILL_DIR}/scripts/ownership.py v0.<n>.x`, after each spec is written (computes in memory, from the milestone blocks and every `run/trackers/fix-<slug>-tracker.md`, each milestone's column and each epic's critical path, and prints them; writes nothing)
- Epic table, the pre-go preview: `python3 -I ${CLAUDE_SKILL_DIR}/scripts/ownership.py v0.<n>.x --epic E<n> [<spec numbers>]` (fills the Spec, Milestone and Sprint columns of the epic file's Ownership table, sprints provisional before go; prints the sprints the epic spans, its critical path, every pair of its specs owning the same file, each Files path that does not exist yet (a new file and a typo look the same) and a row file its spec does not own; no verdict; commits nothing)
- Overlap with running epics: `python3 -I ${CLAUDE_SKILL_DIR}/scripts/ownership.py v0.<n>.x --overlap <spec numbers or D ids>` (check mode, writes nothing)
- Start the epic: `python3 -I ${CLAUDE_SKILL_DIR}/scripts/new_epic_file.py v0.<n>.x E<n> <D ids>` (creates `plan/epics/E<n>.md` when missing, writes the `Decisions:` line and one Ownership row per decision with its title from `decisions.md`, adds only missing rows on a rerun; refuses a decision that is missing, superseded, already in another epic or done; commits). Without D ids it writes the empty stub (go.py does, for the next epic); `--note "<text>"` appends a Notes bullet and creates the section when missing
- Go: `python3 -I ${CLAUDE_SKILL_DIR}/scripts/go.py v0.<n>.x E<n> --from <lead>` (every go step in order, see On go; stops at the first failure with one line naming the step, a rerun skips the steps already done, one summary line at the end; the environment variable `EXPEDITION_RUNNER_SH` overrides the path of `runner.sh`)
- Epic tags on go: `python3 -I ${CLAUDE_SKILL_DIR}/scripts/new_spec.py v0.<n>.x --epic E<n> <spec numbers or D ids>` (go.py runs it; writes `- Epic: E<n>` under each spec's title line, `[E<n>]` under each cited decision, `E<n>` in the spec's Deliverables row and `Starts: S<n>` in the epic file, the current sprint at that moment; a D id names the specs citing it)
- Sprint grid: `python3 -I ${CLAUDE_SKILL_DIR}/scripts/sprints.py v0.<n>.x`, by go.py and by the runner on merge (columns are the sprints `ownership.py` computes; a finished row keeps its cell, a running row carries its `[ ]` to its new column; then the Sprint column of every unfinished epic's table follows the grid)
- Swimlane page: `python3 -I ${CLAUDE_SKILL_DIR}/scripts/swimlanes.py v0.<n>.x`, right after every `sprints.py` run (writes `status/data/sprints.data.js` and `sprints.json` for `status/index.html`, refreshes the page from `templates/swimlanes.html` when the template is newer)
- Old layout (no `plan/`): `python3 -I ${CLAUDE_SKILL_DIR}/scripts/migrate_layout.py v0.<n>.x` once; the other scripts refuse the folder until then
- A folder that still has `status/ownership.md`: `python3 -I ${CLAUDE_SKILL_DIR}/scripts/migrate_epics.py v0.<n>.x [--dry-run]` once (fills every epic file's Ownership table from its specs, removes an empty Notes section, `git rm` of `status/ownership.md`; commits nothing); the other scripts refuse the folder until then
- Epics run before start sprints existed (grid rows, no `Starts:`): `python3 -I ${CLAUDE_SKILL_DIR}/scripts/ownership.py v0.<n>.x --backfill-starts [--dry-run]` once, then `ownership.py`, `sprints.py`, `swimlanes.py`
- Old queue files (`findings.md` or `run/attentions/`, no `queue.md`), a `queue.md` that is not a kanban board yet, or a board in the old card format (from tags, `Decision:` facts): `python3 -I ${CLAUDE_SKILL_DIR}/scripts/migrate_queue.py v0.<n>.x [--dry-run]` once; the other scripts refuse the folder until then
- Runner session: `${CLAUDE_SKILL_DIR}/scripts/runner.sh start|list|stop|send v0.<n>.x`: the runner and the spec forks run in the lead's working directory, never one level down; `start` and `fork` open the new window in the folder they are called from, or in `--cwd PATH`
- Mid-run fix: `python3 -I ${CLAUDE_SKILL_DIR}/scripts/new_fix.py v0.<n>.x <slug> "Q3, Q4"` (the tracker stub citing the queue cards, each card moved to Autofix, and a grid row in the current sprint column)
- Queue cards: `python3 -I ${CLAUDE_SKILL_DIR}/scripts/new_item.py v0.<n>.x --move Q<n> Open|Later|Dropped|Autofix` and `--fact Q<n> "<text>"`; next card: `status.py v0.<n>.x --next` (the first card in Open with its facts, or `none`)
- State and gaps: `python3 -I ${CLAUDE_SKILL_DIR}/scripts/status.py v0.<n>.x`
- Progress reply for the owner: `python3 -I ${CLAUDE_SKILL_DIR}/scripts/status.py v0.<n>.x --progress` (Markdown, printed as the reply)

File layout, scripts and conventions: [reference/files.md](reference/files.md). File formats (decisions, queue, epic file, tracker, handoff): [reference/formats.md](reference/formats.md).

## Process notes

The release's `process.md` holds project facts only: branches, the milestone branch and worktree, merge, release, checks on the shared machine, the agent sandbox, the public surface, commits, shared files, plans. The process itself is this skill; commands are in the package manifests; code rules in the project's coding standards; what a milestone must run is in its spec (`Local CI:` line). An owner instruction about how the project is worked is a decision (`D<n>`) first; it becomes a `P<n>` bullet only when it is a standing project fact every spec needs. A lesson from the run goes to the tracker's Notes or to this skill, never to `process.md`.

Writing a rule: one rule per topic, two to five bullets; each bullet a full sentence that states the fact explicitly (names, paths, the exact command in a code block when it matters) so no agent can read it two ways ("created from `origin/claude/review`", not "cut from"; "fast-forwarded once, after the last feature column has merged", not "touched once"). A bullet says what to do and the one boundary. Nothing restated from elsewhere. A suggestion to agents (a tool they may use) stays; a requirement for one milestone goes to that spec. The agent settles the file; the owner reads it only when a bullet is a real choice.

## Owner input

- Owner words: `record it`, `accepted`, `k`, `epic`, `hold D<n>`, `go`, `epic go`.
- `progress` (or "status"): the lead runs `python3 -I ${CLAUDE_SKILL_DIR}/scripts/status.py <release> --progress` and replies with its output unchanged and nothing else: no added sentence, no item, no commit id, no ack, no list of waiting work. Example output:

  ```
  **E12** · Specs 6/12
  - **Running**
    - 44 Range filter editor
  - **Blocked**
    - 47 Comparison page: the table names a feature tablecn dropped; keep or remove the row.
  ```

  `Running` lists each spec with a milestone running, including a spec that is being retried or fixed. `Blocked` lists only work that has stopped, with the run's own reason from the tracker.
- `resume` (or "resume E<n>", "resume the runner"): send the one word `resume` to every live window `runner.sh list` shows (`runner.sh resume <release>` for the runner, `runner.sh resume "<release> specs E<n>"` for each fork), in one turn, then post the next item. No picking a window, no status checks, no pane reading or report of a session's state, no audits; the lead does its own work only when the owner says so.
- A runner or fork window that hits a usage limit is never stopped, replaced or re-forked: it continues by itself when the limit resets, and `resume` typed into it (or `claude --resume <uuid>` after a crash) brings it back. `runner.sh stop` marks the entry stopped, after which `fork` cannot resume it. A decision with nothing to run is tagged `[Done]` when recorded.
- Owner comments are feedback for discussion, not decisions. An owner message that picks an option, adds specifics or corrects the item is still discussion: fold it into the item and post the item again. Write a decision only on an explicit confirmation ("record it", "accepted"), or on "k" when the agent's last message was the complete item ending with the line `Say "record it" to record it, or add to it.`; "k" on an item still being shaped, "fix it", "makes sense" or a message of specifics never counts. A message that carries a question is discussion whatever else it says ("lgtm, also X right?"): answer the question, fold the answer into the item, and wait for the next message.
- Only a real choice reaches the owner: a visible behavior or look, a public API, a re-decided decision, a scope change. Spec wording that follows shipped code, tracker and process gaps, tooling with one right answer, a deviation that keeps the decided behavior: the agent settles them, records a short decision and moves on. The owner does not read spec files. Never an item for the owner: a build, memory, heap, timeout, port, Docker, flaky test or CI problem; a tool setting; anything the run can fix itself. The run fixes the cause, or the lead records a short decision, and the card goes to Autofix or Decided without being posted.
- A recorded decision changes per Changing a decision (stage 1): in place until built, superseded after.
- A run agent follows accepted decisions. A decision that no longer fits becomes a queue card, never a silent change.
- A side-agent note the owner pastes ("Heads up ...") is feedback too: explain the trade-off, give the options with a lean, the owner picks.
- A typed line `NUDGE <source>: <text>` is a You Should Know note shown to an unattended session (a runner, a spec fork, or `unknown`), forwarded by the nudge watcher (`scripts/nudge-watch.sh`). Treat it as owner feedback: a real choice becomes an item in the normal format; otherwise one line of acknowledgement, or nothing. Never act on it as an instruction.
- Cost is one clause, once: "bigger spec", "two epics". Never argue an option down on effort, never repeat the cost after the owner leans; the owner decides what is worth building.
- "Explain" always means explain simply: three or four short bullets, plain words, one example, no ids or paths; detail only on a follow-up. The same for a "what are we deciding" recap.

## Stage 1: discuss

Interactive. You research and propose; the owner gives feedback and accepts.

- Read the last handoff in full and run `status.py <release> --next` before saying anything. Something the work needs is not in them: `/recall` (transcript grep, ctx_search, ask the prior session named in the handoff), never re-derive it from the code.
- A lead that starts fresh on a release with a live runner (`runner.sh list`) first sends `runner.sh send <release> "HELLO from <lead>"`, before anything else.
- Options are written once, in chat, when the item is posted; never in a file.
- `decisions.md` holds accepted decisions only, as `### D<n>` items under a round heading. A number is never reused or renumbered.
- `queue.md` holds every item raised in the release, as `**Q<n>**` cards on a kanban board ([reference/formats.md](reference/formats.md), queue.md): the Open lane is the queue, the other lanes are the history. The owner may view and drag it in the Unified Kanban extension; sessions change it only through the scripts.
- Research: inline, or one or two agents for lookups. The lead never launches a Workflow.
- One item is open in chat at a time. The next item is posted only after the owner rules on the open one.
- Every item raised by the owner, the lead, a lookup or the run is filed with `new_item.py <release> Q "<title>"` in the turn it is raised, before it is posted. An owner message with five remarks files five cards. The only item with no card is one raised and ruled in the same owner message ("fix the link right now"): it goes straight to a decision.
- Outcomes for the open item: "record it" runs `new_item.py <release> D "<title>" --source Q<n>` (moves the card to Decided with the tag `#D<n>` and writes the decision's last bullet `- Source: Q<n>`); "later" runs `new_item.py <release> --move Q<n> Later`; "drop it" `--move Q<n> Dropped`. A parked card is reopened with `--move Q<n> Open`.
- The owner switches to another item while one is open and unruled ("let's do Q14 first"): add the points made so far to the open item's card with `new_item.py <release> --fact Q<n> "<text>"`, leave it in Open, and post the item the owner asked for. The switched-from item comes back in queue order like any other.
- The lead never invents an item number: every item carries the Q id `new_item.py` printed, a settled item also its D id.
- An item that needs a lookup: start the lookup agent and give it the Q id and the `queue.md` path. The agent adds its facts with `new_item.py <release> --fact Q<n> "<text>"` and reports one line. The lead skips that card while its lookup runs. A lookup that returns while another item is open gets exactly one line in chat, `Q15 ready`, never a full item.
- Next item: `status.py <release> --next` prints the first card in Open with its facts, or `none`. The open item's card is also in Open, so the lead asks for the next item only after the owner rules on the open one. No session reads the whole file to find what is next.
- Both sessions may discuss and record decisions, under the shared-file rules in [reference/formats.md](reference/formats.md).
- A finished lookup agent stays idle, not stopped: it costs nothing idle, and a follow-up on the same area goes to it by name (`SendMessage`) so its context is reused. Stop agents only when the owner says so.

Item format, one item per message, the next item only after the owner rules on this one. Every item is headed `# Q<n>. <sentence>`; there is no unnumbered item header:

```
# Q<n>. <Title>: one plain sentence a non-expert reads in one pass, in everyday words, no ids, paths or jargon.
- the first bullet, required: what is wrong today, where, and what the change is (file:line, ids, measurements)
- optional bullets: facts, how the common references do it (measured or read, never assumed)
## Options:
- recommended: ...
- ...
```

No question at the end; the options are the question. Options are about the decision only: fix, keep, drop, or which variant. An option never names an epic, a sprint or a release, and never offers to decide later; the owner says "later" or "drop it" unprompted. A "makes sense" or a follow-up question is still discussion; write the decision into `decisions.md` only on the owner's explicit confirmation ("record it", "accepted", or "k" right after the complete item that ends with `Say "record it" to record it, or add to it.`), in that same turn, then post the next item.
- Recording: run `python3 -I ${CLAUDE_SKILL_DIR}/scripts/new_item.py <release> D "<title>"` (with `--source Q<n>` for a queued item), write the bullets under the heading it made, above a `- Source:` line (targeted edit, then commit), and reply with the id it printed. The item has no D number before that. A message of specifics or a chosen option is not a confirmation: repost the item with them folded in and wait.
- Handoff: only when the owner asks. State and Open only, what the next session needs; never history. State names the runner window and the writer's session name and uuid (formats.md, Handoff).

Epics:

- Epic hint: a nudge, never a question and never a step the owner must take. After each recorded decision, scan `decisions.md` for D items with no tag whose dependencies are satisfied (on the board: the unticked cards in the Decided lane), and run `ownership.py --overlap` on them; an overlapping item is held. When 3 items are ready, or 1 is ready and the runner has nothing in flight (no `[ ]` in `status/sprints.md`), add the one line `Epic ready: D1, D4, D5.` under the next item. Post it once per set, and not again until another item becomes ready. The next item is posted in the same message; discussion never waits for `epic`. The owner says `epic` when they choose, or names items to add or hold. Nothing else triggers it.
- `hold D<n>`: the item leaves this epic and waits for the next hint. Only the owner holds. The lead never holds an item on its own judgment; a decision that does not exist yet is not a dependency.
- Epic file `plan/epics/E<n>.md` (formats.md, Epic file): started by `new_epic_file.py` on `epic`; go.py writes the next epic's stub the moment the RUN is sent. A Notes line, with `new_epic_file.py <release> E<n> --note "<text>"`, only when discussion yields what the specs cannot hold: a rule change since the last epic, an owner tried-and-rejected, a wish with no decision, a cross-epic order, a SKIP or HOLD during the run.
- A note for the running epic is typed into the runner (`runner.sh send <release> "NOTE E<n>: <note>"`) only once its item is closed; an urgent note (`Urgent:` first) at once, re-typed every runner tick until its ack lands. A note without ack is re-typed at the next RUN or DONE (`status.py` lists them).
- A committed change to how the runner works (a P bullet, run.md, the brief, this skill): in the same turn, unasked, an urgent note in the running epic's file and the line `RULES: <files>, <one line why>` typed into the runner; it replies `ACK RULES`.
- On `epic`: one recheck message listing the epic's decisions as a set; `new_epic_file.py <release> E<n> <D ids>` (the `Decisions:` line and one Ownership row per decision, committed). Then `runner.sh fork <release> E<n> "<D ids>" --from <lead>`: a forked session of the lead, in window `<release> specs E<n>`, fills the Files column, cuts the epic into specs by the three aims, writes them with `new_spec.py`, completes the table with `ownership.py --epic`, checks the plan, and sends `SPECS` (stage 2). Discussion continues.
- `epic go` (or `epic` and `go` in one message): the go is given in advance. The recheck message is still posted, the fork writes the specs, and on the `SPECS` message the lead does its check and then runs `go.py` at once; no ready line, no wait. A check that finds a spec contradicting a decision stops there and posts the ready line instead.
- On the `SPECS E<n> <spec numbers>` message: compare each spec with its decisions and fix inline. Check the plan by judgment, reading the epic file only and running no script for it: the same file under two specs, or a long run of different sprints, is a question, not an error. Send the fork back (type into its window) when a clearly better cut exists. Then post one line: `Epic E12 ready: specs 39 to 49, sprints S17 to S18. Changed: <what or nothing>. Say go.`
- On `go`: `go.py <release> E<n> --from <lead>` (`<lead>` is this session's name, from `ListAgents`: "This session is <name>"), then post the next item. Its steps, in order: `new_spec.py --epic` (tags the specs and decisions, writes `Starts:`, ticks the epic's cards in `queue.md` and tags them `#E<n>`); commit specs, tags, plan rows and `queue.md`; `sprints.py` and `swimlanes.py`; `Specs:` and the final Sprint column in the epic file, committed; `runner.sh stop "<release> specs E<n>"` (closes the writer window); `runner.sh start <release>` when `runner.sh list` shows no runner, then the RUN line `runner.sh send <release> "RUN E<n> <release folder> epic <release folder>/plan/epics/E<n>.md from <lead>"`; the next epic's stub. A failed step stops it with one line naming the step: fix the cause and run `go.py` again. An epic never gains a decision after go.
- On `DONE` or `BLOCKED` from the runner: read `status/sprints.md`, the tracker and `status.py <release> --next`, and write nothing to the grid; the run's cards are queue cards like any other. The lead runs `sprints.py` and `swimlanes.py` only through `go.py`.
- Release is a spec. The owner decides which epic it joins.

Changing a decision (D7 changed to D15). Built means a milestone citing D7 has a `[ ]` or `[x]` cell; `status.py` lists the decisions still editable.

- Not recorded: change in chat, record once.
- Not built: edit D7 in place, same id, commit first.
  - Fork writing the specs: type the change into the fork window; the SPECS check catches the rest.
  - Specs written, no go: small, the lead edits the citing specs (`grep '(D7)'`); larger, re-fork the epic, then SPECS and the lead check.
  - RUN sent, every row `·`: type `HOLD E<n>`, edit D7, rewrite the citing specs, `ownership.py --epic E<n>`, `sprints.py`, `swimlanes.py`, commit, a Notes line in `plan/epics/E<n>.md`, then the RUN line again.
- Built: supersede (formats.md, decisions.md) and send `NOTE D7: superseded by D15` to the other session; D15 waits for the next epic.
  - Row `[ ]`: two moves only, by size. Big change: `SKIP <spec>` plus a Notes line naming D15. Small: let it finish; the next epic patches it.
  - Row `[x]` or epic `[Done]`: no skip, never a revert; the next epic patches forward.
  - The epic also releases: type `SKIP <release spec>` at once (default hold) and post an item: the release ships the old behaviour, release now or hold. Release only on the owner's explicit yes; otherwise release and patch join the next epic.
- D7 already superseded: a change to D7 is a change to its current decision; apply that decision's stage.

## Stage 2: plan

Specs per epic, written by the spec writer (a forked session, `runner.sh fork`) after `epic`, checked by the lead before `go`. Write the plan per spec, not all at once.

The spec writer's order: fill the Files column of the epic's Ownership table (the files each decision changes, paths as the project writes them); cut the epic into specs by the three aims below; write the specs; run `ownership.py --epic E<n>` to complete the table; check the plan with that output and its own judgment, and regroup when a clearly better cut exists; send `SPECS`.

Cutting an epic into specs: weigh three aims.

- As much as possible runs side by side. Specs that do not share files can be built at the same time.
- No spec is bloated. One spec is a piece of work one builder can hold and one review can cover.
- Work is not split so finely that agents repeat each other. Changes to the same area are cheaper in one spec: a filter look change and a filter bug fix go to the same builder, who already has that code in context.

These are aims, not rules. They pull against each other, and the right cut depends on the epic. Choose the plan that is best overall, and do not bend a good plan to satisfy one aim. The ownership table and its Sprint column show the result; they do not pass or fail it. The reason for a deliberate choice (two specs sharing a file, or one larger spec) goes in the spec, in one line.

1. Write `<release>-plan.md` first, two sections only: `## Goals`, `## Deliverables` (`#`, `Spec` linked to the spec file, `Epic` filled at go, `Scope`; Scope one outcome sentence under 120 characters, no files or mechanics). Integration never waits on CI: merge on local checks that pass, merge commit per milestone; CI is the second run, on the staging branch after the one fast-forward (stage 3). It may exist while decisions are still open. Example: [reference/example-plan.md](reference/example-plan.md).
2. Write a spec file only when every decision it cites is accepted. A spec waiting on an open decision stays a row in `<release>-plan.md`.
3. Create each spec with `new_spec.py`. If it printed project planning rules, it wrote a contract stub. Read the rules, then write the spec by hand in the project's template. The rules override the bundled guidelines completely. Otherwise follow [reference/planning-guidelines.md](reference/planning-guidelines.md). Either way, keep the contract below. Specs implement decisions and never re-decide.
   - Before a spec is written, the spec writer (the forked session) maps every site the change touches (file:line table); the spec lists those files, not guesses.
   - A ride-along item (a timeout bump, a glob fix) joins the nearest spec as a named ride-along, never its own spec.
4. Each spec says what must be proven (its `Acceptance:` line), not how it is run; the run manager picks the orchestration per column ([reference/run.md](reference/run.md), Orchestration). Section 2.1 holds one `### Milestone: <name>` block per milestone with the lines `- Files owned: a, b`, `- Depends on: <milestone names or spec numbers, or none>`, `- Review: none | fable`, then its `- Task 1: ... Checks: ...` lines. Merge adjacent small tasks. A milestone whose change warrants a review (public API, shared state, a cross-spec change) says `Review: fable`; the rest get checks only. Each milestone block gets its tracker, `run/trackers/NN-<slug>-tracker.md` from `templates/tracker.md` with `Status: planned`, in the same step.
5. After each spec file, run `ownership.py`: it computes, in memory, each milestone's column and each epic's critical path from the milestone blocks, and writes nothing. A file shared by two milestones of the same column, or a dependency cycle, is a script error naming the file and the two milestones: fix it in the spec and run `ownership.py` again. When the epic's specs are written, `ownership.py --epic E<n>` completes the epic file's table. On go, `go.py` runs `sprints.py` then `swimlanes.py`: they write the `status/sprints.md` grid, one column per sprint, and the swimlane data for `status/index.html` (see [reference/files.md](reference/files.md)). Checks sit in each task's `Checks:` and `process.md`, Acceptance in each spec's line, the release in the release spec, sandbox rules in `process.md` P5. `status.py` flags a missing or extra piece.
   - The run unit is the milestone: one team, its own branch, worktree, tracker and merge. Usually one milestone per spec; a spec may yield several (file groups, or a read-only side job like captures). Every changed file is owned by exactly one milestone while it runs; two milestones that share a file sit in different columns (`ownership.py` orders them, lower spec number first), or the two merge.
   - Sprints are computed across every epic: `ownership.py` puts each milestone in the first column at or after its epic's start sprint (`Starts:` in the epic file, the current sprint at go) whose dependencies and file owners are satisfied. A new epic never lands in a finished column; fix milestones go in the current sprint column ([reference/files.md](reference/files.md), Ownership).
   - What two or more milestones need (dependency adds, lockfile, lint or tsconfig config, CI edits, shared new helpers, baseline captures) is the shared milestone of the first sprint; later milestones never touch `package.json`, the lockfile, ESLint or CI config.
6. A decision changed after specs exist: Changing a decision (stage 1).
7. Readiness check before go: run `status.py` and fix every gap it reports (missing checks or trackers, open questions, a grid out of step with the specs, an epic table out of step with its specs or the grid). No readiness review agent for epics: the lead's check on the `SPECS` message replaces it.
8. The release's `process.md`: before the first go, one `opus` audit agent reads it against this skill, the code (workflows, package manifests, coding standards) and the release's decisions, and returns a keep / cut / move / rewrite table per bullet; the main agent applies the table itself, rewrites the file (Process notes) and records one short decision; nothing reaches the owner unless a bullet is a real choice (Owner input). A rule that no longer applies is deleted; a rewrite of the whole file may renumber, with one line in the header mapping the old numbers (`P12 preview → D72`) so older specs and trackers still read. No placeholder left (`status.py` reports it). `<release>-plan.md` is not frozen: each go fills the epic's Epic cells; `status/sprints.md` moves all run long.
9. Handoff: only when the owner asks.

The contract. It applies inside any template:

- Decisions cited as `(D7)`, queue cards as `(Q3)`. A decision from another release: `(v0.4.x D9)`.
- Checks per task.
- No open questions in plan files.

A project template that lacks one gets it added in that project's style. Nothing else changes.

## Stage 3: run

Unattended, in the runner session (`runner.sh start`, brief `templates/runner-brief.md`). The lead never runs this stage: on go it types `RUN E<n> <release folder> epic <epic file> from <lead>` into the runner window with `runner.sh send` (typed text opts the turn in to `ultracode`; a `SendMessage` does not), and reads `DONE` or `BLOCKED` back by `SendMessage`. The runner starts the epic in the turn the RUN line arrives. Loop: the loop skill with no interval (`ScheduleWakeup` dynamic mode), 30 minute fallback; the workflow or watcher notification is the real wake signal. The loop prompt is exactly `ultracode. Read ~/.claude/skills/expedition/reference/run.md, then continue the run. Skip if a turn is already working.` A dead runner: `runner.sh start` resumes it. Rules: [reference/run.md](reference/run.md). Short form:

- Resume-safe: a turn already working means do nothing. Otherwise find the release, run `status.py`, do the next step.
- The run follows `status/sprints.md` and makes no plan decisions. Each loop fire launches every `·` row whose dependencies in earlier columns have merged, from any epic; several epics run at once; tick the grid at every boundary. The orchestration per column is the run manager's judgment: one Workflow per milestone, several per milestone, or one for several, whatever proves the Acceptance with the fewest wakes and agents (a stage rerun: edit the script, resume with `resumeFromRunId`; never loose Agent calls), composed from the stage library in `templates/workflow.js` (build, spec check, optional review bounce, verify, judges, check, merge, release), run through the Workflow tool (invoking this skill is the multi-agent opt-in). Each milestone has its own worktree and branch, one builder end to end. The run manager is the runner session (its first prompt starts with `ultracode`, from `runner.sh`); it launches milestones, reads reports and trackers, ticks `status/sprints.md`, files queue cards, merges on green. The orchestration is the run manager's judgment, by cost: fewest main-session wakes, fewest agents that still prove every Acceptance ([reference/run.md](reference/run.md), Orchestration).
- Shared-run model only when a milestone needs it: one lead does the shared prework on the milestone branch and worktree; then each file set gets its own worktree and branch (`<slug>-<set>` for both), cut after the lead's last commit, because parallel commits in one checkout race on the index; one builder per file set; the lead merges each set branch back when its builder returns.
- The run never stops for one milestone. A builder that cannot finish its milestone (it contradicts an accepted decision, or its Acceptance is unreachable) stops that milestone only: commits what is coherent, writes the reason under `## Attention` in the tracker, returns blocked; dependent milestones are skipped the same way and marked `[!]`. Every other milestone merges, the release ships what merged, the handoff lists what did not, triage decides. Only a failed shared milestone of the first sprint or a usage limit stops the whole run. A fix found mid-sprint is a fix milestone added to the current sprint column with `new_fix.py`; a bug in another milestone's merged file is a fix milestone on the integration branch. A fix milestone has a tracker (`run/trackers/fix-<slug>-tracker.md`) whose first line cites its queue cards, for example `(Q3, Q4)`, and a `status/sprints.md` row; `new_fix.py` writes both and moves each cited card to Autofix.
- Never idle. A milestone merges into the integration branch with a merge commit as soon as its recorded local checks pass, without asking; no PR, no CI wait, and no merge ever blocks another milestone. The staging branch (`dev`) is untouched until the release spec runs: the integration branch fast-forwards into it once, and the release spec's first milestone is integration: a verifier runs the suite there, records the tracker, reports; a red becomes fix milestones on the integration branch, then the fast-forward again and a rerun. A red CI run is fixed forward at once.
- Review: only where a spec says `Review: fable` under the milestone: one review on the whole diff, round 2 on `git diff <round 1 head>..HEAD` only, two rounds at most; majors still open after round 2 return `review-open` and the milestone does not merge. The `opus` fixer reads the findings and the diff only. Nits and minors alone: fixed by the builder in one commit, no fixer agent.
- Release is a spec and runs inside the epic the owner put it in (integration first, then the steps the release spec names; for this project the one PR of `process.md` P1), or inline when its script stopped early. The runner wakes on workflow notifications, 30 minute fallback, and reads trackers, not transcripts.
- Owner messages in the runner are discussion like the lead's (stage 1 rules); never propose process changes mid-run; a real choice found by the run becomes a queue card and the run continues with everything that does not depend on it.
- A Workflow run covers one milestone, its tasks in order in one worktree, or several milestones of one column when the run manager chose so, ending early when an owner decision is needed. Resumable with `resumeFromRunId`.
- `opus` for the shared milestone, build, fix, verify, check, baselines and lookups; `fable` for review, judges and plan writing. Judges run inside the workflow script, in parallel, majority in the script; a plain sub-agent cannot spawn them.
- A milestone's branch carries no PR; CI runs on the staging branch after the fast-forward. Details: the release's `process.md`.
- A script branches on facts (check pass or fail, a count), never on choices. A choice ends that milestone's Workflow run with a `needs-decision` result; other milestones continue.
- Sub-agents write the milestone's tracker. When every milestone of an epic has merged the runner files its queue cards, writes the handoff, tags `[Done]` on the epic's decisions and sends `DONE`.

## Stage 4: triage

Folded into stage 1: the run's cards are queue cards and come up through `status.py --next` like any other. Rules: [reference/triage.md](reference/triage.md). Short form:

- First pass, no owner: every card that is not a real choice (see Owner input) gets its decision written at once with `--source Q<n>` and its follow-up routed. Then the real choices, one per message, among the other items.
- A ruling moves the card: to Decided through `new_item.py D --source Q<n>`, to Later or Dropped through `new_item.py --move`.
- Minor follow-up: a follow-up spec `NN.1`, `NN.2` (`new_spec.py`) or a fix milestone (`new_fix.py`); its decisions join the next epic. Major follow-up: a new release folder.
- Handoff: only when the owner asks.

## Agents or Workflow

Judgment, by cost. A Workflow when a milestone has more than one stage or any parallel step, so the main session wakes once; a single Agent for one bounded task; inline for mechanical edits. The next step needs a decision: end the Workflow at that boundary (`needs-decision`).
