"""Resolve MIKASA_HOME for standalone skill scripts.

Skill scripts may run outside the Hermes process (e.g. system Python,
nix env, CI) where ``mikasa_constants`` is not importable.  This module
provides the same ``get_mikasa_home()`` and ``display_mikasa_home()``
contracts as ``mikasa_constants`` without requiring it on ``sys.path``.

When ``mikasa_constants`` IS available it is used directly so that any
future enhancements (profile resolution, Docker detection, etc.) are
picked up automatically.  The fallback path replicates the core logic
from ``mikasa_constants.py`` using only the stdlib.

All scripts under ``google-workspace/scripts/`` should import from here
instead of duplicating the ``MIKASA_HOME = Path(os.getenv(...))`` pattern.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from mikasa_constants import display_mikasa_home as display_mikasa_home
    from mikasa_constants import get_mikasa_home as get_mikasa_home
except (ModuleNotFoundError, ImportError):

    def get_mikasa_home() -> Path:
        """Return the Hermes home directory (default: ~/.hermes).

        Mirrors ``mikasa_constants.get_mikasa_home()``."""
        val = os.environ.get("mikasa_HOME", "").strip()
        return Path(val) if val else Path.home() / ".hermes"

    def display_mikasa_home() -> str:
        """Return a user-friendly ``~/``-shortened display string.

        Mirrors ``mikasa_constants.display_mikasa_home()``."""
        home = get_mikasa_home()
        try:
            return "~/" + home.relative_to(Path.home()).as_posix()
        except ValueError:
            return str(home)
