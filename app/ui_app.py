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

import platform
import tkinter as tk

from app.app_models import AppState
from app.persistence import SAVE_FILE, has_saved_match, load_app_state, save_app_state
from app.scoreboard import Scoreboard, load_scoreboard, record_completed_match, save_scoreboard
from app.ui_screen import GameScreen, ResultScreen, WelcomeScreen


WINDOW_WIDTH = 980
WINDOW_HEIGHT = 720
APP_BG = "#102033"
MIN_WINDOW_WIDTH = 820
MIN_WINDOW_HEIGHT = 620
WINDOW_MARGIN_X = 80
WINDOW_MARGIN_Y = 110


def enable_high_dpi_awareness() -> None:
    """Ask Windows to report real pixel sizes so Tk layout is more predictable."""
    if platform.system() != "Windows":
        return

    try:
        import ctypes

        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        return


def compute_initial_window_size(screen_width: int, screen_height: int) -> tuple[int, int]:
    """Return a centered startup size that fits typical desktop screens."""
    max_width = max(MIN_WINDOW_WIDTH, screen_width - WINDOW_MARGIN_X)
    max_height = max(MIN_WINDOW_HEIGHT, screen_height - WINDOW_MARGIN_Y)
    width = min(max_width, max(WINDOW_WIDTH, int(screen_width * 0.82)))
    height = min(max_height, max(WINDOW_HEIGHT, int(screen_height * 0.84)))
    return width, height


def compute_min_window_size(screen_width: int, screen_height: int) -> tuple[int, int]:
    """Return a safe minimum size for smaller screens and terminal-launched windows."""
    min_width = min(MIN_WINDOW_WIDTH, max(720, screen_width - 180))
    min_height = min(MIN_WINDOW_HEIGHT, max(560, screen_height - 180))
    return min_width, min_height


def centered_geometry(width: int, height: int, screen_width: int, screen_height: int) -> str:
    """Return a geometry string that centers the window on the current display."""
    x = max(0, (screen_width - width) // 2)
    y = max(0, (screen_height - height) // 2)
    return f"{width}x{height}+{x}+{y}"


class App(tk.Tk):
    """Main Tkinter application window."""

    def __init__(self) -> None:
        enable_high_dpi_awareness()
        super().__init__()
        self.title("Chess")
        self.configure(bg=APP_BG)

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        window_width, window_height = compute_initial_window_size(screen_width, screen_height)
        min_width, min_height = compute_min_window_size(screen_width, screen_height)

        self.geometry(centered_geometry(window_width, window_height, screen_width, screen_height))
        self.minsize(min_width, min_height)

        self.state = AppState()
        self.scoreboard = self._load_scoreboard()
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
        self._record_completed_match_if_needed()
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

    def _load_scoreboard(self) -> Scoreboard:
        """Load persistent scoreboard stats without blocking app startup."""
        try:
            return load_scoreboard()
        except (OSError, ValueError):
            return Scoreboard()

    def _record_completed_match_if_needed(self) -> None:
        """Persist scoreboard stats exactly once for each completed match."""
        match = self.state.match
        if match.result_recorded or not (match.winner or match.is_draw):
            return

        self.scoreboard = record_completed_match(
            self.scoreboard,
            match,
            self.state.mode,
            self.state.ai_player_color,
        )
        match.result_recorded = True
        try:
            save_scoreboard(self.scoreboard)
        except OSError:
            pass
