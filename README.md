# Chess (Python / Tkinter)

A Battleship-style starter project for a Chess game built with Python and Tkinter.

The goal of this scaffold is to match the structure of the Battleship project we made before:

- `main.py` starts the app
- `app/` owns screens and Tkinter flow
- `game/` owns chess data and rules
- `tests/` owns the early automated checks

## Overview

This version is already playable and includes:

- a Battleship-style folder layout
- a project plan with file-by-file responsibilities
- a runnable Tkinter starter app
- a starting chess board model
- coordinate helpers for algebraic notation like `e2` and `f7`
- full legal move handling with check, checkmate, stalemate, castling, en passant, and promotion choice
- piece themes, board coordinates, move notation, captures, and board highlights
- save/load support for resuming a match
- automated tests for board setup, state reset, rules, and UI helpers

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

## Current Features

- `WelcomeScreen` starts a local two-player match scaffold.
- `GameScreen` shows an 8x8 chess board and lets players click to select and move pieces.
- `ResultScreen` shows end-game outcomes for checkmate and stalemate.
- Special rules include castling, en passant, and player-chosen promotion.
- The UI includes theme previews, move history, captured pieces, and last-move/check highlights.
- Matches can be saved and loaded from the local `saves/` folder.

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
