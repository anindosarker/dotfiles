# Planning Guidelines

How to write an implementation plan for this repository. Applies to humans and agents.

## Location

```
.ai/plans/<name>/<git_username>/
├── <name>-plan/
│   ├── <name>-plan.md   ← the plan file, in a folder of the same name
│   └── tasks/           ← optional: one file per task that has its own plan
└── reference/           ← optional supporting material
```

Every plan sits in a folder named like its file, short or big, so there is one shape. Anything
else that belongs to the plan (a sketch, a capture) goes in the same folder.

`<git_username>` is the output of `git config user.name`. Any other file in the folder belongs
to the workflow or tool that runs the plan and is not described here. This doc says how to
write one plan file (template below).

## Rules

1. **Discuss before writing.** Agree scope in chat first. The plan implements what was agreed
   and never re-decides.
2. **Draft during the discussion** for anything non-trivial, so both sides argue against the
   same text.
3. **No questions in plan files.** Open items are asked in chat.
4. **Structure over prose.** Tables, trees, bullets. Short prose only for a module intro.
5. **Mermaid for flows, ASCII trees for structure.** No hand-drawn box diagrams. Sketches
   made with Excalidraw go in `reference/` as `.excalidraw`, linked from the section they
   illustrate.
6. **No marketing prose.** Plain section names, direct descriptions, exact technical terms.
7. **Status on every operation**: `new`, `keep` or `refactor`. A stub is `new` with "stub,
   implement in task 2.1.N".
8. **Pin what stays unchanged.** Every module lists what it touches but does not modify.
9. **Design in, implementation out.** Include data models and fields, interfaces, types,
   constants, file shapes, usage examples. Never method bodies or algorithm walkthroughs.
   Test: a decision goes in; how to do it stays in the code.
10. **Cleanup task always last.** Delete old code, update references, run the project's checks.
11. **Checks per task.** Each task names the commands that must pass. The commands are the
    project's checks as listed in `docs/code-of-conduct/coding-standards.md`.
12. **No em dashes.** Use a comma, a colon or a new sentence.
13. **Dependency edges need a reason.** A milestone depends on another only through a listed
    dependency or a shared file. With no `Depends on` line, the milestones of a plan are built
    in the order listed.
14. **Tasks are defined once, milestones only organise.** Section 2.1 defines each task; a
    milestone in 2.2 lists the ids of its tasks. A milestone is the unit that is built, merged
    and has a status.
15. **Suggestions, not rules.** Written when it helps, left out when it does not, in both
    types: `Files owned` on a milestone (when it could clash with other work in progress),
    `Depends on` on a milestone (when the order matters), a task file, and the sections of a
    task file.
16. **No status in the plan file.** A milestone's status is kept by the workflow or tool that
    runs the plan. A task's status is the `status` line of its task file, when it has one.

## Types

The front matter of a plan file names its type. No front matter means `structured`.

| Type | What it is | Section 1 | A task points to |
| --- | --- | --- | --- |
| `structured` | A scoped piece of work, planned in full before it is built | The full architecture | A section of the same file, `Detail: 1.6.1` |
| `iterative` | One area that gets feedback item after item; it stays open until its owner closes it | A short scope | Its own task file, `Plan: tasks/03-<slug>.md` |

In an `iterative` plan each feedback item is a task, and a milestone is one round of feedback
that stays open while tasks are added. A `structured` plan may use task files too.

## Template

Numbering is strict: every heading under `## 1.` and `## 2.` carries its dotted number. A task
is `#### 2.1.3 Task: <title>`, a milestone `#### 2.2.1 Milestone: <name>`. The section number is
the id: task `2.1.3`, milestone `2.2.1`. A number is never reused. A milestone is still named
by its plain name where another milestone depends on it.
A skipped optional section keeps its heading with `: none` after the name, so numbers stay
stable and no reader guesses at a gap.

````markdown
---
type: structured
---
# [Feature name] plan

## 1. Architecture

### 1.1 Overview

Two or three sentences: the problem and why this plan exists. Link the decision.

### 1.2 Goals

- Measurable outcome
- Measurable outcome
- Acceptance: the one check the builder runs itself and loops on, programmatic (`tsc`, a grep, a `diff` against a baseline, a test)

### 1.3 Current structure _(optional, skip for greenfield)_

```
path/today/
├── file-a.ts
└── file-b.ts
```

### 1.4 Target structure

```
path/after/
├── file-a.ts        ← one-line purpose
└── sub/
    └── file-c.ts    ← one-line purpose
```

### 1.5 Flow _(optional, for dispatch, state machines, cross-service flows)_

```mermaid
sequenceDiagram
  Caller->>Service: call()
  Service->>Store: persist
```

Sketch: [reference/flow.excalidraw](reference/flow.excalidraw) _(when one exists)_

### 1.6 Modules

A module in a plan is one unit of the design, which may be a NestJS module, a set of pages,
a job or a shared helper. One block per module the plan introduces or modifies, grouped by
logical unit, not by file. Required: a short description and a bullet list of what it does
and does not do. Optional: operations table, interfaces, dependencies, stays unchanged,
usage examples.

#### 1.6.1 Data artifacts _(optional, always first when present)_

Data models and fields, stored enums, config files, generated files: what changes in them.
One entry per data model, with every field.

| Field       | Type   | Notes                                   |
| ----------- | ------ | --------------------------------------- |
| `id`        | string | key                                     |
| `expiresAt` | date   | set on create, default 30 days, indexed |

#### 1.6.2 [Module]

Description and the scope decisions that shaped it.

- Does X
- Does NOT do Y

**Operations:**

| Operation | Status | Notes |
| --------- | ------ | ----- |
| `doX()`   | new    |       |

**Interfaces:**

```typescript
export interface Example {
  readonly id: string;
}
```

**Stays unchanged:** files this module touches without modifying.

**Usage:** one example per distinct caller pattern.

```typescript
example.doX({ id });
```

### 1.7 Dependencies and env _(optional)_

New packages, env vars (name, default, purpose), reused infrastructure.

## 2. Instructions for AI

### 2.1 Tasks

One entry per task: a line of what it is, its checks, and a pointer to its detail (`Detail:` a
section of this file, or `Plan:` a task file).

#### 2.1.1 Task: [what]
- [One line of what it is.]
- Checks: [commands]
- Detail: 1.6.2

#### 2.1.2 Task: Cleanup, delete old code, update references
- Checks: the project's checks

### 2.2 Milestones

One block per milestone. A milestone is a named group of tasks that is built and checked as
one piece of work.

#### 2.2.1 Milestone: [Name]
- Tasks: 2.1.1, 2.1.2
- Files owned: [a, b]
- Depends on: [milestone names, or none]

### 2.3 Checks

- `command`, what green means
````

## Example

Minimal shape:

````markdown
# Notification module plan

## 1. Architecture

### 1.1 Overview

Notifications are sent from the `auth`, `payment` and `payroll` modules, each with its own
email sender. Decision: one `notification` module with pluggable channels.

### 1.2 Goals

- One entry point for all outbound notifications
- Email and SMS channels behind one interface
- Acceptance: a grep finds no direct email sender call outside `notification/`

### 1.3 Current structure

```
auth/auth-email.sender.ts
payment/payment-email.sender.ts
payroll/payroll-email.sender.ts
```

### 1.4 Target structure

```
notification/
├── notification.service.ts      ← public API, send(channel, payload)
└── channels/
    ├── email.channel.ts         ← email provider wrapper
    └── sms.channel.ts           ← SMS provider wrapper (stub)
```

### 1.5 Flow: none

### 1.6 Modules

#### 1.6.1 Data artifacts: none

#### 1.6.2 NotificationService

Single entry point other modules call to send notifications. Owns dispatch only.

- Dispatches a send request to the right channel
- Does NOT handle retries, the job queue does

**Operations:**

| Operation | Status | Notes            |
| --------- | ------ | ---------------- |
| `send()`  | new    | Main entry point |

**Interfaces:**

```typescript
export interface NotificationChannel {
  readonly name: 'email' | 'sms';
  deliver(payload: NotificationPayload): Promise<void>;
}
```

**Stays unchanged:** subject lines, recipients, the job queue setup.

**Usage:**

```typescript
await notificationService.send('email', { to, subject, body });
```

### 1.7 Dependencies and env: none

## 2. Instructions for AI

### 2.1 Tasks

#### 2.1.1 Task: Create `NotificationService` and the email channel
- Checks: type check
- Detail: 1.6.2

#### 2.1.2 Task: Add the SMS channel as a stub
- Checks: type check, unit tests
- Detail: 1.6.2

#### 2.1.3 Task: Point `auth`, `payment` and `payroll` at `send()`
- Checks: type check, unit tests

#### 2.1.4 Task: Cleanup, delete the three old senders, update imports
- Checks: the project's checks

### 2.2 Milestones

#### 2.2.1 Milestone: Notification core
- Tasks: 2.1.1, 2.1.2
- Files owned: `notification/notification.service.ts`, `notification/channels/email.channel.ts`, `notification/channels/sms.channel.ts`

#### 2.2.2 Milestone: Move callers
- Tasks: 2.1.3, 2.1.4
- Files owned: `auth/auth-email.sender.ts`, `payment/payment-email.sender.ts`, `payroll/payroll-email.sender.ts`
- Depends on: Notification core

### 2.3 Checks

- The project's checks as listed in `docs/code-of-conduct/coding-standards.md`, all green
- A grep for the email provider client outside `notification/`, no match
````

## Task file

A task gets its own file, `tasks/NN-<slug>.md` in the plan's folder, when it arrives on its own
or needs its own plan. `NN` is the last part of the task's id. A small task uses two of the
four sections.

````markdown
---
task: 2.1.3
status: not started
type: feat
decision: [the decision it implements, when there is one]
---
# [Task title]

## Description

> [The remark or request that started the task, quoted.]

## Requirements

- [What must hold when the task is done.]

## Plan

- [Where the change goes and how.]

## Result

Written when the task is done: the commit, the checks that ran, anything to look at.
````

`status` is one of `not started`, `in progress`, `blocked`, `done`; a blocked task adds the
line `blocked: <reason>`. A tool, not a person, may maintain these two lines.
