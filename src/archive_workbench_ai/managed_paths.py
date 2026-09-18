from __future__ import annotations

import os
import sys
from pathlib import Path

from .catalog import data_root


def default_bridge_root() -> Path:
    """Return the per-user bridge shared with managed Archive Workbench."""

    return data_root() / "bridge"


def managed_executable_candidates() -> tuple[Path, ...]:
    """Canonical per-user locations used by the managed installers."""

    home = Path.home()
    if os.name == "nt":
        local = Path(os.environ.get("LOCALAPPDATA") or home / "AppData" / "Local")
        return (local / "Programs" / "Archive Workbench AI" / "aw-ai.exe",)
    if sys.platform == "darwin":
        return (
            home / "Applications" / "Archive Workbench AI.app" / "Contents" / "MacOS" / "aw-ai",
            Path("/Applications/Archive Workbench AI.app/Contents/MacOS/aw-ai"),
        )
    xdg = Path(os.environ.get("XDG_DATA_HOME") or home / ".local" / "share")
    return (
        Path("/opt/archive-workbench-ai/aw-ai"),
        xdg / "archive-workbench-ai" / "app" / "aw-ai",
    )
