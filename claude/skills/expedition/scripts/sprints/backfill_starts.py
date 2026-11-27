#!/usr/bin/env python3
"""Moved to migrate/pre-v1.0/backfill_starts.py. This file runs it with the same arguments, for a session that still holds the
earlier path."""
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
runpy.run_path(str(Path(__file__).resolve().parent.parent / "migrate/pre-v1.0/backfill_starts.py"), run_name="__main__")
