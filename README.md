# Chess (Python / Tkinter)

A Battleship-style starter project for a Chess game built with Python and Tkinter.

The goal of this scaffold is to match the structure of the Battleship project we made before:

- `main.py` starts the app
- `app/` owns screens and Tkinter flow
- `game/` owns chess data and rules
- `tests/` owns the early automated checks

## Overview

This version is a planned foundation, not the full finished chess game yet. It already includes:

- a Battleship-style folder layout
- a project plan with file-by-file responsibilities
- a runnable Tkinter starter app
- a starting chess board model
- coordinate helpers for algebraic notation like `e2` and `f7`
- basic move handling for the main piece types
- starter tests for board setup, state reset, and move rules

## Project Structure

```text
Chess/
├── main.py
├── PROJECT_PLAN.md
├── app/
│   ├── __init__.py
│   ├── app_models.py
│   ├── ui_app.py
│   └── ui_screen.py
├── game/
│   ├── __init__.py
│   ├── board.py
│   ├── coords.py
│   ├── game_models.py
│   ├── pieces.py
│   └── rules.py
├── assets/
│   └── README.md
└── tests/
    ├── __init__.py
    ├── test_board.py
    ├── test_coords.py
    ├── test_game_state.py
    └── test_rules.py
```

## Current Foundation

- `WelcomeScreen` starts a local two-player match scaffold.
- `GameScreen` shows an 8x8 chess board and lets players click to select and move pieces.
- `ResultScreen` is ready for end-game flow once full checkmate logic is added.
- Core move generation currently supports standard piece movement patterns.
- Full chess rules like check, checkmate, castling, en passant, and choice-based promotion are planned next.

## How To Run

```bash
python3 main.py
```

## How To Run Tests

```bash
python3 -m unittest
```

## Planning Notes

The detailed build phases and the responsibility of every file live in [PROJECT_PLAN.md](/Users/husseinsbeiti/Desktop/Chess/PROJECT_PLAN.md).
