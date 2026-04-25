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


FAIRNESS_MAGNITUDE_TOLERANCE = 0.25
NEUTRAL_SCORE_TOLERANCE = 0.20
MEDIUM_LATENCY_LIMIT_MS = 50.0
HARD_LATENCY_LIMIT_MS = 500.0


def build_material_state(
    white_pieces: list[tuple[str, str]] | None = None,
    black_pieces: list[tuple[str, str]] | None = None,
) -> MatchState:
    """Build a minimal legal board useful for evaluator sanity checks."""
    board = create_empty_board()
    set_piece(board, algebraic_to_index("e1"), make_piece("white", "king"))
    set_piece(board, algebraic_to_index("e8"), make_piece("black", "king"))
    for square, kind in white_pieces or []:
        set_piece(board, algebraic_to_index(square), make_piece("white", kind))
    for square, kind in black_pieces or []:
        set_piece(board, algebraic_to_index(square), make_piece("black", kind))
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


def material_pair_report(
    name: str,
    white_state: MatchState,
    black_state: MatchState,
    model: TinyChessNet,
) -> dict[str, object]:
    """Evaluate a paired white-advantage/black-advantage material scenario."""
    white_score = evaluate_with_model(white_state, model, perspective="white")
    black_score = evaluate_with_model(black_state, model, perspective="white")
    magnitude_gap = abs(abs(white_score) - abs(black_score))
    return {
        "name": name,
        "white_score": white_score,
        "black_score": black_score,
        "ordering_passed": white_score > black_score,
        "fairness_gap": magnitude_gap,
        "fairness_passed": magnitude_gap <= FAIRNESS_MAGNITUDE_TOLERANCE,
    }


def run_evaluation(model_path: str | Path = MODEL_PATH, iterations: int = 3) -> dict[str, object]:
    """Run evaluator sanity checks and return report data."""
    model_path = Path(model_path)
    model = load_model(model_path)

    material_pairs = [
        material_pair_report(
            "queen_advantage",
            build_material_state(white_pieces=[("d1", "queen")]),
            build_material_state(black_pieces=[("d8", "queen")]),
            model,
        ),
        material_pair_report(
            "rook_advantage",
            build_material_state(white_pieces=[("a1", "rook")]),
            build_material_state(black_pieces=[("a8", "rook")]),
            model,
        ),
        material_pair_report(
            "pawn_advantage",
            build_material_state(white_pieces=[("a2", "pawn")]),
            build_material_state(black_pieces=[("a7", "pawn")]),
            model,
        ),
    ]
    even_positions = {
        "bare_kings": evaluate_with_model(build_material_state(), model, perspective="white"),
        "equal_queens": evaluate_with_model(
            build_material_state(
                white_pieces=[("d1", "queen")],
                black_pieces=[("d8", "queen")],
            ),
            model,
            perspective="white",
        ),
        "equal_rooks": evaluate_with_model(
            build_material_state(
                white_pieces=[("a1", "rook")],
                black_pieces=[("a8", "rook")],
            ),
            model,
            perspective="white",
        ),
    }

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

    all_scores = [
        *(pair["white_score"] for pair in material_pairs),
        *(pair["black_score"] for pair in material_pairs),
        *even_positions.values(),
    ]
    checks = {
        "scores_are_finite": all(isinstance(score, float) and score == score for score in all_scores),
        "queen_material_ordering": material_pairs[0]["ordering_passed"],
        "rook_material_ordering": material_pairs[1]["ordering_passed"],
        "pawn_material_ordering": material_pairs[2]["ordering_passed"],
        "queen_fairness": material_pairs[0]["fairness_passed"],
        "rook_fairness": material_pairs[1]["fairness_passed"],
        "pawn_fairness": material_pairs[2]["fairness_passed"],
        "neutral_positions_near_zero": all(
            abs(score) <= NEUTRAL_SCORE_TOLERANCE for score in even_positions.values()
        ),
        "medium_returns_move": medium_move is not None,
        "hard_returns_move": hard_move is not None,
        "hard_captures_rook": move_to_text(hard_move) == "d5->d1",
        "medium_latency_under_limit": medium_ms <= MEDIUM_LATENCY_LIMIT_MS,
        "hard_latency_under_limit": hard_ms <= HARD_LATENCY_LIMIT_MS,
    }
    passed_count = sum(1 for passed in checks.values() if passed)

    return {
        "model_path": str(model_path),
        "model_exists": model_path.exists(),
        "summary": {
            "passed": passed_count,
            "total": len(checks),
        },
        "material_pairs": material_pairs,
        "even_positions": even_positions,
        "checks": checks,
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
    summary = report["summary"]
    material_pairs = report["material_pairs"]
    even_positions = report["even_positions"]
    checks = report["checks"]
    moves = report["moves"]
    latency = report["latency_ms"]
    lines = [
        f"Model path: {report['model_path']}",
        f"Model exists: {report['model_exists']}",
        f"Evaluation summary: {summary['passed']}/{summary['total']} checks passed",
        "Material pairs:",
    ]
    for pair in material_pairs:
        lines.append(
            "  "
            f"{pair['name']}: white={pair['white_score']:.6f} "
            f"black={pair['black_score']:.6f} fairness_gap={pair['fairness_gap']:.6f}"
        )
    lines.append("Neutral positions:")
    for name, score in even_positions.items():
        lines.append(f"  {name}: {score:.6f}")
    lines.extend(
        [
        "Checks:",
        ]
    )
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
