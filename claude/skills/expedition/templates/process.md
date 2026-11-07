# Process, [release]

Project facts only. The process itself is the expedition skill; commands are in the package manifests; code rules in the project's coding standards; what a milestone must run is in its epic.

One rule per topic, two to five bullets. Each bullet is a full sentence that states the fact explicitly (names, paths, the exact command in a code block when it matters) so no agent reads it two ways. Nothing restated from elsewhere. Suggestions to agents stay here; per-milestone requirements go to the epic.

## P1 Branches

- `[integration branch]`: every worktree starts from it and every finished milestone merges back into it.
- `[staging branch]`: fast-forwarded from the integration branch once, after the last feature column has merged.
- `[release branch]`: changes only by merging the release PR from the staging branch.

## P2 Milestone branch and worktree

- Branch `[pattern]`, created from the integration branch, never from another milestone's unmerged branch.
- Worktree from the pool `[path]`; the reset command in a code block.
- Never force-push; never bare `git stash`.

## P3 Merge

- A milestone merges into the integration branch the moment its recorded checks pass: `merge: <milestone> (<epic>)`, branch deleted. No PR, no CI wait.

## P4 Release

- One PR per release, [source] into [release branch], title, label; auto-merge enabled by the owner or the agent as the plan says.

## P5 Checks on a shared machine

- CPU and memory limits; shared servers and ports; known flakes.

## P6 Agent sandbox

- Only the named worktree and branch; the ports agents may use and the ones they never kill; dependencies only in the first sprint's shared milestone.

## P7 Public surface

- What is never renamed or removed; settings the owner alone changes.

## P8 Commits

- Push after every commit; the format command and what never gets reformatted.

## P9 Shared files

- The files no milestone owns, how each is appended or regenerated.

## P10 Plans

- The planning template the epics follow; what `plan.md` names; how bugs are reproduced before planning.
