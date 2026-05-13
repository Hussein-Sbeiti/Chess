# Chess Project Plan

This project is structured to feel like the Battleship project we built before: one clear entry point, one UI package, and one pure game-logic package.

## Main Goal

Build a clean desktop chess game in Python with Tkinter where the code is easy to read and easy to extend.

## Architecture Style

The project follows the same separation of responsibilities we used in Battleship:

- `main.py` only starts the program
- `app/` manages screens, user interaction, and shared UI state
- `game/` contains reusable chess logic with no Tkinter dependency

## Build Phases

### Phase 1: Foundation

- create the folder structure
- define the board and piece data models
- build coordinate helpers
- add a basic Tkinter app with screen switching

### Phase 2: Core Chess Moves

- validate legal movement for pawns, knights, bishops, rooks, queens, and kings
- block illegal destinations
- handle captures cleanly
- promote pawns when they reach the last rank

### Phase 3: Real Match Rules

- prevent moves that leave your own king in check
- detect check and checkmate
- detect stalemate
- add castling
- add en passant
- add player-chosen promotion piece

### Phase 4: UI Polish

- improve board highlights and move hints
- add captured-piece display
- add move log panel with cleaner notation
- add restart and end-game flow
- add visual polish and optional assets

### Phase 5: Extra Features

- optional AI opponent
- save/load match state
- timer or clock mode
- sound effects
- packaging for desktop delivery

## File Responsibilities

### Root Files

`main.py`

- Starts the application.
- Creates the main Tkinter app object.
- Stays small so startup logic never gets mixed with rules or screen code.

`README.md`

- Gives a quick overview of the project.
- Explains the folder structure.
- Shows how to run the app and supporting tools.

`PROJECT_PLAN.md`

- Acts as the planning document for this scaffold.
- Explains phases, architecture, and what each file is supposed to own.

`.gitignore`

- Keeps `__pycache__`, `.DS_Store`, and other generated files out of the project.

### `app/`

`app/__init__.py`

- Marks `app/` as a Python package.

`app/app_models.py`

- Stores UI-level shared state.
- Owns high-level app choices like selected mode and the current chess match object.
- Keeps UI state separate from raw Tkinter widgets.

`app/ui_app.py`

- Defines the main `App` class.
- Creates the root window.
- Registers screens and switches between them.
- Provides shared helper methods like starting a new game or returning home.

`app/ui_screen.py`

- Contains the screen classes.
- Handles click interaction, board rendering, status text, and move history display.
- Talks to `game.rules` instead of embedding chess rules directly in the UI.

### `game/`

`game/__init__.py`

- Marks `game/` as a Python package.

`game/coords.py`

- Converts between board indexes and chess notation such as `e2`.
- Validates coordinates and keeps board math consistent.

`game/pieces.py`

- Defines the `Piece` data model.
- Stores piece names, symbols, and starting back-rank order.

`game/board.py`

- Builds the starting board and empty board.
- Provides safe board read/write helpers.
- Gives the rest of the project a single source of truth for board setup.

`game/game_models.py`

- Defines match-level dataclasses like move records and the current match state.
- Stores whose turn it is, selection info, status messages, and move history.

`game/rules.py`

- Contains chess logic that should stay UI-independent.
- Generates basic candidate moves.
- Applies moves, captures, turn switching, and starter win-state behavior.
- Will grow into full chess legality checks in later phases.

### `assets/`

`assets/README.md`

- Explains what future assets belong here.
- Keeps the folder in place for piece art, sounds, or backgrounds later.

## What This Scaffold Gives Us

- A project that already feels organized like Battleship
- files that each have one clear job
- a place to add real chess logic without rewriting the whole structure later
- comments and docs that make the codebase easier to keep growing


## Todo 
