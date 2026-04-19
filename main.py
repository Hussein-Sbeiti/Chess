"""
Chess/
  main.py
  app/
  game/
  tests/
"""

# main.py
# Chess Project - program entry point
# This file is responsible only for starting the application.
# It should not contain UI layout or chess rules.
# Created: 2026-04-15

import sys
import tkinter as tk

from app.ui_app import App


def main() -> int:
    """Create the app and start Tkinter's event loop."""
    try:
        app = App()
        app.mainloop()
    except tk.TclError as error:
        print(
            "Chess needs a graphical desktop session to open the Tkinter window.",
            file=sys.stderr,
        )
        print(
            "If you launched it from a terminal on headless Linux, remote SSH, or a shell without GUI access, "
            "start it from a desktop session or set up the display first.",
            file=sys.stderr,
        )
        print(f"Tkinter error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
