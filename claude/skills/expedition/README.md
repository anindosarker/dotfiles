# Expedition

Requires: tmux, the `claude` command, python3.

Expedition is a skill for long work that does not fit one session. It keeps the plan of a release in a folder of plain files, lets the owner decide things in conversation, and has a second session build what was decided while the conversation goes on. This page explains how it fits together. The rules the agent follows are in `SKILL.md`.

## The three roles

- The lead is the session the owner talks to. It discusses, records decisions and plans the work.
- The runner is a second session. It starts the builders, merges what they finish and reports back to the lead.
- The builders are agents the runner starts, one group per milestone. Each works on its own branch.

## How a piece of work goes from discussion to merged

1. The owner raises a remark or a problem. The lead files it as an item in the queue: one file per item, and `queue.md` lists them.
2. The lead posts the item with its details and options. The owner decides; the lead writes the item to its file and records the decision.
3. Decisions that are ready are grouped into an epic. A spec writer turns the epic into specs.
4. A spec says what is wanted in modules, lists the work as task files, and groups the tasks into milestones.
5. On the owner's `delegate`, the runner builds each milestone: a builder does the tasks and ticks each task's checks.
6. A milestone merges when its checks pass. A check that only the owner can make waits for the owner's look.
7. The decision is done when its milestones are merged. Problems found on the way come back as new queue items.

## The skill folder

```
SKILL.md          the rules for the agent, and the skill's version
CHANGELOG.md      what each version changed
reference/        one file per stage (discuss, plan, run, triage), then files, formats, scripts, migrations
templates/        the shape of each file the agent writes
board/            the status pages
example/          one small release with every kind of file filled in
scripts/          the commands that do the mechanical steps
  lib/            the code the scripts share
  plan/           new release, new spec, new milestone, new task
  epics/          start an epic, tag its specs, show its table
  sprints/        the sprints, the grid and the milestone statuses
  status/         the status command, the report, the progress reply, the Waits for you line
  queue/          queue items and decisions
  decisions/      close, replace or hold a decision, or set who made it
  run/            the runner session and the go
  migrate/        one folder per version step, each with a guide
```

## A release folder

```
.ai/plans/v0.<n>.x/<owner>/
  <release>-plan.md       goals, and one row per spec
  decisions.md            the list of the decisions, written by the scripts
  decisions/D<n>-<slug>.md one decision: its status, who made it, where it came from, and what was decided
  queue.md                the list of every item raised, written by the scripts
  queue/Q<n>-<slug>.md    one item: its status, who closed it, what it waits for, notes, details and options
  process.md              the facts of this project
  plan/epics/E<n>.md      one epic: its status, its start sprint, and a table of its decisions and specs
  plan/specs/NN-<slug>/   one spec, with its task files in tasks/
  run/trackers/           the run notes of each milestone
  run/handoffs/           notes for the next session
  status/data/status.json the status of everything, and the sprint of each milestone
  status/index.html       the dashboard page, generated
```

## The status words

There are six status words: to-do, in progress, blocked, done, backlog, archived.

- Every epic, spec, milestone and task has one of five of them: to-do, in progress, blocked, done, archived. A blocked or archived one has a short reason. These statuses are kept in one file and set by one command, so no file has to be edited to change one.
- A queue item has one of five of them: to-do, blocked, done, backlog, archived. Backlog is for a queue item only, and a queue item is never in progress. A closed item also says who made the call: you (the owner), the lead or an agent. An item that waits for other items is blocked until they are done; the scripts set that.
- An epic whose specs are ready is blocked until the owner says `delegate`.
- A decision uses all six. It is to-do when decided and in no epic, in progress in an epic, and done when its work has merged or there is nothing to run. It is blocked when it is in no epic and needs a file that a running epic changes; it is to-do again when that epic has merged. It is backlog when it moves to another release, and archived when a later decision replaces it. A decision file also says who made the call. The scripts set every status.
- `scripts/sprints/grid.py <release>` prints the grid: the milestones by sprint, with one mark for each status.

A release in format 2.1 or lower keeps the five words of that format (not started and skipped, and open, decided, later, dropped, autofix for a queue item), the grid file `status/sprints.md`, and its decisions as a board of cards in `decisions.md`, in three lanes: To do, In progress, Done.

## Starting in a new project

Run `/expedition discuss` in the project. On the first run the lead shows a suggested folder layout and asks one question about where the plans should be. After that it creates the first release folder and the conversation starts. `example/` shows what a release looks like once it is in work.

## After a skill update

Read `CHANGELOG.md` first: it says what is new and what a release in work has to do. When a release is in an older format, `scripts/status/report.py <release>` says so in its last line and names the migration folder. Each migration folder under `scripts/migrate/` has a guide with the commands, a way to check the result, a way to undo it, and a prompt to paste into the lead session.

A release in format 2.0 keeps its queue as a kanban board of cards in `queue.md`; `scripts/migrate/v2.0-v2.1/README.md` moves it to item files.

A release in format 2.1 keeps its five status words, the `decisions:` and `specs:` lines of its epic files and its `status/sprints.md`; `scripts/migrate/v2.1-v2.2/README.md` moves it to format 2.2.

## The dashboard page

A release in format 2.2 has the dashboard page at `status/index.html`: open that file in a browser. It has six views: Dashboard, Queue, Epics, Milestones, Tasks and Sprints. Dashboard shows what waits for whom; Queue shows every queue item with its notes, details and options. Its scripts are in `status/src/`. Its data is in `status/data/`, written from the item files, the decision files and `status/data/status.json` on every change: `status.data.js` for the four plan views, and `dashboard.data.js` for Dashboard and Queue. `dashboard.json` holds the same rows for an agent to read. `reference/formats.md`, section Status, lists what the files hold.

A release in format 2.0 or 2.1 has the task board at `status/index.html`. It shows the epics, sprints, milestones and tasks with their statuses and reloads its data every 30 seconds. Its data is `status/data/status.data.js`. In format 2.1 its Queue view shows every queue item with its notes, details and options, from `status/data/queue.data.js`.
