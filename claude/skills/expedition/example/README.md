# Example release

`v1.0.x/owner/` is one small release as it sits under `.ai/plans/`: every kind of file a release has, with content that agrees from file to file. Read it before writing a file of that kind. The shape of each file alone is in [../templates/](../templates/).

- `process.md`: the project facts of this release, with its `updated` time.
- `v1.0.x-plan.md`, `decisions.md`: the release plan and four decisions.
- `queue.md` and `queue/`: the queue items the four decisions came from. `queue.md` is the list that the scripts write, one line per item file. Each item file `queue/Q<n>-<slug>.md` holds its status, its decision and its `## Notes`; `Q42` and `Q49` also have `## Details` and `## Options:`, and `Q42` has the picked `option`. The release is in format 2.1: `scripts/migrate/v2.0-v2.1/format.py` made the list and the item files from the cards of format 2.0.
- `plan/epics/E11.md`: the epic that holds the four decisions and spec 27.
- `plan/specs/27-sidebar/`: the spec (four modules, six task pointers, four milestones) and its six task files in `tasks/`.
- `run/trackers/`: one tracker per milestone; the blocked one has its reason under `## Attention`.
- `status/data/status.json`: the store of every status; `status/sprints.md` is drawn from it.
- A milestone is `done` only by its merge, which stores the merge commit. With every task done and no merge yet it stays `in progress`; it is `blocked` when no task is in work and one is blocked. A spec is counted from its milestones and its tasks together, an epic from its specs. `status.json` holds no machine path: `root` is only in the git-ignored `status.data.js`.

The scripts read this folder as a valid release: copy `v1.0.x/` under `.ai/plans/` of a scratch git repository to try a command on it.
