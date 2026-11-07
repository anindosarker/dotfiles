Example of a release `plan.md`, its `ownership.md` as ownership.py wrote it (first rows only) and its sprint grid from a real project. Its relative links point into that project's plan folder.

# v0.8.x plan

Release 0.8.0 (D32). Decisions: [decisions.md](decisions.md) D1 to D40. Findings: [findings.md](findings.md) F1 to F6. Sprints: [sprints.md](sprints.md). Epics implement decisions and never re-decide.

## Goals

- The stock table looks and behaves like the owner's header demo (`/header-demo`, reference captures under `reference/`, D34) (D1 to D7)
- Filters live as chips with one editor, sorts in a toolbar editor, preferences behind one view settings button (D8 to D11) (D35)
- All three bases identical in every change; registry output regenerated, docs app copies re-installed

## Epics

| # | Epic | Scope |
|---|---|---|
| 01 | [shared surface](epics/01-shared-surface.md) | Types, options, icon keys, strings, state slices and drag helpers every milestone builds on; no default flips. |
| 02 | [frame and body](epics/02-frame-body.md) | Toolbar above the frame, row metrics, tokens, width rule, scroll cues, overflow text, pending-view script. |
| 03 | [header, column menu and dragging](epics/03-header-menu-drag.md) | Quiet header, Notion column menu, hairline resize, header drag with animation and locked columns. |
| 04 | [toolbar chrome](epics/04-toolbar-chrome.md) | Button group, filter chips, sort editor, view settings with pinned items, one search X, real triggers. |
| 05 | [defaults and stories](epics/05-defaults-stories.md) | Stock defaults flipped to the new look; every story and play test follows; changelog lists each way back. |
| 06 | [docs](epics/06-docs.md) | Guides rewritten for the new look and added for each new surface; ship with 0.8.0. |
| 07 | [release 0.8.0](epics/07-release.md) | Checks rerun in throwaway apps per base; 0.8.0 released. |

---

# v0.8.x ownership

Generated: 2026-11-06 by ownership.py

| Milestone | Epic | Depends on | Files |
|---|---|---|---|
| Shared surface | 01 | none | `types.ts`, `features/stConfigFeature.ts`, `features/stFeatures.ts`, `features/stRefsFeature.ts`, `features/stColumnDraggingFeature.ts`, `features/stViewSettingsFeature.ts`, `features/stFilterChipsFeature.ts`, `hooks/useST_TableOptions.ts`, `hooks/useST_TableInstance.ts`, `shared/locales/en.ts`, `icons.ts`, `icons/*.ts`, `components/icons/ST_GridLineIcons.tsx`, `shared/utils/{drag,viewSettingsStorage,column,style}.utils.ts`, `components/head/ST_TableHeadCellGrabHandle.tsx`, `components/menus/ST_ShowHideColumnsMenuItems.tsx`, `components/toolbar/ST_ToolbarDropZone.tsx`, `components/table/ST_TableContainer.tsx`, `components/table/ST_Table.tsx`, `components/body/ST_TableBodyCell.tsx`, `shared/utils/displayColumn.utils.ts`, `components/head/ST_TableHeadCellFilterContainer.tsx`, `index.ts`, `packages/shadcn-table/package.json`, `pnpm-lock.yaml`, `CHANGELOG.md`, `stories/styling/DefaultLook.stories.tsx` |
| Demo captures | 01 | none | `reference/01-*.png`, `reference/01-demo-commit.txt` |
| Frame and body | 02 | Shared surface, Demo captures | `components/table/{ST_TableLayout,ST_TableContainer,ST_Table,ST_ViewPendingScript,ST_ScrollButtons}.tsx`, `components/body/*.tsx`, `components/toolbar/ST_BottomToolbar.tsx`, `hooks/useST_HorizontalOverflow.ts`, `hooks/useST_FullScreenContainer.ts`, `hooks/useST_RowVirtualizer.ts`, `hooks/display-columns/*.tsx`, `shared/utils/{style,displayColumn}.utils.ts`, `stories/styling/DefaultLook.stories.tsx`, `stories/fixed-bugs/RTL.stories.tsx`, `stories/styling/RenderCounts.stories.tsx`, `stories/features/{TableProvider,RowPinning,Virtualization}.stories.tsx`, `stories/styling/StickyHeader.stories.tsx` |
| Header, column menu and dragging | 03 | Shared surface, Demo captures | `components/head/*.tsx`, `components/menus/{ST_ColumnActionMenu,ST_FilterOptionMenu,ST_ActionMenuItem}.tsx`, `hooks/useST_ColumnFlip.ts`, `hooks/useST_DragAutoScroll.ts`, `components/toolbar/ST_ToolbarDropZone.tsx`, `stories/features/{ColumnActions,ColumnDragging,Sorting,ColumnResizing}.stories.tsx`, `stories/fixed-bugs/AriaTooltips.stories.tsx` |
| Toolbar chrome | 04 | Shared surface, Demo captures | `components/toolbar/*.tsx`, `components/menus/{ST_ShowHideColumnsMenu,ST_ShowHideColumnsMenuItems,ST_RowActionMenu}.tsx`, `components/buttons/{ST_ToggleGlobalFilterButton,ST_ShowHideColumnsButton,ST_ToggleDensePaddingButton,ST_ToggleFiltersButton,ST_ToggleRowActionMenuButton}.tsx`, `components/inputs/ST_GlobalFilterTextField.tsx`, `components/inputs/ST_FilterTextField.tsx`, `components/head/ST_TableHeadCellFilterLabel.tsx`, `hooks/useST_ViewPersistence.ts`, `hooks/useST_PopupResize.ts`, `hooks/useST_Effects.ts`, `shared/utils/filterSummary.utils.ts`, `stories/features/{FilterChips,SortPopover,ViewSettings,Search,ColumnHiding,DensePadding,Toolbar}.stories.tsx`, `stories/fixed-bugs/{SearchField,HeadlessFullScreen}.stories.tsx` |
| Defaults and stories | 05 | Frame and body, Header, column menu and dragging, Toolbar chrome | `hooks/useST_TableOptions.ts`, `hooks/useST_TableInstance.ts`, `packages/shadcn-table/stories/`, `apps/shadcn-table-docs/examples/<base>/{customize-filter-variants,enable-filter-facet-values,customize-filter-modes,customize-filter-components,alternate-pagination}/TS.tsx`, `apps/shadcn-table-docs/scripts/page-checks/*.mjs`, `reference/05-check.mjs` |
| Docs | 06 | Defaults and stories | `apps/shadcn-table-docs/`, `reference/06-check.mjs`, `reference/06-audit.md` |
| Toolbar and filters | 06.1 | Check fixes (F8, F9) | `components/toolbar/*.tsx`, `components/menus/*.tsx`, `components/table/ST_TableLayout.tsx`, `shared/locales/en.ts`, `shared/locales/de.ts`, `index.ts`, `packages/shadcn-table/scripts/registry/{base,aria}-diff.json`, `stories/features/{SortPopover,ColumnHiding,FilterChips}.stories.tsx` |

Critical path: Shared surface > Frame and body > Defaults and stories > Docs > Check fixes (F8, F9) > Toolbar and filters > Stories and DefaultLook > Last fixes (F19, F28, F30, F39, F40, F41, D56, D57) > Plays > View settings icons (D75) > Edition icons > Release 0.8.0

---

# v0.8.x sprints

Updated: 2026-11-04 16:35

| Milestone                 | S1  | S2  | S3  | S4  | S5  |
| ------------------------- | --- | --- | --- | --- | --- |
| Shared surface            | [x] | ·   | ·   | ·   | ·   |
| Demo captures             | [x] | ·   | ·   | ·   | ·   |
| Frame and body            | ·   | [x] | ·   | ·   | ·   |
| Header, menu, drag        | ·   | [x] | ·   | ·   | ·   |
| Toolbar chrome            | ·   | [x] | ·   | ·   | ·   |
| Defaults and stories      | ·   | ·   | [x] | ·   | ·   |
| Component fixes F3 to F6  | ·   | ·   | [x] | ·   | ·   |
| Docs                      | ·   | ·   | ·   | [x] | ·   |
| Release 0.8.0             | ·   | ·   | ·   | ·   | [ ] |
