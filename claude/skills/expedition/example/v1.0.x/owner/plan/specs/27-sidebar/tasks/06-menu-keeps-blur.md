---
status: blocked
type: bug
---
# Sidebar menus stay blurred while their list scrolls

> when you open the select menu the color is fine if you scroll past a bit then the color becomes translucent

## Goals
- Keep the blur on a translucent menu while its content scrolls.

## Instructions
- Reproduce first: open the layout menu in the sidebar and scroll down.
- Check the likely cause: `styles/menu.css:1447` puts the blur inside the scroll container.

## Verification
- [x] The layout menu keeps its blur after scrolling.
- [x] `components/ui/` is unchanged.
- [x] Browser: every menu opened from the sidebar keeps the blur, in light and dark.
- [ ] Owner: the blur strength looks right against the page.
