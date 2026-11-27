# 27: Collapse shortcut, tracker

Branch `v1.0/collapse-shortcut`, worktree 05
Checks:
- Check: types, `pnpm types:check` at e02d7f1: pass
- Check: shortcut toggles the sidebar, headless browser run with `Meta+B` and `Control+B` at e02d7f1: pass

## Notes

- `Cmd+B` is also the bold shortcut of a text editor; the text input guard of task 03 covers that case.
- The open or closed state is stored under the key `sidebar:open`.
