#!/usr/bin/env python3
"""Default session names of a release (D28): "<code>-<release>-<role>".

Usage: python3 -I run/name.py <release> lead|runner|E<n> [--cwd PATH] [--apply] [--current NAME]

Prints the default name of a session of the release:
- <code>: from the name of the folder (--cwd, else the folder the script is called from). One
  word: its first 3 letters as written ("Expedition": "Exp"; a shorter word whole). Several words,
  split at "-", "_", "." or a space: the first letter of each, lower case ("web-template": "wt",
  "my_app.v2": "mav").
- <release>: the release without "v" and ".x" ("v2.1.x": "2.1").
- role "lead": "L". Role "E<n>": the spec writer of epic n, "E<n>". Role "runner": the next
  unused runner name of the release in the registry, "R" for the first, then "R2", "R3": the
  number after the highest one of every runner entry of the release, stopped ones and entries of
  the older form "<release> runner<n>" included (after "v2.1.x runner3" comes "Exp-2.1-R4").

--apply (role lead only): give the calling lead session its default name once.
- Does nothing when the session's name already starts with "<code>-<release>-L" (a rolled-over
  lead keeps its number), and nothing when this command renamed the lead of the release in this
  session before (the owner may have chosen another name since). One line says why; exit 0.
- Not inside tmux (TMUX not set): prints the line "/rename <name>" for the owner to type; exit 0.
- Inside tmux: types "/rename <name>" into the calling pane ($TMUX_PANE), records the name as
  registry key "lead" (as runner.sh records the lead), and when a runner of the release is live
  sends it "LEAD <name>" with runner.sh send, so its replies go to the new name.
The session's name is --current, else the last "custom-title" record of the session transcript
(<projects>/*/$CLAUDE_CODE_SESSION_ID.jsonl, set by /rename or claude -n), else the name of
registry key "lead". What this command renamed is kept in <state dir>/lead-names.json, one entry
per release: {"name", "session"}; the registry file and its fields stay as they are.

The names are a default, not a rule: the owner can rename any session at any time, and the
scripts find a session by its registry entry, not by its name.

Env (tests): EXPEDITION_REGISTRY, EXPEDITION_STATE_DIR, EXPEDITION_PROJECTS, EXPEDITION_TMUX_SOCKET.
"""
import argparse
import fcntl
import glob
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

RELEASE_RE = re.compile(r"^v(\d+\.\d+)\.x$")
HOME = Path.home()
REGISTRY = Path(os.environ.get("EXPEDITION_REGISTRY") or HOME / ".claude" / "expedition-runners.json")
STATE_DIR = Path(os.environ.get("EXPEDITION_STATE_DIR") or HOME / ".claude" / "expedition-runners")
PROJECTS = os.environ.get("EXPEDITION_PROJECTS") or str(HOME / ".claude" / "projects")
RUNNER_SH = Path(__file__).resolve().parent / "runner.sh"


def die(msg, code=1):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def code_of(folder):
    """The short code of a folder name: one word, its first 3 letters; several, their initials."""
    base = Path(os.path.abspath(folder)).name  # the name as the session sees it: no link resolved
    words = [w for w in re.split(r"[-_. ]+", base) if w]
    if not words:
        return "root"  # the folder "/" has no name; a fixed word keeps the name valid
    if len(words) == 1:
        return words[0][:3]
    return "".join(w[0] for w in words).lower()


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except (OSError, ValueError):
        return {}


def write_json(path, change):
    """Read, change and write a JSON file under an exclusive lock on "<path>.lock", replaced by
    rename (the protocol of runner.sh reg), so two writers never lose an entry."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(path) + ".lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = read_json(path)
        change(data)
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
        with os.fdopen(fd, "w") as f:
            f.write(json.dumps(data, indent=2) + "\n")
        os.replace(tmp, path)


def runner_number(name, release):
    """The number of a runner entry name: "<release> runner<n>" and "...-R<n>" give n, "...-R"
    and the oldest key "runner-<release>" give 1, a name of the owner's gives 0."""
    m = re.match(re.escape(release) + r" runner(\d+)$", name)
    if m:
        return int(m.group(1))
    m = re.search(r"-R(\d*)$", name)
    if m:
        return int(m.group(1) or 1)
    return 1 if name == f"runner-{release}" else 0


def next_runner(data, release, prefix):
    rel_entries = [n for n, e in data.items() if n != "lead" and isinstance(e, dict)
                   and e.get("kind", "runner") == "runner"
                   and (e.get("release") == release
                        or re.match(re.escape(release) + r" runner\d+$", n) or n == f"runner-{release}")]
    n = max([runner_number(x, release) for x in rel_entries] + [len(rel_entries)]) + 1
    while True:
        name = f"{prefix}R" if n == 1 else f"{prefix}R{n}"
        if name not in data:
            return name
        n += 1


def tmux(*args, check=False):
    sock = os.environ.get("EXPEDITION_TMUX_SOCKET")
    cmd = ["tmux", "-L", sock, *args] if sock else ["tmux", *args]
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def current_name(flag, reg):
    if flag:
        return flag
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    title = ""
    if re.fullmatch(r"[0-9a-f-]+", sid or "x"):
        for f in glob.glob(f"{glob.escape(PROJECTS)}/*/{sid}.jsonl")[:1]:
            for line in open(f, encoding="utf-8", errors="replace"):
                if '"custom-title"' not in line:
                    continue
                try:
                    t = (json.loads(line).get("customTitle") or "").strip()
                except ValueError:
                    continue
                title = t or title
    return title or (reg.get("lead") or {}).get("name", "")


def live_runner(reg, release):
    """The name of a runner entry of the release that is not stopped and whose window is alive."""
    windows = set(tmux("list-windows", "-a", "-F", "#{session_name}:#{window_id}").stdout.split())
    for n, e in reg.items():
        if n == "lead" or not isinstance(e, dict) or e.get("state") == "stopped":
            continue
        if e.get("kind", "runner") == "runner" and e.get("release") == release and e.get("tmux") in windows:
            return n
    return ""


def apply(release, name, prefix, current_flag):
    if os.environ.get("EXPEDITION_RUNNER"):
        die("called from a runner window (EXPEDITION_RUNNER is set); run --apply in the lead session")
    reg = read_json(REGISTRY)
    current = current_name(current_flag, reg)
    if current.startswith(prefix + "L"):
        print(f"lead already named {current}; nothing typed")
        return
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    done = read_json(STATE_DIR / "lead-names.json").get(release) or {}
    if done and (not sid or not done.get("session") or done.get("session") == sid):
        print(f"lead of {release} was renamed to {done.get('name')} by name.py before; nothing typed "
              "(the owner may have chosen another name since)")
        return
    if not os.environ.get("TMUX"):
        print(f"/rename {name}")
        return
    pane = os.environ.get("TMUX_PANE", "")
    info = tmux("display-message", "-p", "-t", pane, "#{session_name}:#{window_id} #{pane_id}")
    if not pane or info.returncode or len(info.stdout.split()) != 2:
        die(f"no tmux pane found for TMUX_PANE='{pane}'; nothing typed. Type /rename {name} yourself")
    target, pane_id = info.stdout.split()
    tmux("send-keys", "-t", pane_id, "-l", "--", f"/rename {name}", check=True)
    time.sleep(0.3)  # tmux needs a moment to draw the typed text before Enter (as runner.sh type_into)
    tmux("send-keys", "-t", pane_id, "Enter", check=True)
    write_json(REGISTRY, lambda d: d.__setitem__("lead", {"tmux": target, "pane": pane_id, "session": sid, "name": name}))
    write_json(STATE_DIR / "lead-names.json", lambda d: d.__setitem__(release, {"name": name, "session": sid}))
    if (read_json(REGISTRY).get("lead") or {}).get("name") != name:
        die(f"typed /rename {name}, but registry key lead does not hold that name; run --apply again")
    print(f"typed /rename {name} into {pane_id}; registry key lead holds {name}")
    runner = live_runner(read_json(REGISTRY), release)
    if not runner:
        print(f"no live runner of {release}: no LEAD line sent")
        return
    r = subprocess.run(["bash", str(RUNNER_SH), "send", release, f"LEAD {name}"], capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip().splitlines()
    if r.returncode:
        die(f"LEAD {name} not sent to {runner}: {out[-1] if out else 'runner.sh send failed'}. "
            f"Send it: run/runner.sh send {release} \"LEAD {name}\"")
    print(f"LEAD {name} sent to {runner}")


def main():
    ap = argparse.ArgumentParser(usage="run/name.py <release> lead|runner|E<n> [--cwd PATH] [--apply] [--current NAME]")
    ap.add_argument("release")
    ap.add_argument("role")
    ap.add_argument("--cwd", default="")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--current", default="")
    a = ap.parse_args()
    m = RELEASE_RE.match(a.release)
    if not m:
        die(f"bad release '{a.release}', expected like v0.9.x", 2)
    if a.role not in ("lead", "runner") and not re.fullmatch(r"E\d+", a.role):
        die(f"bad role '{a.role}', expected lead, runner or E<n> like E7", 2)
    if a.apply and a.role != "lead":
        die("--apply is for the role lead only", 2)
    folder = a.cwd or os.getcwd()
    if not Path(folder).is_dir():
        die(f"--cwd not a folder: {folder}", 2)
    prefix = f"{code_of(folder)}-{m.group(1)}-"
    if a.role == "lead":
        name = prefix + "L"
    elif a.role == "runner":
        name = next_runner(read_json(REGISTRY), a.release, prefix)
    else:
        name = prefix + a.role
    if a.apply:
        apply(a.release, name, prefix, a.current)
    else:
        print(name)


if __name__ == "__main__":
    main()
