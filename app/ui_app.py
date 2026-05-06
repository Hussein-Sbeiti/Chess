"""Tkinter application shell and screen manager for Chess."""
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
from app.persistence import SAVE_FILE, delete_saved_match, has_saved_match, load_app_state, save_app_state
from app.scoreboard import Scoreboard, delete_scoreboard, load_scoreboard, record_completed_match, save_scoreboard
from app.ui_screen import GameScreen, ResultScreen, WelcomeScreen
from game.variants import normalize_game_variant


WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 780
APP_BG = "#050A12"
# Minimums prevent the board/sidebar layout from collapsing on smaller displays.
MIN_WINDOW_WIDTH = 820
MIN_WINDOW_HEIGHT = 620
WINDOW_MARGIN_X = 28
WINDOW_MARGIN_Y = 72


def enable_high_dpi_awareness() -> None:
    """Ask Windows to report real pixel sizes so Tk layout is more predictable."""
    # Non-Windows platforms do not need this ctypes call.
    if platform.system() != "Windows":
        return

    try:
        import ctypes

        try:
            # Preferred modern Windows DPI API.
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            # Older Windows fallback.
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        return


def compute_initial_window_size(screen_width: int, screen_height: int) -> tuple[int, int]:
    """Return a centered startup size that fits typical desktop screens."""
    # Leave a small margin so the window does not hide under desktop panels.
    max_width = max(MIN_WINDOW_WIDTH, screen_width - WINDOW_MARGIN_X)
    max_height = max(MIN_WINDOW_HEIGHT, screen_height - WINDOW_MARGIN_Y)
    width = min(max_width, max(WINDOW_WIDTH, int(screen_width * 0.95)))
    height = min(max_height, max(WINDOW_HEIGHT, int(screen_height * 0.92)))
    return width, height


def compute_min_window_size(screen_width: int, screen_height: int) -> tuple[int, int]:
    """Return a safe minimum size for smaller screens and terminal-launched windows."""
    # Clamp minimums down for small screens while preserving a usable lower bound.
    min_width = min(MIN_WINDOW_WIDTH, max(720, screen_width - 180))
    min_height = min(MIN_WINDOW_HEIGHT, max(560, screen_height - 180))
    return min_width, min_height


def centered_geometry(width: int, height: int, screen_width: int, screen_height: int) -> str:
    """Return a geometry string that centers the window on the current display."""
    # Tk geometry strings include size plus top-left screen position.
    x = max(0, (screen_width - width) // 2)
    y = max(0, (screen_height - height) // 2)
    return f"{width}x{height}+{x}+{y}"


class App(tk.Tk):
    """Main Tkinter application window."""

    def __init__(self) -> None:
        # DPI awareness must be set before creating most Tk widgets.
        enable_high_dpi_awareness()
        super().__init__()
        self.title("Chess Studio")
        self.configure(bg=APP_BG)

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        # Compute startup and minimum sizes from the current monitor.
        window_width, window_height = compute_initial_window_size(screen_width, screen_height)
        min_width, min_height = compute_min_window_size(screen_width, screen_height)

        self.geometry(centered_geometry(window_width, window_height, screen_width, screen_height))
        self.minsize(min_width, min_height)

        self.state = AppState()
        # Scoreboard is persistent, but failures fall back to an empty board.
        self.scoreboard = self._load_scoreboard()
        self.screens: dict[str, tk.Frame] = {}

        # All screens are stacked in one container and raised as needed.
        self._container = tk.Frame(self, bg=APP_BG)
        self._container.pack(fill="both", expand=True)
        self._container.grid_rowconfigure(0, weight=1)
        self._container.grid_columnconfigure(0, weight=1)

        for screen_class in (WelcomeScreen, GameScreen, ResultScreen):
            # Build screens once so their widgets/images stay alive.
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
        # Screens can update labels/buttons immediately before becoming visible.
        refresh = getattr(screen, "refresh", None)
        if callable(refresh):
            refresh()
        screen.tkraise()

    def start_new_game(self) -> None:
        """Reset app state and switch to the main game screen."""
        # Cancel pending AI callbacks so they cannot move in a newly reset game.
        self._cancel_game_screen_ai()
        self.state.reset_for_new_game()
        self.show_screen("GameScreen")

    def save_match(self) -> tuple[bool, str]:
        """Persist the current app state to the default save file."""
        # Save the full AppState so preferences and board state resume together.
        save_app_state(self.state)
        message = f"Match saved to {SAVE_FILE.relative_to(self.state_path_root())}."
        self.state.match.status_message = message
        self.state.screen_message = message
        return True, message

    def load_match(self) -> tuple[bool, str]:
        """Load the most recent saved match and open the board screen."""
        # A pending AI move from the current screen should not fire after loading.
        self._cancel_game_screen_ai()
        if not has_saved_match():
            message = "No saved match found yet."
            self.state.match.status_message = message
            self.state.screen_message = message
            return False, message

        try:
            self.state = load_app_state()
        except (OSError, ValueError) as error:
            # Keep the user in the current flow and show the load error as status text.
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
        # Theme changes affect both previews and the live board.
        self.state.piece_theme = theme_name
        for screen_name in ("WelcomeScreen", "GameScreen"):
            screen = self.screens.get(screen_name)
            refresh = getattr(screen, "refresh", None)
            if callable(refresh):
                refresh()

    def set_board_theme(self, theme_name: str) -> None:
        """Store the selected board palette and refresh any affected screens."""
        self.state.board_theme = theme_name
        for screen_name in ("WelcomeScreen", "GameScreen"):
            screen = self.screens.get(screen_name)
            refresh = getattr(screen, "refresh", None)
            if callable(refresh):
                refresh()

    def set_game_variant(self, variant_name: str) -> None:
        """Store the selected gameplay variant for the next new match."""
        self.state.game_variant = normalize_game_variant(variant_name)
        welcome_screen = self.screens.get("WelcomeScreen")
        refresh = getattr(welcome_screen, "refresh", None)
        if callable(refresh):
            refresh()

    def toggle_sound_enabled(self) -> None:
        """Turn optional UI sounds on or off from the welcome screen."""
        self.state.sound_enabled = not self.state.sound_enabled
        for screen_name in ("WelcomeScreen", "GameScreen"):
            screen = self.screens.get(screen_name)
            refresh = getattr(screen, "refresh", None)
            if callable(refresh):
                refresh()

    def set_mode(self, mode_name: str) -> None:
        """Store the selected play mode and refresh the welcome screen."""
        # Unknown modes are treated as local so invalid UI/state input is harmless.
        self.state.mode = mode_name if mode_name in {"local", "ai", "ai_vs_ai"} else "local"
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

    def set_ai_difficulty(self, difficulty: str) -> None:
        """Store the selected AI difficulty and refresh affected screens."""
        # Import here avoids loading AI/model helpers during basic app startup.
        from game.ai import ai_personality_for_difficulty, normalize_ai_difficulty

        # Difficulty is the newer user setting; personality stays synced for old code paths.
        self.state.ai_difficulty = normalize_ai_difficulty(difficulty)
        self.state.ai_personality = ai_personality_for_difficulty(self.state.ai_difficulty)
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
        # Record the result before showing score/rank summaries.
        self._cancel_game_screen_ai()
        self._record_completed_match_if_needed()
        self.state.screen_message = message
        self.show_screen("ResultScreen")

    def return_home(self) -> None:
        """Return to the welcome screen."""
        self._cancel_game_screen_ai()
        self.show_screen("WelcomeScreen")

    def reset_saved_matches_and_ranking(self) -> tuple[bool, str]:
        """Clear saved match data and reset the long-term scoreboard."""
        changed = False
        try:
            # Delete both persisted stores; missing files are not treated as errors.
            changed = delete_saved_match() or changed
            changed = delete_scoreboard() or changed
        except OSError as error:
            message = f"Could not reset saved data: {error}"
            self.state.screen_message = message
            self.state.match.status_message = message
            return False, message

        # Reset the in-memory scoreboard so visible screens update immediately.
        self.scoreboard = Scoreboard()
        message = (
            "Saved matches and ranking have been reset."
            if changed
            else "No saved matches or ranking data to reset."
        )
        self.state.screen_message = message
        self.state.match.status_message = message

        for screen in self.screens.values():
            # Refresh every existing screen because multiple panels show save/rank state.
            refresh = getattr(screen, "refresh", None)
            if callable(refresh):
                refresh()

        return True, message

    def state_path_root(self):
        """Return the project root used for friendly save-path display."""
        return SAVE_FILE.parent.parent

    def _cancel_game_screen_ai(self) -> None:
        """Cancel any queued AI move before changing the game flow."""
        # Only GameScreen owns AI timers, so ask it politely if it exists.
        game_screen = self.screens.get("GameScreen")
        cancel = getattr(game_screen, "cancel_pending_ai_turn", None)
        if callable(cancel):
            cancel()

    def _load_scoreboard(self) -> Scoreboard:
        """Load persistent scoreboard stats without blocking app startup."""
        try:
            return load_scoreboard()
        except (OSError, ValueError):
            # Corrupt or unreadable scoreboards should not prevent the app from opening.
            return Scoreboard()

    def _record_completed_match_if_needed(self) -> None:
        """Persist scoreboard stats exactly once for each completed match."""
        match = self.state.match
        # result_recorded prevents duplicate ranking updates if the result screen opens twice.
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
            # Scoreboard persistence is nice-to-have; gameplay should still finish.
            pass
