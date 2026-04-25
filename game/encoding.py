from __future__ import annotations

# game/encoding.py
# Chess Project - numeric board encoding for trainable AI

"""
Convert a MatchState into numeric features for the evaluator network.

The first 64 values describe the board from row 0 to row 7, column 0 to
column 7. Extra values describe side-to-move, castling rights, and whether an
en-passant target exists.
"""

from game.game_models import CASTLING_KEYS, MatchState


PIECE_TO_VALUE = {
    ("white", "pawn"): 1.0,
    ("white", "knight"): 2.0,
    ("white", "bishop"): 3.0,
    ("white", "rook"): 4.0,
    ("white", "queen"): 5.0,
    ("white", "king"): 6.0,
    ("black", "pawn"): -1.0,
    ("black", "knight"): -2.0,
    ("black", "bishop"): -3.0,
    ("black", "rook"): -4.0,
    ("black", "queen"): -5.0,
    ("black", "king"): -6.0,
}
BOARD_ONLY_SIZE = 64
ENCODED_STATE_SIZE = 70


def encode_board_only(state: MatchState) -> list[float]:
    """Return the 64 board-square features for a match."""
    values: list[float] = []
    for row in state.board:
        for piece in row:
            if piece is None:
                values.append(0.0)
            else:
                values.append(PIECE_TO_VALUE.get((piece.color, piece.kind), 0.0))
    return values


def encode_state(state: MatchState) -> list[float]:
    """Return the full 70-value feature vector for a match."""
    values = encode_board_only(state)
    values.append(1.0 if state.current_turn == "white" else -1.0)
    values.extend(1.0 if state.castling_rights.get(key, False) else 0.0 for key in CASTLING_KEYS)
    values.append(1.0 if state.en_passant_target is not None else 0.0)
    return values
