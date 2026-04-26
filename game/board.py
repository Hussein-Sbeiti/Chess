"""Board construction and square access helpers for chess positions."""
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
    # Rows are ranks from Black's back rank at index 0 to White's back rank at index 7.
    return [[None for _ in range(8)] for _ in range(8)]


def create_starting_board() -> Board:
    """Return a standard chess starting position."""
    board = create_empty_board()

    # Place the major/minor pieces in normal chess order on each player's back rank.
    for col, kind in enumerate(PIECE_ORDER):
        board[0][col] = make_piece("black", kind)
        board[7][col] = make_piece("white", kind)

    # Pawns occupy the second rank from each player's perspective.
    for col in range(8):
        board[1][col] = make_piece("black", "pawn")
        board[6][col] = make_piece("white", "pawn")

    return board


def copy_board(board: Board) -> Board:
    """Return a shallow copy of the board grid."""
    # Piece objects are immutable dataclasses, so copying rows is enough for move simulation.
    return [row[:] for row in board]


def piece_at(board: Board, coord: Coord) -> Piece | None:
    """Return the piece at the given square, or None for an empty square."""
    # Coords are always stored as zero-based (row, col) tuples.
    row, col = coord
    return board[row][col]


def set_piece(board: Board, coord: Coord, piece: Piece | None) -> None:
    """Replace the piece at a square."""
    # Mutate the shared board grid in place so callers keep the same board object.
    row, col = coord
    board[row][col] = piece


def move_piece(board: Board, origin: Coord, target: Coord) -> Piece | None:
    """Move a piece and return any captured piece from the destination square."""
    # Save both pieces before mutating so captures can be reported to rules/UI code.
    moving_piece = piece_at(board, origin)
    captured_piece = piece_at(board, target)
    # Put the moving piece on the target before clearing the origin square.
    set_piece(board, target, moving_piece)
    set_piece(board, origin, None)
    return captured_piece


def board_to_text(board: Board) -> str:
    """Return a simple multi-line board view useful for debugging."""
    lines: list[str] = []
    for row in board:
        # Empty squares render as dots so text snapshots keep their 8x8 shape.
        lines.append(" ".join(piece.symbol if piece else "." for piece in row))
    return "\n".join(lines)
