"""Pytest bootstrap for local, sandbox-safe test execution."""

from __future__ import annotations

import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
KIVY_HOME = REPO_ROOT / ".test_runtime" / "kivy_home"
KIVY_HOME.mkdir(parents=True, exist_ok=True)

os.environ.setdefault("KIVY_HOME", str(KIVY_HOME))
os.environ.setdefault("KIVY_NO_ARGS", "1")
os.environ.setdefault("KIVY_NO_CONSOLELOG", "1")
os.environ.setdefault("KIVY_WINDOW", "mock")
