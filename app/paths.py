"""Path helpers for source runs and PyInstaller builds."""
from __future__ import annotations

import os
import sys
from pathlib import Path


APP_NAME = "Chess Studio"
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def resource_path(*parts: str) -> Path:
    """Return a bundled read-only resource path."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS).joinpath(*parts)
    return PROJECT_ROOT.joinpath(*parts)


def user_data_path(*parts: str) -> Path:
    """Return a writable app data path, preserving source-run save locations."""
    if not getattr(sys, "frozen", False):
        return PROJECT_ROOT.joinpath(*parts)

    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    return base / APP_NAME / Path(*parts)
