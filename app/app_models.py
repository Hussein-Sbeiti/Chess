from __future__ import annotations

# app/app_models.py
# Chess Project
# Shared UI-level application state.
# This file contains no Tkinter widget layout and no chess rule logic.
# Created: 2026-04-15

"""
This file stores the top-level state shared across screens.
It separates app flow decisions from the Tkinter widgets themselves.

The main object here is AppState:
- it tracks the selected play mode
- it holds the current MatchState object
- it exposes a reset method so the UI can start fresh cleanly
"""

from dataclasses import dataclass, field

from game.game_models import MatchState


@dataclass
class AppState:
    # The project starts in local two-player mode.
    mode: str = "local"

    # Short UI message that screens can show to the player.
    screen_message: str = "Welcome to Chess."

    # Selected piece theme used when rendering the board icons.
    piece_theme: str = "classic"

    # Selected board color palette used for light and dark squares.
    board_theme: str = "classic"

    # Selected AI personality used when playing against the computer.
    ai_personality: str = "random"

    # Selected AI difficulty used by the current computer-opponent flow.
    ai_difficulty: str = "easy"

    # Selected human side in human-vs-AI mode. White moves first, black moves second.
    ai_player_color: str = "white"

    # The active match model used by the game screen.
    match: MatchState = field(default_factory=MatchState)

    def reset_for_new_game(self) -> None:
        """Reset the app state to a brand-new local match."""
        self.screen_message = "White to move."
        self.match = MatchState()
