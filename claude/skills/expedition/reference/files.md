# Cycle files

## Layout

```
.ai/plans/v0.<n>.x/<owner>/
├── v0.<n>.x-plan.md        ← index: goals, parts table, dependency graph, integration, process rules
├── decisions.md            ← accepted decisions only, numbered
├── findings.md             ← problems found in the code, problem files only
├── NN-<slug>.md            ← one part, from the part template
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
| `python3 -I <skill>/scripts/find_rules.py [repo]` | read-only: prints project planning-rules paths, one per line, nothing if none |
| `python3 -I <skill>/scripts/status.py v0.<n>.x` | read-only: missing files, uncited decisions, parts without tracker or gates, phase headings without a `Lane:` line, possible open questions, untagged or untriaged ATTENTION bullets, inferred stage. First line names the planning rules in use |

`<skill>` is this skill's directory.

## Template

Precedence, highest first:

1. `--template PATH` on `new_part.py`.
2. Project planning rules, found by `find_rules.py`: files named like `*plan*guide*.md` or `planning*.md`, and `CLAUDE.md` or `AGENTS.md` lines that mention plan files. `new_part.py` writes a contract stub and prints each path. The project rules override the bundled guidelines completely: structure, headings, rules, template.
3. Bundled default, only when no project rules are found: [planning-guidelines.md](planning-guidelines.md), template [../templates/part.md](../templates/part.md).

The contract applies in all three: decision citations, a `Lane:` line under each phase heading (see [run.md](run.md)), gates per phase, no open questions. A project template that lacks one gets it added in that project's style.

## Conventions

- Decisions are cited by number: `(decision 7)`, triage rulings as `(ruling 3)`. `status.py` reads these two forms.
- Plan tables list `#`, `Part`, `Scope` only. No duration or size column.
- No questions in plan files. They stay in chat until answered.
- No em dashes in any cycle file.
