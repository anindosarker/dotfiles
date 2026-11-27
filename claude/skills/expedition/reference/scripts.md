# Scripts

For any session that is about to run a command of the skill: the commands, then each script with what it writes and what it refuses.

## Contents
- How to run them
- The commands by job
- Each script

## How to run them

- Mechanical steps use the scripts, never hand-written files.
- The scripts sit in `scripts/` by subject, one job each: `plan/`, `epics/`, `sprints/`, `queue/`, `decisions/`, `status/`, `run/`, `migrate/`, and the shared code in `lib/`.
- The scripts find the release folder from the cwd or one level below it, so sessions never `cd` for them and use `git -C <repo>` for git.
- The main agent calls scripts, never does a script's job by hand, never spawns an agent only to call one (the spec writer, a forked session, calls `plan/new_spec.py` as part of its work):

- Each runs as `python3 -I ${CLAUDE_SKILL_DIR}/scripts/<command>`; `run/runner.sh` runs as `${CLAUDE_SKILL_DIR}/scripts/run/runner.sh`.
- Arguments, what each script writes and what it refuses: Each script, below.
- A script that refuses an old release folder names a `migrate/` script: read [reference/migrate.md](migrate.md) then.
- The skill's version is `metadata.version` in this file's front matter, and a release states the format it has in its status file; what each version changed and what a release in work has to do: [CHANGELOG.md](../CHANGELOG.md).
- Also read it for a release started under an older form of this skill: trackers that say `merged` or `skipped`, or an epic with grid rows and no `Starts:`; no script refuses those.

Run as `python3 -I <script> <release>` from the repo, a folder inside it, or the folder one level above it: each script takes the git top level of the cwd when it holds `.ai/plans/<release>/`, else the one direct child folder that does (`plan/new_release.py`: `.ai/plans/`). Several matches stop with a list; `--root PATH` picks one. They never overwrite an authored file.


The `migrate/` scripts, one folder per version step, each run once on an older release folder: [migrate.md](migrate.md).

- `<skill>` is this skill's directory.
- The scripts sit in `scripts/` by subject, one job each: `plan/`, `epics/`, `sprints/`, `queue/`, `decisions/`, `status/`, `run/`, `migrate/`.
- `scripts/lib/` holds the code they share (`common.py`: release folder lookup, file and git helpers; `ownership.py`: the ownership facts and the epic table; `grid.py`: the grid and its refresh chain; `board.py`: the board parser of `queue.md` and `decisions.md`; `decisions.py`: the decisions board and the Done rule), loaded by file path and never run.

- `status/report.py` checks only the spec files linked from the `<release>-plan.md` Deliverables table.
- Other `NN-*.md` files are listed as `supporting:` and not checked.
- A tracker no milestone owns counts as citing the queue cards on its first line.
- Decision states, from the Done rule ([formats.md](formats.md), decisions.md): `to do`, `in progress`, `done`, `superseded by D<n>`, `deferred`.
- Stage inference reports discuss and run together: discuss when there are no decisions, a deciding item or a card in Open; run when an epic is tagged and not done.

## The commands by job

- `plan/new_release.py v0.<n>.x`: a new release folder, in format 2.0 (`plan/new_cycle.py` runs the same script). In a format 1.0 release `plan/new_spec.py` writes the flat spec file and `plan/new_fix.py` adds a fix ([SKILL.md](../SKILL.md), Format 1.0 releases).
  - A release has its specs in folders and its statuses in the status file. A session that holds the text of an earlier version of this skill re-reads the skill whole before it creates a release.
- `plan/new_spec.py <release> NN <slug> "<Title>" "<scope>"`: a new spec folder, with its plan row.
- `sprints/check.py <release>`: the ownership check, after each spec is written; writes nothing.
- `epics/table.py <release> E<n> [<spec numbers>]`: the epic table, the pre-go preview; commits nothing.
- `epics/overlap.py <release> <spec numbers or D ids>`: overlap with running epics; writes nothing.
- `epics/new.py <release> E<n> <D ids>`: starts the epic file; `--note "<text>"` appends a Notes bullet.
- `run/go.py <release> E<n> --from <lead>`: every go step in order (discuss.md, Epics, On `go`), `epics/tag.py` among them.
- `sprints/refresh.py <release>`: the grid refresh; run by `run/go.py` and `sprints/mark.py`, by hand in Changing a decision and after a migration.
- `run/runner.sh start|list|stop|send|fork|resume|adopt <release>`: the runner and spec fork windows; `list <release>` shows the entries of that release only.
- `sprints/mark.py <release> <milestone> launch|wait|resume|merge|stop [--reason "<text>"] [--commit <sha>]`: the milestone's status, by the run's verbs.
- `plan/milestone.py add <release> <spec> "<Name>" [--decision D<n>] [--task "<title>"]... [--type feat|bug] [--files a,b]`: a piece of work in a spec: the next module, its task files and its milestone. A mid-run fix and follow-up work go the same way.
- `plan/task.py add <release> <spec> "<Title>" [--module 1.6.N] [--milestone "<name>"]`: one more task file and its pointer; it joins a milestone only while that milestone is not started.
- `status/status.py <release> set <id> "<status>" [--reason "<text>"]`, `get <id>`, `list [--status "<status>"] [--kind epic|spec|milestone|task]`: the only reader and writer of statuses (`status/data/status.json`). Ids: task `27-03`, milestone `27-collapse-shortcut`, spec `27`, epic `E11`.
- `queue/item.py <release> D|Q "<title>"`, `--move Q<n> <lane>`, `--fact Q<n> "<text>"`: every new decision and card, every card move and fact.
- `queue/next.py <release>`: the first card in Open, or `none`. `queue/list.py <release> [lane] [--facts]`: the cards of a lane.
- `decisions/close.py <release> D<n>`: a decision with nothing to run.
- `decisions/supersede.py <release> D<old> D<new>`: supersede a built decision.
- `status/report.py <release>`: state and gaps.
- `status/progress.py <release>`: the progress reply for the owner (formats.md, Progress reply and reports).
- The runner's own: `run/runs.py` (the run id record) and `run/check.py` (the wake check).

## Each script

### plan/new_release.py

- Command: `python3 -I <skill>/scripts/plan/new_release.py v0.<n>.x [--owner X]`
- Does:
  - creates the release folder with `<release>-plan.md` from `templates/plan.md` (`## Goals`, `## Deliverables`),
    - `decisions.md` and `queue.md` (the empty boards of their templates),
    - the subfolders `plan/specs/`,
    - `plan/epics/`,
    - `run/trackers/`,
    - `run/handoffs/`,
    - `status/data/`,
    - `status/index.html` from `board/task-board.html`,
    - `status/data/status.json` with the skill's version as its `format`,
    - the scripts' lock file,
    - the `.gitignore` lines that ignore `status/index.html` and `status/data/*` and keep `status.json` (an older line that ignores the whole `status/data/` folder is replaced),
    - and `process.md` copied from the newest earlier release (else from `templates/process.md`, the release in its title),
    - with `updated` set to now.
  - Prints one line naming the status command
- When: a new release

### plan/new_spec.py

- Command: `python3 -I <skill>/scripts/plan/new_spec.py v0.<n>.x NN <slug> "<Title>" "<scope>"`
- Does: creates the spec folder `plan/specs/NN-<slug>/` with `NN-<slug>.md` from `templates/spec.md` (sections 1.6, 2.1 and 2.2 empty) and the folder `tasks/`, adds the row to the `<release>-plan.md` Deliverables table in order; refuses a title, scope or template citing a superseded decision
- When: each new spec; in a format 1.0 release it writes the flat file `plan/specs/NN-<slug>.md` and the first milestone's tracker, as it did then

### epics/tag.py

- Command: `python3 -I <skill>/scripts/epics/tag.py v0.<n>.x E<n> <spec numbers or D ids>`
- Does: writes `- Epic: E<n>` under each spec's title line (a D id names the specs citing it),
  - the tag `#E<n>` on the card of each decision those specs cite and each named D id (moved to In progress, then the Done rule sync),
  - `E<n>` in each spec's Deliverables Epic cell,
  - and `Starts: S<n>` (the current sprint, before the epic's rows exist) under `Specs:` in `plan/epics/E<n>.md`,
  - then ticks each Decided card of those decisions in `queue.md` and tags it `#E<n>`;
  - an existing Epic line, tag or Starts value is kept;
  - refuses a missing epic file;
  - refuses a spec citing a superseded decision
- When: run/go.py, on go

### epics/new.py

- Command: `python3 -I <skill>/scripts/epics/new.py v0.<n>.x E<n> [<D ids> | --note "<text>"]`
- Does: D ids: creates `plan/epics/E<n>.md` when missing, writes the `Decisions:` line (the ids there plus the new ones, in number order) and one Ownership row per decision, `| D<n> <title from decisions.md> |  |  |  |  |`; a rerun adds only the missing rows; refuses, writing nothing, a decision that is missing, superseded, already tagged with another epic, or done with nothing to run.
  - No D ids: the stub (`# E<n>`, empty `Decisions:`, `Specs:` and `Starts:`, the empty Ownership table, no Notes heading); refuses an existing file.
  - `--note`: appends `- <text>` to `## Notes`, creating the section at the end.
  - Each commits the file
- When: D ids on `epic`; the stub from run/go.py; `--note` whenever a note is written

### run/go.py

- Command: `python3 -I <skill>/scripts/run/go.py v0.<n>.x E<n> --from <lead>`
- Does: runs every go step ([discuss.md](discuss.md), Epics, On `go`) in order: tag, commit, grid, epic file (`Specs:` and the final table, committed with the grid), close the writer window, start the runner when `run/runner.sh list` shows none and send the RUN line, the next epic's stub.
  - Each step is skipped when already done; the two `run/runner.sh` steps are recorded in `status/data/go.log` for that.
  - Stops at the first failure with one line `go E<n> stopped at step <i> (<name>): <reason>`, exit 1; prints one summary line on success.
  - `EXPEDITION_RUNNER_SH` overrides the path of `run/runner.sh` (tests point it at a stub)
- When: on go

### sprints/check.py

- Command: `python3 -I <skill>/scripts/sprints/check.py v0.<n>.x`
- Does: reads the milestone blocks of every spec in `plan/specs/`, both forms, computes the columns and each epic's critical path (Ownership above), prints the milestone and column count and one path per epic, writes nothing; errors on a shared file inside one column or a dependency cycle, naming the file and the two milestones.
- When: after each spec is written

### epics/table.py

- Command: `python3 -I <skill>/scripts/epics/table.py v0.<n>.x E<n> [<spec numbers>]`
- Does: the epic's specs are its tagged specs plus the numbers given (else, before go, the untagged specs citing its decisions), counted as E<n> and placed from the current sprint;
  - fills the Spec, Milestone and Sprint columns of the epic file's table ([formats.md](formats.md), Epic file) and prints the sprints the epic spans, its critical path, each pair of its specs owning the same file, each Files path that does not exist yet, as `new or missing` (a new file and a typo look the same), and each row file no milestone of its spec owns;
  - no verdict, commits nothing, exit 1 only for the errors above or an unreadable table
- When: by the spec writer before `SPECS`

### epics/overlap.py

- Command: `python3 -I <skill>/scripts/epics/overlap.py v0.<n>.x <spec numbers or D ids>`
- Does: check mode, writes nothing, reports files shared with milestones of running sprints, exit 1 on a shared file
- When: before the epic hint

### sprints/swimlanes.py

- Command: `python3 -I <skill>/scripts/sprints/swimlanes.py v0.<n>.x`
- Does: reads `status/sprints.md`,
  - the ownership facts (in memory, each epic's critical path computed on the fly) and `<release>-plan.md`,
  - writes `status/data/sprints.data.js` and `status/data/sprints.json` (each milestone's status from its cell, with a short reason for a waiting or stopped one read from its tracker as `status/progress.py` reads it; each epic's path milestones marked critical, `criticalPaths` per epic, `criticalPath` their union);
  - copies `board/swimlanes.html` to `status/index.html` when the template is newer or the page is missing
- When: the last step of `sprints/refresh.py` and `sprints/mark.py`

### `<skill>/board/swimlanes.html`

- Command: `<skill>/board/swimlanes.html`
- Does: the swimlane page: lanes per epic, sprint columns, Depends on arrows, red arrows only between two milestones of one epic's path; reads `data/sprints.data.js` beside it; one self-contained file, no network requests: its CSS is Tailwind compiled from `board/swimlanes.tw.css` and inlined (the rebuild command is at the top of that file, needed only when the page's classes change)
- When: copied, never edited in a release

### sprints/refresh.py

- Command: `python3 -I <skill>/scripts/sprints/refresh.py v0.<n>.x`
- Does: writes the `status/sprints.md` grid from the ownership facts: the computed sprint columns, one row per milestone of a spec with an `- Epic: E<n>` line, `·` in new cells;
  - finished cells, running `[ ]` and waiting `[~]` cells stay;
  - then rewrites the Sprint column of every unfinished epic's table that has a `Starts:` value, touching only that column;
  - then moves the cards of `decisions.md` to the lanes of the Done rule;
  - then syncs the Decided cards of `queue.md` with those lanes;
  - then writes the swimlane data (`sprints/swimlanes.py`);
  - commits nothing (commit `decisions.md`, `queue.md` and the changed epic files with the grid);
  - runs under the `.ids.lock` lock.
  - The chain is `lib/grid.py` refresh; each step alone: `sprints/grid.py` (the grid only), `sprints/sync_epic_sprints.py` (the Sprint column only), `queue/sync.py` (the Decided cards only)
- When: `run/go.py`, Changing a decision

### run/runner.sh

- Command: `<skill>/scripts/run/runner.sh start|list|stop|send|fork|resume|adopt v0.<n>.x`
- Does: `start`: reuses the live runner of the release,
  - resumes a dead one,
  - or opens the next `<release> runner<n>` (numbers never reused; `--new` opens another beside the live one, `--new --name "<name>"` names it as given, and called from a runner window it runs on that runner's model; window name is also the `claude -n` name; the runner of a release is its newest entry that is not stopped) in the current tmux session running the runner (fable, bypass, fixed `--session-id`, `templates/runner-settings.json`, brief),
  - records it in `~/.claude/expedition-runners.json`,
  - resumes a dead one with `--resume`,
  - prints the command outside tmux;
  - `list`: entries with busy or idle, release and kind;
  - `stop`: closes the window, marks the entry stopped;
  - `send <release> "<line>"`: types `ultracode <line>` into the runner window and submits it (the RUN line `RUN E<n> <release folder> epic <epic file> from <lead>`; a runner by full window name, for example `send "v0.9.x runner2" "LEAD <name>"`);
  - `fork <release> E<n> "<D ids>" --from <lead>`: opens window `<release> specs E<n>` running a forked session of the lead (`--resume $CLAUDE_CODE_SESSION_ID --fork-session`, model fable unless `--model`) that fills the epic table's Files column, writes the epic's specs, completes the table with `epics/table.py` and replies `SPECS E<n> <spec numbers>`, with its own `--session-id` in the registry;
  - a fork whose window died is resumed by the same `fork` call, never forked again;
  - `stop "<release> specs E<n>"` closes it;
  - `resume <release or window name>`: types `resume` into a live window (the runner with the ultracode prefix), starts a dead runner, reopens a dead fork whose session transcript exists in a new window with its name (`claude --resume <uuid>`), else prints that line with the reason;
  - `adopt <release> [--uuid UUID] [--pane PANE] [--replaces <name>]`: registers a claude session that already runs (default the calling one) as the next `<release> runner<n>` with its own uuid, renames its window, marks `--replaces` stopped.
  - A registry write that gives one session uuid to a second entry that is not stopped is refused, and `list` warns on a shared uuid.
  - The runner and every spec fork run in the lead's working directory, never in a subfolder: `start` and `fork` open the new window in the folder they are called from, or in `--cwd PATH`.
  - The registry is never edited by hand.
  - Env overrides for tests: `EXPEDITION_REGISTRY`, `EXPEDITION_STATE_DIR`, `EXPEDITION_PROJECTS`, `EXPEDITION_CLAUDE`, `EXPEDITION_TMUX_SOCKET`
- When: once per release, to revive a runner, and on every go (through run/go.py)

### run/runner.sh

- Command: `<skill>/scripts/run/runner.sh watch start|stop|status`, `<skill>/scripts/run/nudge-watch.sh`
- Does: `start`, `send` and `fork` run inside tmux record the calling window as registry key `lead` (`{"tmux": "<session>:<window id>", "session": $CLAUDE_CODE_SESSION_ID, "name": --from, the line's "from <name>" or the name of a `LEAD <name>` line}`), except when called from a runner window (`EXPEDITION_RUNNER` set);
  - `start` also starts the watcher (pid `~/.claude/expedition-runners/nudge-watch.pid`), `stop` stops it once no runner or fork window is live.
  - The watcher polls the You Should Know store every 5 s and types `NUDGE <source>: <text>` into the lead window for each note shown to a runner, a fork or an unknown session, never one shown to the lead; state `nudge-watch.state` (no replay on restart), log `nudge-watch.log`; exits when `lead` is missing or its window is gone.
  - Every minute it also runs `run/check.py` for each live runner's release and types `ultracode resume` into a runner that owns a `silent`, `finished` or `no run` row while its own transcript has been quiet for 20 minutes, at most once per 20 minutes per runner, logged; a failing `check.py` is logged and skipped.
  - Env overrides for tests: `NUDGE_STORE`, `NUDGE_STATE`, `NUDGE_LOG`, `NUDGE_REGISTRY`, `NUDGE_INTERVAL`, `NUDGE_RESUME_EVERY`, `NUDGE_STALE_MINUTES`, `NUDGE_RESUME_STATE`, `EXPEDITION_PROJECTS`, `EXPEDITION_TMUX_SOCKET`
- When: automatic with `start`; `watch` for manual control

### run/runs.py

- Command: `python3 -I <skill>/scripts/run/runs.py v0.<n>.x set <milestone> <run id>`, `get <milestone>`, `list`
- Does: writes the Workflow run id of a milestone to `status/data/runs.json` in the main checkout's release folder (also when called from a worktree), with the calling session id and the time, under the `.ids.lock` lock; a new id replaces the old one; refuses a milestone with no tracker; `get` prints the id or `none`
- When: the runner, at each Workflow launch and relaunch

### run/check.py

- Command: `python3 -I <skill>/scripts/run/check.py v0.<n>.x [--stale MINUTES] [--tsv]`
- Does: read-only: for each `[ ]` row of `status/sprints.md`,
  - the milestone,
  - its recorded run id,
  - the registry entry whose session folder holds the run (`<projects>/*/<session>/subagents/workflows/<run id>/`, the final state `<session>/workflows/<run id>.json`),
  - the last activity (newest file in that folder) and a state: `alive` (activity within `--stale`, default 20 minutes),
  - `paused` (the run's last limit event is its pause),
  - `silent` (no activity past the threshold, or ended killed or failed),
  - `finished` (final state completed, row still `[ ]`),
  - `no run` (no id, or the id in no session);
  - `[~]` rows as `waiting`;
  - a count line.
  - `--tsv` gives tab-separated lines for the watcher.
  - Exit 0 for any read
- When: the runner's wake check (tick.md, step 3); the nudge watcher every minute

### plan/milestone.py

- Command: `python3 -I <skill>/scripts/plan/milestone.py add v0.<n>.x <spec> "<Name>" [--decision D<n>] [--task "<title>"]... [--type feat|bug] [--module 1.6.N] [--cites "Q3, Q4"] [--files a,b] [--depends "<names>"] [--checks "<checks>"] [--epic E<n>]`
- Does:
  - adds a piece of work to `<spec>`: the module `#### 1.6.N <Name> (<ids>)` (or an existing `--module`),
    - one task file per `--task` from `templates/task.md` (default one task named like the milestone) with its pointer line,
    - the block `#### 2.2.N Milestone: <Name>` (`Tasks`, `Files owned` when `--files`, `Depends on` every other milestone owning one of those files plus `--depends`) and the tracker `run/trackers/NN-<name slug>-tracker.md`.
  - For a spec in an epic: `Starts:` the current sprint, and with `--decision` the decision on the epic file's decisions line, its Ownership row and its `#E<n>` tag (In progress).
  - A done spec: refused with `--decision`; without, the follow-up spec `NN.M` with that one milestone in a running epic (`--epic` when several run).
  - An old-form spec gets one `### Milestone:` block with one task line (`--files` and `--checks` required).
  - Moves each cited card to Autofix, reruns `sprints/refresh.py` and the page data, commits under the `.ids.lock` lock and prints one line naming spec, milestone, sprint and tracker.
  - Refuses, writing nothing: a D id in `--cites`, an unknown card, decision, module or spec, a superseded decision or one in another epic, a taken milestone name, milestones that no longer schedule
- When: each milestone of a new spec, a feedback item on a spec in progress, a fix found during a run

### plan/new_fix.py

- Command: `python3 -I <skill>/scripts/plan/new_fix.py v0.<n>.x <slug> "<Title>" <spec> --files a,b --checks "<checks>" [--cites "Q3, Q4"] [--depends "<names>"] [--epic E<n>]`
- Does: adds a fix in a format 1.0 release, with the arguments the sessions of that format use: a `### Milestone:` block in a spec that is still building, or the follow-up file `NN.M-<slug>.md`. In a format 2.0 release it calls `plan/milestone.py add` with the same arguments (the slug is not used).
- When: a fix found during the run of a format 1.0 release

### plan/task.py

- Command: `python3 -I <skill>/scripts/plan/task.py add v0.<n>.x <spec> "<Title>" [--module 1.6.N] [--milestone "<name>"] [--type feat|bug]`
- Does: writes the task file `tasks/NN-<slug>.md` (`status: not started`) and its pointer line in 2.1; with `--milestone` adds the number to that milestone's `Tasks` line. Refuses an old-form or done spec, an unknown module or milestone, a milestone that has started
- When: one more task for a module, or for a milestone not yet started

### status/status.py

- Command: `python3 -I <skill>/scripts/status/status.py v0.<n>.x set <id> "<status>" [--reason "<text>"] [--commit <sha>]`, `get <id>`, `list [--status "<status>"] [--kind epic|spec|milestone|task]`, `drop <id>`
- Does: the only reader and writer of statuses.
  - Ids: task `27-03`, milestone `27-collapse-shortcut` (its tracker name), spec `27`, epic `E11`.
  - `set` on a task or a milestone: writes `status/data/status.json` (through a temporary file), rolls a task up into its milestone, counts spec, epic and sprint, writes the word into the `status:` line of the task, spec and epic files, draws `status/sprints.md`, writes the page data, commits; a set that changes nothing writes nothing.
  - `blocked` and `skipped` need `--reason`.
  - A task set to done with an open `Owner:` box becomes blocked, "waits for the owner's look"; with another open box it is refused.
  - A milestone set to done needs `--commit`, a commit hash, and is refused while one of its tasks is not finished.
  - `drop` removes a stored entry that no spec has.
  - Run from a milestone worktree it writes the one release folder that holds the scripts' lock, never the worktree's copy.
  - Refuses a release with no `status.json`; a file that cannot be parsed stops it with one line
- When: the builder at the start and end of each task; the lead after the owner's look

### migrate/v1.0-v2.0/format.py

- Command: `python3 -I <skill>/scripts/migrate/v1.0-v2.0/format.py v0.<n>.x [--dry-run] [--force]`
- Does: moves a format 1.0 release to spec folders, task files and the status store, in one commit; counts before and after must be equal; details in [migrate.md](migrate.md)
- When: once per release that is in work, when no milestone runs

### queue/item.py

- Command: `python3 -I <skill>/scripts/queue/item.py v0.<n>.x D|Q "<title>" [--source Q<n>] [--bullet "<text>"] [--new-round]`, `--move Q<n> Open|Later|Dropped|Autofix`, `--fact Q<n> "<text>"`
- Does:
  - under a lock on `status/data/.ids.lock` in the release folder,
    - re-reading the files right before the write: D: takes the highest D id,
    - appends the card `- [ ] **D<n>** <title> #R<n>` at the end of To do in `decisions.md` (the highest round in the file, the next with `--new-round`),
    - the bullet if given,
    - then `- Source: Q<n>` if given,
    - tab-indented,
    - and moves that card to the end of Decided,
    - unticked,
    - with `#D<n>` at the end of its title (a card already in Decided keeps the highest number).
  - Q: takes the highest card id, appends the tagless card `- [ ] **Q<n>** <title>` at the end of Open, the bullet as its first fact.
  - `--move`: the card with its facts to the end of that lane; a card leaving Decided loses its `#D` and `#E` tags.
  - `--fact`: one tab-indented fact at the end of the card.
  - Every call then moves the `decisions.md` cards to the lanes of the Done rule and syncs the Decided cards with those lanes.
  - `queue.md` is created from the template if missing; every other byte stays as found.
  - Commits the files it wrote, prints the id alone; another kind exits non-zero
- When: every new D or Q item and every card move or fact, by either session

### decisions/close.py

- Command: `python3 -I <skill>/scripts/decisions/close.py v0.<n>.x D<n>`
- Does: under the `.ids.lock` lock: moves the decision's card to Done, ticked (the record of "closed, nothing to run"); refuses an unknown id, a decision with an epic tag or with a row in an epic that has gone; one already in Done changes nothing; then the Done rule and queue syncs, one commit
- When: a decision with nothing to run, when recorded

### decisions/supersede.py

- Command: `python3 -I <skill>/scripts/decisions/supersede.py v0.<n>.x D<old> D<new>`
- Does: under the `.ids.lock` lock: `(superseded by D<new>)` at the end of the old title, `#superseded`, the old card to Done; `- Supersedes D<old>.` as the new decision's first bullet; refuses an unknown id and an old decision already superseded; then the Done rule and queue syncs, one commit
- When: Changing a decision, once built

### plan/find_rules.py

- Command: `python3 -I <skill>/scripts/plan/find_rules.py [repo]`
- Does: read-only: prints project planning-rules paths, one per line, nothing if none
- When: 

### plan/process.py

- Command: `python3 -I <skill>/scripts/plan/process.py [v0.<n>.x] [stage words]`
- Does: read-only: prints `process.md: <absolute path>` and then the release's `process.md` in full; the release is the first argument that is a release name, else the highest-numbered release folder that holds a `process.md`; other words are ignored; repo root and owner found as for every script. Nothing found: one line naming the folder searched. Always exits 0, never a traceback
- When: SKILL.md injects it at invocation; again after a handoff, a compaction or a RUN line

### status/report.py

- Command: `python3 -I <skill>/scripts/status/report.py v0.<n>.x`
- Does: read-only: missing files,
  - a state table per decision and per queue card (its lane),
  - queue gaps (an unknown or missing lane, a card without a `**Q<n>**` token, a duplicate id, a title tag other than `#D<n>` or `#E<n>`, a leftover `Decision:` fact, a Decided card without `#D<n>` or naming a missing decision, a Decided card whose tick or `#E<n>` disagrees with the lane of its decision, a `(Q<n>)` or `Source: Q<n>` citation of a missing card; a `**Complete**` marker line is ignored),
  - milestones without tracker,
  - `Status:` line or checks,
  - possible open questions,
  - a `<release>-plan.md` `## ` section other than Goals and Deliverables,
  - a Deliverables Scope cell over 120 characters,
  - milestones `sprints/check.py` would refuse,
  - `status/sprints.md` missing,
  - without a ` | Milestone` table,
  - with rows that differ from the milestones or with a cell that is no mark of [formats.md](formats.md),
  - Milestone status;
  - each tagged epic's critical path;
  - the release's `process.md` (missing, placeholders left, undefined `(P<n>)` citations),
    - the decisions board gaps (a missing lane, a card without a `**D<n>**` token, a tag other than `#superseded`, `#deferred`, `#E<n>`, `#R<n>`, a duplicate id, ids out of order in a lane, a lane that disagrees with the Done rule, a tick that disagrees with its lane),
    - an epic summary (deciding, in E<n>, running, done per D item),
    - the decisions still editable in place,
    - a supersede marked on one side only,
    - an unbuilt spec citing a superseded decision,
    - epic files missing or with notes without ack (only a file with a `## Notes` section),
    - the next epic file missing while an epic runs;
  - the epic tables: an epic with grid rows whose file has no Ownership table, a decision of the `Decisions:` line with no row, a spec of the epic with no row, a row file no milestone of its spec owns, a Sprint cell that disagrees with the grid (an epic file without a table and no grid rows is not flagged);
  - inferred stage.
  - First line names the planning rules in use.
- When: any time

### queue/next.py

- Command: `python3 -I <skill>/scripts/queue/next.py v0.<n>.x`
- Does: read-only: prints only the first card in Open with its facts, or `none`
- When: before each item

### queue/list.py

- Command: `python3 -I <skill>/scripts/queue/list.py v0.<n>.x [lane] [--facts]`
- Does: read-only: prints the cards of one lane in board order, one line each: `Q<n>`, the title, its `#D<n>` and `#E<n>` tags, in Decided the tick `[x]` or `[ ]` first; `--facts` adds each card's facts under it; lane `all` prints one line per lane with its card count; default lane Open, lane names in any case; an empty lane prints `none`; an unknown lane exits 1 naming the valid lanes
- When: when a session needs more than the next card

### sprints/mark.py

- Command: `python3 -I <skill>/scripts/sprints/mark.py v0.<n>.x <milestone> launch|wait|resume|merge|stop`
- Does: the only writer of grid marks: `<milestone>` is the tracker file name without `-tracker.md` (`47-comparison-page`);
  - sets that milestone's cell in the column its row has now (the marks of [formats.md](formats.md), Milestone status; `launch` on a `[~]` cell resumes; `wait` only on a `·`, `[ ]` or `[~]` cell; `resume` only on a `[~]` cell),
    - then,
    - under the `.ids.lock` lock,
    - the grid chain of `sprints/refresh.py` with a new `Updated:` line,
    - and commits the grid with the epic files,
    - `decisions.md` and `queue.md` it changed (never pushes);
  - an unknown milestone or one with no grid row is refused with one line;
  - a repeat call changes nothing and exits 0
- When: at every launch, wait, resume, merge and stop: the workflow's merger for `merge`, the runner otherwise

### status/progress.py

- Command: `python3 -I <skill>/scripts/status/progress.py v0.<n>.x`
- Does: read-only: prints only the owner's progress reply in Markdown: per epic with an unfinished milestone,
  - `**E<n>** · Specs d/t` (a spec is done when every milestone of it is done),
  - `- **Running**` (specs with a running milestone) and `- **Blocked**` (specs with a stopped milestone, with the first `## Attention` bullet of its tracker, or a waiting one, as `waits on the lead: <what>` or `waits on the owner: <what>`),
  - each spec as its number and its Deliverables title;
  - with nothing unfinished, the last epic's line, then `Nothing running.` and the unticked Decided cards as `Ready for an epic: **Q<n>**`.
  - Per milestone it reads the grid cell and the most advanced copy of its tracker (planned < running < waiting < done or stopped) among the main checkout and the worktree on the branch its `Branch` line names (every worktree's copy when none does): a done tracker counts as done, a waiting tracker or a `[~]` cell as Blocked; each disagreement with the grid goes to stderr as one `warning:` line.
  - The reply rule: [formats.md](formats.md), Progress reply and reports.
- When: on `progress`
