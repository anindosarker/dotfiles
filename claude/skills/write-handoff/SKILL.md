---
name: write-handoff
description: Writes a handoff doc summarising the current conversation so a fresh agent can continue the work. Use when the user runs /write-handoff or asks for a handoff note for the next session.
argument-hint: "[optional: next session focus]"
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

Drop empty sections. Reply with the file path only.
