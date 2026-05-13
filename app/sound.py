"""Lightweight cross-platform sound playback helpers for the chess UI."""
from __future__ import annotations

import platform
import shutil
import subprocess
from tkinter import Misc

from app.paths import resource_path


SOUND_DIR = resource_path("assets", "sounds")
SOUND_FILES = {
    "move": SOUND_DIR / "move.wav",
    "capture": SOUND_DIR / "capture.wav",
    "check": SOUND_DIR / "check.wav",
    "game_end": SOUND_DIR / "game_end.wav",
}


def play_sound(root: Misc, sound_name: str) -> None:
    """Play one named sound effect without blocking the game loop."""
    sound_path = SOUND_FILES.get(sound_name)
    if sound_path is None or not sound_path.exists():
        _ring_bell(root)
        return

    system_name = platform.system()
    try:
        if system_name == "Darwin":
            subprocess.Popen(
                ["afplay", str(sound_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return

        if system_name == "Windows":
            import winsound

            winsound.PlaySound(str(sound_path), winsound.SND_FILENAME | winsound.SND_ASYNC)
            return

        for player in ("paplay", "aplay"):
            player_path = shutil.which(player)
            if player_path:
                subprocess.Popen(
                    [player_path, str(sound_path)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return
    except Exception:
        pass

    _ring_bell(root)


def _ring_bell(root: Misc) -> None:
    """Use Tk's built-in bell when no sound player is available."""
    try:
        root.bell()
    except Exception:
        return
