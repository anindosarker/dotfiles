---
kanban-plugin: basic
---

<!--
Accepted decisions only, as a kanban board. Questions stay in chat.
The lane is the state of the decision: To do (in no epic), In progress (in an epic, its work not all merged), Done. The box is ticked only in Done.
A script writes the card line, its lane and its tags. A session writes only the bullets, each indented with one tab.
Example of a filled file: ../example/v1.0.x/owner/decisions.md.
-->

## To do

- [ ] **D[n]** [Decision title, one sentence] #R[n]
	- [Required first bullet: the decision, clear without any other text.]
	- [Optional: more bullets.]
	- Source: Q[n]

## In progress

- [ ] **D[n]** [Decision title] #E[n] #R[n]
	- [First bullet.]

## Done

- [x] **D[n]** [Decision title] #E[n] #R[n]
	- [First bullet.]

%% kanban:settings
{"kanban-plugin":"basic","lane-width":600,"date-format":"YYYY-MM-DD","time-format":"HH:mm","tag-action":"kanban","set-view":"list","full-list-lane-width":true,"show-add-list":false,"show-archive-all":false,"custom-title":"[release] decisions"}
%%
