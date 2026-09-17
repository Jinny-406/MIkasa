"""Resolve MIKASA_HOME for standalone skill scripts.

Skill scripts may run outside the Hermes process (system Python, nix env,
CI) where ``mikasa_constants`` is not importable.  This module provides the
same ``get_mikasa_home()`` contract without requiring it on ``sys.path``.

When ``mikasa_constants`` IS available it is used directly so profile
resolution and any future enhancements are picked up automatically.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from mikasa_constants import get_mikasa_home as get_mikasa_home
except (ModuleNotFoundError, ImportError):

    def get_mikasa_home() -> Path:
        """Return the Hermes home directory (default: ``~/.hermes``)."""
        val = os.environ.get("mikasa_HOME", "").strip()
        return Path(val) if val else Path.home() / ".hermes"
