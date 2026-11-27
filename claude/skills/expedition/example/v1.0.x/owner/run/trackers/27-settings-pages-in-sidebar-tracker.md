# 27: Settings pages in sidebar, tracker

Branch `v1.0/settings-pages-in-sidebar`, worktree 03
Checks:
- Check: types, `pnpm types:check` at 4c1e9a2: pass
- Check: lint, `pnpm lint` at 4c1e9a2: pass
- Check: settings links, headless browser run of the `Browser:` line of task 01 at 4c1e9a2: pass
- Check: no import of the removed side menu, `grep -r SettingsSideMenu apps/web/src` at 7be03d5: pass (no match)
- Check (verifier): types and lint at 7be03d5, clean tree: pass

## Notes

- The sidebar reads the list of settings pages from `settings-nav.tsx`; a new settings page shows in the sidebar without a change here.
