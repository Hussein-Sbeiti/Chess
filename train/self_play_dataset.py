from __future__ import annotations

# train/self_play_dataset.py
# Chess Project - JSONL dataset helpers for self-play positions

import json
import csv
from pathlib import Path
from typing import Any

from game.encoding import ENCODED_STATE_SIZE, encode_state
from game.game_models import MatchState


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = PROJECT_ROOT / "data" / "self_play_positions.jsonl"
METADATA_PATH = PROJECT_ROOT / "data" / "self_play_metadata.json"
TrainingExample = tuple[list[float], float]


def state_result_to_example(state: MatchState, result: float) -> TrainingExample:
    """Convert one seen state and final game result into a training example."""
    return encode_state(state), max(-1.0, min(1.0, float(result)))


def self_play_history_to_examples(
    history: list[MatchState],
    result: float,
) -> list[TrainingExample]:
    """Convert a self-play game history into result-labeled examples."""
    return [state_result_to_example(state, result) for state in history]


def save_examples(
    examples: list[TrainingExample],
    path: str | Path = DATASET_PATH,
    append: bool = True,
) -> None:
    """Persist training examples as JSON lines."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"

    with output_path.open(mode, encoding="utf-8") as output_file:
        for features, target in examples:
            if len(features) != ENCODED_STATE_SIZE:
                raise ValueError(f"Expected {ENCODED_STATE_SIZE} features, got {len(features)}.")
            record = {"features": features, "target": max(-1.0, min(1.0, float(target)))}
            output_file.write(json.dumps(record, separators=(",", ":")) + "\n")


def load_examples(path: str | Path = DATASET_PATH) -> list[TrainingExample]:
    """Load JSONL training examples from disk."""
    input_path = Path(path)
    if not input_path.exists():
        return []

    examples: list[TrainingExample] = []
    with input_path.open("r", encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            text = line.strip()
            if not text:
                continue
            record = json.loads(text)
            if not isinstance(record, dict):
                raise ValueError(f"Dataset row {line_number} is invalid.")
            features = record.get("features")
            target = record.get("target")
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
) -> list[TrainingExample]:
    """Load examples from a supported external training dataset path."""
    input_path = Path(path)
    suffix = input_path.suffix.lower()
    if suffix == ".csv":
        with input_path.open("r", encoding="utf-8", newline="") as input_file:
            fieldnames = csv.DictReader(input_file).fieldnames or []
        if "moves" in fieldnames and "winner" in fieldnames:
            from train.game_csv_import import load_game_csv_examples

            return load_game_csv_examples(
                input_path,
                max_games=max_games,
                max_positions_per_game=max_positions_per_game,
            )
        return load_csv_examples(input_path)
    if suffix in {".jsonl", ".json"}:
        return load_examples(input_path)
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
