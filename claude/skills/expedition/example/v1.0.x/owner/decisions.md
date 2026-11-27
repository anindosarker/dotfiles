---
kanban-plugin: basic
---

## To do

## In progress

- [ ] **D58** The sidebar has a collapse shortcut #E11 #R1
	- `Cmd+B` on macOS and `Ctrl+B` elsewhere opens and closes the sidebar.
	- The open or closed state is kept across reloads.
	- Source: Q42
- [ ] **D61** The layout picker is a numbered list #E11 #R2
	- The picker shows the layouts as a numbered list, and layout versions 2 and 7 are removed.
	- The numbers are given after the removal, so the list has no gap.
	- Source: Q48
- [ ] **D62** Sidebar menus keep their blur #E11 #R2
	- A translucent menu opened from the sidebar keeps its blur while its content scrolls.
	- The fix is in the app's own styles; `components/ui/` stays unchanged.
	- Source: Q49

## Done

- [x] **D57** Settings pages live in the sidebar #E11 #R1
	- The settings pages are a section of the sidebar, and the side menu inside the settings pages is removed.
	- Source: Q41

%% kanban:settings
{"kanban-plugin":"basic","lane-width":600,"date-format":"YYYY-MM-DD","time-format":"HH:mm","tag-action":"kanban","set-view":"list","full-list-lane-width":true,"show-add-list":false,"show-archive-all":false,"custom-title":"v1.0.x decisions"}
%%
