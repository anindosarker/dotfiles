---
name: autopilot
description: Hands off agreed work for unattended execution. Clarifies open questions first, then on the user's go works autonomously to completion, using a 30-minute /loop as retry fallback. Use when the user runs /autopilot or says they are stepping away and Claude should finish alone.
disable-model-invocation: true
---

# Autopilot

## 1. Clarify (interactive)
- Summarize the agreed work in 5 bullets or fewer.
- Ask every open question or ambiguity now, batched. Keep discussing as long as the user wants.
- Do not start work. Wait for an explicit go ("go", "start", "yes").
- The go authorizes all agreed scope. Project and user CLAUDE.md rules still apply.

## 2. Start (on go)
1. Run `bash ${CLAUDE_SKILL_DIR}/scripts/start.sh`. Relay each `WARN` line in one line. Keep the `ATTENTION=` path.
2. Invoke the `loop` skill with interval `30m`. Keep the cron job ID it returns. Prompt: if a skill or the plan defines the loop prompt, use it as is. Otherwise use
   `Continue autopilot: <one-line task>. Skip if a turn is already working.`
3. Say "Autopilot on." and begin.

## 3. Work (unattended)
- Never ask or wait for the user. Pick the sensible default and keep going.
- Blocked item: skip it, continue with the rest.
- Verify as you go (type-check, tests) per project rules.
- Write the ATTENTION file only when something needs the user: a blocked item, or a judgment call they may want reverted. One short bullet each. No status, no progress logs. Nothing to flag: no file.
- Loop fire while background agents still run: end the turn. The next fire checks again.
- 5-hour usage limit: Claude Code auto-continue resumes at the reset. The 30m loop is the backup when auto-continue does not arm (extra usage active, rearm cap hit, setting off).

## 4. Done
- Commit and push per project rules, including the ATTENTION file if it exists. On failure, leave the loop running so the next fire retries.
- Then stop the loop: `CronDelete` with the loop's cron job ID.
- Chat report, 5 bullets max: done, skipped, ATTENTION path if any, last commit hash.
