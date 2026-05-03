# Chess

A playable Tkinter chess app with local play, AI opponents, persistent saves, scoring, themes, and a trainable evaluator model.

## Current Features

- Local two-player chess.
- Vs Computer mode with Easy, Medium, and Hard difficulty.
- AI vs AI mode.
- Legal move handling for check, checkmate, stalemate, castling, en passant, promotion, threefold repetition, fifty-move rule, and insufficient material.
- Neural evaluator weights loaded from `models/chess_eval_weights.json`.
- Dataset import and training tools for `games.csv`.
- Model evaluation reports with saved history in `data/evaluation_history.jsonl`.
- Save/load support for unfinished matches.
- Persistent scoreboard, rank points, streaks, and recent match history.
- Piece themes and board color themes.
- Board coordinates, selected-square hints, legal-move hints, last-move highlights, and check highlights.
- Chess-style move notation, recent move history, and captured-piece display.
- Responsive board sizing with wrapped captured pieces so the match screen does not stretch as the game grows.

## Project Structure

```text
Chess/
├── main.py                         # App entry point
├── README.md                       # Project overview and commands
├── Todo.md                         # Current working checklist
├── codex.txt                       # Original project guidance notes
├── games.csv                       # Raw chess game dataset for evaluator training
├── .gitignore                      # Ignored generated files and caches
├── .codex                          # Local Codex marker/config file
├── app/
│   ├── __init__.py
│   ├── app_models.py               # App-level state
│   ├── persistence.py              # Save/load match persistence
│   ├── scoreboard.py               # Scoreboard, rank, and recent match helpers
│   ├── ui_app.py                   # Tk root app and screen navigation
│   └── ui_screen.py                # Welcome, game, and result screens
├── assets/
│   └── README.md                   # Asset folder notes
├── data/
│   ├── evaluation_history.jsonl    # Saved model evaluation history
│   └── games_training_metadata.json # Latest training run metadata
├── game/
│   ├── __init__.py
│   ├── ai.py                       # AI move selection and difficulty behavior
│   ├── board.py                    # Board creation and board helpers
│   ├── coords.py                   # Coordinate conversion helpers
│   ├── encoding.py                 # Numeric state encoding for the model
│   ├── game_models.py              # Match state and move records
│   ├── nn_model.py                 # Dependency-free neural evaluator
│   ├── pieces.py                   # Piece model and constructors
│   ├── rules.py                    # Chess rules and move application
│   └── self_play.py                # Self-play game generation helpers
├── icons/
│   ├── bishop black.png
│   ├── bishop white.png
│   ├── king black.png
│   ├── king white.png
│   ├── knight black.png
│   ├── knight white.png
│   ├── pawn black.png
│   ├── pawn white.png
│   ├── queen black.png
│   ├── queen white.png
│   ├── rook black.png
│   └── rook white.png
├── models/
│   └── chess_eval_weights.json     # Current trained evaluator weights
├── saves/
│   └── scoreboard.json             # Local scoreboard save data
├── tests/
│   ├── __init__.py
│   ├── test_ai.py
│   ├── test_ai_nn.py
│   ├── test_app_window.py
│   ├── test_board.py
│   ├── test_coords.py
│   ├── test_encoding.py
│   ├── test_evaluate_model.py
│   ├── test_game_csv_import.py
│   ├── test_game_state.py
│   ├── test_persistence.py
│   ├── test_rules.py
│   ├── test_scoreboard.py
│   ├── test_self_play_dataset.py
│   ├── test_train_supervised.py
│   └── test_ui_helpers.py
└── train/
    ├── __init__.py
    ├── evaluate_model.py           # Model sanity checks and evaluation history
    ├── game_csv_import.py          # Raw `games.csv` SAN importer
    ├── self_play_dataset.py        # Dataset, metadata, and calibration helpers
    ├── train_self_play.py          # Dataset import and evaluator training CLI
    └── train_supervised.py         # Shared model training loop
```

Generated cache files such as `data/games_positions.jsonl`, `__pycache__/`, `.DS_Store`, and save files are ignored or removable. The trained model and metadata are kept small enough to stay in the repo.

## How To Run

```bash
python3 main.py
```

## How To Run Tests

Run the full test suite:

```bash
python3 -m unittest discover -v
```

Run one test file:

```bash
python3 -m unittest tests.test_rules -v
```

## AI Evaluation

Run evaluator sanity checks:

```bash
python3 -m train.evaluate_model --model-path models/chess_eval_weights.json
```

Show recent evaluator history:

```bash
python3 -m train.evaluate_model --show-history
```

Compare two evaluator weight files in capped AI-vs-AI games:

```bash
python3 -m train.evaluate_model \
  --model-path models/chess_eval_weights.json \
  --compare-model /path/to/other_weights.json \
  --match-games 24 \
  --match-max-turns 100 \
  --match-depth 1
```

## Training

The current model was trained from `games.csv`. The generated JSONL dataset cache is intentionally not kept in the repo because it can become very large.

Rebuild and train from the full imported dataset:

```bash
python3 -m train.train_self_play \
  --train-only \
  --fresh-model \
  --overwrite \
  --epochs 8 \
  --lr 0.0005 \
  --result-weight 0.4 \
  --material-weight 0.6 \
  --material-calibration-repeats 300 \
  --import-dataset games.csv \
  --import-max-games 20000 \
  --import-max-positions-per-game 20 \
  --dataset-path data/games_positions.jsonl \
  --metadata-path data/games_training_metadata.json \
  --model-path models/chess_eval_weights.json \
  --import-progress-every 1000 \
  --training-progress-every 50000
```

After training, run evaluation again to append a new history record:

```bash
python3 -m train.evaluate_model \
  --model-path models/chess_eval_weights.json \
  --metadata-path data/games_training_metadata.json \
  --history-path data/evaluation_history.jsonl
```
