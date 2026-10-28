# Stage 4: triage

Interactive with the owner. Input: an `ATTENTION-<YYYY-MM-DD>.md` file from stage 3.

## Steps

1. Run `python3 -I <skill>/scripts/status.py <cycle>` to list untriaged ATTENTION files.
2. Go through the file one bullet at a time. For each bullet, give the facts and a recommendation. The owner rules. Discuss in chat, not in the file.
3. Record each ruling in `decisions-review.md` as a numbered item. Continue the numbering from earlier triage rounds. Link the ATTENTION file at the top.
4. Record bugs found during triage in `findings-review.md`.
5. Route each piece of follow-up work (rules below).
6. Back to stage 2 for the new parts: add each one with `scripts/new_part.py`, cite the rulings as `(ruling N)`, and run the readiness check again.
7. End: invoke the `write-handoff` skill.

## Routing

| Follow-up | Goes to | Example |
|---|---|---|
| Minor: fits the current decisions, touches one area, can land before the next part | sub-part `NN.1`, `NN.2` of the current cycle, placed before the next dependent part | review fixes after part 04 and before release part 05 become `04.1` |
| Major: a new public API, re-decides an accepted decision, spans several parts, or needs its own release | a new cycle folder, made with `scripts/new_cycle.py` | a new feature area found during the run |

- In doubt: a new cycle. A sub-part that grows past the current decisions blocks the release.
- Update the dependency graph in the plan index whenever a sub-part is added.
- A sub-part made only of small phases gets the `inline` or `agent` lane (see [run.md](run.md)).
