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

from app.ui_app import App


def main() -> None:
    """Create the app and start Tkinter's event loop."""
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
