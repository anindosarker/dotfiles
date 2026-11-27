# First run

For the lead, once per project: the first time the skill runs in a project that has no `.ai/plans/` folder.

## The first run

Only when the project has no `.ai/plans/` folder, in the repo or in the root, and before `plan/new_release.py` runs. A project that already has one is never asked. Trees and the root `CLAUDE.md` lines: Folder layouts, below.

- The lead shows the suggested tree, says what the current folder has and what differs, and hints at a local `git init` in the root (no remote needed) and worktrees under `<repo>.worktrees/`.
- It asks the one thing that varies, `Plans inside the repo (default), or in the root?`, and ends with `Say "set up" to arrange it, or "keep" to stay as is.`
- `set up`: the lead creates what is missing: the root `CLAUDE.md` from the template (an existing one is never overwritten: the lead shows the lines to add), the folder `<repo>.worktrees/`, and a local git repo in the root when there is none, with `<repo>/` and `<repo>.worktrees/` added to the root's `.git/info/exclude`. Then the release folder, and the layout bullets of `process.md` filled for the chosen tree.
- `keep`: nothing is arranged; `process.md` is filled by hand.
- The first release folder, run from the root after either word: `plan/new_release.py <release> --owner <owner> --root <repo>` for plans in the repo, `--root .` for plans in the root.
- Nothing existing is moved or renamed, ever. A project whose worktrees or plans already sit elsewhere is told the difference and keeps them unless the owner moves them.

## Folder layouts

The suggested layout of a project worked with expedition. Sessions start in the root folder, one level above the project repo, so the repo and its worktrees sit side by side. The lead shows one of the two trees on the first run ([SKILL.md](../SKILL.md), First run).

### Plans in the repo (default)

The plan folder is committed with the project.

```
<root>/                    sessions start here; local git repo
├── CLAUDE.md
├── <name>.code-workspace
├── <repo>/                project repo, with its own CLAUDE.md
│   └── .ai/plans/         plans, committed with the project
└── <repo>.worktrees/      all worktrees
```

### Plans in the root

The plan folder stays out of the project repo. Plan commits are made in the root's git repo, or in the repo the link points to.

```
<root>/                    sessions start here; local git repo
├── CLAUDE.md              has the extra plans line
├── <name>.code-workspace
├── .ai/plans/             plans, a real folder here or a link to another repo
├── <repo>/                project repo, with its own CLAUDE.md
└── <repo>.worktrees/      all worktrees
```

### Root CLAUDE.md

The root `CLAUDE.md` holds exactly these lines, with `<name>` and `<repo>` filled in.

```markdown
## <name> workspace

- Read first, always: @<repo>/CLAUDE.md. The project is that repo and its rules apply here.
- Use `git -C <repo>`; commit a file in the repo that contains it.
- Worktrees go in `<repo>.worktrees/`
```

Only when plans are in the root, one more line:

```markdown
- Plans are in `.ai/plans` here, not in the project repo.
```

### process.md

`plan/new_release.py` writes the new `process.md` from the short template, or copies the one of the newest earlier release, and sets `updated`. The lead writes the folder facts as a topic of that file: the project repo's folder name, where the plan folder is (`.ai/plans/` in the repo, or `.ai/plans/` in the root folder), and the repository that holds the plans (the project repo, or the root folder's own repo).
