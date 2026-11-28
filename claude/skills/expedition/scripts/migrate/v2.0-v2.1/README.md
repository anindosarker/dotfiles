# Migration v2.0 to v2.1

Moves the queue of one release from the kanban board `queue.md` to one file per item, `queue/Q<n>-<slug>.md`, and makes `queue.md` a plain list of those files.

## Who needs it

A release whose `status/data/status.json` says `"format": "2.0"`. A release in format `1.0` runs [../v1.0-v2.0/README.md](../v1.0-v2.0/README.md) first. A release that stays in format 2.0 keeps working: every script reads its board as before.

## What changes for you

- Each card is now a file: front matter (`status`, `decision`), the title `# Q<n>. <title>`, and its bullets under `## Notes`. The lead adds `## Details` and `## Options:` when it writes an item out.
- `queue.md` is a list that the scripts write. Do not edit it by hand, and do not drag cards in it any more.
- The task board (`status/index.html`) shows the queue in its Queue view.
- The commands stay the same: `queue/item.py`, `queue/list.py`, `queue/next.py`. They now write and read the item files.

## What stays

- `decisions.md`, the specs, the task files, the trackers and every status.
- Every line of every card: each bullet goes under `## Notes` at the same depth.
- Only the tick and the `#E<n>` tag of a card are dropped. The scripts read both from `decisions.md`.
- A `#D<n>` tag stays only on a card in Decided, as `decision: D<n>`. A `#D<n>` tag of a card in another lane, and the lower tag of a card with two, are dropped. The command prints one line for each, so you can add it back by hand.

## Before you start

- `queue.md` and `status/data/status.json` have no uncommitted change.
- The release has no `queue/` folder.

## The commands

`<skill>` is the skill's folder. Run from the project folder.

```
python3 -I <skill>/scripts/migrate/v2.0-v2.1/format.py <release> --check
python3 -I <skill>/scripts/migrate/v2.0-v2.1/format.py <release>
```

The first line, on stderr, tells the session to read the skill again. `--check` prints one line per item file and the counts, and writes nothing. The run writes the item files, the list, `"format": "2.1"` in `status/data/status.json`, the page data, and makes one commit: `docs(plan): <release> queue moved to item files`.

The command refuses, and writes nothing, when the release is not in format 2.0, when `queue.md` or `status/data/status.json` has uncommitted changes, when `queue/` exists (a second run), or when a line of `queue.md` is in no card. Move such a line into a card or remove it, commit, and run again.

## How to check it worked

- The command prints the counts: cards read and item files written, bullets read and bullets written. They are equal, or it commits nothing and names each card whose bullets differ. The usual cause is a line that starts with `## ` under the card: it ends `## Notes`. Change that line, commit, and run again.
- `python3 -I <skill>/scripts/status/report.py <release>` exits 0, and its `Queue:` line counts as many items as there were cards.

## How to undo it

It is one commit in the repository that holds the plan folder: `git revert <that commit>`. If a run stops before its commit, run `git checkout -- queue.md status/data/status.json` and remove `queue/` in the release folder.

## Prompt for a lead session

```
The expedition skill keeps the queue in item files from format 2.1. Read its CHANGELOG.md and scripts/migrate/v2.0-v2.1/README.md, then re-read SKILL.md whole.
For release <release>: run migrate/v2.0-v2.1/format.py <release> --check, read its lines, then run it without --check. Then run status/report.py <release>.
Do not stop, replace or restart any session or Workflow for this.
Report in under five lines.
```
