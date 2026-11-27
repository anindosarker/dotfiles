# Expedition

Requires: tmux, the `claude` command, python3.

Expedition is a skill for long work that does not fit one session. It keeps the plan of a release in a folder of plain files, lets the owner decide things in conversation, and has a second session build what was decided while the conversation goes on. This page explains how it fits together. The rules the agent follows are in `SKILL.md`.

## The three roles

- The lead is the session the owner talks to. It discusses, records decisions and plans the work.
- The runner is a second session. It starts the builders, merges what they finish and reports back to the lead.
- The builders are agents the runner starts, one group per milestone. Each works on its own branch.

## How a piece of work goes from discussion to merged

1. The owner raises a remark or a problem. The lead files it as a card in the queue.
2. The lead posts the card with its options. The owner decides, and the lead records the decision.
3. Decisions that are ready are grouped into an epic. A spec writer turns the epic into specs.
4. A spec says what is wanted in modules, lists the work as task files, and groups the tasks into milestones.
5. On the owner's `delegate`, the runner builds each milestone: a builder does the tasks and ticks each task's checks.
6. A milestone merges when its checks pass. A check that only the owner can make waits for the owner's look.
7. The decision moves to Done when its milestones are merged. Problems found on the way come back as new cards.

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
  sprints/        the sprint grid and the milestone marks
  status/         the status command, the report, the progress reply
  queue/          cards and decisions
  decisions/      close or replace a decision
  run/            the runner session and the go
  migrate/        one folder per version step, each with a guide
```

## A release folder

```
.ai/plans/v0.<n>.x/<owner>/
  <release>-plan.md       goals, and one row per spec
  decisions.md            the decisions, as a board
  queue.md                every card raised, as a board
  process.md              the facts of this project
  plan/epics/E<n>.md      one epic: its decisions and specs
  plan/specs/NN-<slug>/   one spec, with its task files in tasks/
  run/trackers/           the run notes of each milestone
  run/handoffs/           notes for the next session
  status/sprints.md       the sprint grid, drawn from the status file
  status/data/status.json the status of everything
```

## The status words

Every epic, spec, milestone and task has one of five statuses: not started, in progress, blocked, done, skipped. A blocked or skipped item has a short reason. The statuses are kept in one file and set by one command, so no file has to be edited to change one.

## Starting in a new project

Run `/expedition discuss` in the project. On the first run the lead shows a suggested folder layout and asks one question about where the plans should be. After that it creates the first release folder and the conversation starts. `example/` shows what a release looks like once it is in work.

## After a skill update

Read `CHANGELOG.md` first: it says what is new and what a release in work has to do. When a release is in an older format, `scripts/status/report.py <release>` says so in its last line and names the migration folder. Each migration folder under `scripts/migrate/` has a guide with the commands, a way to check the result, a way to undo it, and a prompt to paste into the lead session.

## The status board data

A release in format 2.0 has the task board at `status/index.html`: open that file in a browser. It shows the epics, sprints, milestones and tasks with their statuses and reloads its data every 30 seconds. Its data is `status/data/status.data.js`, written from `status/data/status.json` on every status change. `reference/formats.md`, section Status, lists what the file holds.
