# Cycle files

## Layout

```
.ai/plans/v0.<n>.x/<owner>/
├── v0.<n>.x-plan.md        ← index: goals, parts table, dependency graph, integration, process rules
├── decisions.md            ← accepted decisions only, numbered
├── findings.md             ← problems found in the code, problem files only
├── NN-<slug>.md            ← one part, from the planning template
├── NN-tracker.md           ← deviations and run decisions for that part
├── NN.M-<slug>.md          ← sub-part from triage, with NN.M-tracker.md
├── ATTENTION-<YYYY-MM-DD>.md
├── decisions-review.md     ← triage rulings, numbered
├── findings-review.md      ← bugs found during triage
└── handoffs/               ← write-handoff output
```

## Scripts

Run from inside the repo. They never overwrite an existing file.

| Script | Does |
|---|---|
| `python3 -I <skill>/scripts/new_cycle.py v0.<n>.x [--owner X]` | creates the cycle folder with the index, decisions and findings stubs, and `handoffs/` |
| `python3 -I <skill>/scripts/new_part.py v0.<n>.x NN <slug> "<Title>" "<scope>"` | creates the part file and its tracker, adds the row to the parts table in order |
| `python3 -I <skill>/scripts/status.py v0.<n>.x` | read-only: missing files, uncited decisions, parts without tracker or gates, possible open questions, untagged or untriaged ATTENTION bullets, inferred stage |

`<skill>` is this skill's directory.

## Template

`new_part.py` takes the part template from the fenced block under `## Template` in the project's `docs/code-of-conduct/planning-guidelines.md`. A project without that file uses [../templates/part.md](../templates/part.md).

Every phase heading in a part file is followed by a `Lane:` line (see [run.md](run.md)).

## Conventions

- Decisions are cited by number: `(decision 7)`, triage rulings as `(ruling 3)`. `status.py` reads these two forms.
- Plan tables list `#`, `Part`, `Scope` only. No duration or size column.
- No questions in plan files. They stay in chat until answered.
- No em dashes in any cycle file.
