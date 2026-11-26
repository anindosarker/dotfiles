# Root layout

The suggested layout of a project worked with expedition. Sessions start in the root folder, one level above the project repo, so the repo and its worktrees sit side by side. The lead shows one of the two trees on the first run ([SKILL.md](../SKILL.md), First run).

## Plans in the repo (default)

The plan folder is committed with the project.

```
<root>/                    sessions start here; local git repo
├── CLAUDE.md
├── <name>.code-workspace
├── <repo>/                project repo, with its own CLAUDE.md
│   └── .ai/plans/         plans, committed with the project
└── <repo>.worktrees/      all worktrees
```

## Plans in the root

The plan folder stays out of the project repo. Plan commits are made in the root's git repo, or in the repo the link points to.

```
<root>/                    sessions start here; local git repo
├── CLAUDE.md              has the extra plans line
├── <name>.code-workspace
├── .ai/plans/             plans, a real folder here or a link to another repo
├── <repo>/                project repo, with its own CLAUDE.md
└── <repo>.worktrees/      all worktrees
```

## Root CLAUDE.md

The root `CLAUDE.md` holds exactly these lines, with `<name>` and `<repo>` filled in.

```markdown
# <name> workspace

- Read first, always: @<repo>/CLAUDE.md. The project is that repo and its rules apply here.
- Use `git -C <repo>`; commit a file in the repo that contains it.
- Worktrees go in `<repo>.worktrees/`
```

Only when plans are in the root, one more line:

```markdown
- Plans are in `.ai/plans` here, not in the project repo.
```

## process.md

With plans in the repo, `plan/new_cycle.py` fills `[repo]`, `[plan folder]` and `[plan repo]` in the new `process.md`. With plans in the root it leaves them, and the lead fills them: `[repo]` is the project repo's folder name, `[plan folder]` is `.ai/plans/` in the root folder, and `[plan repo]` is the git repo that holds that folder, never `<repo>`.
