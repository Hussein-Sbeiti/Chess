"""Piece construction helpers and chess piece metadata."""
from __future__ import annotations

from dataclasses import dataclass


# Back-rank layout from file a through file h.
PIECE_ORDER = ("rook", "knight", "bishop", "queen", "king", "bishop", "knight", "rook")
# White pieces use uppercase symbols; black pieces lowercase them in Piece.symbol.
PIECE_SYMBOLS = {
    "pawn": "P",
    "rook": "R",
    "knight": "N",
    "bishop": "B",
    "queen": "Q",
    "king": "K",
}
# Pawns can promote to any non-king, non-pawn piece.
PROMOTION_CHOICES = ("queen", "rook", "bishop", "knight")


@dataclass(frozen=True)
class Piece:
    """Simple immutable piece model shared by the board and rules."""

    # Color is "white" or "black"; kind is one key from PIECE_SYMBOLS.
    color: str
    kind: str

    @property
    def symbol(self) -> str:
        """Return a compact board symbol. White is uppercase, black is lowercase."""
        # The base symbol table stores white-style uppercase letters.
        symbol = PIECE_SYMBOLS[self.kind]
        # Lowercase makes black pieces easy to distinguish in text/debug output.
        return symbol if self.color == "white" else symbol.lower()


def make_piece(color: str, kind: str) -> Piece:
    """Create a piece in a single readable helper call."""
    # This helper keeps board setup code concise and consistent.
    return Piece(color=color, kind=kind)
