---
name: roll-over
description: Rolls the current session over in place when its context is full. Writes a handoff, clears the session in the same window, renames it with the version bumped and starts it again from the handoff. Use when the user says "roll over" or "rollover".
---

# Roll over

Three steps, in this order, nothing else:

1. Write the handoff with the `write-handoff` skill. Everything the next session must know or do goes in the handoff: next steps, and every Workflow or background task still running (what it is for, its run id and task id). Two optional sections change what the script does: `## Starter prompt` when the next session must start with more than reading the handoff (a slash command, a keyword such as `ultracode`), one message per line, and `## Session name`, one line, when the next session needs a set name. Add them only when a skill or the user asks for them.
2. Run `${CLAUDE_SKILL_DIR}/scripts/rollover.sh --handoff <absolute handoff path>`. Add `--name "<name>"` only when the user gave a name for the next session. Run it exactly as written. Do none of its steps yourself.
3. Reply with the line the script printed and end the turn. Call no more tools.

What the script does once this turn has ended, in this session's own tmux window:

- Types `/clear`. Workflows and background tasks keep running, and their results still arrive in this window.
- Types `/rename <next name>`: the name the user gave, else the handoff's `## Session name` line, else this session's name with its version bumped (`v0.9.x lead` to `v0.9.x lead v2`, `Parallel workflow V3` to `Parallel workflow V4`).
- Types the starter prompt: each line under `## Starter prompt` in the handoff as its own message, in order, each after the input box shows; else `Read <handoff path> and continue.`

Script exits 3 (not inside tmux): tell the user to type `/clear` and paste each line of the starter prompt the script printed, one at a time.
