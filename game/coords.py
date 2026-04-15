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
FILES = "abcdefgh"


def is_in_bounds(coord: Coord) -> bool:
    """Return True when the coordinate lives on the 8x8 board."""
    row, col = coord
    return 0 <= row < 8 and 0 <= col < 8


def algebraic_to_index(square: str) -> Coord:
    """Convert a square like 'e2' into internal row and column indexes."""
    if len(square) != 2:
        raise ValueError(f"Invalid square: {square!r}")

    file_char = square[0].lower()
    rank_char = square[1]

    if file_char not in FILES or rank_char not in "12345678":
        raise ValueError(f"Invalid square: {square!r}")

    col = FILES.index(file_char)
    row = 8 - int(rank_char)
    return row, col


def index_to_algebraic(coord: Coord) -> str:
    """Convert internal row and column indexes back into algebraic notation."""
    if not is_in_bounds(coord):
        raise ValueError(f"Out-of-bounds coordinate: {coord!r}")

    row, col = coord
    return f"{FILES[col]}{8 - row}"
