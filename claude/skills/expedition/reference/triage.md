# Stage 4: triage

Folded into stage 1: the run's cards in `queue.md` are queue cards like any other, read when the runner sends DONE or BLOCKED.

## Steps

1. Run `python3 -I <skill>/scripts/queue/next.py <release>` for the first card in Open.
2. Run the screen ([discuss.md](discuss.md), Screen) on every card. Settle every card that is not a real choice first, without the owner (decision with its `Source:` line, follow-up routed, spec or process text fixed inline, or the Lead-side close). Post the settled list ([formats.md](formats.md), Settled list). Then go through the real choices one at a time. For each, give the facts and a recommendation. Use the item format from [discuss.md](discuss.md), Item format (`# Q<n>.` title sentence, bullets, `## Options:` with the recommended option first); the next item only after the explicit word on this one. The owner gives feedback. Discuss in chat, not in the file.
3. Record a decision only on the explicit word (SKILL.md, Explicit word), with `queue/item.py <release> D "<title>" --source Q<n>`. The first decision of the triage adds `--new-round`, so it and the rest of the triage carry the next `#R<n>` in `decisions.md`. Numbering continues. Each decision ends with `- Source: Q<n>`, and the card moves to Decided. "later" moves it to Later, "drop it" to Dropped (`queue/item.py <release> --move Q<n> Later|Dropped`). Format: [formats.md](formats.md).
4. A card the owner takes as it is still gets a short decision with its `Source:` line, on the explicit word, so the card is decided.
5. File bugs found during triage in `queue.md` (`queue/item.py <release> Q`).
6. A decision that changes an earlier one: [discuss.md](discuss.md), Changing a decision.
7. Route each piece of follow-up work (rules below).
8. The new decisions join the next epic ([discuss.md](discuss.md), Epics): the spec writer writes their specs.
9. Handoff: only when the owner asks.

## Routing

| Follow-up | Goes to | Example |
|---|---|---|
| Minor: fits the current decisions, touches one area, can land before the next spec | a new module, task and milestone in the spec it follows while that spec is not done, `plan/milestone.py add <release> <spec> "<Name>" --decision D<n>`; a new spec when it is done | review fixes after spec 04 and before release spec 05 become a milestone of spec 04 |
| Major: a new public API, re-decides an accepted decision, spans several specs, or needs its own release | a new release folder, made with `scripts/plan/new_release.py` | a new feature area found during the run |

- In doubt: a new release. Follow-up work that grows past the current decisions blocks the release.
- A decision moved to another release gets the bullet `- Deferred to v0.<n>.x`. That release's specs cite it as `(v0.<m>.x D<n>)`.
- `plan/milestone.py add` writes the module, the task files and the milestone into the spec, with the current sprint as its start; its grid row comes from the same call. A fix found while an epic runs needs no decision and goes through the same command without `--decision` ([run.md](run.md), Milestones and sprints); on a done spec that makes the follow-up spec `NN.M` in a running epic.
- A follow-up milestone runs as its own milestone in the sprint `lib/ownership.py` gives it, as one agent or as a Workflow, by the runner's judgment ([run.md](run.md), Orchestration).
