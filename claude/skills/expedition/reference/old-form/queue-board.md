# The queue board, for a release of format 2.0 or 1.0

A release whose `status/data/status.json` says `"format": "2.0"`, or that has no status file (format 1.0), keeps its queue as this board. A release of format 2.1 keeps one item file per item and a list `queue.md` instead: [../formats.md](../formats.md), queue.md and Item file. To move a release of format 2.0 to item files: [../../scripts/migrate/v2.0-v2.1/README.md](../../scripts/migrate/v2.0-v2.1/README.md). The section below is the `queue.md` section of `formats.md` of format 2.0, with its links set for this folder.

## queue.md

One file per release, in the release folder root, template [../../templates/queue.md](../../templates/queue.md): a kanban board in the obsidian-kanban Markdown format, which the owner may view and drag in the VS Code extension Unified Kanban. It holds every card filed in the release: every owner remark, and every other item that passes the bar at filing, filed in the turn it is raised. The Open lane is the queue; the other lanes are the history.

```md
---
kanban-plugin: basic
---

## Open

- [ ] **Q30** Home title is too technical
- [ ] **Q31** Sidebar link does not match the theme
	- `components/sidebar.tsx:88`: the link uses the default colour, not the muted one.

## Decided

- [ ] **Q21** Change the button color #D85
- [ ] **Q23** Example intros in the short style #D83
	- One or two plain sentences per example, no option names.
- [x] **Q15** Comparison page moves to the end of Getting Started #D71 #E12
- [x] **Q5** Process file audited #D40

## Later

- [ ] **Q7** Row pinning drops hand-pinned rows on unselect all
	- `features/stRowPinning.ts:42`.

## Dropped

## Autofix

- [x] **Q9** Typo in the pinning guide

%% kanban:settings
{"kanban-plugin":"basic","lane-width":300,"date-format":"YYYY-MM-DD","time-format":"HH:mm","tag-action":"kanban"}
%%
```

- Sessions change the file only through the scripts: `queue/item.py` (`Q`, `D --source`, `--move`, `--fact`), `plan/milestone.py` (a cited card to Autofix), and the tag sync in `epics/tag.py` and `sprints/refresh.py`. They re-read it inside the lock, find a card by its `**Q<n>**` token and its lane by the `## ` heading above it, and leave every other byte as found, the `%% kanban:settings` block included. The extension may drop the frontmatter when it saves its settings; the next script write puts it back.
- Five lanes, always all present, in this order. The lane is the card's state:

  | Lane | Meaning |
  |---|---|
  | Open | Waiting to be discussed |
  | Decided | Decided; `#D<n>` names the decision |
  | Later | Parked; reopened by moving it back to Open |
  | Dropped | Will not be done |
  | Autofix | Fixed without a decision |

- A card is one top-level list item: `- [ ] **Q<n>** <title>`, then its tags. The title is a plain sentence naming the problem or idea. Two tags exist, at the end of the title line, space separated, decision before epic:

  | Tag | Meaning |
  |---|---|
  | `#D<n>` | The decision that settled the card |
  | `#E<n>` | The epic that decision is in |

  An open card usually has no tag. No other tag is written, and never a sub-bullet that holds only tags.
- **Bar at filing.** A card's first fact line says what goes wrong for a user of the library or a reader of the docs if the card is ignored. A raiser (the lead, a lookup, the runner, a builder, a verifier) that cannot say it files no card: it writes the point in its tracker's `## Notes`, or leaves it out when it has no tracker. The owner's remarks are exempt: every one is filed.
- The checkbox:

  | Lane | Box | Meaning |
  |---|---|---|
  | Open, Later | `[ ]` | Not decided |
  | Decided | `[ ]` | Ready for an epic: the decision is in To do |
  | Decided | `[x]` with `#E<n>` | In an epic: the decision is In progress |
  | Decided | `[x]`, no `#E` tag | Closed: the decision is Done (merged, nothing to run, superseded or deferred) |
  | Dropped, Autofix | `[x]` | Closed |

  `decisions.md` is the record. The tick and `#E<n>` of a Decided card mirror the lane of its decision; `epics/tag.py`, `sprints/refresh.py` and every `queue/item.py` call sync them, and `status/report.py` flags a card that disagrees.
- Facts are sub-bullets indented with one tab: path:line, measurement, lookup result. Every sub-bullet is a fact. Options are never written in the file. A `#word` that is not a tag is written in backticks, so the extension shows no tag badge.
- New cards go to the end of Open. A moved card goes, with its facts, to the end of its lane. Decided only through `queue/item.py <release> D "<title>" --source Q<n>`, which adds `#D<n>` to the title and leaves the card unticked; a card already in Decided keeps the highest decision number. A card leaving Decided loses its `#D` and `#E` tags.
- `plan/milestone.py add` moves each card it cites (`--cites`) to Autofix, ticked and without tags; the fix is traced through its module heading and its tracker's first line, for example `(Q9)`.
- A lookup agent adds its facts to the card it was given with `queue/item.py <release> --fact Q<n> "<text>"`.
- Citations elsewhere: `(Q3)` in specs and trackers; a decision that came from a card ends with `- Source: Q3`; a fix's tracker cites `(Q3, Q4)` on its first line.
- The run reports; it does not solve. Do not research solutions for a run card.
- Not a queue card: a point that fails the bar at filing, spec text that lags shipped code, a tracker gap, a process lesson, a tooling fact with one right answer. Those go to the tracker Notes, a decision or the spec file directly (`process.md` holds project facts only); the owner sees choices only.
