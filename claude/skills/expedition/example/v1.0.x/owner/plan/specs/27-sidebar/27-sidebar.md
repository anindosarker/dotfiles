---
status: in progress
---
# 27: Sidebar
- Epic: E11

## 1. Architecture

### 1.1 Overview

The sidebar of the app shell. The owner reviews it in the live preview and gives feedback one item at a time. Each item is the next module below.

### 1.2 Goals

- The sidebar matches what the owner asked for in each module.
- Acceptance: every module is built and the owner has seen it in the preview.

### 1.5 Flow

The sections of the sidebar, top to bottom, are drawn in [reference/sidebar-sections.md](../../../reference/sidebar-sections.md).

### 1.6 Modules

#### 1.6.1 Settings pages in sidebar (D57)

- The settings pages are a section of the sidebar.
- The old side menu inside the settings pages is removed.

#### 1.6.2 Collapse shortcut (D58)

- `Cmd+B` on macOS and `Ctrl+B` elsewhere toggles the sidebar.
- The open or closed state is kept across reloads.

#### 1.6.3 Layout picker as a numbered list (D61)

- The picker shows the layouts as a numbered list.
- Layout versions 2 and 7 are removed.

#### 1.6.4 Sidebar menus keep their blur (D62)

- A translucent menu opened from the sidebar keeps its blur while its content scrolls.

## 2. Instructions for AI

### 2.1 Tasks

- 01 Settings pages as a sidebar section · module 1.6.1 · tasks/01-settings-pages-in-sidebar.md
- 02 Remove the old settings side menu · module 1.6.1 · tasks/02-remove-settings-side-menu.md
- 03 Toggle the sidebar with a keyboard shortcut · module 1.6.2 · tasks/03-shortcut.md
- 04 Layout picker as a numbered list · module 1.6.3 · tasks/04-layout-picker-numbered-list.md
- 05 Remove layout versions 2 and 7 · module 1.6.3 · tasks/05-remove-layouts-2-and-7.md
- 06 Sidebar menus stay blurred while their list scrolls · module 1.6.4 · tasks/06-menu-keeps-blur.md

### 2.2 Milestones

#### 2.2.1 Milestone: Settings pages in sidebar
- Tasks: 01, 02

#### 2.2.2 Milestone: Collapse shortcut
- Tasks: 03

#### 2.2.3 Milestone: Layout picker
- Tasks: 04, 05
- Files owned: `apps/web/src/lib/layouts.ts`
- Starts: S2

#### 2.2.4 Milestone: Sidebar menus keep their blur
- Tasks: 06
- Starts: S2
