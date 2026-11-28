---
kanban-plugin: basic
---

<!--
Every card filed in the release, as a kanban board. The Open lane is the queue; the other lanes are the history.
A script writes the card line and moves it. Fact bullets are optional, each indented with one tab.
A card in Decided carries the tag of its decision, and the tag of the epic when the decision is in one.
Example of a filled file: the example release's queue.md before it moved to format 2.1, `git show 5a5c1ca:claude/skills/expedition/example/v1.0.x/owner/queue.md`.
-->

## Open

- [ ] **Q[n]** [The remark or the problem, one sentence]
	- [Optional: a fact, with its file and line.]

## Decided

- [ ] **Q[n]** [Card title] #D[n] #E[n]

## Later

## Dropped

## Autofix

%% kanban:settings
{"kanban-plugin":"basic","lane-width":300,"date-format":"YYYY-MM-DD","time-format":"HH:mm","tag-action":"kanban"}
%%
