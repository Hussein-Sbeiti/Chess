from __future__ import annotations

# app/ui_app.py
# Chess Project - Tkinter app and screen manager
# Created: 2026-04-15

"""
This file defines the main App class for the Chess project.

Its responsibilities are:
- create the root Tkinter window
- create the shared AppState
- register every screen once
- switch between screens without destroying them

This mirrors the same role ui_app.py had in the Battleship project.
"""

import tkinter as tk

from app.app_models import AppState
from app.persistence import SAVE_FILE, has_saved_match, load_app_state, save_app_state
from app.ui_screen import GameScreen, ResultScreen, WelcomeScreen


WINDOW_WIDTH = 980
WINDOW_HEIGHT = 720
APP_BG = "#102033"


class App(tk.Tk):
    """Main Tkinter application window."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Chess")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(860, 640)
        self.configure(bg=APP_BG)

        self.state = AppState()
        self.screens: dict[str, tk.Frame] = {}

        self._container = tk.Frame(self, bg=APP_BG)
        self._container.pack(fill="both", expand=True)
        self._container.grid_rowconfigure(0, weight=1)
        self._container.grid_columnconfigure(0, weight=1)

        for screen_class in (WelcomeScreen, GameScreen, ResultScreen):
            self._add_screen(screen_class)

        self.show_screen("WelcomeScreen")

    def _add_screen(self, screen_class: type[tk.Frame]) -> None:
        """Create a screen once and keep it available for raising later."""
        screen = screen_class(self._container, self)
        self.screens[screen_class.__name__] = screen
        screen.grid(row=0, column=0, sticky="nsew")

    def show_screen(self, screen_name: str) -> None:
        """Raise a previously created screen to the front."""
        screen = self.screens[screen_name]
        refresh = getattr(screen, "refresh", None)
        if callable(refresh):
            refresh()
        screen.tkraise()

    def start_new_game(self) -> None:
        """Reset app state and switch to the main game screen."""
        self._cancel_game_screen_ai()
        self.state.reset_for_new_game()
        self.show_screen("GameScreen")

    def save_match(self) -> tuple[bool, str]:
        """Persist the current app state to the default save file."""
        save_app_state(self.state)
        message = f"Match saved to {SAVE_FILE.relative_to(self.state_path_root())}."
        self.state.match.status_message = message
        self.state.screen_message = message
        return True, message

    def load_match(self) -> tuple[bool, str]:
        """Load the most recent saved match and open the board screen."""
        self._cancel_game_screen_ai()
        if not has_saved_match():
            message = "No saved match found yet."
            self.state.match.status_message = message
            self.state.screen_message = message
            return False, message

        try:
            self.state = load_app_state()
        except (OSError, ValueError) as error:
            message = f"Could not load saved match: {error}"
            self.state.match.status_message = message
            self.state.screen_message = message
            return False, message

        message = f"Loaded saved match from {SAVE_FILE.relative_to(self.state_path_root())}."
        self.state.match.status_message = message
        self.state.screen_message = message
        self.show_screen("GameScreen")
        return True, message

    def set_piece_theme(self, theme_name: str) -> None:
        """Store the selected piece theme and refresh any affected screens."""
        self.state.piece_theme = theme_name
        for screen_name in ("WelcomeScreen", "GameScreen"):
            screen = self.screens.get(screen_name)
            refresh = getattr(screen, "refresh", None)
            if callable(refresh):
                refresh()

    def set_mode(self, mode_name: str) -> None:
        """Store the selected play mode and refresh the welcome screen."""
        self.state.mode = mode_name if mode_name in {"local", "ai"} else "local"
        welcome_screen = self.screens.get("WelcomeScreen")
        refresh = getattr(welcome_screen, "refresh", None)
        if callable(refresh):
            refresh()

    def set_ai_personality(self, personality: str) -> None:
        """Store the selected AI personality and refresh affected screens."""
        self.state.ai_personality = personality
        for screen_name in ("WelcomeScreen", "GameScreen"):
            screen = self.screens.get(screen_name)
            refresh = getattr(screen, "refresh", None)
            if callable(refresh):
                refresh()

    def set_ai_player_color(self, color: str) -> None:
        """Store whether the human plays first as white or second as black."""
        self.state.ai_player_color = color if color in {"white", "black"} else "white"
        for screen_name in ("WelcomeScreen", "GameScreen"):
            screen = self.screens.get(screen_name)
            refresh = getattr(screen, "refresh", None)
            if callable(refresh):
                refresh()

    def open_result_screen(self, message: str) -> None:
        """Show the result screen with a user-facing message."""
        self._cancel_game_screen_ai()
        self.state.screen_message = message
        self.show_screen("ResultScreen")

    def return_home(self) -> None:
        """Return to the welcome screen."""
        self._cancel_game_screen_ai()
        self.show_screen("WelcomeScreen")

    def state_path_root(self):
        """Return the project root used for friendly save-path display."""
        return SAVE_FILE.parent.parent

    def _cancel_game_screen_ai(self) -> None:
        """Cancel any queued AI move before changing the game flow."""
        game_screen = self.screens.get("GameScreen")
        cancel = getattr(game_screen, "cancel_pending_ai_turn", None)
        if callable(cancel):
            cancel()
