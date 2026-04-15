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
        self.state.reset_for_new_game()
        self.show_screen("GameScreen")

    def open_result_screen(self, message: str) -> None:
        """Show the result screen with a user-facing message."""
        self.state.screen_message = message
        self.show_screen("ResultScreen")

    def return_home(self) -> None:
        """Return to the welcome screen."""
        self.show_screen("WelcomeScreen")
