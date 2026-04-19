from __future__ import annotations

# game/game_models.py
# Chess Project - shared match state
# Created: 2026-04-15

"""
This file stores the pure data models that describe an active chess match.

MoveRecord
- stores what moved, from where, to where, and whether something was captured

MatchState
- stores the board
- tracks whose turn it is
- tracks which square is selected in the UI
- stores short status text and move history

There is intentionally no Tkinter code here.
"""

from dataclasses import dataclass, field

from game.board import Board, create_starting_board
from game.coords import Coord


@dataclass(frozen=True)
class MoveRecord:
    """History entry for one completed move."""

    start: Coord
    end: Coord
    piece_symbol: str
    notation: str = ""
    captured_symbol: str | None = None
    note: str = ""


@dataclass
class MatchState:
    """All data needed to describe one active match."""

    board: Board = field(default_factory=create_starting_board)
    current_turn: str = "white"
    selected_square: Coord | None = None
    highlighted_moves: list[Coord] = field(default_factory=list)
    winner: str | None = None
    is_draw: bool = False
    castling_rights: dict[str, bool] = field(
        default_factory=lambda: {
            "white_kingside": True,
            "white_queenside": True,
            "black_kingside": True,
            "black_queenside": True,
        }
    )
    en_passant_target: Coord | None = None
    status_message: str = "White to move."
    move_history: list[MoveRecord] = field(default_factory=list)

    def reset(self) -> None:
        """Reset the match to a fresh starting position."""
        self.board = create_starting_board()
        self.current_turn = "white"
        self.selected_square = None
        self.highlighted_moves.clear()
        self.winner = None
        self.is_draw = False
        self.castling_rights = {
            "white_kingside": True,
            "white_queenside": True,
            "black_kingside": True,
            "black_queenside": True,
        }
        self.en_passant_target = None
        self.status_message = "White to move."
        self.move_history.clear()
