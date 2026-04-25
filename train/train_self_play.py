from __future__ import annotations

# train/train_self_play.py
# Chess Project - first self-play training loop

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from game.ai import choose_nn_move
from game.game_models import MatchState
from game.nn_model import TinyChessNet
from game.self_play import play_self_play_game
from train.self_play_dataset import DATASET_PATH, load_examples, save_examples, self_play_history_to_examples
from train.train_supervised import MODEL_PATH, train_model


def generate_self_play_examples(
    model: TinyChessNet,
    games: int = 20,
) -> list[tuple[list[float], float]]:
    """Generate result-labeled examples from neural self-play."""
    examples: list[tuple[list[float], float]] = []
    for _ in range(games):
        history, result = play_self_play_game(
            MatchState,
            lambda state: choose_nn_move(state, "white", model),
            lambda state: choose_nn_move(state, "black", model),
        )
        examples.extend(self_play_history_to_examples(history, result))
    return examples


def generate_and_save_self_play_examples(
    model: TinyChessNet,
    games: int = 20,
    path: str | Path = DATASET_PATH,
    append: bool = True,
) -> list[tuple[list[float], float]]:
    """Generate self-play examples and persist them for future training runs."""
    examples = generate_self_play_examples(model, games=games)
    save_examples(examples, path=path, append=append)
    return examples


def main() -> None:
    """Generate self-play data, train from accumulated labels, and save weights."""
    model = TinyChessNet()
    if MODEL_PATH.exists():
        model.load(MODEL_PATH)

    generated = generate_and_save_self_play_examples(model)
    dataset = load_examples()
    if not dataset:
        dataset = generated
    trained_model = train_model(dataset, epochs=5, lr=0.0005, model=model)
    trained_model.save(MODEL_PATH)
    print(f"saved {len(generated)} examples to {DATASET_PATH}")
    print(f"saved {MODEL_PATH}")


if __name__ == "__main__":
    main()
