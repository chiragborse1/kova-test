"""Resolve KOVA_HOME for standalone skill scripts.

Skill scripts may run outside the Kova process (e.g. system Python,
nix env, CI) where ``kova_constants`` is not importable.  This module
provides the same ``get_kova_home()`` and ``display_kova_home()``
contracts as ``kova_constants`` without requiring it on ``sys.path``.

When ``kova_constants`` IS available it is used directly so that any
future enhancements (profile resolution, Docker detection, etc.) are
picked up automatically.  The fallback path replicates the core logic
from ``kova_constants.py`` using only the stdlib.

All scripts under ``google-workspace/scripts/`` should import from here
instead of duplicating the ``KOVA_HOME = Path(os.getenv(...))`` pattern.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from kova_constants import display_kova_home as display_kova_home
    from kova_constants import get_kova_home as get_kova_home
except (ModuleNotFoundError, ImportError):

    def get_kova_home() -> Path:
        """Return the Kova home directory (default: ~/.kova).

        Mirrors ``kova_constants.get_kova_home()``."""
        val = os.environ.get("KOVA_HOME", "").strip()
        return Path(val) if val else Path.home() / ".kova"

    def display_kova_home() -> str:
        """Return a user-friendly ``~/``-shortened display string.

        Mirrors ``kova_constants.display_kova_home()``."""
        home = get_kova_home()
        try:
            return "~/" + home.relative_to(Path.home()).as_posix()
        except ValueError:
            return str(home)
