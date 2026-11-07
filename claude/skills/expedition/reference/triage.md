# Stage 4: triage

Interactive with the owner. Input: an `attentions/ATTENTION-<YYYY-MM-DD>.md` file from stage 3.

## Steps

1. Run `python3 -I <skill>/scripts/status.py <release>` to list the untriaged ATTENTION items.
2. Settle every item that is not a real choice first, without the owner (decision with its `Source:` line, follow-up routed, epic or process text fixed inline). Then go through the real choices one at a time. For each, give the facts and a recommendation. Use the item format from SKILL.md stage 1 (title sentence, bullets, `## Options:` with the recommended option first); the next item only after the owner rules on this one. The owner gives feedback. Discuss in chat, not in the file.
3. Record a decision only when the owner accepts it. It goes in `decisions.md` under a new heading `## Round <n>: triage of ATTENTION-<YYYY-MM-DD>`. Numbering continues. Each decision ends with `- Source: A<n>`. Format: [formats.md](formats.md).
4. An item the owner accepts as it is still gets a short decision with its `Source:` line, so `status.py` sees it triaged.
5. Record bugs found during triage in `findings.md`, under the same round heading.
6. A decision that changes an earlier one supersedes it: mark the old heading `(superseded by D<n>)`.
7. Route each piece of follow-up work (rules below).
8. Back to stage 2 for the new epics: add each one with `scripts/new_epic.py` (a fix with no epic: `scripts/new_fix.py`), cite the decisions as `(D<n>)`, run `ownership.py` and `sprints.py`, and run the readiness check again.
9. Handoff: only when the owner asks.

## Routing

| Follow-up | Goes to | Example |
|---|---|---|
| Minor: fits the current decisions, touches one area, can land before the next epic | follow-up epic `NN.1`, `NN.2` of the current release, placed before the next dependent epic; or a fix milestone when no epic is needed | review fixes after epic 04 and before release epic 05 become `04.1` |
| Major: a new public API, re-decides an accepted decision, spans several epics, or needs its own release | a new release folder, made with `scripts/new_cycle.py` | a new feature area found during the run |

- In doubt: a new release. A follow-up epic that grows past the current decisions blocks the release.
- A decision moved to another release gets the bullet `- Deferred to v0.<n>.x`. That release's epics cite it as `(v0.<m>.x D<n>)`.
- `new_epic.py` adds the Epics row; the follow-up epic's milestones get their `ownership.md` rows from `ownership.py` and their grid rows from `sprints.py` (ticks survive). A fix milestone gets its tracker and its grid row in the running sprint column from `new_fix.py`.
- A follow-up epic's milestones run as their own milestones in the column `ownership.py` gives them, with their own Workflow, or as a single Agent when nothing follows ([run.md](run.md), Orchestration).
