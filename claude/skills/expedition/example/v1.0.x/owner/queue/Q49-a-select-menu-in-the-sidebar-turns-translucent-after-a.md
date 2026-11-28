---
status: done
decision: D62
option: 1
---
# Q49. A select menu in the sidebar turns translucent after a short scroll

## Notes

- `styles/menu.css:1447`: the blur is inside the scroll container.

## Details

- To see it: open the layout menu in the sidebar and scroll down.
- Likely cause: `styles/menu.css:1447` puts the blur inside the scroll container.

## Options:

1. Recommended: fix the blur in the app's own styles
   - A translucent menu opened from the sidebar keeps its blur while its content scrolls.
   - `components/ui/` stays unchanged.
2. Fix the blur in `components/ui/`
   - The change is in `components/ui/`, not in the app's own styles.
