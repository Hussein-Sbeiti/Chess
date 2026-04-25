from __future__ import annotations

# train/evaluate_model.py
# Chess Project - quick sanity checks for evaluator weights

import argparse
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from game.ai import choose_nn_move, choose_nn_search_move, evaluate_with_model
from game.board import create_empty_board, set_piece
from game.coords import algebraic_to_index, index_to_algebraic
from game.game_models import MatchState
from game.nn_model import TinyChessNet
from game.pieces import make_piece
from train.train_supervised import MODEL_PATH


def build_material_state(white_queen: bool = True, black_queen: bool = True) -> MatchState:
    """Build a minimal legal board useful for evaluator sanity checks."""
    board = create_empty_board()
    set_piece(board, algebraic_to_index("e1"), make_piece("white", "king"))
    set_piece(board, algebraic_to_index("e8"), make_piece("black", "king"))
    if white_queen:
        set_piece(board, algebraic_to_index("d1"), make_piece("white", "queen"))
    if black_queen:
        set_piece(board, algebraic_to_index("d8"), make_piece("black", "queen"))
    return MatchState(board=board)


def build_capture_choice_state() -> MatchState:
    """Build a position where black can capture a rook or a pawn."""
    board = create_empty_board()
    set_piece(board, algebraic_to_index("a1"), make_piece("white", "king"))
    set_piece(board, algebraic_to_index("h8"), make_piece("black", "king"))
    set_piece(board, algebraic_to_index("d5"), make_piece("black", "queen"))
    set_piece(board, algebraic_to_index("d1"), make_piece("white", "rook"))
    set_piece(board, algebraic_to_index("a5"), make_piece("white", "pawn"))
    return MatchState(board=board, current_turn="black")


def move_to_text(move) -> str:
    """Return a compact text form for a move tuple."""
    if move is None:
        return "None"
    origin, target, promotion_choice = move
    promotion_text = f"={promotion_choice}" if promotion_choice else ""
    return f"{index_to_algebraic(origin)}->{index_to_algebraic(target)}{promotion_text}"


def load_model(path: str | Path = MODEL_PATH) -> TinyChessNet:
    """Load evaluator weights, or return a deterministic fresh model if absent."""
    model = TinyChessNet()
    model_path = Path(path)
    if model_path.exists():
        model.load(model_path)
    return model


def run_evaluation(model_path: str | Path = MODEL_PATH, iterations: int = 3) -> dict[str, object]:
    """Run evaluator sanity checks and return report data."""
    model_path = Path(model_path)
    model = load_model(model_path)

    white_advantage = build_material_state(white_queen=True, black_queen=False)
    black_advantage = build_material_state(white_queen=False, black_queen=True)
    even_position = build_material_state(white_queen=True, black_queen=True)

    white_score = evaluate_with_model(white_advantage, model, perspective="white")
    black_score = evaluate_with_model(black_advantage, model, perspective="white")
    even_score = evaluate_with_model(even_position, model, perspective="white")

    capture_state = build_capture_choice_state()
    medium_move = choose_nn_move(capture_state, "black", model)
    hard_move = choose_nn_search_move(capture_state, "black", model, depth=2)

    latency_state = MatchState(current_turn="black")
    medium_start = time.perf_counter()
    for _ in range(max(1, iterations)):
        choose_nn_move(latency_state, "black", model)
    medium_ms = ((time.perf_counter() - medium_start) / max(1, iterations)) * 1000.0

    hard_start = time.perf_counter()
    for _ in range(max(1, iterations)):
        choose_nn_search_move(latency_state, "black", model, depth=2)
    hard_ms = ((time.perf_counter() - hard_start) / max(1, iterations)) * 1000.0

    return {
        "model_path": str(model_path),
        "model_exists": model_path.exists(),
        "scores": {
            "white_queen_advantage": white_score,
            "black_queen_advantage": black_score,
            "even_queens": even_score,
        },
        "checks": {
            "white_advantage_scores_higher_than_black": white_score > black_score,
            "scores_are_finite": all(
                isinstance(score, float) and score == score
                for score in (white_score, black_score, even_score)
            ),
            "medium_returns_move": medium_move is not None,
            "hard_returns_move": hard_move is not None,
        },
        "moves": {
            "medium_capture_choice": move_to_text(medium_move),
            "hard_capture_choice": move_to_text(hard_move),
        },
        "latency_ms": {
            "medium": medium_ms,
            "hard": hard_ms,
        },
    }


def format_report(report: dict[str, object]) -> str:
    """Return a human-readable model evaluation report."""
    scores = report["scores"]
    checks = report["checks"]
    moves = report["moves"]
    latency = report["latency_ms"]
    lines = [
        f"Model path: {report['model_path']}",
        f"Model exists: {report['model_exists']}",
        "Scores:",
        f"  white queen advantage: {scores['white_queen_advantage']:.6f}",
        f"  black queen advantage: {scores['black_queen_advantage']:.6f}",
        f"  even queens: {scores['even_queens']:.6f}",
        "Checks:",
    ]
    for name, passed in checks.items():
        lines.append(f"  {'PASS' if passed else 'FAIL'} {name}")
    lines.extend(
        [
            "Move choices:",
            f"  medium: {moves['medium_capture_choice']}",
            f"  hard: {moves['hard_capture_choice']}",
            "Latency:",
            f"  medium: {latency['medium']:.3f} ms",
            f"  hard: {latency['hard']:.3f} ms",
        ]
    )
    return "\n".join(lines)


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(description="Evaluate chess model sanity checks.")
    parser.add_argument("--model-path", type=Path, default=MODEL_PATH, help="Model weight path.")
    parser.add_argument("--iterations", type=int, default=3, help="Latency averaging iterations.")
    return parser


def main(argv: list[str] | None = None) -> None:
    """Run model checks and print a report."""
    args = build_arg_parser().parse_args(argv)
    report = run_evaluation(args.model_path, iterations=max(1, args.iterations))
    print(format_report(report))


if __name__ == "__main__":
    main()
