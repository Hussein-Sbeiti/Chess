"""Dataset generation, import, and training pipeline helpers for self-play data."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, TextIO

from game.encoding import ENCODED_STATE_SIZE, encode_state
from game.board import create_empty_board, set_piece
from game.coords import algebraic_to_index
from game.game_models import MatchState
from game.pieces import make_piece


PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Default generated dataset/metadata locations.
DATASET_PATH = PROJECT_ROOT / "data" / "self_play_positions.jsonl"
METADATA_PATH = PROJECT_ROOT / "data" / "self_play_metadata.json"
# A training row is one encoded feature vector plus one scalar target.
TrainingExample = tuple[list[float], float]
# Material scoring uses standard rough piece values.
PIECE_VALUES = {
    "pawn": 1.0,
    "knight": 3.0,
    "bishop": 3.0,
    "rook": 5.0,
    "queen": 9.0,
    "king": 0.0,
}


def clamp_target(value: float) -> float:
    """Clamp a scalar target to the model output range."""
    return max(-1.0, min(1.0, float(value)))


def material_score(state: MatchState) -> float:
    """Return a white-positive material score normalized to [-1, 1]."""
    score = 0.0
    # Positive material balance favors white; negative favors black.
    for row in state.board:
        for piece in row:
            if piece is None:
                continue
            value = PIECE_VALUES.get(piece.kind, 0.0)
            score += value if piece.color == "white" else -value
    # Keep labels inside the model's output range.
    return clamp_target(score / 20.0)


def blended_target(
    state: MatchState,
    result: float,
    result_weight: float = 1.0,
    material_weight: float = 0.0,
) -> float:
    """Blend final game result with current-position material balance."""
    # At least one signal must contribute to the label.
    total_weight = result_weight + material_weight
    if total_weight <= 0.0:
        raise ValueError("At least one target weight must be positive.")
    mixed = ((result_weight * result) + (material_weight * material_score(state))) / total_weight
    # Clamp the blended value after weighting.
    return clamp_target(mixed)


def state_result_to_example(
    state: MatchState,
    result: float,
    result_weight: float = 1.0,
    material_weight: float = 0.0,
) -> TrainingExample:
    """Convert one seen state and final game result into a training example."""
    # Features come from the position; target blends result/material signals.
    return encode_state(state), blended_target(
        state,
        result,
        result_weight=result_weight,
        material_weight=material_weight,
    )


def self_play_history_to_examples(
    history: list[MatchState],
    result: float,
    result_weight: float = 1.0,
    material_weight: float = 0.0,
) -> list[TrainingExample]:
    """Convert a self-play game history into result-labeled examples."""
    # Every pre-move state in the game gets the same final-result label component.
    return [
        state_result_to_example(
            state,
            result,
            result_weight=result_weight,
            material_weight=material_weight,
        )
        for state in history
    ]


def _material_state(white_pieces: list[tuple[str, str]], black_pieces: list[tuple[str, str]]) -> MatchState:
    """Build a small legal material-only board for calibration data."""
    board = create_empty_board()
    # Include both kings so positions are valid enough for all chess helpers.
    set_piece(board, algebraic_to_index("e1"), make_piece("white", "king"))
    set_piece(board, algebraic_to_index("e8"), make_piece("black", "king"))
    for square, kind in white_pieces:
        set_piece(board, algebraic_to_index(square), make_piece("white", kind))
    for square, kind in black_pieces:
        set_piece(board, algebraic_to_index(square), make_piece("black", kind))
    return MatchState(board=board)


def generate_material_calibration_examples(repeats: int = 1) -> list[TrainingExample]:
    """Generate synthetic examples that teach clean material ordering."""
    # These templates anchor obvious material advantages for the evaluator.
    templates = [
        _material_state([("d1", "queen")], []),
        _material_state([], [("d8", "queen")]),
        _material_state([("d1", "queen")], [("d8", "queen")]),
        _material_state([("a1", "rook")], []),
        _material_state([], [("a8", "rook")]),
        _material_state([("a1", "rook"), ("h1", "rook")], [("d8", "queen")]),
        _material_state([("d1", "queen")], [("a8", "rook"), ("h8", "rook")]),
        _material_state([("a2", "pawn"), ("b2", "pawn"), ("c2", "pawn")], []),
        _material_state([], [("a7", "pawn"), ("b7", "pawn"), ("c7", "pawn")]),
    ]

    examples: list[TrainingExample] = []
    for _ in range(max(0, repeats)):
        # Repeat templates to let callers strengthen this calibration signal.
        for state in templates:
            examples.append((encode_state(state), material_score(state)))
    return examples


def save_examples(
    examples: list[TrainingExample],
    path: str | Path = DATASET_PATH,
    append: bool = True,
) -> None:
    """Persist training examples as JSON lines."""
    output_path = Path(path)
    # Create data/ lazily for fresh checkouts.
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"

    with output_path.open(mode, encoding="utf-8") as output_file:
        for features, target in examples:
            # Every saved row must match the model's fixed feature size.
            if len(features) != ENCODED_STATE_SIZE:
                raise ValueError(f"Expected {ENCODED_STATE_SIZE} features, got {len(features)}.")
            record = {"features": features, "target": max(-1.0, min(1.0, float(target)))}
            output_file.write(json.dumps(record, separators=(",", ":")) + "\n")


def load_examples(path: str | Path = DATASET_PATH) -> list[TrainingExample]:
    """Load JSONL training examples from disk."""
    input_path = Path(path)
    # Missing datasets are treated as empty so train-only flows can report clearly.
    if not input_path.exists():
        return []

    examples: list[TrainingExample] = []
    with input_path.open("r", encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            text = line.strip()
            # Blank lines are ignored to make hand-edited JSONL files more forgiving.
            if not text:
                continue
            record = json.loads(text)
            if not isinstance(record, dict):
                raise ValueError(f"Dataset row {line_number} is invalid.")
            features = record.get("features")
            target = record.get("target")
            # Validate type and feature width before converting numeric values to floats.
            if (
                not isinstance(features, list)
                or len(features) != ENCODED_STATE_SIZE
                or not all(isinstance(value, int | float) for value in features)
                or not isinstance(target, int | float)
            ):
                raise ValueError(f"Dataset row {line_number} is invalid.")
            examples.append(([float(value) for value in features], float(target)))
    return examples


def _validate_example(features: list[float], target: float, row_label: str) -> TrainingExample:
    """Return one normalized example or raise a helpful dataset error."""
    # All imported formats funnel through this shape check.
    if len(features) != ENCODED_STATE_SIZE:
        raise ValueError(f"{row_label} expected {ENCODED_STATE_SIZE} features, got {len(features)}.")
    return [float(value) for value in features], max(-1.0, min(1.0, float(target)))


def load_csv_examples(path: str | Path) -> list[TrainingExample]:
    """
    Load examples from CSV.

    Supported columns:
    - target plus f0..f69
    - target plus feature_0..feature_69
    - target plus features, where features is a JSON array
    """
    input_path = Path(path)
    examples: list[TrainingExample] = []
    with input_path.open("r", encoding="utf-8", newline="") as input_file:
        reader = csv.DictReader(input_file)
        if reader.fieldnames is None:
            return []

        for row_number, row in enumerate(reader, start=2):
            row_label = f"CSV row {row_number}"
            target_text = row.get("target")
            if target_text is None or target_text == "":
                raise ValueError(f"{row_label} is missing target.")

            if row.get("features"):
                features_data = json.loads(row["features"])
                if not isinstance(features_data, list):
                    raise ValueError(f"{row_label} features must be a JSON array.")
                features = [float(value) for value in features_data]
            else:
                features = []
                for index in range(ENCODED_STATE_SIZE):
                    value = row.get(f"f{index}", row.get(f"feature_{index}"))
                    if value is None or value == "":
                        raise ValueError(f"{row_label} is missing feature {index}.")
                    features.append(float(value))

            examples.append(_validate_example(features, float(target_text), row_label))
    return examples


def load_training_examples(
    path: str | Path,
    max_games: int | None = None,
    max_positions_per_game: int | None = None,
    result_weight: float = 1.0,
    material_weight: float = 0.0,
) -> list[TrainingExample]:
    """Load examples from a supported external training dataset path."""
    examples, _summary = load_training_examples_with_summary(
        path,
        max_games=max_games,
        max_positions_per_game=max_positions_per_game,
        result_weight=result_weight,
        material_weight=material_weight,
    )
    return examples


def load_training_examples_with_summary(
    path: str | Path,
    max_games: int | None = None,
    max_positions_per_game: int | None = None,
    result_weight: float = 1.0,
    material_weight: float = 0.0,
    progress_every: int = 0,
    progress_stream: TextIO | None = None,
) -> tuple[list[TrainingExample], dict[str, Any]]:
    """Load examples and return JSON-friendly import metadata."""
    input_path = Path(path)
    suffix = input_path.suffix.lower()
    if suffix == ".csv":
        with input_path.open("r", encoding="utf-8", newline="") as input_file:
            fieldnames = csv.DictReader(input_file).fieldnames or []
        if "moves" in fieldnames and "winner" in fieldnames:
            from train.game_csv_import import load_game_csv_examples_with_stats

            result = load_game_csv_examples_with_stats(
                input_path,
                max_games=max_games,
                max_positions_per_game=max_positions_per_game,
                result_weight=result_weight,
                material_weight=material_weight,
                progress_every=progress_every,
                progress_stream=progress_stream,
            )
            return result.examples, result.summary()
        examples = load_csv_examples(input_path)
        return examples, {
            "attempted_games": 0,
            "imported_games": 0,
            "skipped_games": 0,
            "skip_rate": 0.0,
            "examples_generated": len(examples),
        }
    if suffix in {".jsonl", ".json"}:
        examples = load_examples(input_path)
        return examples, {
            "attempted_games": 0,
            "imported_games": 0,
            "skipped_games": 0,
            "skip_rate": 0.0,
            "examples_generated": len(examples),
        }
    raise ValueError(f"Unsupported dataset format: {input_path.suffix or input_path.name}.")


def summarize_examples(examples: list[TrainingExample]) -> dict[str, int]:
    """Return basic result distribution stats for a dataset."""
    white_result_examples = 0
    black_result_examples = 0
    draw_examples = 0
    for _features, target in examples:
        if target > 0.0:
            white_result_examples += 1
        elif target < 0.0:
            black_result_examples += 1
        else:
            draw_examples += 1
    return {
        "example_count": len(examples),
        "white_result_examples": white_result_examples,
        "black_result_examples": black_result_examples,
        "draw_examples": draw_examples,
    }


def save_dataset_metadata(
    metadata: dict[str, Any],
    path: str | Path = METADATA_PATH,
) -> None:
    """Save dataset/training metadata as pretty JSON."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")


def load_dataset_metadata(path: str | Path = METADATA_PATH) -> dict[str, Any]:
    """Load dataset/training metadata when it exists."""
    input_path = Path(path)
    if not input_path.exists():
        return {}
    data = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Dataset metadata is invalid.")
    return data
