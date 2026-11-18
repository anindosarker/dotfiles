---
name: write-handoff
description: Writes a handoff doc summarising the current conversation so a fresh agent can continue the work, and gives the command that starts the next session. Use when the user runs /write-handoff, asks for a handoff note for the next session, or says "roll over" (the session then opens the next session itself in a new tmux window).
argument-hint: "[optional: next session focus] [roll over]"
---

# Write handoff

- Summarise the current conversation in a handoff doc so a fresh agent can continue the work.
- Do not duplicate content already in other artifacts (specs, plans, ADRs, issues, commits, diffs). Reference them by path or URL.
- Arguments: `$ARGUMENTS`. None: cover the whole conversation. Present: treat them as the next session's focus and tailor the doc to it.
- Use very small, precise bullet points. One fact per bullet.
- The user never reads this file. The next agent is the only reader.

## Location

- DATETIME from `date +%Y-%m-%d-%H%M`.
- Find the active plan: the plan file named in the conversation. None named: the plan most recently changed on this branch (`git log --name-only -- .ai/plans`).
- Plan found: write to `<plan dir>/handoffs/handoff-<DATETIME>.md`.
- No plan: write to `.ai/handoffs/handoff-<DATETIME>.md` in the repo root.
- Do not edit the plan file.

## Sections

- **Ask the user first**: open questions, decisions, or anything needing the user's attention. Put this section at the top, with this line under the heading: `Agent: before any other work, ask the user each item below in chat. Do not assume answers.`
- **Goal**: what the work is for, one or two bullets.
- **State**: done, in progress, branch, last commit hash.
- **Decisions**: choices made and why, only if not recorded elsewhere.
- **Gotchas**: dead ends, traps, things that failed.
- **Next steps**: ordered, concrete, first step first.
- **References**: paths and URLs to plans, specs, issues, PRs.

Drop empty sections.

## Next session

- Next name: the script works it out, never you. It reads this session's own name from its transcript (the name set by `/rename` or `claude -n`) and bumps the version: `Parallel workflow V3` to `Parallel workflow V4`; `v0.9.x lead 2` to `v0.9.x lead 3`; `docs-v9` to `docs-v10`; `Slack bot for new pr` to `Slack bot for new pr v2`. Do not take the name from ListAgents, the folder or the handoff's goal.
- A name the owner gives is passed with `--name "<name>"` and used exactly as given. Pass `--name` in no other case, except when the script exits 4 (the session has no name): then pass a short name taken from the Goal and say so in one clause.
- The script's last output line is `name: <next name>`: that is the name to report.
- Start command: the output of `${CLAUDE_SKILL_DIR}/scripts/rollover.sh --cwd <absolute cwd of this session> --handoff <absolute handoff path> --print`, its first line as printed. It has the form `cd <cwd> && claude -n <next name> --model <model> "Read <handoff> and continue."`. The `cd` matters: a session started in another folder loads other project instructions and memory. The script reads the model this session runs on from its transcript: never pass `--model` yourself, never guess it. It reads the permission mode the same way and starts the next session in this session's mode.

## Reply

- Plain: the file path, then the start command on its own line in a code block.
- Roll over (the request or the arguments say "roll over"): after writing the file, run `${CLAUDE_SKILL_DIR}/scripts/rollover.sh --cwd <dir> --handoff <abs path> [--name "<name the owner gave>"] [--prompt-prefix "<text>"]`. It opens the next session in a new, detached window of the current tmux session. `--prompt-prefix` is for a calling skill that puts a slash command or a first instruction before the read. Reply with the file path, then `Rolled over to <next name>`, nothing else. The next session runs on the same model and in the same permission mode as this one. The script exits 3 outside tmux: then give the plain reply.
