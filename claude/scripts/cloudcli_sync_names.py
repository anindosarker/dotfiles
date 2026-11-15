#!/usr/bin/env python3
"""Copy Claude Code session names into the CloudCLI database.

CloudCLI (npm @cloudcli-ai/cloudcli) reads a session's name from its transcript only while it has
no name stored, so a later /rename in the terminal never reaches its session list (upstream issue
siteboon/claudecodeui#1402). This script reads the last "custom-title" record of every Claude
transcript the database knows and writes it to sessions.custom_name where the two differ.

    python3 cloudcli_sync_names.py            # list the names that would change, write nothing
    python3 cloudcli_sync_names.py --apply    # write them
    python3 cloudcli_sync_names.py --db PATH  # another database (default ~/.cloudcli/auth.db)

Only a manual rename (custom-title) is copied; a session never renamed in the terminal is left
alone. A name set in CloudCLI's own UI is replaced when the transcript holds a terminal rename,
because the database does not record where a name came from. --apply first saves a copy of the
database beside it as auth.db.names-backup. Reload the CloudCLI page afterwards.
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

MARK = b'"custom-title"'


def last_custom_title(path, session_id):
    """The customTitle of the last custom-title record of this session id, or None."""
    title = None
    try:
        with open(path, "rb") as f:
            for line in f:
                if MARK not in line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if rec.get("type") != "custom-title" or rec.get("sessionId") != session_id:
                    continue
                value = rec.get("customTitle")
                if isinstance(value, str) and value.strip():
                    title = value.strip()
    except OSError:
        return None
    return title


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--apply", action="store_true", help="write the names (default: list only)")
    ap.add_argument("--db", default=str(Path.home() / ".cloudcli" / "auth.db"))
    args = ap.parse_args()

    db_path = Path(args.db)
    if not db_path.is_file():
        sys.exit(f"no database at {db_path}")

    con = sqlite3.connect(str(db_path), timeout=15)
    rows = con.execute(
        "SELECT session_id, COALESCE(provider_session_id, session_id), custom_name, jsonl_path "
        "FROM sessions WHERE provider = 'claude' AND jsonl_path IS NOT NULL"
    ).fetchall()

    changes = []
    for session_id, provider_id, name, jsonl_path in rows:
        title = last_custom_title(jsonl_path, provider_id)
        if title and title != name:
            changes.append((session_id, name, title))

    for _, old, new in changes:
        print(f"{old or '-'}  =>  {new}")

    if not changes:
        print(f"{len(rows)} sessions checked, every name is current")
        return
    if not args.apply:
        print(f"{len(rows)} sessions checked, {len(changes)} names differ; nothing written (--apply writes)")
        return

    backup = db_path.with_name(db_path.name + ".names-backup")
    dst = sqlite3.connect(str(backup))
    with dst:
        con.backup(dst)
    dst.close()

    with con:
        con.executemany(
            "UPDATE sessions SET custom_name = ? WHERE session_id = ?",
            [(new, session_id) for session_id, _, new in changes],
        )
    print(f"{len(rows)} sessions checked, {len(changes)} names written; backup at {backup}")


if __name__ == "__main__":
    main()
