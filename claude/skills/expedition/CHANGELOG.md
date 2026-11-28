# Changelog

One section per version of the skill, newest first. The version is `metadata.version` in the front matter of `SKILL.md`. A release folder states the format it has in `status/data/status.json` (`format`); a release with no status file is format 1.0.

## 2.2

What is new:

- Six status words: `to-do`, `in progress`, `blocked`, `done`, `backlog`, `archived`. A queue item uses `to-do`, `blocked`, `done`, `backlog` and `archived` (before: `open`, `decided`, `autofix`, `later`, `dropped`). An epic, a spec, a milestone and a task use `to-do`, `in progress`, `blocked`, `done` and `archived` (before: `not started` and `skipped` in place of `to-do` and `archived`). The owner words "record it", "later" and "drop it" stay; they set `done`, `backlog` and `archived`.
- A closed queue item has a `decider` line: `you`, `lead` or `agent`, who made the call. A command that closes an item takes `--decider`: `queue/item.py <release> D "<title>" --source Q<n> --decider you` (or `lead`), and `--move Q<n> Dropped --decider lead` or `--move Q<n> Autofix --decider agent`. Without it the command writes nothing. The status file gives a `decider` for each epic, spec, milestone and task too, worked out on each write.
- A queue item can wait for other items: `queue/item.py <release> --depends Q<n> "Q14, Q15"` writes its `depends_on` line. The scripts set it `blocked` while an item it names is not `done`, and `to-do` again after that. `queue/next.py` skips a blocked item.
- An epic whose specs are ready is `blocked`, with the reason `waits for delegate`, until the owner says `delegate`.
- The epic file `plan/epics/E<n>.md` has no `decisions:` and no `specs:` line. Its `## Ownership` table is the one copy of both.
- There is no `status/sprints.md`. The status file holds the sprint of each milestone, and `sprints/grid.py <release>` prints the grid and writes nothing.
- `status/index.html` is the dashboard page in place of the task board: six views, Dashboard, Queue, Epics, Milestones, Tasks and Sprints. Dashboard shows what waits for whom. The page loads its scripts from `status/src/`, and its data from `status/data/dashboard.data.js` and `status/data/status.data.js`; `status/data/dashboard.json` holds the same rows for an agent. `queue.data.js` is no longer written. Reference: [board/README.md](board/README.md).
- The side panel of a queue item, in the Dashboard and Queue views, shows its notes, details and options.
- `queue/list.py <release> all` counts the six status words in a release of format 2.2: one line per word with its item count.
- `plan/new_release.py` makes a new release in format 2.2.
- `plan/new_spec.py` writes the flat file `plan/specs/NN-<slug>.md` in a format 1.0 release.
- `status/report.py` on a release of an older format names, in its last line, the migration folders to run, in order.
- One file per decision: `decisions/D<n>-<slug>.md`, with the front matter `status`, `decider`, `source`, `epic` and `replaced_by`, the title line and a free body (bullets by default, a table or a code block where it reads better). `decisions.md` is the list of the decision files, written by the scripts. The rules: [reference/formats.md](reference/formats.md), Decision file.
- A decision has the six status words and a `decider`. `to-do`, `in progress`, `blocked` and `done` come from the status rule, `backlog` from `decisions/close.py --backlog`, `archived` from `decisions/supersede.py`, which writes `replaced_by: D<new>` into the old file and nothing into the new one. Every `queue/item.py <release> D` call takes `--decider you`, `lead` or `agent`; a run agent records a deviation it settled with `--decider agent`.
- A decision in no epic that shares a file with a running epic is `blocked`, and `to-do` again when that epic has merged. For a decision that no spec cites, the lead gives its files with `epics/overlap.py <release> D<n> --files "<files>"`.
- `decisions/close.py <release> D<n> --backlog` moves a decision to another release (before: the bullet `- Deferred to`).
- `decisions/decider.py <release> D<n> you|lead|agent` writes the decider of a decision file that has none: a decision recorded before its release moved to decision files.
- `decisions/decider.py <release> D<n> you|lead|agent --change` replaces the decider of a decision file that has one.
- The `Epic ready` message lists the blocked decisions under `**Blocked:**` (before: `**Decided, not in this epic:**`). The lead copies the ready lines and the blocked lines from `epics/overlap.py <release>`, which prints them.
- Item post rules, for a release of every format: during a discussion the lead answers in chat, and the whole item comes again only when the talk on it ended and the proposal changed, or on the new owner word `restate` (before: a repost after each reply that changed the item). Every post of an item, the first post too, passes four checks: each line is needed for this decision, what the owner needs to finish the item is in it, ASD-STE100 words in short lines, and option 2 is a different idea or there is one option. Inside an option: bullets by default, a table or a code block only where bullets do not work. Rules: [reference/discuss.md](reference/discuss.md), Item format.
- A Waits for you line under every message of the lead in a release of format 2.2: `status/waits.py <release>` prints each thing that waits for the owner (`E3 planned: delegate · D14 ready: compose · 05-04: your look`) and, after `Held:`, each decision the owner holds. An entry stays until the owner answers it; the `Epic ready` message is no longer posted once per set. The owner's `hold D<n>` is stored in the status file by `decisions/hold.py`, with `--until <id>` or a reason in words; when the id of `--until` is closed, the line says `D14: hold over, ready: compose`. The held block (`status/waits.py <release> --held`) comes in the first message of a session and with `DONE E<n>`. One push (`PushNotification`, when the session has the tool) when a run is done or blocked and when a thing starts to wait that the owner did not cause; the runner sends `NOTE <task id>: waits for the owner's look` for that. On the dashboard page a ready decision file gets the turn `you`, and a held one gets no turn. A release of format 2.1 or lower works as before. Rules: [reference/discuss.md](reference/discuss.md), Waits for you line, Hold and Push.
- `run/go.py` writes "RUN sent" only when the RUN line is in the runner's own transcript: it waits until the runner's window takes input, types the line, types it once more when it is not there, and else stops with `go E<n> stopped at step 6 (run): <reason>`; the next call does the step again. `run/runner.sh send --confirm` does that wait and check; `send` with no flag is unchanged.
- `run/runner.sh start`, `fork` and a `resume` that starts a dead session type the voice line `/caveman:ultracave` into the new window first, when it takes input, then the start prompt, and check that the prompt is in the transcript. A live window gets no voice line. `EXPEDITION_VOICE` sets the line; empty, nothing is typed and the prompt goes on the claude command line as before. The starter prompt of a lead's handoff and of a runner's roll over handoff begins with the voice line, on a line of its own; the `roll-over` skill types each line of `## Starter prompt` as its own message (before: the first line only). The skill no longer asks a session to load `caveman:ultracave` itself (D26).
- The note watcher (`run/nudge-watch.sh`) finds a new note by the session it was shown to, so side notes reach the lead also after the store holds 50 notes.
- Status sync, in a release of format 2.2: `status/status.py set` and `sprints/mark.py launch|wait|resume|stop` write the files and make no commit. The new `status/sync.py <release> [-m "<message>"]` commits every change under the release folder in one commit, or prints `nothing to sync`. `sprints/mark.py ... merge` and a status change that makes an epic `done` end with the sync; a session runs it before a handoff and a roll over. `status/report.py` prints `Uncommitted: <n> file(s) in the release folder: run status/sync.py <release>` while the folder has uncommitted changes. The dashboard page reloads its data every 2 seconds (before: 30). A release of format 2.1 or lower commits each status change as before. Rules: [reference/run.md](reference/run.md), Status and tasks.
- Dashboard page: a milestone chip reads M<ref> (M13.1) and a task chip T<spec>-<number> (T13-01), in all six views and the side panel; the search finds both with and without the letter. Ids, data and commands do not change (D27).

What changes for a release in work:

- Nothing has to change at once. A release in format 2.1 or lower keeps its words, its epic file lines and its `status/sprints.md`, and every script reads and writes it as before. Its rules: the section Format 2.1 releases of `SKILL.md`, and [reference/old-form/format-2.1.md](reference/old-form/format-2.1.md).
- To use the new words and the dashboard page, migrate the release. The migration is one commit, keeps every id and every line of the item files and of the decision cards, and can be undone with `git revert`. A migrated `decided` or `dropped` item, and a migrated decision, has no `decider` line, because the files of format 2.1 do not say who made the call.
- A release of format 2.2 whose `decisions.md` is still the board keeps working as before. The same migration command moves only its decisions to decision files: [scripts/migrate/v2.1-v2.2/README.md](scripts/migrate/v2.1-v2.2/README.md), A release of format 2.2 with the board.
- A session that read the skill before this version re-reads it before it creates a release or migrates one.

What stops working:

- Nothing that a 2.1 release used is removed. Every command and every flag stays, and a command takes the words of both formats.
- In a release of format 2.2, no script writes `status/sprints.md`, and `queue.data.js` is not written.
- In a release with decision files, `queue/item.py <release> D` without `--decider` is refused, and `decisions/supersede.py` writes no `- Supersedes` line into the new decision.

Migration: [scripts/migrate/v2.1-v2.2/README.md](scripts/migrate/v2.1-v2.2/README.md).

## 2.1

What is new:

- Each queue item is its own file, `queue/Q<n>-<slug>.md`: front matter (`status`, `decision`, `option`), the title `# Q<n>. <title>`, `## Notes`, `## Details` and `## Options:`. `queue.md` is a plain list of the item files, written by the scripts. The commands stay `queue/item.py`, `queue/next.py` and `queue/list.py`; what each does on item files: `reference/scripts.md`.
- The task board has a Queue view: every item with its status, notes, details and options. It reads `status/data/queue.data.js`, written for a release of format 2.1.
- The item in chat is the title, `Details` and `Options:` as they are in its file, then the `Say:` block; `## Notes` is not shown. During the back and forth nothing is written to the file. The lead writes `## Details` and `## Options:` to the file when the item settles: the owner reaches a final state on it, or the talk moves to another item, or another item comes in. An item is recorded with `queue/item.py <release> D "<title>" --source Q<n> --option <n>`.
- `templates/queue-item.md` and `templates/queue-list.md` are the shapes; the example release is in format 2.1, with filled items in `example/v1.0.x/owner/queue/`.
- One command moves a release from format 2.0 to 2.1: `scripts/migrate/v2.0-v2.1/format.py <release>`, guide [scripts/migrate/v2.0-v2.1/README.md](scripts/migrate/v2.0-v2.1/README.md).
- `plan/new_release.py` makes a new release in format 2.1: a `queue.md` list and an empty `queue/` folder.
- A runner started with no `--model` and no `$EXPEDITION_RUNNER_MODEL` runs on `opus` (before: `fable`); a live runner keeps its model. `SKILL.md` says near its start that how the owner works in a release is in `process.md`, a change is a `process.md` update, and every agent follows it.

What changes for a release in work:

- Nothing has to change at once. A release in format 2.0 keeps its queue as a kanban board, and every script reads and writes it as before. Its rules: `reference/old-form/queue-board.md`; its item chat form: `templates/item.md`.
- To use item files and the Queue view, migrate the release. The migration is one commit, keeps every line of every card, and can be undone with `git revert`.
- A session that read the skill before this version re-reads it before it creates a release or migrates one.

What stops working:

- Nothing that a 2.0 release used is removed.
- In a release of format 2.1, `queue.md` is not dragged in a kanban extension and not edited by hand, and `queue/sync.py` has nothing to sync.

Migration: [scripts/migrate/v2.0-v2.1/README.md](scripts/migrate/v2.0-v2.1/README.md).

## 2.0

What is new:

- One kind of spec, always a folder: `plan/specs/NN-<slug>/NN-<slug>.md` with its task files in `tasks/`. A spec has modules (what is wanted, with the decision cite), tasks (one file each: Goals and a Verification checklist) and numbered milestones (the tasks built and merged together).
- A spec in work grows: a new piece of work is the next module, its task files and its own milestone, added with `plan/milestone.py add`. `plan/task.py add` adds one more task. A spec that is done takes nothing; later work is a new spec.
- One status file, `status/data/status.json`, holds the status of every epic, spec, milestone and task in five words: not started, in progress, blocked, done, skipped. One command reads and writes it, `status/status.py`. The sprint grid and the `status:` line of each file are copies it writes.
- A task whose only open check is the owner's own look is blocked with that reason, and shows as such.
- A release in format 2.0 has the task board at `status/index.html`, in place of the swimlane page. It reads `status/data/status.data.js`, written from the status file on every change, and reloads every 30 seconds.
- The process file starts from a short template and carries `updated`, the time its facts were last checked.
- `templates/` holds the shape of every authored file, `example/` one small release with every kind of file filled in, and `board/` the status pages.
- `SKILL.md` is short; the detail of each stage is in its own file under `reference/` (`discuss.md`, `plan.md`, `run.md`, `triage.md`), the commands in `reference/scripts.md`. `reference/planning-guidelines.md` describes the 2.0 plan file; the 1.0 text is in `reference/old-form/`.
- `plan/new_cycle.py` is now `plan/new_release.py`; the old name still runs it.
- Migrations sit in `scripts/migrate/`, one folder per version step, each with a guide.

What changes for a release in work:

- Nothing has to change at once. A release in format 1.0 is read as before, and `plan/new_spec.py` and `plan/new_fix.py` still write the earlier form there.
- To use task files and the status command, migrate the release when no milestone is running. The migration is one commit and the reports print the same before and after.
- A session that read the skill before this version re-reads it before it creates a release or migrates one.

What stops working:

- Nothing that a 1.0 release used is removed.
- In a migrated or new release, a status is no longer written into a tracker or the grid by hand or by a prompt: `sprints/mark.py` needs `--reason` for a wait or a stop and `--commit` for a merge.

Changed after the tag `expedition-v2.0`, same format:

- The runner no longer starts a Workflow for every milestone. It judges each one: a Workflow only for several builders at the same time, a second opinion, the release milestone, or a word from the lead or the owner. Every other milestone is built by one agent and merged by the runner.
- A failed Workflow stage is resumed when that is possible; a plain agent may do it otherwise.
- In discuss, the lead fills the module and the task file of a milestone it adds to a spec in progress.
- `queue/item.py` refuses a second `--bullet`.
- Owner words: `compose`, `delegate` and `compose delegate` replace `epic`, `go` and `epic go`, which stay accepted as old names.
- Messages to the owner end with a `Say:` block of lettered commands; a letter alone is the command. `Epic ready: E<n>` and `Epic planned: E<n>` have a template (`templates/epic-messages.md`) and filled examples. The `Held:` line and the `Changed:` report are gone: a waiting decision is listed under `Decided, not in this epic:`, and the lead reports nothing it fixed in its check.
- Every session of a release starts in the `caveman:ultracave` voice when that skill is installed.
- Repost rules: a reply that changes an item gets the whole item posted again, every line word for word except the lines the owner asked to change, with no rephrasing and no "unchanged" line. A reply that changes nothing in the item gets no repost: the lead answers and names the open item in one line. When a decision is recorded, lines taken from the picked option stay word for word.
- Item format: a template (`templates/item.md`) and filled items (`example/item-examples.md`). Fixed are the title and the numbered options, recommended first; the rest is free. Wording: ASD-STE100 words, caveman shortness, key details kept.
- New owner word `iterate`: the open item is decided, planned by the regular steps and sent to the runner at once, as the next module of its spec or as a new spec with its own epic. The runner chooses the moment it starts.

Migration: [scripts/migrate/v1.0-v2.0/README.md](scripts/migrate/v1.0-v2.0/README.md).

## 1.0

The skill before versions were kept. Folders older than that: [scripts/migrate/pre-v1.0/README.md](scripts/migrate/pre-v1.0/README.md).
