# [Part name]

## 1. Architecture

### 1.1 Overview

Two or three sentences: the problem and why this part exists. Link the decision.

### 1.2 Goals

- Measurable outcome
- Measurable outcome

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

### 1.6 Components

One block per logical unit the part introduces or modifies. Required: a short description
and a bullet list of what it does and does not do. Optional: operations table, interfaces,
dependencies, stays unchanged, usage examples.

#### 1.6.1 Data artifacts _(optional, always first when present)_

Registry items, config files, generated files, changelog entries: what changes in them.

#### 1.6.2 [Component]

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

**Stays unchanged:** files this component touches without modifying.

**Usage:**

```typescript
example.doX({ id });
```

### 1.7 Dependencies and env _(optional)_

New packages, env vars (name, default, purpose), reused infrastructure.

## 2. Instructions for AI

### 2.1 Phases

#### 2.1.1 Phase 1: [Name]

Lane: [workflow | agent | inline]

- Step
- Step

#### 2.1.N Final phase: Cleanup

Lane: [workflow | agent | inline]

- Delete old code, update references
- Repo gates

### 2.2 Gates

- `command` per base, what green means
