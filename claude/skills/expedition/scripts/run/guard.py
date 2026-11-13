#!/usr/bin/env python3
"""PreToolUse guard for runner and spec-fork sessions (templates/runner-settings.json).

Reads the hook JSON on stdin and blocks a Bash command that no run ever needs:
- a git push that forces: --force, -f (alone or in a flag group), --force-with-lease, a +refspec;
- a shell read of a credential store (cat, less, head, tail, cp, base64, grep and similar, or a
  "<" redirect) naming ~/.ssh/, ~/.aws/, ~/.gnupg/, ~/.netrc, ~/.npmrc, ~/.config/gh/hosts.yml,
  ~/.claude/.credentials.json or ~/.claude.json;
- rm -r / rm -rf whose target is /, ~, $HOME, or a path not strictly inside the session's
  repo, its worktrees folder (<repo>.worktrees), the working folder, or a temp folder.
A block prints one line on stderr and exits 2 (the hook protocol's block). Anything else, and
any input it cannot parse, exits 0 with no output, so the guard can never wedge a run. It only
parses its input; nothing in it is executed. A guard against mistakes and poisoned text, not a
sandbox. Usage (hook): python3 -I guard.py < hook.json
"""
import json
import os
import re
import shlex
import subprocess
import sys

HOME = os.path.expanduser("~")
SECRETS = [os.path.join(HOME, p) for p in (
    ".ssh", ".aws", ".gnupg", ".netrc", ".npmrc", ".config/gh/hosts.yml",
    ".claude/.credentials.json", ".claude.json")]
READERS = {"cat", "less", "more", "head", "tail", "cp", "base64", "grep", "egrep", "fgrep", "rg",
           "xxd", "od", "hexdump", "strings", "bat", "nl", "awk", "sed", "tac", "cut", "diff",
           "tar", "zip", "scp", "rsync", "openssl", "gpg", "jq", "curl", "dd", "tee", "pbcopy",
           "python", "python3", "node", "perl", "ruby"}
SHELLS = {"sh", "bash", "zsh", "dash", "ksh"}
WRAPPERS = {"sudo", "env", "command", "nohup", "time", "exec", "nice", "builtin"}
SEPARATORS = {";", "&&", "||", "|", "&", "(", ")", "|&", ";;", "\n"}


def block(why):
    print(f"expedition guard blocked this command: {why}", file=sys.stderr)
    sys.exit(2)


def tokens(command):
    """Shell-like tokens with separators as their own tokens; a fallback split on bad quoting."""
    lex = shlex.shlex(command.replace("\n", " ; "), posix=True, punctuation_chars=";&|()<>")
    lex.whitespace_split = True
    lex.commenters = ""
    try:
        return list(lex)
    except ValueError:
        return re.findall(r"[;&|()<>]+|[^\s;&|()<>]+", command)


def segments(toks):
    seg = []
    for t in toks:
        if t in SEPARATORS:
            if seg:
                yield seg
            seg = []
        else:
            seg.append(t)
    if seg:
        yield seg


def command_words(seg):
    """The segment without leading VAR=x assignments and wrapper words; backticks stripped."""
    words = [w.lstrip("`").rstrip("`") for w in seg]
    while words and (re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", words[0]) or words[0] in WRAPPERS
                     or words[0] in ("$", "")):
        words = words[1:]
    return words


def expand(word, cwd):
    """An absolute normalised path for a word, or None when it holds an unresolved variable."""
    w = word.strip("'\"")
    if w == "~" or w.startswith("~/"):
        w = HOME + w[1:]
    w = re.sub(r"^\$\{?HOME\}?(?=/|$)", HOME, w)
    w = os.path.expandvars(w)
    if "$" in w or "`" in w:
        return None
    if not os.path.isabs(w):
        if cwd is None:
            return None
        w = os.path.join(cwd, w)
    head, tail = os.path.split(os.path.normpath(w))
    return os.path.join(os.path.realpath(head), tail) if tail else os.path.realpath(head)


def under(path, root, strict=False):
    if path == root:
        return not strict
    return path.startswith(root.rstrip("/") + "/")


def secret(path):
    secrets = SECRETS + [os.path.realpath(s) for s in SECRETS]
    return next((s for s in secrets if path and under(path, s)), None)


def git_roots(cwd):
    """The session's repo roots: the current top level, the main checkout, <main>.worktrees."""
    roots = []
    try:
        out = subprocess.run(["git", "-C", cwd, "rev-parse", "--path-format=absolute",
                              "--show-toplevel", "--git-common-dir"],
                             capture_output=True, text=True, timeout=2).stdout.split("\n")
        if len(out) >= 2 and out[0]:
            roots.append(os.path.realpath(out[0]))
            common = out[1]
            if common.endswith("/.git"):
                main = os.path.realpath(common[:-5])
                roots += [main, main + ".worktrees"]
    except (OSError, subprocess.SubprocessError):
        pass
    return roots


def allowed_roots(cwd):
    roots = [os.path.realpath(cwd)] + git_roots(cwd)
    for t in ("/tmp", "/private/tmp", "/var/folders", "/private/var/folders",
              os.environ.get("TMPDIR", ""), os.environ.get("CLAUDE_SCRATCHPAD", "")):
        if t:
            roots.append(os.path.realpath(t))
    return [r for r in roots if r not in ("/", os.path.realpath(HOME))]


def check_push(words):
    args = words[2:] if len(words) > 1 else []
    for a in args:
        if a in ("--force", "-f") or a.startswith("--force-with-lease") or a == "--force-if-includes":
            block(f"git push with {a} (forced pushes are never part of a run)")
        if re.match(r"^-[A-Za-z]*f[A-Za-z]*$", a):
            block(f"git push with {a} (forced pushes are never part of a run)")
        if a.startswith("+"):
            block(f"git push with the forcing refspec {a}")


def git_subcommand(words):
    """For a git invocation, (index of the subcommand, its name); options like -C dir skipped."""
    i = 1
    while i < len(words):
        w = words[i]
        if w in ("-C", "-c", "--git-dir", "--work-tree", "--namespace"):
            i += 2
            continue
        if w.startswith("-"):
            i += 1
            continue
        return i, w
    return None, None


def check_rm(words, cwd):
    flags = [w for w in words[1:] if w.startswith("-") and w != "--"]
    recursive = any(f in ("--recursive",) or (not f.startswith("--") and re.search(r"[rR]", f))
                    for f in flags)
    if not recursive:
        return
    targets, seen_dashdash = [], False
    for w in words[1:]:
        if w == "--" and not seen_dashdash:
            seen_dashdash = True
            continue
        if w.startswith("-") and not seen_dashdash:
            continue
        targets.append(w)
    roots = allowed_roots(cwd) if cwd else None
    home = os.path.realpath(HOME)
    for t in targets:
        raw = t.strip("'\"")
        p = expand(raw, cwd)
        if p is None:
            continue  # an unresolved variable or a relative path with no known folder: allowed
        base = p.split("*", 1)[0].rstrip("/") or "/"
        if base in ("/", home):
            block(f"rm -r on {raw}")
        if roots is not None and not any(under(base, r, strict=True) for r in roots):
            block(f"rm -r on {raw}: outside the repo, its worktrees, the working folder and temp folders")


def check(command, cwd, depth=0):
    # Command substitutions, also inside double quotes: check their text as a command.
    if depth < 3:
        for sub in re.findall(r"`([^`]*)`", command) + re.findall(r"\$\(([^()]*)\)", command):
            check(sub, cwd, depth + 1)
    toks = tokens(command)
    # Redirects: "< path" anywhere reads that path.
    for i, t in enumerate(toks):
        if t == "<" and i + 1 < len(toks):
            s = secret(expand(toks[i + 1], cwd))
            if s:
                block(f"redirect reads the credential store {s}")
    for seg in segments(toks):
        words = command_words(seg)
        if not words:
            continue
        name = os.path.basename(words[0])
        if name == "cd" and cwd is not None:
            nxt = expand(words[1], cwd) if len(words) > 1 else HOME
            cwd = nxt
            continue
        if name == "git":
            i, sub = git_subcommand(words)
            if sub == "push":
                check_push(words[i - 1:])
            continue
        if name == "rm":
            check_rm(words, cwd)
            continue
        if name in SHELLS and "-c" in words[1:-1] and depth < 3:
            check(words[words.index("-c", 1) + 1], cwd, depth + 1)
            continue
        if name in READERS:
            for w in words[1:]:
                for part in w.split("="):  # --file=~/.netrc, if=~/.ssh/id
                    s = secret(expand(part, cwd))
                    if s:
                        block(f"{name} reads the credential store {s}")


def main():
    try:
        data = json.loads(sys.stdin.read())
        if data.get("tool_name") != "Bash":
            return
        command = (data.get("tool_input") or {}).get("command")
        cwd = data.get("cwd") or None
        if not isinstance(command, str):
            return
        check(command, cwd if isinstance(cwd, str) and os.path.isabs(cwd) else None)
    except SystemExit:
        raise
    except Exception:  # fail open: a guard bug must never stop a run
        return


if __name__ == "__main__":
    main()
    sys.exit(0)
