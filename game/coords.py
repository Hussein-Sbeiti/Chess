"""Coordinate conversion helpers between board indexes and algebraic notation."""
from __future__ import annotations


# game/coords.py
# Chess Project - coordinate helpers
# Created: 2026-04-15

"""
This file keeps all board-coordinate conversion in one place.

Chess players think in algebraic notation like:
- a1
- e4
- h8

The program internally uses row and column indexes:
- row 0 is the top of the board
- row 7 is the bottom
- col 0 is file a
- col 7 is file h

By centralizing the conversion here, the rest of the project can stay cleaner.
"""

from typing import Tuple


Coord = Tuple[int, int]
# Algebraic file labels are columns from White's left to right.
FILES = "abcdefgh"


def is_in_bounds(coord: Coord) -> bool:
    """Return True when the coordinate lives on the 8x8 board."""
    # All board helpers use zero-based row and column indexes.
    row, col = coord
    return 0 <= row < 8 and 0 <= col < 8


def algebraic_to_index(square: str) -> Coord:
    """Convert a square like 'e2' into internal row and column indexes."""
    # Algebraic squares must be exactly one file letter plus one rank digit.
    if len(square) != 2:
        raise ValueError(f"Invalid square: {square!r}")

    # Files are case-insensitive, ranks are always the characters 1 through 8.
    file_char = square[0].lower()
    rank_char = square[1]

    # Reject malformed input before trying to compute indexes.
    if file_char not in FILES or rank_char not in "12345678":
        raise ValueError(f"Invalid square: {square!r}")

    # Internal rows count from the top, while chess ranks count from White's side.
    col = FILES.index(file_char)
    row = 8 - int(rank_char)
    return row, col


def index_to_algebraic(coord: Coord) -> str:
    """Convert internal row and column indexes back into algebraic notation."""
    # Keep invalid coordinates from becoming misleading square names.
    if not is_in_bounds(coord):
        raise ValueError(f"Out-of-bounds coordinate: {coord!r}")

    # Reverse the same orientation math used by algebraic_to_index().
    row, col = coord
    return f"{FILES[col]}{8 - row}"
