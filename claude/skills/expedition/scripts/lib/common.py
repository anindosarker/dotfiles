#!/usr/bin/env python3
"""Shared helpers of the expedition scripts, one copy each. Library, no CLI.

Every script runs as "python3 -I <script> <release> ...", so plain imports of sibling files do
not work: each script loads this file by its path, then any other script with load("<folder>/<name>")
(for example load("lib/ownership")). A module is loaded once per process.

Holds: the release pattern and the release folder paths, die, the repository root and the owner
lookup, the release folder lookup with its refusals of older layouts, spec number order, file
reading, code fences, pipe tables, the .gitignore lines for the status/ renders, git commits, the
tracker and Deliverables row helpers the spec scripts share, and the planning rules lookup.
"""
import collections
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
TEMPLATES = SCRIPTS.parent / "templates"
BOARD = SCRIPTS.parent / "board"  # the status pages: dashboard.html with src/, task-board.html, swimlanes.html

RELEASE_RE = re.compile(r"^v\d+\.\d+\.x$")
SPECS_DIR = "plan/specs"
EPICS_DIR = "plan/epics"
TRACKERS_DIR = "run/trackers"
QUEUE_MD = "queue.md"
QUEUE_DIR = "queue"  # the item files of a release of format 2.1 and higher (lib/queue.py)
HANDOFFS_DIR = "run/handoffs"
STATUS_DIR = "status"
SPRINTS_MD = "status/sprints.md"  # the grid file of a release below format 2.2 (lib/grid.py)
INDEX_HTML = "status/index.html"
LEGACY_OWNERSHIP_MD = "status/ownership.md"
LEGACY_FIX_GLOB = "fix-*-tracker.md"
ROW_RE = re.compile(r"^\|\s*(\d{2}(?:\.\d+)?)\s*\|")
# status/data/ holds renders and the lock, never committed, apart from status.json, the status store.
RENDER_IGNORES = (".ai/plans/*/*/status/index.html", ".ai/plans/*/*/status/data/*",
                  "!.ai/plans/*/*/status/data/status.json")
# A release of format 2.2 also has status/src/, the copies of board/src/ that its dashboard page
# loads (D15): a render too. The line is written only for such a release (page_src=True), so the
# .gitignore of a repository with no release of format 2.2 stays as it is.
PAGE_SRC_IGNORE = ".ai/plans/*/*/status/src/"


def load(rel):
    """The module scripts/<rel>.py, loaded by its file path, once per process."""
    name = "expedition_" + rel.replace("/", "_")
    mod = sys.modules.get(name)
    if mod is not None:
        return mod
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{rel}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def skill_version():
    """The skill's version, from the one place that holds it: "version" in the "metadata" block
    of the front matter of SKILL.md."""
    text = (SCRIPTS.parent / "SKILL.md").read_text(encoding="utf-8")
    front = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    m = re.search(r"^metadata:\n(?:[ \t]+.*\n)*?[ \t]+version:[ \t]*\"?([0-9][0-9.]*)\"?[ \t]*$",
                  (front.group(1) + "\n") if front else "", re.M)
    if not m:
        die("SKILL.md has no metadata version in its front matter")
    return m.group(1)


def script(rel):
    """The path of scripts/<rel>, as messages name it."""
    return SCRIPTS / rel


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def repo_root(flag, release, new=False):
    """The repository root every script works in. Order: --root; else the git top level of the
    cwd when it holds .ai/plans/<release>/; else the one direct child folder of the cwd or of
    that top level that holds it. new=True (plan/new_release.py, release not made yet) looks for
    .ai/plans/ instead. Several matches stop with the list. No match falls back to the git top
    level, so the caller's usual error follows."""
    if flag:
        p = Path(flag).resolve()
        if not p.is_dir():
            die(f"root not a folder: {p}")
        return p
    mark = Path(".ai", "plans") if new else Path(".ai", "plans", release)
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
        top = Path(out.stdout.strip()) if out.returncode == 0 else None
    except FileNotFoundError:
        top = None
    if top and (top / mark).is_dir():
        return top if new else one_copy(top, mark)
    found = []
    for base in (Path.cwd(), top):
        try:
            kids = sorted(base.iterdir()) if base else []
        except OSError:
            continue
        for d in kids:
            try:
                hit = d.is_dir() and (d / mark).is_dir()
            except OSError:
                hit = False
            if hit and d.resolve() not in found:
                found.append(d.resolve())
    if not found and top:
        # plans in a root folder: a project repo or one of its worktrees sits one or two levels below it
        found = [p for p in list(top.parents)[:2] if (p / mark).is_dir()]
    if len(found) == 1:
        return found[0]
    if found:
        die(f"several folders hold {mark}/; pass --root with one of:\n"
            + "\n".join(f"  {d}" for d in found))
    if top is None:
        die("not inside a git repository")
    return top


def one_copy(top, mark):
    """The checkout whose copy of a release folder the scripts write in, for a release with
    status/data/status.json: every writer must use one copy, also when it is run from a
    milestone worktree that holds a copy of the plan folder. The main checkout's copy when it
    has one; else the copy of the one worktree that holds the scripts' lock file; else top.
    A release made before status.json is read where it is found, as before."""
    if not any((top / mark).glob("*/status/data/status.json")):
        return top
    r = subprocess.run(["git", "-C", str(top), "worktree", "list", "--porcelain"], capture_output=True, text=True)
    wts = [Path(l[len("worktree "):]) for l in r.stdout.splitlines() if l.startswith("worktree ")] if r.returncode == 0 else []
    if not wts or wts[0] == top:
        return top
    if any((wts[0] / mark).glob("*/status/data/status.json")):
        return wts[0]
    held = [w for w in wts if any((w / mark).glob("*/status/data/.ids.lock"))]
    return held[0] if len(held) == 1 else top


def check_name(value, what):
    """value when it is one plain path segment (letters, digits, '.', '_', '-'; not '.' or '..'),
    else die with one line."""
    if not re.fullmatch(r"[A-Za-z0-9._-]+", value or "") or value in (".", ".."):
        die(f"bad {what} '{value}': letters, digits, '.', '_' and '-' only, not '.' or '..'")
    return value


def detect_owner(root, flag):
    if flag:
        return check_name(flag, "owner")
    plans = root / ".ai" / "plans"
    counts = collections.Counter(
        p.name for p in plans.glob("v*.x/*") if p.is_dir()
    )
    if not counts:
        die("no owner found under .ai/plans/v*.x/*/; pass --owner")
    return check_name(counts.most_common(1)[0][0], "owner")


def ignore_renders(folder, page_src=False):
    """Append the status/ render lines to the repo's .gitignore when missing (repo root from
    git rev-parse run in the plan folder). index.html and data/ (and src/ with page_src, a release
    of format 2.2) are regenerated by sprints/swimlanes.py and never committed; sprints.md stays
    in git (a release below format 2.2; a release of format 2.2 has no sprints.md)."""
    r = subprocess.run(["git", "-C", str(folder), "rev-parse", "--show-toplevel"],
                       capture_output=True, text=True)
    if r.returncode:
        print(f"warning: {folder} is not in a git repo; .gitignore not touched", file=sys.stderr)
        return
    path = Path(r.stdout.strip()) / ".gitignore"
    upgrade_ignore(path, render_ignores(folder, r.stdout.strip(), page_src))
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    have = {l.strip() for l in text.splitlines()}
    missing = [l for l in render_ignores(folder, r.stdout.strip(), page_src) if l not in have]
    if missing:
        sep = "" if not text or text.endswith("\n") else "\n"
        path.write_text(text + sep + "".join(l + "\n" for l in missing), encoding="utf-8")
        print(f"{path}: added {', '.join(missing)}")


def upgrade_ignore(path, lines):
    """Replace every line that ignores a whole status/data/ folder, whatever its prefix, by the
    pair that keeps status.json in git: a file inside an ignored folder cannot be un-ignored."""
    if not path.is_file():
        return
    out, hit = [], False
    for l in path.read_text(encoding="utf-8").splitlines():
        s = l.strip()
        if s.endswith("status/data/") and not s.startswith(("#", "!")):
            hit = True
            pair = [s + "*", "!" + s + "status.json"]
            out += [x for x in pair if x not in out]
        elif not (hit and s in out and s.endswith(("status/data/*", "status/data/status.json"))):
            out.append(l)
    if hit:
        path.write_text("".join(l + "\n" for l in out), encoding="utf-8")


def render_ignores(folder, top, page_src=False):
    """RENDER_IGNORES (and PAGE_SRC_IGNORE with page_src) relative to the repo top level that holds
    the release folder: the same lines when .ai/plans is a plain folder, the link target's path in
    its own repo when it is a link."""
    rel = Path(folder).resolve().parent.parent.relative_to(Path(top).resolve()).as_posix()
    return [l.replace(".ai/plans", rel, 1) for l in RENDER_IGNORES + ((PAGE_SRC_IGNORE,) if page_src else ())]


def ensure_gitignore(folder, page_src=False):
    """Append the status render ignores (and PAGE_SRC_IGNORE with page_src) to the repo's
    .gitignore when missing. plan/new_release.py runs it before ignore_renders, which then finds
    nothing missing. Returns the path of the .gitignore, or None when the folder is in no git
    repo."""
    try:
        root = subprocess.run(["git", "-C", str(folder), "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return None
    gi = Path(root) / ".gitignore"
    lines = render_ignores(folder, root, page_src)
    upgrade_ignore(gi, lines)
    have = gi.read_text().splitlines() if gi.is_file() else []
    missing = [l for l in lines if l not in have]
    if missing:
        with gi.open("a") as f:
            if have and not have[-1].strip() == "":
                f.write("\n")
            f.write("\n".join(missing) + "\n")
    return gi


def older_than_v1(folder):
    """The one refusal line for a folder older than format 1.0 (D31). The skill no longer has a
    migration for it, so the line names no script; c86eacc is the last skill commit that has one."""
    return (f"{folder} is older than format 1.0, and the skill does not support such a folder: "
            f"its migration is only in skill commit c86eacc")


def release_folder(root, owner, release):
    """The release folder. A folder older than format 1.0 is refused with one line: it has no
    plan/ folder, or it still has status/ownership.md or free-standing fix trackers."""
    folder = root / ".ai" / "plans" / release / owner
    if not folder.is_dir():
        die(f"release folder missing: {folder}")
    if not (folder / "plan").is_dir() or (folder / LEGACY_OWNERSHIP_MD).is_file() or legacy_fixes(folder):
        die(older_than_v1(folder))
    return folder


def find_folder(release, owner=None, root=None):
    """(root, folder) of a release from the --owner and --root flags."""
    r = repo_root(root, release)
    return r, release_folder(r, detect_owner(r, owner), release)


def legacy_fixes(folder):
    """The run/trackers/fix-<slug>-tracker.md files of an unmigrated folder, sorted."""
    return sorted((folder / TRACKERS_DIR).glob(LEGACY_FIX_GLOB))


def lock_file(folder):
    """The release's write lock, status/data/.ids.lock: git-ignored with the rest of status/data,
    which is created here when a fresh clone does not have it yet."""
    data = folder / STATUS_DIR / "data"
    data.mkdir(parents=True, exist_ok=True)
    return data / ".ids.lock"


def num_key(num):
    """Sort key of a spec number ("41", "41.1"); None sorts last."""
    if num is None:
        return (1,)
    return (0,) + tuple(int(x) for x in num.split("."))


def spec_key(num):
    """Sort key of status/report.py and status/progress.py: a spec number, or a key that is not a
    number (a tracker no milestone owns), which sorts after the numbers by its text. Unlike
    num_key it never raises and takes no None."""
    try:
        return (0,) + tuple(int(x) for x in num.split("."))
    except ValueError:
        return (1, num)


def read(p):
    return p.read_text(encoding="utf-8", errors="replace")


def fence_flags(text):
    """Yield (line, inside_fence) for every line; a fence line itself counts as inside."""
    fence = None
    for line in text.splitlines():
        s = line.lstrip()
        m = re.match(r"^(`{3,}|~{3,})", s)
        if m:
            mark = m.group(1)
            if fence is None:
                fence = mark
            elif mark[0] == fence[0] and len(mark) >= len(fence) and s.strip() == mark:
                fence = None
            yield line, True
            continue
        yield line, fence is not None


def outside_fences(text):
    """Yield (1-based line number, line) for every line outside code fences."""
    for i, (line, inside) in enumerate(fence_flags(text), 1):
        if not inside:
            yield i, line


def table_rows(text, first_col):
    """Header and data rows of the first pipe table whose header starts with first_col."""
    lines = [l.strip() for l in text.splitlines()]
    start = next((i for i, l in enumerate(lines)
                  if re.match(r"^\|\s*" + re.escape(first_col) + r"\s*\|", l)), None)
    if start is None:
        return None, []
    split = lambda l: [c.strip() for c in l.strip().strip("|").split("|")]
    block = []
    for l in lines[start:]:
        if not l.startswith("|"):
            break
        block.append(l)
    head = split(block[0])
    data = [split(l) for l in block[1:] if not re.fullmatch(r"\|[\s:|-]+\|?", l)]
    return head, data


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def git(root, *args):
    """Run git in root; die with one line on a failure."""
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    if r.returncode != 0:
        die(f"git {' '.join(args[:1])} failed: {(r.stderr or r.stdout).strip()}")


def plan_repo(root, paths):
    """(repo, paths) for a commit of plan files: root and the paths as given, or, when
    root/.ai/plans is a link, the repo the link points into and the paths resolved through it."""
    plans = Path(root) / ".ai" / "plans"
    if not plans.is_symlink():
        return Path(root), [str(p) for p in paths]
    r = subprocess.run(["git", "-C", str(plans.resolve()), "rev-parse", "--show-toplevel"],
                       capture_output=True, text=True)
    if r.returncode:
        die(f"{plans} links to {plans.resolve()}, which is not in a git repo")
    return Path(r.stdout.strip()), [str(Path(p).resolve()) for p in paths]


def push_plans(root, repo):
    """Push repo when it is not root (the .ai/plans link target) and has a remote; a failed push
    warns and the commit stays."""
    if Path(repo).resolve() == Path(root).resolve():
        return
    remotes = subprocess.run(["git", "-C", str(repo), "remote"], capture_output=True, text=True).stdout.split()
    if not remotes:
        return
    push = lambda: subprocess.run(["git", "-C", str(repo), "push", "-q", remotes[0], "HEAD"], capture_output=True, text=True)
    r = push()
    if r.returncode:
        # The remote moved (another session pushed): rebase with local edits set aside, then push once more.
        subprocess.run(["git", "-C", str(repo), "pull", "-q", "--rebase", "--autostash"], capture_output=True, text=True)
        r = push()
    if r.returncode:
        print(f"warning: git push in {repo} failed: {(r.stderr or r.stdout).strip()}", file=sys.stderr)


def commit(root, paths, message):
    """git add and commit the paths that exist, with --only; nothing when none changed. Dies with
    one line on a git failure. Commits in the repo plan_repo names; pushes only that repo when it
    is not root and has a remote. A folder that holds no file is not named: git has no such
    pathspec and would refuse the commit (the empty decisions/ of a new release)."""
    repo, paths = plan_repo(root, paths)
    git_ = lambda *args: subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    tracked = [str(p) for p in paths if Path(p).exists()]
    tracked = [p for p in tracked
               if not Path(p).is_dir() or git_("ls-files", "-co", "--exclude-standard", "--", p).stdout.strip()]
    if not tracked:
        return False
    r = git_("add", "--", *tracked)
    if r.returncode:
        die(f"git add failed: {(r.stderr or r.stdout).strip()}")
    staged = git_("diff", "--cached", "--name-only", "--", *tracked).stdout.split()
    if not staged:
        return False
    r = git_("commit", "-q", "-m", message, "--only", "--", *tracked)
    if r.returncode:
        die(f"git commit failed: {(r.stderr or r.stdout).strip()}")
    push_plans(root, repo)
    return True


def commit_tree(root, folder, message):
    """git add and commit every change under folder (changed, new and removed files that git does
    not ignore) in one commit, by that path only: a change outside folder stays as it is. Returns
    False when folder has nothing to commit. Dies with one line on a git failure. The repo and
    the push are those of commit (plan_repo, push_plans). The sync of status/sync.py (D22)."""
    repo, (path,) = plan_repo(root, [folder])
    git_ = lambda *args: subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    r = git_("add", "-A", "--", path)
    if r.returncode:
        die(f"git add failed: {(r.stderr or r.stdout).strip()}")
    if not git_("diff", "--cached", "--name-only", "--", path).stdout.strip():
        return False
    r = git_("commit", "-q", "-m", message, "--only", "--", path)
    if r.returncode:
        die(f"git commit failed: {(r.stderr or r.stdout).strip()}")
    # The check after the commit: a file written while the commit ran (an edit by hand that takes
    # no lock) is named, and the next sync commits it.
    left = git_("status", "--porcelain", "--", path).stdout.strip()
    if left:
        print(f"warning: {len(left.splitlines())} file(s) under {folder} changed during the commit "
              f"and stay uncommitted, first: {left.splitlines()[0][3:]}; the next sync commits them",
              file=sys.stderr)
    push_plans(root, repo)
    return True


def template(name):
    """templates/<name> as a script writes it into a release: without its "<!-- ... -->" note,
    and for a board without the placeholder cards ("**D[n]**", "**Q[n]**") and their bullets."""
    path = TEMPLATES / name
    if not path.is_file():
        die(f"bundled template missing: {path}")
    text = re.sub(r"<!--.*?-->\n?", "", path.read_text(encoding="utf-8"), flags=re.S)
    out, card = [], False
    for line in text.splitlines():
        if re.match(r"^- \[[ x]\] \*\*[DQ]\[n\]\*\*", line):
            card = True
            continue
        if card and line.startswith("\t"):
            continue
        card = False
        out.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).rstrip("\n") + "\n"


def tracker_text(num, title, status_line=False):
    """templates/tracker.md with the header filled in, up to its first "## " section (Attention
    and Notes are optional; empty is normal). status_line=True adds "Status: planned" for a
    release made before status/data/status.json, where the tracker holds the milestone status."""
    if status_line:
        return (f"# {num}: {title}, tracker\n\nStatus: planned\nBranch `[branch]`, worktree [name]\nChecks:\n"
                "- Check: [name], `[command]` at [commit]: [pass | fail]\n\n"
                "- Task 1 [name]: [planned | running | done (<commit>, <workflow run id>)]\n")
    out = []
    for line in template("tracker.md").splitlines():
        if line.startswith("## "):
            break
        if line.startswith("# "):
            line = f"# {num}: {title}, tracker"
        out.append(line)
    return "\n".join(out).rstrip() + "\n"


def insert_row(plan_text, num, row):
    """The plan text with row added to its Deliverables table, in spec number order."""
    lines = plan_text.splitlines(keepends=True)
    try:
        start = next(i for i, l in enumerate(lines) if l.strip() == "## Deliverables")
    except StopIteration:
        die("plan has no ## Deliverables section")
    i = start + 1
    while i < len(lines) and not lines[i].lstrip().startswith("|"):
        if lines[i].startswith("## "):
            die("plan ## Deliverables section has no table")
        i += 1
    if i >= len(lines):
        die("plan ## Deliverables section has no table")
    header = i
    if header + 1 >= len(lines) or not re.match(r"^\|[\s|:-]+\|\s*$", lines[header + 1]):
        die("plan Deliverables table has no separator row")
    end = header + 2
    insert_at = None
    while end < len(lines) and lines[end].lstrip().startswith("|"):
        m = ROW_RE.match(lines[end].lstrip())
        if m:
            if m.group(1) == num:
                die(f"plan already has a row for spec {num}")
            if insert_at is None and num_key(m.group(1)) > num_key(num):
                insert_at = end
        end += 1
    if insert_at is None:
        insert_at = end
    if insert_at > 0 and not lines[insert_at - 1].endswith("\n"):
        lines[insert_at - 1] += "\n"
    lines.insert(insert_at, row + "\n")
    return "".join(lines)


def find_rules(root):
    """Project planning-rules paths (plan/find_rules.py)."""
    return load("plan/find_rules").find_rules(root)
