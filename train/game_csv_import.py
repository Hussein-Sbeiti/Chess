from __future__ import annotations

# train/game_csv_import.py
# Chess Project - convert raw chess game CSV rows into evaluator examples

import csv
import re
from copy import deepcopy
from pathlib import Path

from game.ai import all_legal_moves
from game.board import piece_at
from game.coords import FILES, Coord, algebraic_to_index
from game.game_models import MatchState
from game.rules import make_move
from train.self_play_dataset import TrainingExample, self_play_history_to_examples


PIECE_LETTERS = {
    "K": "king",
    "Q": "queen",
    "R": "rook",
    "B": "bishop",
    "N": "knight",
}
PROMOTION_LETTERS = {
    "Q": "queen",
    "R": "rook",
    "B": "bishop",
    "N": "knight",
}
SAN_SUFFIX_RE = re.compile(r"[+#?!]+$")


def result_for_winner(winner: str) -> float:
    """Convert a CSV winner value into a white-positive training target."""
    normalized = winner.strip().lower()
    if normalized == "white":
        return 1.0
    if normalized == "black":
        return -1.0
    return 0.0


def _clean_san(san: str) -> str:
    """Remove common SAN annotation suffixes we do not need for replay."""
    return SAN_SUFFIX_RE.sub("", san.strip())


def _parse_castle_move(state: MatchState, san: str) -> tuple[Coord, Coord, str | None] | None:
    """Return a castling move tuple when the SAN token is castling."""
    normalized = san.replace("0", "O")
    if normalized not in {"O-O", "O-O-O"}:
        return None

    row = 7 if state.current_turn == "white" else 0
    target_col = 6 if normalized == "O-O" else 2
    return (row, 4), (row, target_col), None


def _split_promotion(san: str) -> tuple[str, str | None]:
    """Return SAN without promotion text plus promotion kind."""
    if "=" in san:
        move_text, promotion_text = san.split("=", 1)
        promotion_letter = promotion_text[:1]
        return move_text, PROMOTION_LETTERS.get(promotion_letter)

    if len(san) >= 3 and san[-1] in PROMOTION_LETTERS and san[-2].isdigit():
        return san[:-1], PROMOTION_LETTERS[san[-1]]

    return san, None


def _origin_matches_disambiguation(origin: Coord, disambiguation: str) -> bool:
    """Return whether a legal origin square satisfies SAN disambiguation."""
    origin_row, origin_col = origin
    for char in disambiguation:
        if char in FILES and origin_col != FILES.index(char):
            return False
        if char in "12345678" and origin_row != 8 - int(char):
            return False
    return True


def parse_san_move(state: MatchState, san: str) -> tuple[Coord, Coord, str | None]:
    """Parse one SAN move token into this project's move tuple."""
    cleaned = _clean_san(san)
    castle_move = _parse_castle_move(state, cleaned)
    if castle_move is not None:
        return castle_move

    move_text, promotion_choice = _split_promotion(cleaned)
    if len(move_text) < 2:
        raise ValueError(f"Unsupported move token: {san}")

    target = algebraic_to_index(move_text[-2:])
    prefix = move_text[:-2]
    if prefix.startswith(tuple(PIECE_LETTERS)):
        piece_kind = PIECE_LETTERS[prefix[0]]
        disambiguation = prefix[1:].replace("x", "")
    else:
        piece_kind = "pawn"
        disambiguation = prefix.replace("x", "")

    matches: list[tuple[Coord, Coord, str | None]] = []
    for move in all_legal_moves(state, state.current_turn):
        origin, legal_target, legal_promotion = move
        if legal_target != target:
            continue
        piece = piece_at(state.board, origin)
        if piece is None or piece.kind != piece_kind:
            continue
        expected_promotion = promotion_choice or legal_promotion
        if legal_promotion != expected_promotion:
            continue
        if not _origin_matches_disambiguation(origin, disambiguation):
            continue
        matches.append((origin, legal_target, expected_promotion))

    if len(matches) != 1:
        raise ValueError(f"Could not resolve move {san!r}; matched {len(matches)} legal moves.")
    return matches[0]


def examples_from_san_game(
    moves_text: str,
    winner: str,
    max_positions: int | None = None,
) -> list[TrainingExample]:
    """Replay one SAN move list and return result-labeled position examples."""
    result = result_for_winner(winner)
    state = MatchState()
    history: list[MatchState] = []

    for san in moves_text.split():
        if max_positions is not None and len(history) >= max_positions:
            break
        history.append(deepcopy(state))
        origin, target, promotion_choice = parse_san_move(state, san)
        success, message = make_move(state, origin, target, promotion_choice=promotion_choice)
        if not success:
            raise ValueError(f"Could not apply move {san!r}: {message}")
        if state.winner or state.is_draw:
            break

    return self_play_history_to_examples(history, result)


def load_game_csv_examples(
    path: str | Path,
    max_games: int | None = None,
    max_positions_per_game: int | None = None,
    skip_invalid: bool = True,
) -> list[TrainingExample]:
    """Load a raw games.csv file with moves/winner columns into training examples."""
    input_path = Path(path)
    examples: list[TrainingExample] = []

    with input_path.open("r", encoding="utf-8", newline="") as input_file:
        reader = csv.DictReader(input_file)
        if reader.fieldnames is None or "moves" not in reader.fieldnames or "winner" not in reader.fieldnames:
            raise ValueError("Game CSV must include moves and winner columns.")

        imported_games = 0
        for row in reader:
            if max_games is not None and imported_games >= max_games:
                break
            try:
                game_examples = examples_from_san_game(
                    row.get("moves", ""),
                    row.get("winner", "draw"),
                    max_positions=max_positions_per_game,
                )
            except ValueError:
                if skip_invalid:
                    continue
                raise

            examples.extend(game_examples)
            imported_games += 1

    return examples
