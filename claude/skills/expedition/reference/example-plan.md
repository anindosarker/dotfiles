Example of a release `<release>-plan.md` and its sprint grid (v0.8.x), and an epic file with its Ownership table as migrate_epics.py wrote it (v0.9.x), from a real project. Its relative links point into that project's plan folder.

# v0.8.x plan

Release 0.8.0 (D32). Decisions: [decisions.md](decisions.md) D1 to D40. Queue: [queue.md](queue.md) Q1 to Q6. Sprints: [status/sprints.md](status/sprints.md). Specs implement decisions and never re-decide.

## Goals

- The stock table looks and behaves like the owner's header demo (`/header-demo`, reference captures under `reference/`, D34) (D1 to D7)
- Filters live as chips with one editor, sorts in a toolbar editor, preferences behind one view settings button (D8 to D11) (D35)
- All three bases identical in every change; registry output regenerated, docs app copies re-installed

## Deliverables

| # | Spec | Epic | Scope |
|---|---|---|---|
| 01 | [shared surface](plan/specs/01-shared-surface.md) | E1 | Types, options, icon keys, strings, state slices and drag helpers every milestone builds on; no default flips. |
| 02 | [frame and body](plan/specs/02-frame-body.md) | E1 | Toolbar above the frame, row metrics, tokens, width rule, scroll cues, overflow text, pending-view script. |
| 03 | [header, column menu and dragging](plan/specs/03-header-menu-drag.md) | E1 | Quiet header, Notion column menu, hairline resize, header drag with animation and locked columns. |
| 04 | [toolbar chrome](plan/specs/04-toolbar-chrome.md) | E1 | Button group, filter chips, sort editor, view settings with pinned items, one search X, real triggers. |
| 05 | [defaults and stories](plan/specs/05-defaults-stories.md) | E1 | Stock defaults flipped to the new look; every story and play test follows; changelog lists each way back. |
| 06 | [docs](plan/specs/06-docs.md) | E1 | Guides rewritten for the new look and added for each new surface; ship with 0.8.0. |
| 07 | [release 0.8.0](plan/specs/07-release.md) | E1 | Checks rerun in throwaway apps per base; 0.8.0 released. |

---

# E9

`docs/` is `apps/shadcn-table-docs/`; the Files cell of spec 22 is cut short here.

Decisions: D50, D51, D52
Specs: 21, 22, 23
Starts: S1

## Ownership

| Decision | Files | Spec | Milestone | Sprint |
|---|---|---|---|---|
| D50 Sitemap and robots for the docs site | docs/app/sitemap.ts, docs/app/robots.ts | 21 | Sitemap and robots | S1 |
| D51 Remove the /dev preview routes from the docs site | docs/app/sitemap.ts, docs/app/robots.ts | 21 | Sitemap and robots | S1 |
| D51 Remove the /dev preview routes from the docs site | docs/app/dev/**, docs/components/theme-demo/theme-chips.tsx | 22 | Remove dev routes | S7 |
| D50 Sitemap and robots for the docs site | CHANGELOG.md | 23 | Integration 0.9.2; Release PR 0.9.2; After release 0.9.2 | S8 to S10 |
| D51 Remove the /dev preview routes from the docs site | CHANGELOG.md | 23 | Integration 0.9.2; Release PR 0.9.2; After release 0.9.2 | S8 to S10 |
| D52 Release 0.9.2 ships E9 | CHANGELOG.md | 23 | Integration 0.9.2; Release PR 0.9.2; After release 0.9.2 | S8 to S10 |

## Notes

- Scope: SEO for www.shadcn-table.com; E9 runs while E8 (docs restructuring) stays parked with no decisions. [ack 00:21]

---

# v0.8.x sprints

Updated: 2026-11-04 16:35

| Milestone                 | S1  | S2  | S3  | S4  | S5  |
| ------------------------- | --- | --- | --- | --- | --- |
| E1 01 Shared surface      | [x] | ·   | ·   | ·   | ·   |
| E1 01 Demo captures       | [x] | ·   | ·   | ·   | ·   |
| E1 02 Frame and body      | ·   | [x] | ·   | ·   | ·   |
| E1 03 Header, menu, drag  | ·   | [x] | ·   | ·   | ·   |
| E1 04 Toolbar chrome      | ·   | [x] | ·   | ·   | ·   |
| E1 05 Defaults and stories | ·   | ·   | [x] | ·   | ·   |
| fix Component fixes Q3 to Q6 | ·   | ·   | [x] | ·   | ·   |
| E1 06 Docs                | ·   | ·   | ·   | [x] | ·   |
| E1 07 Release 0.8.0       | ·   | ·   | ·   | ·   | [ ] |
