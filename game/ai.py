from __future__ import annotations

# game/ai.py
# Chess Project - lightweight AI personalities
# Created: 2026-04-19

"""
This file provides simple computer-move selection for the chess app.

The goal is not to build a strong engine yet. Instead, it gives us three
distinct personalities that pick from legal moves in noticeably different ways.
"""

from copy import deepcopy
import random

from game.board import piece_at
from game.coords import Coord
from game.rules import is_in_check, is_promotion_move, legal_moves_for_piece, make_move, other_color


AI_PERSONALITY_LABELS = {
    "random": "Random",
    "aggressive": "Aggressive",
    "defensive": "Defensive",
}
PIECE_VALUES = {
    "pawn": 1,
    "knight": 3,
    "bishop": 3,
    "rook": 5,
    "queen": 9,
    "king": 0,
}


def normalize_ai_personality(personality: str) -> str:
    """Return a supported AI personality name."""
    return personality if personality in AI_PERSONALITY_LABELS else "random"


def _promotion_choice_for_move(state, origin: Coord, target: Coord) -> str | None:
    """Return the AI's promotion choice for a move when needed."""
    if is_promotion_move(state.board, origin, target):
        return "queen"
    return None


def all_legal_moves(state, color: str) -> list[tuple[Coord, Coord, str | None]]:
    """Collect every legal move available for one side."""
    moves: list[tuple[Coord, Coord, str | None]] = []
    for row in range(8):
        for col in range(8):
            piece = state.board[row][col]
            if piece is None or piece.color != color:
                continue
            origin = (row, col)
            for target in legal_moves_for_piece(state, origin):
                moves.append((origin, target, _promotion_choice_for_move(state, origin, target)))
    return moves


def _captured_piece_value(state, origin: Coord, target: Coord) -> int:
    """Return the material value gained by moving to the target square."""
    moving_piece = piece_at(state.board, origin)
    captured_piece = piece_at(state.board, target)
    if captured_piece is None and moving_piece is not None and moving_piece.kind == "pawn" and origin[1] != target[1]:
        capture_square = (origin[0], target[1])
        captured_piece = piece_at(state.board, capture_square)
    if captured_piece is None:
        return 0
    return PIECE_VALUES.get(captured_piece.kind, 0)


def _attacked_material(board, color: str) -> int:
    """Estimate how much of one side's material is currently under attack."""
    enemy_color = other_color(color)
    score = 0
    for row in range(8):
        for col in range(8):
            piece = board[row][col]
            if piece is None or piece.color != color:
                continue
            square = (row, col)
            from game.rules import is_square_attacked

            if is_square_attacked(board, square, enemy_color):
                score += PIECE_VALUES.get(piece.kind, 0)
    return score


def _score_move_for_personality(state, color: str, move, personality: str) -> int:
    """Score one legal move according to the chosen AI personality."""
    origin, target, promotion_choice = move
    simulated_state = deepcopy(state)
    success, _ = make_move(simulated_state, origin, target, promotion_choice=promotion_choice)
    if not success:
        return -10_000

    capture_value = _captured_piece_value(state, origin, target)
    moving_piece = piece_at(state.board, origin)
    promotion_bonus = 8 if promotion_choice == "queen" else 0

    if simulated_state.winner == color:
        return 100_000

    enemy_color = other_color(color)
    check_bonus = 30 if is_in_check(simulated_state.board, enemy_color) else 0

    if personality == "aggressive":
        return (capture_value * 25) + (promotion_bonus * 3) + check_bonus

    if personality == "defensive":
        moved_piece_risk = 0
        from game.rules import is_square_attacked

        if moving_piece is not None and is_square_attacked(simulated_state.board, target, enemy_color):
            moved_piece_risk = PIECE_VALUES.get(moving_piece.kind, 0)
        attacked_material_penalty = _attacked_material(simulated_state.board, color)
        return (capture_value * 8) + promotion_bonus + check_bonus - (attacked_material_penalty * 6) - (moved_piece_risk * 10)

    return 0


def choose_ai_move(state, color: str, personality: str = "random") -> tuple[Coord, Coord, str | None] | None:
    """Pick one legal move for the computer player."""
    legal_moves = all_legal_moves(state, color)
    if not legal_moves:
        return None

    personality = normalize_ai_personality(personality)
    if personality == "random":
        return random.choice(legal_moves)

    best_score: int | None = None
    best_moves: list[tuple[Coord, Coord, str | None]] = []
    for move in legal_moves:
        score = _score_move_for_personality(state, color, move, personality)
        if best_score is None or score > best_score:
            best_score = score
            best_moves = [move]
        elif score == best_score:
            best_moves.append(move)

    return random.choice(best_moves)
