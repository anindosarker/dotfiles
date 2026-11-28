# Scripts

For any session that is about to run a command of the skill: how to run them, the commands by job, then each script with what it writes and what it refuses.

## Contents
- How to run them
- The commands by job
- Each script

## How to run them

- Mechanical steps use the scripts, never hand-written files. The main agent calls scripts, never does a script's job by hand, and never spawns an agent only to call one (the spec writer calls `plan/new_spec.py` and `plan/milestone.py` as part of its work).
- The scripts sit in `scripts/` by subject, one job each: `plan/`, `epics/`, `sprints/`, `queue/`, `decisions/`, `status/`, `run/`, `migrate/`. `<skill>` is this skill's directory.
- `scripts/lib/` holds the code they share, loaded by file path: `common.py` (release folder lookup, file and git helpers), `ownership.py` (the ownership facts and the epic table), `grid.py` (the grid and its refresh chain), `board.py` (the board parser of `decisions.md`, and of `queue.md` in a release below format 2.1), `queue.py` (the item files, the list, the blocked check and the queue page data), `decisions.py` (the decisions board and the Done rule), `specs.py` (spec edits), `status.py` (the status file), `dashboard.py` (the data of the dashboard page).
- Each runs as `python3 -I ${CLAUDE_SKILL_DIR}/scripts/<command> <release>`; `run/runner.sh` runs as `${CLAUDE_SKILL_DIR}/scripts/run/runner.sh`.
- Run it from the repo, a folder inside it, or a folder above it, so sessions never `cd` for the scripts and use `git -C <repo>` for git. Each script takes the git top level of the cwd when it holds `.ai/plans/<release>/`, else the one direct child folder that does, else a folder one or two levels above that does (`plan/new_release.py` looks for `.ai/plans/`). Several matches stop with a list; `--root PATH` picks one.
- For a format 2.0 release every script writes one copy of the release folder, the main checkout's, also when it is run from a milestone worktree that holds its own copy.
- A script that refuses an old release folder names a `migrate/` script: read [migrate.md](migrate.md) then. Also read it for a release started under an older form of this skill: trackers that say `merged` or `skipped`, or an epic with grid rows and no `Starts:`; no script refuses those. The `migrate/` scripts sit one folder per version step, each run once on an older release folder.
- The skill's version is `metadata.version` in SKILL.md's front matter, and a release states the format it has in its status file; what each version changed and what a release in work has to do: [CHANGELOG.md](../CHANGELOG.md).
- `status/report.py` checks only the spec files linked from the `<release>-plan.md` Deliverables table. Other `NN-*.md` files are listed as `supporting:` and not checked. A tracker no milestone owns counts as citing the queue cards on its first line.
- Decision states, from the Done rule ([formats.md](formats.md), decisions.md): `to do`, `in progress`, `done`, `superseded by D<n>`, `deferred`.
- Stage inference reports discuss and run together: discuss when there are no decisions, a deciding item or a card in Open; run when an epic is tagged and not done.

## The commands by job

- `plan/new_release.py v0.<n>.x`: a new release folder, in the format of the skill's version (`plan/new_cycle.py` runs the same script). In a format 1.0 release `plan/new_spec.py` writes the flat spec file and `plan/new_fix.py` adds a fix ([SKILL.md](../SKILL.md), Format 1.0 releases).
  - A release has its specs in folders and its statuses in the status file. A session that holds the text of an earlier version of this skill re-reads the skill whole before it creates a release.
- `plan/new_spec.py <release> NN <slug> "<Title>" "<scope>"`: a new spec folder, with its plan row.
- `sprints/check.py <release>`: the ownership check, after each spec is written; writes nothing.
- `epics/table.py <release> E<n> [<spec numbers>]`: the epic table, the pre-go preview; commits nothing.
- `epics/overlap.py <release> <spec numbers or D ids>`: overlap with running epics; writes nothing. `epics/overlap.py <release>`: the ready and the blocked decisions, in the lines of the Epic ready message. `epics/overlap.py <release> D<n> --files "<files>"`: the files of a decision that no spec cites.
- `epics/new.py <release> E<n> <D ids>`: starts the epic file; `--note "<text>"` appends a Notes bullet.
- `run/go.py <release> E<n> --from <lead>`: every go step in order (discuss.md, Epics, On `go`), `epics/tag.py` among them.
- `sprints/refresh.py <release>`: the refresh chain (sprints, epic tables, decision lanes, the blocked check, the page data); run by `run/go.py` and `sprints/mark.py`, by hand in Changing a decision, after a hand edit of an item file and after a migration.
- `sprints/grid.py <release>`: prints the grid from the status file; writes nothing.
- `run/runner.sh start|list|stop|send|fork|resume|adopt <release>`: the runner and spec writer windows; `list <release>` shows the entries of that release only.
- `sprints/mark.py <release> <milestone> launch|wait|resume|merge|stop [--reason "<text>"] [--commit <sha>]`: the milestone's status, by the run's verbs.
- `plan/milestone.py add <release> <spec> "<Name>" [--decision D<n>] [--task "<title>"]... [--type feat|bug] [--files a,b]`: a piece of work in a spec: the next module, its task files and its milestone. A mid-run fix and follow-up work go the same way.
- `plan/task.py add <release> <spec> "<Title>" [--module 1.6.N] [--milestone "<name>"]`: one more task file and its pointer; it joins a milestone only while that milestone is `to-do`.
- `status/status.py <release> set <id> "<status>" [--reason "<text>"]`, `get <id>`, `list [--status "<status>"] [--kind epic|spec|milestone|task]`: the only reader and writer of statuses (`status/data/status.json`). Ids: task `27-03`, milestone `27-collapse-shortcut`, spec `27`, epic `E11`.
- `queue/item.py <release> D|Q "<title>" [--source Q<n>] [--option <n>] [--decider you|lead|agent]`, `--move Q<n> <word> [--decider you|lead|agent]`, `--fact Q<n> "<text>"`, `--depends Q<n> "<Q ids>"`: every new decision and item, every status change, fact and dependency of an item. A decision is a decision file, `decisions/D<n>-<slug>.md`. An item is an item file, `queue/Q<n>-<slug>.md`, and `queue.md` is the list of them (a card of the board `queue.md` in format 2.0).
- `queue/next.py <release>`: the `to-do` item with the lowest number, or `none`. `queue/list.py <release> [word] [--facts]`: the items of a lane word or a status word.
- `decisions/close.py <release> D<n> [--backlog]`: a decision with nothing to run; with `--backlog`, a decision that moves to another release.
- `decisions/supersede.py <release> D<old> D<new>`: supersede a built decision.
- `decisions/decider.py <release> D<n> you|lead|agent [--change]`: the decider of a decision file that has none; `--change` replaces an existing one.
- `status/report.py <release>`: state and gaps.
- `status/progress.py <release>`: the progress reply for the owner (formats.md, Progress reply and reports).
- The runner's own: `run/runs.py` (the run id record) and `run/check.py` (the wake check).

## Each script

### plan/new_release.py

- Command: `python3 -I <skill>/scripts/plan/new_release.py v0.<n>.x [--owner X] [--root PATH]`
- Does: creates the release folder in the format of the skill's version (`metadata.version` of SKILL.md), with:
  - `<release>-plan.md` from `templates/plan.md` (`## Goals`, `## Deliverables`); below 2.2 the script adds the link to `status/sprints.md` in its first lines;
  - `decisions.md` and `queue.md`; the decisions take the form of the skill's version: from 2.2 on `decisions.md` from `templates/decisions-list.md` (an empty list) and an empty `decisions/` folder for the decision files, below 2.2 the empty board of `templates/decisions.md`; the queue too: below 2.1 the board stub of `templates/queue.md`, from 2.1 on `queue.md` from `templates/queue-list.md` (an empty list) and an empty `queue/` folder for the item files;
  - the subfolders `plan/specs/`, `plan/epics/`, `run/trackers/`, `run/handoffs/`, `status/data/`;
  - the page: in format 2.2 the dashboard page, `status/index.html` from `board/dashboard.html` and `status/src/` from `board/src/`, and it prints their paths; below 2.2 the task board, `status/index.html` from `board/task-board.html`;
  - `status/data/status.json` with the skill's version as its `format`;
  - the scripts' lock file;
  - the `.gitignore` lines that ignore `status/index.html` and `status/data/*` and keep `status.json` (an older line that ignores the whole `status/data/` folder is replaced), and in format 2.2 the line `.ai/plans/*/*/status/src/`;
  - `process.md` copied from the newest earlier release (else from `templates/process.md`, the release in its title), with `updated` set to now.
- Prints one line naming the status command
- When: a new release

### plan/new_spec.py

- Command: `python3 -I <skill>/scripts/plan/new_spec.py v0.<n>.x NN <slug> "<Title>" "<scope>"`
- Does: creates the spec folder `plan/specs/NN-<slug>/` with `NN-<slug>.md` from `templates/spec.md` (sections 1.6, 2.1 and 2.2 empty) and the folder `tasks/`, adds the row to the `<release>-plan.md` Deliverables table in order; refuses a title, scope or template citing a superseded decision
- When: each new spec; in a format 1.0 release it writes the flat file `plan/specs/NN-<slug>.md` and the first milestone's tracker, as it did then

### epics/tag.py

- Command: `python3 -I <skill>/scripts/epics/tag.py v0.<n>.x E<n> <spec numbers or D ids>`
- Does: writes:
  - `- Epic: E<n>` under each spec's title line (a D id names the specs citing it);
  - the line `epic: E<n>` in the file of each decision those specs cite and each named D id, then the status rule makes it `in progress`; with a decision board, the tag `#E<n>` on its card (moved to In progress, then the Done rule sync);
  - `E<n>` in each spec's Deliverables Epic cell;
  - `starts: S<n>` directly after the `status:` line of `plan/epics/E<n>.md`: the current sprint, read from the status file ([files.md](files.md), Ownership). Below format 2.2: `Starts: S<n>` under the `Specs:` line, the current sprint of `status/sprints.md`.
- Then, in format 2.2, the status chain runs: with its `starts` value the epic is counted from its specs, no longer `waits for delegate`. Nothing is synced into the item files: a `done` item holds its decision id only. In a format 2.0 release it ticks each Decided card of those decisions in `queue.md` and tags it `#E<n>`.
- An existing Epic line, tag or starts value is kept.
- Refuses a missing epic file, and a spec citing a superseded decision.
- When: run/go.py, on go

### epics/new.py

- Command: `python3 -I <skill>/scripts/epics/new.py v0.<n>.x E<n> [<D ids> | --note "<text>"]`
- Does: D ids: creates `plan/epics/E<n>.md` when missing and writes one Ownership row per decision, `| D<n> <title of the decision file> |  |  |  |  |`; a rerun adds only the missing rows; refuses, writing nothing, an id with no decision file, an `archived` or `backlog` decision, a decision with the `epic` line of another epic, and one that is done with nothing to run. A `blocked` decision is accepted: the owner may put it into an epic. With a decision board: the title from `decisions.md`, and it refuses a decision that is missing, superseded, already tagged with another epic, or done with nothing to run.
- No D ids: the stub (front matter `status` and an empty `starts`, `# E<n>`, the empty Ownership table, no Notes heading); refuses an existing file.
- After a stub or a start the status chain runs, so the status file and the `status:` lines follow at once, committed with the epic file.
- Below format 2.2 it writes the lines `Decisions:` (the ids there plus the new ones, in number order), `Specs:` and `Starts:` as well, and runs no status chain.
- `--note`: appends `- <text>` to `## Notes`, creating the section at the end.
- Each commits the file
- When: D ids on `compose`; the stub from run/go.py; `--note` whenever a note is written

### run/go.py

- Command: `python3 -I <skill>/scripts/run/go.py v0.<n>.x E<n> --from <lead>`
- Does: runs every go step ([discuss.md](discuss.md), Epics, On `go`) in order: tag, commit, grid (`sprints/refresh.py`), epic file (the final table, committed), close the spec writer's window, start the runner when `run/runner.sh list` shows none and send the RUN line, the next epic's stub. It fails at the tag step when a decision of the epic's table is cited by no spec of the epic.
- Each step is skipped when already done; the grid step and the two `run/runner.sh` steps are recorded in `status/data/go.log` for that. The grid step is done when every milestone of the epic's specs has a `sprint` in the status file and `go.log` records the step.
- Below format 2.2 the epic file step also writes the `Specs:` line and commits `status/sprints.md`, and the grid step is done when every milestone has a row in that file.
- Stops at the first failure with one line `go E<n> stopped at step <i> (<name>): <reason>`, exit 1; prints one summary line on success.
- The commits of steps 2 and 4 name `queue.md`, and in a format 2.1 release also the item files in `queue/`.
- `EXPEDITION_RUNNER_SH` overrides the path of `run/runner.sh` (tests point it at a stub)
- When: on go

### sprints/check.py

- Command: `python3 -I <skill>/scripts/sprints/check.py v0.<n>.x`
- Does: reads the milestone blocks of every spec in `plan/specs/`, both forms, computes the columns and each epic's critical path ([files.md](files.md), Ownership), prints the milestone and column count and one path per epic, writes nothing; errors on a shared file inside one column or a dependency cycle, naming the file and the two milestones.
- When: after each spec is written

### epics/table.py

- Command: `python3 -I <skill>/scripts/epics/table.py v0.<n>.x E<n> [<spec numbers>]`
- Does: the epic's specs are its tagged specs plus the numbers given (else, before go, the untagged specs citing its decisions), counted as E<n> and placed from the current sprint.
- It fills the Spec, Milestone and Sprint columns of the epic file's table ([formats.md](formats.md), Epic file) and prints:
  - the sprints the epic spans;
  - its critical path;
  - each pair of its specs owning the same file;
  - each Files path that does not exist yet, as `new or missing` (a new file and a typo look the same);
  - each row file no milestone of its spec owns.
- No verdict, commits nothing, exit 1 only for the errors above or an unreadable table.
- When: by the spec writer before `SPECS`

### epics/overlap.py

- Command: `python3 -I <skill>/scripts/epics/overlap.py v0.<n>.x <spec numbers or D ids>`, `... v0.<n>.x D<n> --files "<files>"`, `... v0.<n>.x`
- Does, with spec numbers or D ids: check mode, writes nothing, reports each file shared with a milestone of a running epic, exit 1 on a shared file. A D id that no spec cites is checked with the files given for it (`D14 given files: ... shared with <milestone> (E<n>)`), or prints `no spec cites it yet, files unknown`.
- Does, with `D<n> --files "a, b"`: stores the files of a decision that no spec cites yet in the status file (it replaces the list; `""` removes it), runs the status rule, commits, writes the dashboard data, and prints `D14: blocked. Waits for E2, same file: <files>` or `D14: to-do, no shared file`. The files are dropped once a spec cites the decision, it has a row in an epic file, or it is no longer `to-do` or `blocked`.
- Does, with no id: writes nothing and prints `Ready:` (or `Ready: none`) with a line `- D<n>: <title>` per decision that is `to-do` with no `epic` line and no row in an epic file, then, only when a decision is blocked, `Blocked:` with a line `- D<n>: <title>. Waits for E<n>, same file.` per blocked decision.
- With a decision board the two new forms are refused (a usage error with no id), and a running epic is the `#E<n>` tag of a card not in Done.
- When: with no id after each recorded decision (the Epic hint); `--files` when the lead records a decision whose files it knows and that no spec cites

### sprints/swimlanes.py

- Command: `python3 -I <skill>/scripts/sprints/swimlanes.py v0.<n>.x`
- Does: keeps the page of the release and its data current, by the release's format:
  - format 2.2: `status/index.html` is a copy of `board/dashboard.html`, and `status/src/` holds copies of the files of `board/src/`; each is copied when it is missing or differs. It writes `status/data/status.data.js` and the dashboard data (`dashboard.data.js`, `dashboard.json`), and removes a left-over `status/data/queue.data.js`. It reads no grid file;
  - format 2.1 and 2.0: `status/index.html` is a copy of `board/task-board.html`; it writes `status.data.js`, and in format 2.1 `queue.data.js` for the Queue view. It writes no swimlane data and removes `sprints.json` and `sprints.data.js` when they are there;
  - format 1.0: it reads `status/sprints.md`, the ownership facts (in memory, each epic's critical path computed on the fly) and `<release>-plan.md`, and writes `status/data/sprints.data.js` and `status/data/sprints.json`: each milestone's status from its cell, with a short reason for a waiting or stopped one read from its tracker as `status/progress.py` reads it; each epic's path milestones marked critical, `criticalPaths` per epic, `criticalPath` their union. It copies `board/swimlanes.html` to `status/index.html` when the template is newer or the page is missing.
- When: the last step of `sprints/refresh.py` and `sprints/mark.py`

### board/swimlanes.html

- File: `<skill>/board/swimlanes.html`
- Does: the swimlane page: lanes per epic, sprint columns, Depends on arrows, red arrows only between two milestones of one epic's path; reads `data/sprints.data.js` beside it; one self-contained file, no network requests: its CSS is Tailwind compiled from `board/swimlanes.tw.css` and inlined (the rebuild command is at the top of that file, needed only when the page's classes change)
- When: copied, never edited in a release

### sprints/refresh.py

- Command: `python3 -I <skill>/scripts/sprints/refresh.py v0.<n>.x`
- Does, under the `.ids.lock` lock, the chain of `lib/grid.py` refresh, in this order:
  1. the placement: the sprint of each milestone of a spec with an `- Epic: E<n>` line, stored in the status file; a milestone that is `in progress`, `done` or `archived`, or `blocked` after its launch, keeps its sprint;
  2. it rewrites the Sprint column of every unfinished epic's table that has a `starts` value, touching only that column;
  3. the decisions: the status rule on every decision file and `decisions.md` written again as the list (with a decision board: the cards moved to the lanes of the Done rule);
  4. the queue: the blocked check of every item file, and `queue.md` written again;
  5. the page data (`sprints/swimlanes.py`): the status file, the `status:` lines, `status.data.js` and the dashboard data.
- Below format 2.2 step 1 writes the grid file `status/sprints.md` (finished, `[ ]` and `[~]` cells stay; in format 2.0 and 2.1 every mark is drawn from the status file), and step 4 syncs the Decided cards of a board `queue.md` (format 2.0) or writes `queue.data.js` (format 2.1). Format 1.0 gets the swimlane data.
- Commits nothing (commit `decisions.md`, `queue.md`, the item files and the changed epic files; below 2.2 the grid too).
- Each step alone: `sprints/grid.py` (prints the grid), `sprints/sync_epic_sprints.py` (the Sprint column only), `queue/sync.py` (the Decided cards of a board only)
- When: `run/go.py`, Changing a decision, after a hand edit of an item file

### sprints/grid.py

- Command: `python3 -I <skill>/scripts/sprints/grid.py v0.<n>.x`
- Does: prints the grid on stdout, built from the status file, in the shape of [formats.md](formats.md), The grid: `# <release> sprints`, an `Updated:` line, the table and the `Marks:` legend. Writes nothing.
- Below format 2.2 it writes the grid file `status/sprints.md` instead, and nothing else; sessions run `sprints/refresh.py` for that.
- When: the lead on `DONE` or `BLOCKED`, the runner in its tick, any session that wants the grid

### run/runner.sh

- Command: `<skill>/scripts/run/runner.sh start|list|stop|send|fork|resume|adopt v0.<n>.x`
- Does, by mode:
  - `start`: reuses the live runner of the release, resumes a dead one, or opens the next `<release> runner<n>` in the current tmux session running the runner (opus unless `--model` or `$EXPEDITION_RUNNER_MODEL`, bypass, fixed `--session-id`, `templates/runner-settings.json`, brief).
    - Numbers are never reused; `--new` opens another beside the live one; `--new --name "<name>"` names it as given; called from a runner window it runs on that runner's model; the window name is also the `claude -n` name; the runner of a release is its newest entry that is not stopped.
    - It records the runner in `~/.claude/expedition-runners.json`.
    - It resumes a dead one with `--resume`.
    - It prints the command outside tmux.
  - `list [<release>]`: entries with busy or idle, release and kind; with a release, the entries of that release only.
  - `stop`: closes the window, marks the entry stopped.
  - `send <release> "<line>"`: types `ultracode <line>` into the runner window and submits it (the RUN line `RUN E<n> <release folder> epic <epic file> from <lead>`; a runner by full window name, for example `send "v0.9.x runner2" "LEAD <name>"`).
  - `fork <release> E<n> "<D ids>" --from <lead>`: opens window `<release> specs E<n>` running the spec writer, a forked session of the lead (`--resume $CLAUDE_CODE_SESSION_ID --fork-session`, model fable unless `--model`), that fills the epic table's Files column, writes the epic's specs, completes the table with `epics/table.py` and replies `SPECS E<n> <spec numbers>`, with its own `--session-id` in the registry.
    - A spec writer whose window died is resumed by the same `fork` call, never forked again.
    - `stop "<release> specs E<n>"` closes it.
  - `resume <release or window name>`: types `resume` into a live window (the runner with the ultracode prefix), starts a dead runner, reopens a dead spec writer whose session transcript exists in a new window with its name (`claude --resume <uuid>`), else prints that line with the reason.
  - `adopt <release> [--uuid UUID] [--pane PANE] [--replaces <name>]`: registers a claude session that already runs (default the calling one) as the next `<release> runner<n>` with its own uuid, renames its window, marks `--replaces` stopped.
- A registry write that gives one session uuid to a second entry that is not stopped is refused, and `list` warns on a shared uuid.
- The runner and every spec writer run in the lead's working directory, never in a subfolder: `start` and `fork` open the new window in the folder they are called from, or in `--cwd PATH`.
- The registry is never edited by hand.
- Env overrides for tests: `EXPEDITION_REGISTRY`, `EXPEDITION_STATE_DIR`, `EXPEDITION_PROJECTS`, `EXPEDITION_CLAUDE`, `EXPEDITION_TMUX_SOCKET`
- When: once per release, to revive a runner, and on every go (through run/go.py)

### run/runner.sh watch, run/nudge-watch.sh

- Command: `<skill>/scripts/run/runner.sh watch start|stop|status`, `<skill>/scripts/run/nudge-watch.sh`
- `start`, `send` and `fork` run inside tmux record the calling window as registry key `lead` (`{"tmux": "<session>:<window id>", "session": $CLAUDE_CODE_SESSION_ID, "name": --from, the line's "from <name>" or the name of a `LEAD <name>` line}`), except when called from a runner window (`EXPEDITION_RUNNER` set).
- `start` also starts the watcher (pid `~/.claude/expedition-runners/nudge-watch.pid`); `stop` stops it once no runner or spec writer window is live.
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
- Does: read-only. For each milestone that is `in progress` in the status file (a `[ ]` row of `status/sprints.md` below format 2.2) it prints:
  - the milestone;
  - its recorded run id;
  - the registry entry whose session folder holds the run (`<projects>/*/<session>/subagents/workflows/<run id>/`, the final state `<session>/workflows/<run id>.json`);
  - the last activity (newest file in that folder);
  - a state, one of:
    - `alive`: activity within `--stale`, default 20 minutes;
    - `paused`: the run's last limit event is its pause;
    - `silent`: no activity past the threshold, or ended killed or failed;
    - `finished`: final state completed, milestone still `in progress`;
    - `no run`: no id, or the id in no session.
- It prints each `blocked` milestone (a `[~]` row) as `waiting`, and a count line.
- `--tsv` gives tab-separated lines for the watcher.
- Exit 0 for any read
- When: the runner's wake check (tick.md, step 3); the nudge watcher every minute

### plan/milestone.py

- Command: `python3 -I <skill>/scripts/plan/milestone.py add v0.<n>.x <spec> "<Name>" [--decision D<n>] [--task "<title>"]... [--type feat|bug] [--module 1.6.N] [--cites "Q3, Q4"] [--files a,b] [--depends "<names>"] [--checks "<checks>"] [--epic E<n>]`
- Does: adds a piece of work to `<spec>`:
  - the module `#### 1.6.N <Name> (<ids>)` (or an existing `--module`);
  - one task file per `--task` from `templates/task.md` (default one task named like the milestone) with its pointer line;
  - the block `#### 2.2.N Milestone: <Name>` (`Tasks`, `Files owned` when `--files`, `Depends on` every other milestone owning one of those files plus `--depends`);
  - the tracker `run/trackers/NN-<name slug>-tracker.md`.
- For a spec in an epic: `- Starts: S<n>`, the current sprint, and with `--decision` the decision's Ownership row in the epic file and its `#E<n>` tag (In progress); below format 2.2 also the epic file's decisions line.
- A done spec: refused with `--decision`; without, the follow-up spec `NN.M` with that one milestone in a running epic (`--epic` when several run).
- An old-form spec gets one `### Milestone:` block with one task line (`--files` and `--checks` required).
- Closes each cited item as fixed by a run agent: `status: done` and `decider: agent` in its item file, without its `decision` and `option` lines, then the blocked check and `queue.md` written again (format 2.1: `status: autofix`, no decider; format 2.0: the card moves to Autofix). Then it reruns `sprints/refresh.py` and the page data, commits under the `.ids.lock` lock and prints one line naming spec, milestone, sprint and tracker.
- Refuses, writing nothing: a D id in `--cites`, an unknown item (a Q id with no item file in `queue/`; a card not in `queue.md` in format 2.0), decision, module or spec, a superseded decision or one in another epic, a taken milestone name, milestones that no longer schedule
- When: each milestone of a new spec, a feedback item on a spec in progress, a fix found during a run

### plan/new_fix.py

- Command: `python3 -I <skill>/scripts/plan/new_fix.py v0.<n>.x <slug> "<Title>" <spec> --files a,b --checks "<checks>" [--cites "Q3, Q4"] [--depends "<names>"] [--epic E<n>]`
- Does: adds a fix in a format 1.0 release, with the arguments the sessions of that format use: a `### Milestone:` block in a spec that is still building, or the follow-up file `NN.M-<slug>.md`.
- In a release with a status file it calls `plan/milestone.py add` with the same arguments (the slug is not used): from format 2.1 on a cited Q id is checked against the item files there.
- When: a fix found during the run of a format 1.0 release

### plan/task.py

- Command: `python3 -I <skill>/scripts/plan/task.py add v0.<n>.x <spec> "<Title>" [--module 1.6.N] [--milestone "<name>"] [--type feat|bug]`
- Does: writes the task file `tasks/NN-<slug>.md` (`status: to-do`; `status: not started` below format 2.2) and its pointer line in 2.1; with `--milestone` adds the number to that milestone's `Tasks` line.
- Refuses an old-form or done spec, an unknown module or milestone, a milestone that has started
- When: one more task for a module, or for a milestone not yet started

### status/status.py

- Command: `python3 -I <skill>/scripts/status/status.py v0.<n>.x set <id> "<status>" [--reason "<text>"] [--commit <sha>]`, `get <id>`, `list [--status "<status>"] [--kind epic|spec|milestone|task]`, `drop <id>`
- Does: the only reader and writer of statuses.
- Ids: task `27-03`, milestone `27-collapse-shortcut` (its tracker name), spec `27`, epic `E11`.
- Words: `to-do`, `in progress`, `blocked`, `done`, `archived`; it takes `not started` for `to-do` and `skipped` for `archived` too, stores the word of the release's format and prints it. Below format 2.2 the stored words are `not started` and `skipped`.
- `set` on a task or a milestone: writes `status/data/status.json` (through a temporary file), rolls a task up into its milestone, counts spec, epic and sprint, writes the word into the `status:` line of the task, spec and epic files, writes the page data, commits; below format 2.2 it also draws `status/sprints.md`. A set that changes nothing writes nothing.
- `blocked` and `archived` need `--reason`. The status of a spec and an epic is counted, never set.
- A task set to done with an open `Owner:` box becomes blocked, "waits for the owner's look"; with another open box it is refused.
- A milestone set to done needs `--commit`, a commit hash, and is refused while one of its tasks is not finished.
- `drop` removes a stored entry that no spec has, and refuses one a spec still has.
- Run from a milestone worktree it writes the one release folder that holds the scripts' lock, never the worktree's copy.
- Refuses a release with no `status.json`; a file that cannot be parsed stops it with one line
- When: the builder at the start and end of each task; the lead after the owner's look

### migrate/v1.0-v2.0/format.py

- Command: `python3 -I <skill>/scripts/migrate/v1.0-v2.0/format.py v0.<n>.x [--dry-run] [--force]`
- Does: moves a format 1.0 release to spec folders, task files and the status store, in one commit; counts before and after must be equal; details in [migrate.md](migrate.md)
- When: once per release that is in work, when no milestone runs

### migrate/v2.0-v2.1/format.py

- Command: `python3 -I <skill>/scripts/migrate/v2.0-v2.1/format.py v0.<n>.x [--check] [--owner X] [--root PATH]`
- Does: moves the queue of a format 2.0 release from the board `queue.md` to one item file per card under `queue/` and `queue.md` as a list, sets the format to 2.1, in one commit; `--check` prints what it would write and the counts, and writes nothing; details in [its README](../scripts/migrate/v2.0-v2.1/README.md)
- When: once per format 2.0 release that should use queue item files

### migrate/v2.1-v2.2/format.py

- Command: `python3 -I <skill>/scripts/migrate/v2.1-v2.2/format.py v0.<n>.x [--check] [--owner X] [--root PATH]`
- Does: moves a format 2.1 release to format 2.2 in one run and one commit, `docs(plan): <release> moved to format 2.2`: the status words of the item files and of the status file, each decision card to a decision file in `decisions/` and `decisions.md` to the list (the round of each decision to the status file, no `decider` line), `decider: agent` on each `autofix` item, `launched` on each milestone that was launched, the `status:` lines of the task, spec and epic files, the epic files without their `decisions:` and `specs:` lines (a row added for each decision or spec they named and the table did not have), `status/sprints.md` removed after a check that it equals the status file, its link removed from `<release>-plan.md`, `"format": "2.2"`, and the dashboard page installed. It prints the counts before and after and stops before the commit, restoring the files, when one differs. `--check` prints the files and the counts and writes nothing. Details in [its README](../scripts/migrate/v2.1-v2.2/README.md).
- The decision step alone: a release of format 2.2 whose `decisions.md` is still the board gets only the decision files, the list and the rounds, in one commit `docs(plan): <release> decisions moved to decision files`.
- Refuses, writing nothing: a release that is not in format 2.1 and not a format 2.2 release with the board (it names the migration to run first), an uncommitted change in a file it rewrites, a `decisions/` folder that exists, a line of `decisions.md` in no card.
- When: once per format 2.1 release that should use the forms of format 2.2, and once per format 2.2 release that still has the board

### queue/item.py

- Command: `python3 -I <skill>/scripts/queue/item.py v0.<n>.x D|Q "<title>" [--source Q<n>] [--option <n>] [--decider you|lead|agent] [--bullet "<text>"] [--new-round]`, `--move Q<n> Open|Later|Dropped|Autofix|to-do|backlog|archived|done [--decider you|lead|agent]`, `--fact Q<n> "<text>"`, `--depends Q<n> "<Q ids>"`
- Does: every mode runs under a lock on `status/data/.ids.lock` in the release folder and re-reads the files right before the write. Each item is the file `queue/Q<n>-<slug>.md` (`templates/queue-item.md`) and `queue.md` is the list of the files (`templates/queue-list.md`), written again after each change.
- `D`: needs `--decider you`, `lead` or `agent` on every call, and `you` or `lead` with `--source`. It writes the decision file `decisions/D<n>-<slug>.md`, `<n>` one above the highest decision file, with `status: to-do`, `decider`, `source` with `--source`, the title line and the bullet as the first body line; no `- Source:` line. The round goes to the status file (the highest round, the next with `--new-round`). Then the status rule, `decisions.md` written again as the list, and the dashboard data. With a decision board: the card `- [ ] **D<n>** <title> #R<n>` at the end of To do in `decisions.md`, the bullet if given, then `- Source: Q<n>` if given, tab-indented; there `D` with no `--source` needs no `--decider`. With `--source Q<n>` it closes the item: `status: done`, `decision: D<n>` (an item already done by a decision keeps the highest number), `option: <n>` with `--option`, and `decider: you` or `lead` from `--decider`. An option number the item's `## Options:` does not have is refused, and `--option` needs `--source`. `D` with no `--source` closes no item.
- `Q`: a new item file with `status: to-do`, `# Q<n>. <title>` and the bullet under `## Notes`; `<n>` is one above every item file and every line of `queue.md`.
- `--move`: the lane words and the status words mean the same: `Open` is `to-do`, `Later` is `backlog`, `Dropped` is `archived`, `Autofix` is `done`. Every move first removes `decision`, `option` and `decider`. `Dropped` needs `--decider you` or `lead`, `Autofix` needs `--decider agent`; `Open` and `Later` take none.
- `--fact`: one bullet at the end of `## Notes`, no other line changed.
- `--depends Q<n> "Q14, Q15"`: replaces the `depends_on` line of Q<n>; `""` removes it. Refused: an id that is not a queue item id, an id with no item file, the item itself, a ring of items that wait for each other.
- After every command the blocked check sets `blocked` or `to-do` on each `to-do` or `blocked` item from its `depends_on` line. A call that is refused writes nothing.
- `## Details` and `## Options:` are never written or reordered.
- It writes the item files, `queue.md` and the dashboard data (`status/data/dashboard.data.js` and `dashboard.json`, git-ignored), commits the item files, `queue.md`, `decisions.md`, the decision file and the status file, and prints the id alone; another kind exits non-zero.
- Format 2.1: the same files, with the words `open`, `decided`, `later`, `dropped`, `autofix` (`--move` stores the lane word in lower case); `--decider` is accepted and not stored, `--depends` is refused with one line naming `scripts/migrate/v2.1-v2.2`, and it writes `status/data/queue.data.js` in place of the dashboard data. Format 2.0: the board `queue.md`, where an item is a card in a lane ([old-form/queue-board.md](old-form/queue-board.md)); `--option` is refused there.
- When: every new D or Q item and every status change, fact or dependency of an item, by either session

### decisions/close.py

- Command: `python3 -I <skill>/scripts/decisions/close.py v0.<n>.x D<n> [--backlog]`
- Does: under the `.ids.lock` lock: writes `status: done` into the decision file (the record of "closed, nothing to run"); refuses an id with no file, a decision with an `epic` line or with a row in an epic that has gone; one already `done` changes nothing. `--backlog` writes `status: backlog`, for a decision that moves to another release; it refuses an id with no file and a decision that is `done` or `archived`. Then the status rule, the list, one commit of `decisions.md` and the decision files, and the dashboard data. Prints `D<n> to Done (nothing to run); committed` or `D<n> to backlog; committed`.
- With a decision board: moves the decision's card to Done, ticked; refuses an unknown id, a decision with an epic tag or with a row in an epic that has gone; one already in Done changes nothing; then the Done rule sync, and the queue sync of a board `queue.md` (format 2.0 only), one commit. `--backlog` is refused with one line that names `scripts/migrate/v2.1-v2.2`.
- When: a decision with nothing to run, when recorded; `--backlog` when a decision moves to another release

### decisions/supersede.py

- Command: `python3 -I <skill>/scripts/decisions/supersede.py v0.<n>.x D<old> D<new>`
- Does: under the `.ids.lock` lock: `status: archived` and `replaced_by: D<new>` in the old file, its title line unchanged; the new file is not changed, and no line goes into its body. Refuses an id with no file, the same id twice, and an old decision with a `replaced_by` line already. Then the status rule, the list, one commit of `decisions.md` and the decision files, and the dashboard data. Prints `D<old> superseded by D<new>, to Done; committed`.
- With a decision board: the supersede marks of [old-form/format-2.1.md](old-form/format-2.1.md), Decision board, on both cards (the old card to Done, `- Supersedes D<old>.` as the new decision's first bullet); refuses an unknown id and an old decision already superseded; then the Done rule sync, and the queue sync of a board `queue.md` (format 2.0 only), one commit
- When: Changing a decision, once built

### decisions/decider.py

- Command: `python3 -I <skill>/scripts/decisions/decider.py v0.<n>.x D<n> you|lead|agent [--change]`
- Does: under the `.ids.lock` lock: writes the `decider` line after the `status` line of a decision file that has none (a decision recorded before its release moved to decision files); nothing else of the file changes. Then the status rule, the list, one commit, and the dashboard data. Prints `D<n> decider <word>; committed`.
- `--change`: replaces the `decider` line of a file that has one, in the same place; prints `D<n> decider <old> to <word>; committed`. On a file with no `decider` line it writes the line, as without the flag.
- Refuses, writing nothing: a word that is not `you`, `lead` or `agent`, an id with no file, without `--change`, a file that has a `decider` line (`D<n> has decider <word>: nothing changed`); with `--change`, a file whose `decider` line holds the word already (`D<n> has decider <word> already: nothing changed`); and a decision board, with one line that names `scripts/migrate/v2.1-v2.2`.
- When: `status/report.py` counts decision files with no decider, and the lead knows who made the call; with `--change`, when a recorded decider is wrong

### plan/find_rules.py

- Command: `python3 -I <skill>/scripts/plan/find_rules.py [repo]`
- Does: read-only: prints project planning-rules paths, one per line, nothing if none

### plan/process.py

- Command: `python3 -I <skill>/scripts/plan/process.py [v0.<n>.x] [stage words]`
- Does: read-only: prints `process.md: <absolute path>` and then the release's `process.md` in full; the release is the first argument that is a release name, else the highest-numbered release folder that holds a `process.md`; other words are ignored; repo root and owner found as for every script.
- Nothing found: one line naming the folder searched.
- Always exits 0, never a traceback
- When: SKILL.md injects it at invocation; again after a handoff, a compaction or a RUN line

### status/report.py

- Command: `python3 -I <skill>/scripts/status/report.py v0.<n>.x`
- Does: read-only. It prints:
  - missing files;
  - a state table per decision, the item count per status and one row per item file with its status (format 2.0: per queue card, its lane);
  - queue gaps: an unknown or missing lane, a card without a `**Q<n>**` token, a duplicate id, a title tag other than `#D<n>` or `#E<n>`, a leftover `Decision:` fact, a Decided card without `#D<n>` or naming a missing decision, a Decided card whose tick or `#E<n>` disagrees with the lane of its decision, a `(Q<n>)` or `Source: Q<n>` citation of a missing card (a `**Complete**` marker line is ignored); with item files instead: an item file with no `# Q<n>.` title or a number that differs from its file name, a `queue.md` that differs from the item files, a duplicate number, a citation of a missing item, and a `status` outside the five words of a queue item (`to-do`, `blocked`, `done`, `backlog`, `archived`), a `decider` that is not `you`, `lead` or `agent` or one on an item that is not closed, the `decision` of a `done` item not in `decisions.md`, a `depends_on` id with no item file, an item that waits for an `archived` item, an item whose status differs from what the blocked check gives (fix: `sprints/refresh.py`). A closed item with no `decider` is no gap: it was closed before format 2.2. Format 2.1: a `status` outside open, decided, later, dropped and autofix, a decided item with no decision or one not in `decisions.md`;
  - milestones without tracker, `Status:` line or checks;
  - possible open questions;
  - a `<release>-plan.md` `## ` section other than Goals and Deliverables;
  - a Deliverables Scope cell over 120 characters;
  - milestones `sprints/check.py` would refuse;
  - a left-over `status/sprints.md` (delete it), and a milestone of an epic with no `sprint` in the status file (fix: `sprints/refresh.py`); below format 2.2 instead: `status/sprints.md` missing, without a ` | Milestone` table, with rows that differ from the milestones or with a cell that is no grid mark;
  - each tagged epic's critical path;
  - the release's `process.md`: missing, placeholders left, undefined `(P<n>)` citations;
  - the decisions: `Decisions: <n> in decisions/`, one row per decision file (id, citing specs, status), the count per status word, and one line that counts the files with no `decider` line and names `decisions/decider.py`; gaps: a status that is none of the six words or differs from the status rule (fix: `sprints/refresh.py`), a front matter line that is none of the five, a `decider` that is not `you`, `lead` or `agent`, a `replaced_by`, `epic` or `source` that names nothing, a file with no `# D<n>.` title or a number that differs from its file name, a list that differs from the files, a D id a spec cites and no file has. With a decision board, the board gaps instead: a missing lane, a card without a `**D<n>**` token, a tag that is not one of the four tags of the board ([old-form/format-2.1.md](old-form/format-2.1.md), Decision board), a duplicate id, ids out of order in a lane, a lane that disagrees with the Done rule, a tick that disagrees with its lane, and in format 2.2 one line that names `scripts/migrate/v2.1-v2.2/format.py`;
  - an epic summary: deciding, in E<n>, running, done per D item; an epic runs while a milestone of it is not `to-do` in the status file;
  - the decisions still editable in place (no citing spec has a milestone `in progress`, `blocked` after a launch, or `done`);
  - a supersede marked on one side only;
  - an unbuilt spec citing a superseded decision;
  - epic files missing or with notes without ack (only a file with a `## Notes` section);
  - the next epic file missing while an epic runs;
  - the epic tables: an epic with milestones whose file has no Ownership table, a spec of the epic with no row (below format 2.2 also a decision of the `Decisions:` line with no row), a row file no milestone of its spec owns, a Sprint cell that disagrees with the grid (an epic file without a table and no grid rows is not flagged);
  - in a format 2.0 release: a pointer whose task file is missing, a task file with no Verification box, a `status:` front matter line that differs from the status file;
  - the inferred stage;
  - one last line when the release's format is lower than the skill's version: the migration folders under `scripts/migrate/` from the release's format up, in the order to run them; it names only folders that exist.
- First line names the planning rules in use.
- When: any time

### queue/next.py

- Command: `python3 -I <skill>/scripts/queue/next.py v0.<n>.x`
- Does: read-only: prints the `to-do` item with the lowest number, as its file path on one line and the text of the file below it, or `none`. A `blocked` item is never printed.
- Format 2.1: the `open` item with the lowest number. Format 2.0: the first card in Open with its facts.
- When: before each item

### queue/list.py

- Command: `python3 -I <skill>/scripts/queue/list.py v0.<n>.x [word] [--facts]`
- Does: read-only: one line `Q<n> <title>` per item, in number order; `--facts` adds the lines of each item's `## Notes`, each indented with one tab; default `Open`, words in any case; none found prints `none`; an unknown word exits 1 naming the valid ones.
- The word is a lane word or a status word. `Open` lists the `to-do` and the `blocked` items, a blocked one with ` (blocked: waits for Q14, Q15)` after its title (the ids of its `depends_on` line that are not done); `Decided` the `done` items with a decision; `Autofix` the `done` items without one; `Later` the `backlog` items; `Dropped` the `archived` ones. The six status words select by `status` alone. `all` prints one line `<word> <count>` per status word, in the order `to-do`, `in progress`, `blocked`, `done`, `backlog`, `archived`; each item is counted once, a blocked item under `blocked` only.
- Format 2.1: the lane word selects the items whose `status` is that word in lower case, and a status word the status it maps to; `all` counts the items per lane word. Format 2.0: the cards of one lane of the board, with their `#D<n>` and `#E<n>` tags and, in Decided, the tick first.
- When: when a session needs more than the next item

### queue/sync.py

- Command: `python3 -I <skill>/scripts/queue/sync.py v0.<n>.x`
- Does: under the `.ids.lock` lock, syncs the Decided cards of `queue.md` with the lanes of `decisions.md` (the tick and the `#E<n>` tag) and prints the cards it changed; commits nothing.
- From format 2.1 on (item files): prints that there is nothing to sync, writes nothing, exits 0; an item holds its decision id only.
- When: step 3 of the `sprints/refresh.py` chain alone

### sprints/mark.py

- Command: `python3 -I <skill>/scripts/sprints/mark.py v0.<n>.x <milestone> launch|wait|resume|merge|stop [--reason "<text>"] [--commit <sha>]`
- Does: the verb sets the milestone's status in the status file ([formats.md](formats.md), Milestone status): `launch` `in progress` (and `launched` true); `wait` and `stop` `blocked`, with `--reason`; `stop --reason "D<n> ..."` `archived`; `merge --commit <sha>` `done`, refused while a task of the milestone is not finished; `resume` only on a blocked milestone, `in progress` when it was launched before and `to-do` when it never was. `<milestone>` is the tracker file name without `-tracker.md` (`47-comparison-page`). Then, under the `.ids.lock` lock, the chain of `sprints/refresh.py`, and one commit of the status file and the files the chain changed (never pushes).
- Format 2.1 and 2.0: the same, with `not started` and `skipped` for `to-do` and `archived`; the chain also draws `status/sprints.md` and the commit holds it, and launched before means a commit `docs(plan): <release> <milestone> launch` in its history. Format 1.0: the only writer of grid marks, by the rules of [old-form/format-2.1.md](old-form/format-2.1.md), The grid file; the two flags are accepted and not used.
- An unknown milestone, or one with no sprint (no grid row below format 2.2), is refused with one line; a repeat call changes nothing and exits 0.
- When: at every launch, wait, resume, merge and stop: the workflow's merger for `merge`, the runner otherwise

### status/progress.py

- Command: `python3 -I <skill>/scripts/status/progress.py v0.<n>.x`
- Does: read-only. It prints only the owner's progress reply in Markdown:
  - per epic with an unfinished milestone: `**E<n>** · Specs d/t` (a spec is done when every milestone of it is done or archived by a decision), `- **Running**` (specs with a milestone in progress) and `- **Blocked**` (specs with a blocked milestone, with its reason), each spec as its number and its Deliverables title; an unfinished milestone with a task started adds ` · <milestone> d/t` and a blocked task its reason;
  - with nothing unfinished: the last epic's line, then `Nothing running.` and `Ready for an epic: **Q<n>**, ...`: the `done` items whose decision file has `status: to-do` (a `blocked` decision is not ready; with a decision board, whose decision card is in To do).
- Every status comes from the status file; it reads no grid file and no tracker status.
- Format 2.1 and 2.0: the same block from the status file, with the words of that format; Ready for an epic lists the `decided` items (format 2.0: the unticked Decided cards). Format 1.0: per milestone the grid cell and the most advanced copy of its tracker (planned < running < waiting < done or stopped) among the main checkout and the worktree on the branch its `Branch` line names; each disagreement with the grid goes to stderr as one `warning:` line.
- The reply rule: [formats.md](formats.md), Progress reply and reports.
- When: on `progress`

### run/guard.py

- Command: `python3 -I <skill>/scripts/run/guard.py < hook.json`, as the PreToolUse hook of `templates/runner-settings.json`; no session types it.
- Does: reads the hook JSON on stdin and blocks a Bash command that no run needs: a git push that forces; a shell read of a credential store; `rm -r` whose target is `/`, the home folder, or a path outside the session's repo, its worktrees folder, the working folder and a temp folder.
- A block prints one line on stderr and exits 2. Anything else, and any input it cannot parse, exits 0 with no output, so the guard never holds up a run. It is a guard against mistakes and poisoned text, not a sandbox.
- When: every Bash call of a runner or a spec writer
