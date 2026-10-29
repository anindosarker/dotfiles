# Cycle files

## Layout

```
.ai/plans/v0.<n>.x/<owner>/
├── v0.<n>.x-plan.md        ← index: goals, parts table, dependency graph, integration, process rules
├── decisions.md            ← accepted decisions, D<n> items under round headings
├── findings.md             ← problems found in the code, F<n> items under round headings
├── NN-<slug>.md            ← one part, from the part template, linked from the index
├── NN-tracker.md           ← status, phase lines, staged attention items for that part
├── NN.M-<slug>.md          ← sub-part from triage, with NN.M-tracker.md
├── ATTENTION-<YYYY-MM-DD>.md ← A<n> items for the owner, written during the run
└── handoffs/               ← write-handoff output
```

Formats of each file: [formats.md](formats.md).

## Scripts

Run from inside the repo. They never overwrite an existing file.

| Script | Does |
|---|---|
| `python3 -I <skill>/scripts/new_cycle.py v0.<n>.x [--owner X]` | creates the cycle folder with the index, `decisions.md` and `findings.md` (from the templates, with a `## Round 1: discussion, <today>` heading), and `handoffs/` |
| `python3 -I <skill>/scripts/new_part.py v0.<n>.x NN <slug> "<Title>" "<scope>"` | creates the part file and its tracker (`Status: planned`), adds the row to the parts table in order |
| `python3 -I <skill>/scripts/find_rules.py [repo]` | read-only: prints project planning-rules paths, one per line, nothing if none |
| `python3 -I <skill>/scripts/status.py v0.<n>.x` | read-only: missing files, a state table per decision and finding, parts without tracker, `Status:` line or gates, phase headings without a `Lane:` line, possible open questions, untriaged ATTENTION items, inferred stage. First line names the planning rules in use |

`<skill>` is this skill's directory.

`status.py` checks only the part files linked from the index Parts table. Other `NN-*.md` files are listed as `supporting:` and not checked. Decision states: `unplanned` (no part cites it), `planned`, `running`, `done` (every citing part done), `deferred` (a `Deferred to` bullet), `superseded`, `unknown` (a citing tracker has no `Status:` line). Stage inference: discuss (no decisions), plan (no part files), triage (untriaged ATTENTION items), else run.

## Template

Precedence, highest first:

1. `--template PATH` on `new_part.py`.
2. Project planning rules, found by `find_rules.py`: files named like `*plan*guide*.md` or `planning*.md`, and `CLAUDE.md` or `AGENTS.md` lines that mention plan files. `new_part.py` writes a contract stub and prints each path. The project rules override the bundled guidelines completely: structure, headings, rules, template.
3. Bundled default, only when no project rules are found: [planning-guidelines.md](planning-guidelines.md), template [../templates/part.md](../templates/part.md).

The contract applies in all three: citations, a `Lane:` line under each phase heading (see [run.md](run.md)), gates per phase, no open questions. A project template that lacks one gets it added in that project's style.

## Conventions

- Citations: `(D7)` for a decision, `(F3)` for a finding, `(A2)` for an ATTENTION item, `(v0.4.x D9)` for a decision of another cycle. `status.py` also reads the older `(decision N)` form.
- Plan tables list `#`, `Part`, `Scope` only. No duration or size column.
- No questions in plan files. They stay in chat until answered.
- No em dashes in any cycle file.
