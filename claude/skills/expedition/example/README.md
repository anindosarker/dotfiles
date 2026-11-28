# Example release

`v1.0.x/owner/` is one small release as it sits under `.ai/plans/`: every kind of file a release has, with content that agrees from file to file. Read it before writing a file of that kind. The shape of each file alone is in [../templates/](../templates/).

- `process.md`: the project facts of this release, with its `updated` time.
- `v1.0.x-plan.md`: the release plan.
- `decisions.md` and `decisions/`: the four decisions of the release, `D57`, `D58`, `D61` and `D62`, one file each in `decisions/`, and `decisions.md` as their list that the scripts write. `scripts/migrate/v2.1-v2.2/format.py` moved them from the decisions board: each file has the lines of its card, all four (`D57`, `D58`, `D61` and `D62`) have `epic: E11`, and the round of each decision is in `status/data/status.json`. The `decider` line of each file was set after the move with `scripts/decisions/decider.py`, because the board does not say who made a call.
- `queue.md` and `queue/`: the queue items. `queue.md` is the list that the scripts write, one line per item file. Each item file `queue/Q<n>-<slug>.md` holds its status, its `## Notes` and, when it is closed, its `decider`. `Q41`, `Q42`, `Q48` and `Q49` are `done`, each with the decision it gave and the one who made the call (`you` or `lead`); `Q42` and `Q49` also have `## Details` and `## Options:` and the picked `option`; `Q41` and `Q48` show an item without them. `Q50` is `to-do`, and `Q51` is `blocked` with `depends_on: Q50`, which `queue/item.py --depends` set. The release is in format 2.2: `scripts/migrate/v2.1-v2.2/format.py` moved it from format 2.1, and the `decider` lines and the items `Q50` and `Q51` were added after it, because the files of format 2.1 do not say who made a call.
- `plan/epics/E11.md`: the epic that holds the four decisions and spec 27. Its front matter has `status` and `starts` only; the `## Ownership` table is the one list of its decisions and specs.
- `plan/specs/27-sidebar/`: the spec (four modules, six task pointers, four milestones) and its six task files in `tasks/`.
- `run/trackers/`: one tracker per milestone; the blocked one has its reason under `## Attention`.
- `status/data/status.json`: the store of every status, with the sprint of each milestone and its `launched` value. The grid is no file: `scripts/sprints/grid.py v1.0.x` prints it from the status file and writes nothing.
- A milestone is `done` only by its merge, which stores the merge commit. With every task done and no merge yet it stays `in progress`; it is `blocked` when no task is in work and one is blocked. A spec is counted from its milestones and its tasks together, an epic from its specs. `status.json` holds no machine path: `root` is only in the git-ignored `status.data.js`.

The model of a free body of a decision file is [v1.0.x/owner/decisions/D58-the-sidebar-has-a-collapse-shortcut.md](v1.0.x/owner/decisions/D58-the-sidebar-has-a-collapse-shortcut.md): a small table, then bullets, and a key as a nested bullet. Read it before the first decision file is written, then the list [v1.0.x/owner/decisions.md](v1.0.x/owner/decisions.md). The empty shapes are `templates/decision.md` and `templates/decisions-list.md`.

The scripts read this folder as a valid release: copy `v1.0.x/` under `.ai/plans/` of a scratch git repository to try a command on it.
