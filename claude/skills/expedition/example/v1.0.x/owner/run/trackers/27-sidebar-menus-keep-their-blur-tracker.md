# 27: Sidebar menus keep their blur, tracker

Branch `v1.0/sidebar-menus-keep-their-blur`, worktree 07
Checks:
- Check: reproduced on the unchanged code, headless browser run of the layout menu at 19ac3e0: fail (the blur is lost after a scroll of 40 pixels)
- Check: the same run after the fix at b63f08d: pass
- Check: every sidebar menu, light and dark, headless browser run at b63f08d: pass
- Check: `git diff --stat origin/review -- apps/web/src/components/ui` at b63f08d: pass (no change)

## Attention

- Task 06 waits for the owner's look: the blur strength of a sidebar menu against the page, in light and dark. The branch is built and not merged; the layout menu in the sidebar shows it.

## Notes

- The cause was the one the task named: the blur was inside the scroll container. It is now on the menu surface.
