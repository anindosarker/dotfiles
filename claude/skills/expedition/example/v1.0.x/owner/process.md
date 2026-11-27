---
updated: 2026-11-27 10:00
---
# Process, v1.0.x

Example of a filled process file, for one web app project (`apps/web/`), made from a real release and cleaned of private detail.

## P1 Folders and branches

- Every session starts in the workspace folder above the repository `web/`, so every session resolves the same paths.
- `review` is the integration branch: every milestone branch starts from it and merges back into it.
- `master` is the release branch: it changes only by the release pull request, never by a direct push.
- `dev` is the staging branch: fast-forwarded from `review` once, when a release spec runs.

## P2 Worktrees

- The worktree pool is `web.worktrees/01` to `11`, each clean and with dependencies installed.
- A milestone takes a free pool worktree, switches it to a new branch `v<major>.<minor>/<slug>` from `origin/review`, and leaves it detached and clean after the merge.
- Dependencies are installed in a pool worktree only when its lockfile differs from the branch's lockfile.
- No worktree is created or removed while a run is going.
- Never force-push; never a bare `git stash`: the stash stack is shared by every worktree.

## P3 Merge

- A milestone merges into `review` when its checks pass, with the message `merge: <milestone> (<spec>)`, and the merge is pushed.
- The milestone branch is deleted, local and remote, right after the merge. No pull request per milestone.

## P4 Release

- A release is one pull request, `dev` into `master`, with the title `release: <version>`, merged by auto-merge.
- A hold the owner asks for stays until the owner lifts it; no agent lifts it, whatever has merged or passed.

## P5 Machine load

- Several agents share this machine. Before a build, a type-check, a test run or a browser run, check the load with `top -l 1 | head -5` and `memory_pressure | tail -1`.
- Do not start such work while CPU is above 90 percent or memory pressure is not green; wait and check again.
- At most 2 builders, one build or type-check or test run, and one headless browser run at the same time.

## P6 Servers and ports

- The owner's servers are on ports 3000, 5273, 5320, 5330, 6006, 6007 and 6008. An agent never starts, stops, restarts or uses them.
- Agents use ports 5340 to 5360.
- The shared server is the API on port 5310 (`pnpm api:dev`): reuse it when it runs, start it when it is missing, never stop it.
- An agent stops every server it started before it reports.

## P7 Owner space

- The main checkout `web/` and the worktrees `wt1`, `wt2` and `changelog` are the owner's. No agent switches a branch, installs, builds or stops a process there.
- The owner's preview of the app runs from `wt2`: never started, stopped or rebuilt by an agent.

## P8 Agent sandbox

- An agent works only in the worktree and branch it was given.
- Temporary output goes to the session's scratchpad, never into the repository.
- A new dependency is added by the first milestone of the epic that needs it, with one `pnpm install`; that milestone owns `package.json` and the lockfile for its epic.

## P9 Browser checks

- The owner judges how a page looks. An agent checks that it works.
- The tool depends on the task: a check that needs the owner's signed-in browser uses browser-use; any other check runs headless with Playwright or agent-browser, with no window opened.
- A check that the owner takes over is written as an `Owner:` line in the task's Verification list, and no agent opens a browser for it.

## P10 Public surface

- A public page address and an API path are never renamed or removed.
- A field of a public API response is never removed without its own decision.
- Repository settings and branch rules are changed only by the owner.

## P11 Commits

- A code commit is pushed right after it is made.
- Only changed files are formatted, with `pnpm format`; a reformat of an untouched file is reverted, never committed.

## P12 Shared files

- `apps/web/src/lib/routes.ts`: every milestone appends its routes under its own `// spec NN` comment; in a conflict both sides are kept in order.
- `CHANGELOG.md`: one block per milestone under `## Unreleased`; in a conflict both sides are kept in order.
- Generated files, never edited by hand: the route types and the generated API client.

## P13 Plans

- The plan folder is `.ai/plans/` in the workspace folder; plan commits are made in the plan repository and pushed by the scripts.
- A bug is reproduced in the running app before it is planned.
- A diagram or other visual aid the owner asks for is saved in the release's `reference/` folder and committed; the reply names its path.

## P14 Owner requests

- The owner's approval of a remark that belongs to a spec already in progress is also its go: the lead records the decision, files the task and sends it to the runner, and answers in one line.
- Work that needs a new spec keeps the two steps: the decision is recorded first, and it starts on the owner's `delegate`.
