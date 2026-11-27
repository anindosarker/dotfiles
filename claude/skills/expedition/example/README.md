# Example release

`v1.0.x/owner/` is one small release as it sits under `.ai/plans/`: every kind of file a release has, with content that agrees from file to file. Read it before writing a file of that kind. The shape of each file alone is in [../templates/](../templates/).

- `process.md`: the project facts of this release, with its `updated` time.
- `v1.0.x-plan.md`, `decisions.md`, `queue.md`: the release plan, four decisions and the cards they came from.
- `plan/epics/E11.md`: the epic that holds the four decisions and spec 27.
- `plan/specs/27-sidebar/`: the spec (four modules, six task pointers, four milestones) and its six task files in `tasks/`.
- `run/trackers/`: one tracker per milestone; the blocked one has its reason under `## Attention`.
- `status/data/status.json`: the store of every status; `status/sprints.md` is drawn from it.

The scripts read this folder as a valid release: copy `v1.0.x/` under `.ai/plans/` of a scratch git repository to try a command on it.
