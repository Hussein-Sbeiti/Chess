from __future__ import annotations

# train/train_self_play.py
# Chess Project - first self-play training loop

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from game.ai import choose_nn_move
from game.encoding import encode_state
from game.game_models import MatchState
from game.nn_model import TinyChessNet
from game.self_play import play_self_play_game
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
        examples.extend((encode_state(state), result) for state in history)
    return examples


def main() -> None:
    """Train from self-play result labels and save updated weights."""
    model = TinyChessNet()
    if MODEL_PATH.exists():
        model.load(MODEL_PATH)
    dataset = generate_self_play_examples(model)
    trained_model = train_model(dataset, epochs=5, lr=0.0005, model=model)
    trained_model.save(MODEL_PATH)
    print(f"saved {MODEL_PATH}")


if __name__ == "__main__":
    main()
