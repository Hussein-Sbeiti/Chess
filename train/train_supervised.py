from __future__ import annotations

# train/train_supervised.py
# Chess Project - first supervised evaluator training loop

import random
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from game.ai import all_legal_moves, apply_simulated_move
from game.encoding import encode_state
from game.game_models import MatchState
from game.nn_model import TinyChessNet


MODEL_PATH = PROJECT_ROOT / "models" / "chess_eval_weights.json"
PIECE_VALUES = {
    "pawn": 1.0,
    "knight": 3.0,
    "bishop": 3.0,
    "rook": 5.0,
    "queen": 9.0,
    "king": 0.0,
}


def simple_material_score(state: MatchState) -> float:
    """Return a white-positive material target normalized to [-1, 1]."""
    score = 0.0
    for row in state.board:
        for piece in row:
            if piece is None:
                continue
            value = PIECE_VALUES.get(piece.kind, 0.0)
            score += value if piece.color == "white" else -value
    return max(-1.0, min(1.0, score / 20.0))


def random_playout_state(max_random_moves: int = 20) -> MatchState:
    """Create a position by playing random legal moves from the starting board."""
    state = MatchState()
    for _ in range(random.randint(0, max_random_moves)):
        if state.winner or state.is_draw:
            break
        moves = all_legal_moves(state, state.current_turn)
        if not moves:
            break
        state = apply_simulated_move(state, random.choice(moves))
    return state


def generate_training_examples(num_samples: int = 2000) -> list[tuple[list[float], float]]:
    """Generate simple supervised examples labeled by material balance."""
    dataset: list[tuple[list[float], float]] = []
    for _ in range(num_samples):
        state = random_playout_state()
        dataset.append((encode_state(state), simple_material_score(state)))
    return dataset


def train_model(
    dataset: list[tuple[list[float], float]],
    epochs: int = 10,
    lr: float = 0.001,
    model: TinyChessNet | None = None,
) -> TinyChessNet:
    """Train a tiny evaluator on encoded positions and scalar labels."""
    trained_model, _loss_history = train_model_with_history(
        dataset,
        epochs=epochs,
        lr=lr,
        model=model,
    )
    return trained_model


def train_model_with_history(
    dataset: list[tuple[list[float], float]],
    epochs: int = 10,
    lr: float = 0.001,
    model: TinyChessNet | None = None,
) -> tuple[TinyChessNet, list[float]]:
    """Train an evaluator and return per-epoch average loss values."""
    if not dataset:
        raise ValueError("Cannot train on an empty dataset.")

    model = model or TinyChessNet(input_size=len(dataset[0][0]))
    loss_history: list[float] = []
    for epoch in range(epochs):
        random.shuffle(dataset)
        total_loss = 0.0
        for features, target in dataset:
            total_loss += model.train_step(features, target, lr=lr)
        average_loss = total_loss / len(dataset)
        loss_history.append(average_loss)
        print(f"epoch={epoch + 1} loss={average_loss:.6f}")
    return model, loss_history


def main() -> None:
    """Train the first material evaluator and save it for the UI AI."""
    dataset = generate_training_examples()
    model = train_model(dataset)
    model.save(MODEL_PATH)
    print(f"saved {MODEL_PATH}")


if __name__ == "__main__":
    main()
