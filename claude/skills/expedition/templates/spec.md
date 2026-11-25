# [Spec name]

## 1. Architecture

### 1.1 Overview

Two or three sentences: the problem and why this spec exists. Cite the decision, as (D<n>).

### 1.2 Goals

- Measurable outcome
- Measurable outcome
- Acceptance: the one check the builder runs itself and loops on, programmatic (a type check, a grep, a `diff` against a baseline, a test) or a reference plus judges (captures next to a named reference, three judges on named points)

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

A module in a spec is one unit of the design. One block per module the spec introduces or
modifies, grouped by logical unit, not by file. Required: a short description and a bullet
list of what it does and does not do. Optional: operations table, interfaces, dependencies,
stays unchanged, usage examples.

#### 1.6.1 Data artifacts _(optional, always first when present)_

Data models and fields, stored enums, config files, generated files: what changes in them.
One entry per data model, with every field.

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

### 2.1 Milestones

One block per milestone. A milestone is one branch, one worktree, one tracker and one merge.

### Milestone: [Name]

- Files owned: [a, b]
- Depends on: [milestone names or spec numbers, or none]
- Review: [none | fable]
- Local CI: [none | `pnpm test --changed` | `act pull_request -j <job>`] (what runs on the merged tree before the merge, beyond the task checks)
- Task 1: [what]. Checks: [commands]
- Task 2: [what]. Checks: [commands]
- Task N: Cleanup, delete old code, update references. Checks: the project's checks

### 2.2 Checks

- `command` per base, what green means
