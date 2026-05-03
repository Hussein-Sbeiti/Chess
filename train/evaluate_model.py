"""Command-line evaluator sanity checks and history reporting."""
from __future__ import annotations


# train/evaluate_model.py
# Chess Project - quick sanity checks for evaluator weights

import argparse
import json
import random
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Support running this script directly with python train/evaluate_model.py.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from game.ai import choose_nn_move, choose_nn_search_move, evaluate_with_model
from game.board import create_empty_board, set_piece
from game.coords import algebraic_to_index, index_to_algebraic
from game.game_models import MatchState
from game.nn_model import TinyChessNet
from game.rules import make_move
from game.pieces import make_piece
from train.train_supervised import MODEL_PATH


EVALUATION_HISTORY_PATH = PROJECT_ROOT / "data" / "evaluation_history.jsonl"
TRAINING_METADATA_PATH = PROJECT_ROOT / "data" / "games_training_metadata.json"
# Tolerances define what "reasonable" means for quick evaluator sanity checks.
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
    # Include kings so rule/evaluator helpers receive a legal-enough position.
    set_piece(board, algebraic_to_index("e1"), make_piece("white", "king"))
    set_piece(board, algebraic_to_index("e8"), make_piece("black", "king"))
    # Optional material lets tests create mirrored advantage positions.
    for square, kind in white_pieces or []:
        set_piece(board, algebraic_to_index(square), make_piece("white", kind))
    for square, kind in black_pieces or []:
        set_piece(board, algebraic_to_index(square), make_piece("black", kind))
    return MatchState(board=board)


def build_capture_choice_state() -> MatchState:
    """Build a position where black can capture a rook or a pawn."""
    board = create_empty_board()
    # This tactical position checks whether the AI prefers the valuable capture.
    set_piece(board, algebraic_to_index("a1"), make_piece("white", "king"))
    set_piece(board, algebraic_to_index("h8"), make_piece("black", "king"))
    set_piece(board, algebraic_to_index("d5"), make_piece("black", "queen"))
    set_piece(board, algebraic_to_index("d1"), make_piece("white", "rook"))
    set_piece(board, algebraic_to_index("a5"), make_piece("white", "pawn"))
    return MatchState(board=board, current_turn="black")


def move_to_text(move) -> str:
    """Return a compact text form for a move tuple."""
    # None is printed explicitly so missing-move failures are easy to read.
    if move is None:
        return "None"
    origin, target, promotion_choice = move
    # Promotion text is appended only for promotion moves.
    promotion_text = f"={promotion_choice}" if promotion_choice else ""
    return f"{index_to_algebraic(origin)}->{index_to_algebraic(target)}{promotion_text}"


def load_model(path: str | Path = MODEL_PATH) -> TinyChessNet:
    """Load evaluator weights, or return a deterministic fresh model if absent."""
    # The evaluation script should still run before any trained weights exist.
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
    # Both states are scored from White's perspective so ordering should be obvious.
    white_score = evaluate_with_model(white_state, model, perspective="white")
    black_score = evaluate_with_model(black_state, model, perspective="white")
    magnitude_gap = abs(abs(white_score) - abs(black_score))
    # Fairness checks whether mirrored advantages have similar absolute strength.
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
    # Normalize the path once so reports and existence checks agree.
    model_path = Path(model_path)
    model = load_model(model_path)

    # Material pairs test whether the evaluator orders obvious advantages correctly.
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
        # Balanced positions should stay close to zero.
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

    # Capture-choice checks look at actual move selection, not just scalar scores.
    capture_state = build_capture_choice_state()
    medium_move = choose_nn_move(capture_state, "black", model)
    hard_move = choose_nn_search_move(capture_state, "black", model, depth=2)

    # Latency checks guard against AI choices becoming too slow for UI play.
    latency_state = MatchState(current_turn="black")
    medium_start = time.perf_counter()
    for _ in range(max(1, iterations)):
        choose_nn_move(latency_state, "black", model)
    medium_ms = ((time.perf_counter() - medium_start) / max(1, iterations)) * 1000.0

    hard_start = time.perf_counter()
    for _ in range(max(1, iterations)):
        choose_nn_search_move(latency_state, "black", model, depth=2)
    hard_ms = ((time.perf_counter() - hard_start) / max(1, iterations)) * 1000.0

    # Gather every scalar score for a finite-number sanity check.
    all_scores = [
        *(pair["white_score"] for pair in material_pairs),
        *(pair["black_score"] for pair in material_pairs),
        *even_positions.values(),
    ]
    checks = {
        # NaN is the only float value not equal to itself.
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
    # Count pass/fail summary without losing individual check names.
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


def choose_match_move(
    state: MatchState,
    color: str,
    model: TinyChessNet,
    search_depth: int = 1,
):
    """Choose one model-vs-model move at the requested search depth."""
    if search_depth <= 1:
        return choose_nn_move(state, color, model)
    return choose_nn_search_move(state, color, model, depth=search_depth)


def play_model_match(
    white_model: TinyChessNet,
    black_model: TinyChessNet,
    max_turns: int = 120,
    search_depth: int = 1,
    seed: int | None = None,
) -> dict[str, object]:
    """Play one capped model-vs-model game and return a compact result."""
    if seed is not None:
        random.seed(seed)

    state = MatchState()
    turns_played = 0
    for turns_played in range(max(1, max_turns)):
        if state.winner or state.is_draw:
            break
        model = white_model if state.current_turn == "white" else black_model
        move = choose_match_move(state, state.current_turn, model, search_depth=search_depth)
        if move is None:
            break
        origin, target, promotion_choice = move
        success, _message = make_move(state, origin, target, promotion_choice=promotion_choice)
        if not success:
            break
    else:
        turns_played = max(1, max_turns)

    if state.winner == "white":
        result = "white"
    elif state.winner == "black":
        result = "black"
    else:
        result = "draw"

    return {
        "result": result,
        "winner": state.winner,
        "is_draw": state.is_draw or result == "draw",
        "turns": turns_played,
    }


def run_model_match_series(
    model_a_path: str | Path,
    model_b_path: str | Path,
    games: int = 4,
    max_turns: int = 120,
    search_depth: int = 1,
    seed: int = 1,
) -> dict[str, object]:
    """Run alternating-color model matches and return aggregate score data."""
    model_a = load_model(model_a_path)
    model_b = load_model(model_b_path)
    game_count = max(1, games)
    game_reports: list[dict[str, object]] = []
    model_a_wins = 0
    model_b_wins = 0
    draws = 0

    for game_index in range(game_count):
        model_a_is_white = game_index % 2 == 0
        white_model = model_a if model_a_is_white else model_b
        black_model = model_b if model_a_is_white else model_a
        game = play_model_match(
            white_model,
            black_model,
            max_turns=max_turns,
            search_depth=search_depth,
            seed=seed + game_index,
        )
        result = game["result"]
        if result == "draw":
            draws += 1
            model_a_points = 0.5
            model_b_points = 0.5
        else:
            model_a_won = (result == "white" and model_a_is_white) or (result == "black" and not model_a_is_white)
            if model_a_won:
                model_a_wins += 1
                model_a_points = 1.0
                model_b_points = 0.0
            else:
                model_b_wins += 1
                model_a_points = 0.0
                model_b_points = 1.0

        game_reports.append(
            {
                "game": game_index + 1,
                "model_a_color": "white" if model_a_is_white else "black",
                "result": result,
                "turns": game["turns"],
                "model_a_points": model_a_points,
                "model_b_points": model_b_points,
            }
        )

    model_a_score = model_a_wins + (draws * 0.5)
    model_b_score = model_b_wins + (draws * 0.5)
    return {
        "model_a_path": str(model_a_path),
        "model_b_path": str(model_b_path),
        "games": game_count,
        "max_turns": max(1, max_turns),
        "search_depth": max(1, search_depth),
        "seed": seed,
        "summary": {
            "model_a_wins": model_a_wins,
            "model_b_wins": model_b_wins,
            "draws": draws,
            "model_a_score": model_a_score,
            "model_b_score": model_b_score,
            "model_a_score_rate": model_a_score / game_count,
        },
        "game_results": game_reports,
    }


def format_match_series(report: dict[str, object]) -> str:
    """Return a readable model-vs-model match report."""
    summary = report["summary"]
    lines = [
        f"Model A: {report['model_a_path']}",
        f"Model B: {report['model_b_path']}",
        f"Games: {report['games']}  max_turns={report['max_turns']}  depth={report['search_depth']}",
        (
            "Score: "
            f"A {summary['model_a_score']:.1f} - B {summary['model_b_score']:.1f} "
            f"(A score rate {summary['model_a_score_rate']:.3f})"
        ),
        (
            "Results: "
            f"A wins={summary['model_a_wins']} "
            f"B wins={summary['model_b_wins']} "
            f"draws={summary['draws']}"
        ),
        "Games:",
    ]
    for game in report["game_results"]:
        lines.append(
            "  "
            f"{game['game']}: A as {game['model_a_color']} "
            f"result={game['result']} turns={game['turns']} "
            f"points={game['model_a_points']:.1f}-{game['model_b_points']:.1f}"
        )
    return "\n".join(lines)


def format_report(report: dict[str, object]) -> str:
    """Return a human-readable model evaluation report."""
    # Pull typed-ish sections out of the report dict for readable formatting below.
    summary = report["summary"]
    material_pairs = report["material_pairs"]
    even_positions = report["even_positions"]
    checks = report["checks"]
    moves = report["moves"]
    latency = report["latency_ms"]
    lines = [
        # First lines summarize the model file and overall result.
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


def load_json_object(path: str | Path) -> dict[str, object]:
    """Load a JSON object from disk, returning an empty object when absent."""
    input_path = Path(path)
    if not input_path.exists():
        return {}
    data = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected {input_path} to contain a JSON object.")
    return data


def build_history_record(
    report: dict[str, object],
    metadata_path: str | Path = TRAINING_METADATA_PATH,
) -> dict[str, object]:
    """Return one compact, comparable evaluation-history record."""
    metadata = load_json_object(metadata_path)
    summary = report["summary"]
    material_pairs = report["material_pairs"]
    import_summary = metadata.get("import_summary", {})
    dataset_summary = metadata.get("dataset", {})
    if not isinstance(import_summary, dict):
        import_summary = {}
    if not isinstance(dataset_summary, dict):
        dataset_summary = {}

    return {
        "evaluated_at": datetime.now().isoformat(timespec="seconds"),
        "model_path": report["model_path"],
        "model_exists": report["model_exists"],
        "checks_passed": summary["passed"],
        "checks_total": summary["total"],
        "all_checks_passed": summary["passed"] == summary["total"],
        "training": {
            "generated_at": metadata.get("generated_at"),
            "final_training_loss": metadata.get("final_training_loss"),
            "epochs": metadata.get("epochs"),
            "learning_rate": metadata.get("learning_rate"),
            "result_weight": metadata.get("result_weight"),
            "material_weight": metadata.get("material_weight"),
            "material_calibration_examples": metadata.get("material_calibration_examples"),
            "imported_games": import_summary.get("imported_games"),
            "attempted_games": import_summary.get("attempted_games"),
            "skipped_games": import_summary.get("skipped_games"),
            "dataset_examples": dataset_summary.get("example_count"),
        },
        "material_fairness_gaps": {
            str(pair["name"]): pair["fairness_gap"] for pair in material_pairs
        },
        "material_scores": {
            str(pair["name"]): {
                "white": pair["white_score"],
                "black": pair["black_score"],
            }
            for pair in material_pairs
        },
        "neutral_scores": report["even_positions"],
        "moves": report["moves"],
        "latency_ms": report["latency_ms"],
        "checks": report["checks"],
    }


def append_evaluation_history(
    report: dict[str, object],
    history_path: str | Path = EVALUATION_HISTORY_PATH,
    metadata_path: str | Path = TRAINING_METADATA_PATH,
) -> dict[str, object]:
    """Append one evaluation record to the JSONL history file."""
    record = build_history_record(report, metadata_path=metadata_path)
    output_path = Path(history_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as output_file:
        output_file.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    return record


def load_evaluation_history(path: str | Path = EVALUATION_HISTORY_PATH) -> list[dict[str, object]]:
    """Load evaluation history records from JSONL."""
    input_path = Path(path)
    if not input_path.exists():
        return []

    records: list[dict[str, object]] = []
    with input_path.open("r", encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            text = line.strip()
            if not text:
                continue
            record = json.loads(text)
            if not isinstance(record, dict):
                raise ValueError(f"Evaluation history row {line_number} is invalid.")
            records.append(record)
    return records


def _format_optional_number(value: object, digits: int = 3) -> str:
    """Format optional numeric values for compact history tables."""
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return "-"


def format_history(records: list[dict[str, object]], limit: int = 5) -> str:
    """Return a compact comparison table for recent evaluation history."""
    if not records:
        return "No evaluation history found."

    recent = records[-max(1, limit) :]
    rows = [
        [
            "evaluated_at",
            "checks",
            "games",
            "examples",
            "loss",
            "queen_gap",
            "rook_gap",
            "pawn_gap",
            "medium_ms",
            "hard_ms",
            "hard_move",
        ]
    ]
    for record in recent:
        training = record.get("training", {})
        fairness = record.get("material_fairness_gaps", {})
        latency = record.get("latency_ms", {})
        moves = record.get("moves", {})
        if not isinstance(training, dict):
            training = {}
        if not isinstance(fairness, dict):
            fairness = {}
        if not isinstance(latency, dict):
            latency = {}
        if not isinstance(moves, dict):
            moves = {}

        rows.append(
            [
                str(record.get("evaluated_at", "-")),
                f"{record.get('checks_passed', '-')}/{record.get('checks_total', '-')}",
                _format_optional_number(training.get("imported_games"), digits=0),
                _format_optional_number(training.get("dataset_examples"), digits=0),
                _format_optional_number(training.get("final_training_loss"), digits=6),
                _format_optional_number(fairness.get("queen_advantage"), digits=4),
                _format_optional_number(fairness.get("rook_advantage"), digits=4),
                _format_optional_number(fairness.get("pawn_advantage"), digits=4),
                _format_optional_number(latency.get("medium"), digits=2),
                _format_optional_number(latency.get("hard"), digits=2),
                str(moves.get("hard_capture_choice", "-")),
            ]
        )

    widths = [max(len(row[index]) for row in rows) for index in range(len(rows[0]))]
    lines = []
    for row_index, row in enumerate(rows):
        lines.append("  ".join(value.ljust(widths[index]) for index, value in enumerate(row)))
        if row_index == 0:
            lines.append("  ".join("-" * width for width in widths))
    return "\n".join(lines)


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(description="Evaluate chess model sanity checks.")
    parser.add_argument("--model-path", type=Path, default=MODEL_PATH, help="Model weight path.")
    parser.add_argument("--iterations", type=int, default=3, help="Latency averaging iterations.")
    parser.add_argument(
        "--compare-model",
        type=Path,
        default=None,
        help="Run model-path against another model instead of evaluator sanity checks.",
    )
    parser.add_argument("--match-games", type=int, default=4, help="Number of model-vs-model games.")
    parser.add_argument("--match-max-turns", type=int, default=120, help="Maximum half-moves per match game.")
    parser.add_argument("--match-depth", type=int, default=1, help="Search depth for model-vs-model moves.")
    parser.add_argument("--match-seed", type=int, default=1, help="Base random seed for model-vs-model games.")
    parser.add_argument(
        "--metadata-path",
        type=Path,
        default=TRAINING_METADATA_PATH,
        help="Training metadata path to include in evaluation history.",
    )
    parser.add_argument(
        "--history-path",
        type=Path,
        default=EVALUATION_HISTORY_PATH,
        help="JSONL path where evaluation history is appended.",
    )
    parser.add_argument("--no-history", action="store_true", help="Print evaluation without appending history.")
    parser.add_argument(
        "--show-history",
        action="store_true",
        help="Print recent evaluation history instead of running model checks.",
    )
    parser.add_argument("--history-limit", type=int, default=5, help="Number of recent history rows to print.")
    return parser


def main(argv: list[str] | None = None) -> None:
    """Run model checks and print a report."""
    args = build_arg_parser().parse_args(argv)
    if args.show_history:
        print(format_history(load_evaluation_history(args.history_path), limit=max(1, args.history_limit)))
        return
    if args.compare_model is not None:
        match_report = run_model_match_series(
            args.model_path,
            args.compare_model,
            games=max(1, args.match_games),
            max_turns=max(1, args.match_max_turns),
            search_depth=max(1, args.match_depth),
            seed=args.match_seed,
        )
        print(format_match_series(match_report))
        return

    report = run_evaluation(args.model_path, iterations=max(1, args.iterations))
    print(format_report(report))
    if not args.no_history:
        append_evaluation_history(report, history_path=args.history_path, metadata_path=args.metadata_path)
        print(f"Saved evaluation history to {args.history_path}")


if __name__ == "__main__":
    main()
