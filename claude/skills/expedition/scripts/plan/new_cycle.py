#!/usr/bin/env python3
"""Renamed to plan/new_release.py. This file runs it with the same arguments, for a session
that still holds this name."""
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
runpy.run_path(str(Path(__file__).resolve().parent / "new_release.py"), run_name="__main__")
