# Epic messages

## Epic ready

```Markdown
**Epic ready: E<n>**
- D<n>: <the decision's title, one plain line>
- D<n>: <the decision's title, one plain line>

**Decided, not in this epic:**                      optional: only when a decision waits
- D<n>: <the decision's title>. Waits for E<n>, same file.

**Say:**
- A. `compose`: plan.
- B. `compose delegate`: plan and start.
- C. `compose delegate with D<n>`: the same, with D<n> in it.     only with the optional block
```

## Epic planned

```Markdown
**Epic planned: E<n>**
- Spec <n> <name>: <what it builds, one plain line>
- Spec <n> <name>: <what it builds, one plain line>

**Say:**
- A. `delegate`: start.
```
