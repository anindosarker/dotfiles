# Stage 4: triage

Interactive with the owner. Input: an `ATTENTION-<YYYY-MM-DD>.md` file from stage 3.

## Steps

1. Run `python3 -I <skill>/scripts/status.py <cycle>` to list the untriaged ATTENTION items.
2. Go through the items one at a time. For each, give the facts and a recommendation. The owner gives feedback. Discuss in chat, not in the file.
3. Record a decision only when the owner accepts it. It goes in `decisions.md` under a new heading `## Round <n>: triage of ATTENTION-<YYYY-MM-DD>`. Numbering continues. Each decision ends with `- Source: A<n>`. Format: [formats.md](formats.md).
4. An item the owner accepts as it is still gets a short decision with its `Source:` line, so `status.py` sees it triaged.
5. Record bugs found during triage in `findings.md`, under the same round heading.
6. A decision that changes an earlier one supersedes it: mark the old heading `(superseded by D<n>)`.
7. Route each piece of follow-up work (rules below).
8. Back to stage 2 for the new parts: add each one with `scripts/new_part.py`, cite the decisions as `(D<n>)`, and run the readiness check again.
9. Handoff: only when the owner asks.

## Routing

| Follow-up | Goes to | Example |
|---|---|---|
| Minor: fits the current decisions, touches one area, can land before the next part | sub-part `NN.1`, `NN.2` of the current cycle, placed before the next dependent part | review fixes after part 04 and before release part 05 become `04.1` |
| Major: a new public API, re-decides an accepted decision, spans several parts, or needs its own release | a new cycle folder, made with `scripts/new_cycle.py` | a new feature area found during the run |

- In doubt: a new cycle. A sub-part that grows past the current decisions blocks the release.
- A decision moved to another cycle gets the bullet `- Deferred to v0.<n>.x`. That cycle's parts cite it as `(v0.<m>.x D<n>)`.
- Update the dependency graph in the plan index whenever a sub-part is added.
- A sub-part made only of small phases gets the `inline` or `agent` lane (see [run.md](run.md)).
