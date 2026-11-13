# Stage 4: triage

Folded into stage 1: the run's cards in `queue.md` are queue cards like any other, read when the runner sends DONE or BLOCKED.

## Steps

1. Run `python3 -I <skill>/scripts/queue/next.py <release>` for the first card in Open.
2. Settle every card that is not a real choice first, without the owner (decision with its `Source:` line, follow-up routed, spec or process text fixed inline). Then go through the real choices one at a time. For each, give the facts and a recommendation. Use the item format from SKILL.md stage 1 (`# Q<n>.` title sentence, bullets, `## Options:` with the recommended option first); the next item only after the owner rules on this one. The owner gives feedback. Discuss in chat, not in the file.
3. Record a decision only when the owner accepts it, with `queue/item.py <release> D "<title>" --source Q<n>`. The first decision of the triage adds `--new-round`, so it and the rest of the triage carry the next `#R<n>` in `decisions.md`. Numbering continues. Each decision ends with `- Source: Q<n>`, and the card moves to Decided. A deferral moves it to Later, a rejection to Dropped (`queue/item.py <release> --move Q<n> Later|Dropped`). Format: [formats.md](formats.md).
4. A card the owner accepts as it is still gets a short decision with its `Source:` line, so the card is decided.
5. File bugs found during triage in `queue.md` (`queue/item.py <release> Q`).
6. A decision that changes an earlier one: SKILL.md, Changing a decision.
7. Route each piece of follow-up work (rules below).
8. The new decisions join the next epic (SKILL.md, Epics): the spec writer (a forked session) writes their specs.
9. Handoff: only when the owner asks.

## Routing

| Follow-up | Goes to | Example |
|---|---|---|
| Minor: fits the current decisions, touches one area, can land before the next spec | follow-up spec `NN.1`, `NN.2` of the current release, placed before the next dependent spec | review fixes after spec 04 and before release spec 05 become `04.1` |
| Major: a new public API, re-decides an accepted decision, spans several specs, or needs its own release | a new release folder, made with `scripts/plan/new_cycle.py` | a new feature area found during the run |

- In doubt: a new release. A follow-up spec that grows past the current decisions blocks the release.
- A decision moved to another release gets the bullet `- Deferred to v0.<n>.x`. That release's specs cite it as `(v0.<m>.x D<n>)`.
- `plan/new_spec.py` adds the Specs row; the follow-up spec's milestones get their column from `lib/ownership.py` and their grid rows from `sprints/refresh.py`. A fix found while an epic runs needs no decision and goes through `plan/new_fix.py` (SKILL.md, stage 3).
- A follow-up spec's milestones run as their own milestones in the column `lib/ownership.py` gives them, with their own Workflow, or as a single Agent when nothing follows ([run.md](run.md), Orchestration).
