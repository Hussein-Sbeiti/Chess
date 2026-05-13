"""Command-line training loop for self-play generated evaluator data."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Allow direct script execution without installing the package.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from game.ai import AI_DIFFICULTY_LABELS, choose_nn_move, choose_nn_search_move, choose_random_move, normalize_ai_difficulty
from game.game_models import MatchState
from game.nn_model import TinyChessNet
from game.self_play import play_self_play_game
from train.self_play_dataset import (
    DATASET_PATH,
    METADATA_PATH,
    load_dataset_metadata,
    load_examples,
    load_training_examples_with_summary,
    generate_material_calibration_examples,
    save_dataset_metadata,
    save_examples,
    self_play_history_to_examples,
    summarize_examples,
)
from train.train_supervised import MODEL_PATH, train_model_with_history


def choose_self_play_move(state: MatchState, model: TinyChessNet, difficulty: str):
    """Choose a self-play move using the requested difficulty and supplied model."""
    # Self-play difficulty mirrors the UI difficulty mapping.
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
    result_weight: float = 0.7,
    material_weight: float = 0.3,
) -> list[tuple[list[float], float]]:
    """Generate result-labeled examples from neural self-play."""
    examples: list[tuple[list[float], float]] = []
    for _ in range(games):
        # Both sides use the same move selector so generated games are symmetric.
        history, result = play_self_play_game(
            MatchState,
            lambda state: choose_self_play_move(state, model, difficulty),
            lambda state: choose_self_play_move(state, model, difficulty),
            max_turns=max_turns,
        )
        examples.extend(
            # Convert stored positions into model-ready feature/target rows.
            self_play_history_to_examples(
                history,
                result,
                result_weight=result_weight,
                material_weight=material_weight,
            )
        )
    return examples


def generate_and_save_self_play_examples(
    model: TinyChessNet,
    games: int = 20,
    max_turns: int = 200,
    difficulty: str = "medium",
    result_weight: float = 0.7,
    material_weight: float = 0.3,
    path: str | Path = DATASET_PATH,
    append: bool = True,
) -> list[tuple[list[float], float]]:
    """Generate self-play examples and persist them for future training runs."""
    # Keep generation and persistence together for CLI convenience.
    examples = generate_self_play_examples(
        model,
        games=games,
        max_turns=max_turns,
        difficulty=difficulty,
        result_weight=result_weight,
        material_weight=material_weight,
    )
    save_examples(examples, path=path, append=append)
    return examples


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for self-play training."""
    # Flags support generate-only, train-only, and mixed import/generation workflows.
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
    parser.add_argument("--result-weight", type=float, default=0.7, help="Final-result label weight.")
    parser.add_argument("--material-weight", type=float, default=0.3, help="Material-balance label weight.")
    parser.add_argument(
        "--material-calibration-repeats",
        type=int,
        default=0,
        help="Repeat a small synthetic material calibration set this many times.",
    )
    parser.add_argument("--dataset-path", type=Path, default=DATASET_PATH, help="JSONL dataset path.")
    parser.add_argument("--metadata-path", type=Path, default=METADATA_PATH, help="JSON metadata path.")
    parser.add_argument("--model-path", type=Path, default=MODEL_PATH, help="Model weight path.")
    parser.add_argument("--fresh-model", action="store_true", help="Start training from fresh weights.")
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
    parser.add_argument(
        "--import-progress-every",
        type=int,
        default=100,
        help="Print raw game CSV import progress after this many attempted games. Use 0 to disable.",
    )
    parser.add_argument(
        "--training-progress-every",
        type=int,
        default=50000,
        help="Print training progress after this many examples within each epoch. Use 0 to disable.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite the dataset instead of appending.")
    parser.add_argument("--generate-only", action="store_true", help="Generate dataset rows without training.")
    parser.add_argument("--train-only", action="store_true", help="Train from existing dataset rows without generating.")
    return parser


def build_cache_settings(args: argparse.Namespace) -> dict[str, object]:
    """Return the dataset-building inputs that make an import cache reusable."""
    # Store only options that influence dataset contents.
    return {
        "dataset_path": str(args.dataset_path),
        "train_only": bool(args.train_only),
        "import_paths": [str(path) for path in args.import_dataset],
        "import_max_games": args.import_max_games,
        "import_max_positions_per_game": args.import_max_positions_per_game,
        "result_weight": max(0.0, args.result_weight),
        "material_weight": max(0.0, args.material_weight),
        "material_calibration_repeats": max(0, args.material_calibration_repeats),
    }


def can_reuse_dataset_cache(args: argparse.Namespace, metadata: dict[str, object]) -> bool:
    """Return whether the existing JSONL dataset matches this import-only run."""
    # Cache reuse is only valid for train-only import runs with an existing dataset.
    if args.overwrite or not args.train_only or not args.import_dataset:
        return False
    if not args.dataset_path.exists() or not metadata:
        return False
    return metadata.get("cache_settings") == build_cache_settings(args)


def empty_import_summary() -> dict[str, int | float]:
    """Return a blank import summary for metadata."""
    return {
        "attempted_games": 0,
        "imported_games": 0,
        "skipped_games": 0,
        "skip_rate": 0.0,
        "examples_generated": 0,
    }


def add_import_summary(
    left: dict[str, int | float],
    right: dict[str, object],
) -> dict[str, int | float]:
    """Combine per-file import summaries."""
    attempted = int(left.get("attempted_games", 0)) + int(right.get("attempted_games", 0))
    skipped = int(left.get("skipped_games", 0)) + int(right.get("skipped_games", 0))
    return {
        "attempted_games": attempted,
        "imported_games": int(left.get("imported_games", 0)) + int(right.get("imported_games", 0)),
        "skipped_games": skipped,
        "skip_rate": skipped / attempted if attempted else 0.0,
        "examples_generated": int(left.get("examples_generated", 0)) + int(right.get("examples_generated", 0)),
    }


def run_self_play_pipeline(args: argparse.Namespace) -> dict[str, object]:
    """Run generation/training from parsed CLI args and return metadata."""
    model = TinyChessNet()
    if args.model_path.exists() and not args.fresh_model:
        model.load(args.model_path)

    previous_metadata = load_dataset_metadata(args.metadata_path)
    cache_settings = build_cache_settings(args)
    cache_used = can_reuse_dataset_cache(args, previous_metadata)
    generated: list[tuple[list[float], float]] = []
    imported: list[tuple[list[float], float]] = []
    import_summary = empty_import_summary()
    calibration = []
    material_calibration_examples = 0
    if not cache_used:
        calibration = generate_material_calibration_examples(max(0, args.material_calibration_repeats))
        material_calibration_examples = len(calibration)
    else:
        material_calibration_examples = int(previous_metadata.get("material_calibration_examples", 0))
    if not args.train_only:
        generated = generate_and_save_self_play_examples(
            model,
            games=max(0, args.games),
            max_turns=max(1, args.max_turns),
            difficulty=args.difficulty,
            result_weight=max(0.0, args.result_weight),
            material_weight=max(0.0, args.material_weight),
            path=args.dataset_path,
            append=not args.overwrite,
        )

    if cache_used:
        cached_summary = previous_metadata.get("import_summary", empty_import_summary())
        if isinstance(cached_summary, dict):
            import_summary = add_import_summary(empty_import_summary(), cached_summary)
    else:
        for import_path in args.import_dataset:
            import_examples, file_summary = load_training_examples_with_summary(
                import_path,
                max_games=args.import_max_games,
                max_positions_per_game=args.import_max_positions_per_game,
                result_weight=max(0.0, args.result_weight),
                material_weight=max(0.0, args.material_weight),
                progress_every=max(0, args.import_progress_every),
                progress_stream=sys.stderr if args.import_progress_every > 0 else None,
            )
            imported.extend(import_examples)
            import_summary = add_import_summary(import_summary, file_summary)
    if imported:
        save_examples(imported, path=args.dataset_path, append=bool(generated) or not args.overwrite)
    if calibration:
        save_examples(
            calibration,
            path=args.dataset_path,
            append=bool(generated) or bool(imported) or not args.overwrite,
        )

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
            progress_every=max(0, args.training_progress_every),
            progress_stream=sys.stderr if args.training_progress_every > 0 else None,
        )
        args.model_path.parent.mkdir(parents=True, exist_ok=True)
        trained_model.save(args.model_path)
        trained = True

    metadata: dict[str, object] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "dataset_path": str(args.dataset_path),
        "model_path": str(args.model_path),
        "fresh_model": args.fresh_model,
        "games_requested": max(0, args.games),
        "max_turns": max(1, args.max_turns),
        "difficulty": args.difficulty,
        "epochs": max(1, args.epochs),
        "learning_rate": args.lr,
        "result_weight": max(0.0, args.result_weight),
        "material_weight": max(0.0, args.material_weight),
        "material_calibration_examples": material_calibration_examples,
        "material_calibration_repeats": max(0, args.material_calibration_repeats),
        "append": not args.overwrite,
        "cache_used": cache_used,
        "cache_settings": cache_settings,
        "generated_examples": len(generated),
        "imported_examples": import_summary["examples_generated"] if cache_used else len(imported),
        "import_summary": import_summary,
        "import_paths": [str(path) for path in args.import_dataset],
        "import_max_games": args.import_max_games,
        "import_max_positions_per_game": args.import_max_positions_per_game,
        "import_progress_every": max(0, args.import_progress_every),
        "training_progress_every": max(0, args.training_progress_every),
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
    if metadata.get("cache_used"):
        print(f"reused cached dataset with {metadata['imported_examples']} imported examples")
    else:
        saved_examples = int(metadata["generated_examples"]) + int(metadata["imported_examples"])
        print(f"saved {saved_examples} examples to {metadata['dataset_path']}")
    if metadata["trained"]:
        print(f"saved {metadata['model_path']}")
    print(f"saved metadata to {args.metadata_path}")


if __name__ == "__main__":
    main()
