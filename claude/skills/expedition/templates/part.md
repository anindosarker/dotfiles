# NN: [title]

## 1. Overview
[Problem and why this part exists, 2 or 3 sentences. Cite decisions as (decision N).]

## 2. Goals
- [Measurable outcome (decision N)]

## 3. Target structure
[Tree of files after this part, one-line purpose each. `: none` if nothing structural.]

## 4. Components
### 4.1 [Component]
- Does [x]
- Does NOT do [y]
[Interfaces or usage only when they pin a decision.]

## 5. Phases
### 5.1 Phase 01: [name]
Lane: [workflow | agent | inline]
- [Step]
- Gates: `[command]`, [what green means]

### 5.N Final phase: Cleanup
Lane: [workflow | agent | inline]
- Delete old code, update references
- Gates: [repo gates]

## 6. Gates
- `[command]`, [what green means]
