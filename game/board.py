from __future__ import annotations

# game/board.py
# Chess Project - board creation and board helpers
# Created: 2026-04-15

"""
This file is responsible for the chess board itself.

It does not decide whether a move is legal.
Instead, it focuses on:
- creating an empty board
- creating the starting board
- reading and writing pieces on the board
- moving pieces from one square to another

That keeps board storage separate from the rule engine.
"""

from game.coords import Coord
from game.pieces import PIECE_ORDER, Piece, make_piece


Board = list[list[Piece | None]]


def create_empty_board() -> Board:
    """Return a blank 8x8 board."""
    return [[None for _ in range(8)] for _ in range(8)]


def create_starting_board() -> Board:
    """Return a standard chess starting position."""
    board = create_empty_board()

    for col, kind in enumerate(PIECE_ORDER):
        board[0][col] = make_piece("black", kind)
        board[7][col] = make_piece("white", kind)

    for col in range(8):
        board[1][col] = make_piece("black", "pawn")
        board[6][col] = make_piece("white", "pawn")

    return board


def copy_board(board: Board) -> Board:
    """Return a shallow copy of the board grid."""
    return [row[:] for row in board]


def piece_at(board: Board, coord: Coord) -> Piece | None:
    """Return the piece at the given square, or None for an empty square."""
    row, col = coord
    return board[row][col]


def set_piece(board: Board, coord: Coord, piece: Piece | None) -> None:
    """Replace the piece at a square."""
    row, col = coord
    board[row][col] = piece


def move_piece(board: Board, origin: Coord, target: Coord) -> Piece | None:
    """Move a piece and return any captured piece from the destination square."""
    moving_piece = piece_at(board, origin)
    captured_piece = piece_at(board, target)
    set_piece(board, target, moving_piece)
    set_piece(board, origin, None)
    return captured_piece


def board_to_text(board: Board) -> str:
    """Return a simple multi-line board view useful for debugging."""
    lines: list[str] = []
    for row in board:
        lines.append(" ".join(piece.symbol if piece else "." for piece in row))
    return "\n".join(lines)
