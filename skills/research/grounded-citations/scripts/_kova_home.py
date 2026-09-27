"""Resolve KOVA_HOME for standalone skill scripts.

Skill scripts may run outside the Kova process (system Python, nix env,
CI) where ``kova_constants`` is not importable.  This module provides the
same ``get_kova_home()`` contract without requiring it on ``sys.path``.

When ``kova_constants`` IS available it is used directly so profile
resolution and any future enhancements are picked up automatically.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from kova_constants import get_kova_home as get_kova_home
except (ModuleNotFoundError, ImportError):

    def get_kova_home() -> Path:
        """Return the Kova home directory (default: ``~/.kova``)."""
        val = os.environ.get("KOVA_HOME", "").strip()
        return Path(val) if val else Path.home() / ".kova"
