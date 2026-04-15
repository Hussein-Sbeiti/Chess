from __future__ import annotations

# game/pieces.py
# Chess Project - piece definitions and helpers
# Created: 2026-04-15

"""
This file defines the Piece data model and the shared piece-related constants.

Its job is to answer questions like:
- what kinds of pieces exist
- how should they be displayed
- what is the standard back-rank order

Keeping this separate makes it easy to reuse piece definitions in both the UI
and the rules module without duplicating constants.
"""

from dataclasses import dataclass


PIECE_ORDER = ("rook", "knight", "bishop", "queen", "king", "bishop", "knight", "rook")
PIECE_SYMBOLS = {
    "pawn": "P",
    "rook": "R",
    "knight": "N",
    "bishop": "B",
    "queen": "Q",
    "king": "K",
}
PROMOTION_CHOICES = ("queen", "rook", "bishop", "knight")


@dataclass(frozen=True)
class Piece:
    """Simple immutable piece model shared by the board and rules."""

    color: str
    kind: str

    @property
    def symbol(self) -> str:
        """Return a compact board symbol. White is uppercase, black is lowercase."""
        symbol = PIECE_SYMBOLS[self.kind]
        return symbol if self.color == "white" else symbol.lower()


def make_piece(color: str, kind: str) -> Piece:
    """Create a piece in a single readable helper call."""
    return Piece(color=color, kind=kind)
