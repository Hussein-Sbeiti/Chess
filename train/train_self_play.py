from __future__ import annotations

# train/train_self_play.py
# Chess Project - first self-play training loop

import argparse
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from game.ai import AI_DIFFICULTY_LABELS, choose_nn_move, choose_nn_search_move, choose_random_move, normalize_ai_difficulty
from game.game_models import MatchState
from game.nn_model import TinyChessNet
from game.self_play import play_self_play_game
from train.self_play_dataset import (
    DATASET_PATH,
    METADATA_PATH,
    load_examples,
    load_training_examples,
    save_dataset_metadata,
    save_examples,
    self_play_history_to_examples,
    summarize_examples,
)
from train.train_supervised import MODEL_PATH, train_model_with_history


def choose_self_play_move(state: MatchState, model: TinyChessNet, difficulty: str):
    """Choose a self-play move using the requested difficulty and supplied model."""
    difficulty = normalize_ai_difficulty(difficulty)
    if difficulty == "easy":
        return choose_random_move(state, state.current_turn)
    if difficulty == "hard":
        return choose_nn_search_move(state, state.current_turn, model, depth=2)
    return choose_nn_move(state, state.current_turn, model)


def generate_self_play_examples(
    model: TinyChessNet,
    games: int = 20,
    max_turns: int = 200,
    difficulty: str = "medium",
) -> list[tuple[list[float], float]]:
    """Generate result-labeled examples from neural self-play."""
    examples: list[tuple[list[float], float]] = []
    for _ in range(games):
        history, result = play_self_play_game(
            MatchState,
            lambda state: choose_self_play_move(state, model, difficulty),
            lambda state: choose_self_play_move(state, model, difficulty),
            max_turns=max_turns,
        )
        examples.extend(self_play_history_to_examples(history, result))
    return examples


def generate_and_save_self_play_examples(
    model: TinyChessNet,
    games: int = 20,
    max_turns: int = 200,
    difficulty: str = "medium",
    path: str | Path = DATASET_PATH,
    append: bool = True,
) -> list[tuple[list[float], float]]:
    """Generate self-play examples and persist them for future training runs."""
    examples = generate_self_play_examples(
        model,
        games=games,
        max_turns=max_turns,
        difficulty=difficulty,
    )
    save_examples(examples, path=path, append=append)
    return examples


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for self-play training."""
    parser = argparse.ArgumentParser(description="Generate and train from chess self-play data.")
    parser.add_argument("--games", type=int, default=20, help="Number of self-play games to generate.")
    parser.add_argument("--max-turns", type=int, default=200, help="Maximum half-moves per generated game.")
    parser.add_argument(
        "--difficulty",
        choices=tuple(AI_DIFFICULTY_LABELS),
        default="medium",
        help="AI difficulty used while generating self-play games.",
    )
    parser.add_argument("--epochs", type=int, default=5, help="Training epochs when training is enabled.")
    parser.add_argument("--lr", type=float, default=0.0005, help="Learning rate when training is enabled.")
    parser.add_argument("--dataset-path", type=Path, default=DATASET_PATH, help="JSONL dataset path.")
    parser.add_argument("--metadata-path", type=Path, default=METADATA_PATH, help="JSON metadata path.")
    parser.add_argument("--model-path", type=Path, default=MODEL_PATH, help="Model weight path.")
    parser.add_argument(
        "--import-dataset",
        action="append",
        type=Path,
        default=[],
        help="External JSONL or CSV dataset to merge before training.",
    )
    parser.add_argument(
        "--import-max-games",
        type=int,
        default=None,
        help="Maximum raw games to import from each moves/winner CSV.",
    )
    parser.add_argument(
        "--import-max-positions-per-game",
        type=int,
        default=None,
        help="Maximum positions to import from each raw game.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite the dataset instead of appending.")
    parser.add_argument("--generate-only", action="store_true", help="Generate dataset rows without training.")
    parser.add_argument("--train-only", action="store_true", help="Train from existing dataset rows without generating.")
    return parser


def run_self_play_pipeline(args: argparse.Namespace) -> dict[str, object]:
    """Run generation/training from parsed CLI args and return metadata."""
    model = TinyChessNet()
    if args.model_path.exists():
        model.load(args.model_path)

    generated: list[tuple[list[float], float]] = []
    imported: list[tuple[list[float], float]] = []
    if not args.train_only:
        generated = generate_and_save_self_play_examples(
            model,
            games=max(0, args.games),
            max_turns=max(1, args.max_turns),
            difficulty=args.difficulty,
            path=args.dataset_path,
            append=not args.overwrite,
        )

    for import_path in args.import_dataset:
        imported.extend(
            load_training_examples(
                import_path,
                max_games=args.import_max_games,
                max_positions_per_game=args.import_max_positions_per_game,
            )
        )
    if imported:
        save_examples(imported, path=args.dataset_path, append=True)

    dataset = load_examples(args.dataset_path)
    trained = False
    loss_history: list[float] = []
    if not args.generate_only:
        if not dataset:
            raise ValueError("No self-play examples available to train on.")
        trained_model, loss_history = train_model_with_history(
            dataset,
            epochs=max(1, args.epochs),
            lr=args.lr,
            model=model,
        )
        args.model_path.parent.mkdir(parents=True, exist_ok=True)
        trained_model.save(args.model_path)
        trained = True

    metadata: dict[str, object] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "dataset_path": str(args.dataset_path),
        "model_path": str(args.model_path),
        "games_requested": max(0, args.games),
        "max_turns": max(1, args.max_turns),
        "difficulty": args.difficulty,
        "epochs": max(1, args.epochs),
        "learning_rate": args.lr,
        "append": not args.overwrite,
        "generated_examples": len(generated),
        "imported_examples": len(imported),
        "import_paths": [str(path) for path in args.import_dataset],
        "import_max_games": args.import_max_games,
        "import_max_positions_per_game": args.import_max_positions_per_game,
        "trained": trained,
        "training_loss_history": loss_history,
        "final_training_loss": loss_history[-1] if loss_history else None,
        "dataset": summarize_examples(dataset),
    }
    save_dataset_metadata(metadata, args.metadata_path)
    return metadata


def main(argv: list[str] | None = None) -> None:
    """Generate self-play data, train from accumulated labels, and save weights."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if args.generate_only and args.train_only:
        parser.error("--generate-only and --train-only cannot be used together.")

    metadata = run_self_play_pipeline(args)
    print(f"saved {metadata['generated_examples']} examples to {metadata['dataset_path']}")
    if metadata["trained"]:
        print(f"saved {metadata['model_path']}")
    print(f"saved metadata to {args.metadata_path}")


if __name__ == "__main__":
    main()
