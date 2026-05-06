"""Variant setup helpers for non-standard chess modes."""
from __future__ import annotations

from game.board import (
    Board,
    create_pawn_rush_board,
    create_pawns_only_board,
    create_random_army_board,
    create_starting_board,
)


STANDARD_VARIANT = "standard"
GAME_VARIANT_LABELS = {
    "standard": "Standard",
    "all_pawns": "All Pawns",
    "random_army": "Random Army",
    "random_moves": "Random Moves",
    "pawn_rush": "Pawn Rush",
}
GAME_VARIANT_DESCRIPTIONS = {
    "standard": "Classic chess setup and movement.",
    "all_pawns": "Kings and pawn armies only.",
    "random_army": "Randomized back-rank armies with normal rules.",
    "random_moves": "Normal setup, but non-king pieces borrow changing movement styles.",
    "pawn_rush": "A crowded pawn battle with two pawn lines per side.",
}


def normalize_game_variant(variant_name: str) -> str:
    """Return a known game variant name, falling back to standard chess."""
    return variant_name if variant_name in GAME_VARIANT_LABELS else STANDARD_VARIANT


def create_board_for_variant(variant_name: str) -> Board:
    """Create the starting board for one game variant."""
    normalized_variant = normalize_game_variant(variant_name)
    if normalized_variant == "all_pawns":
        return create_pawns_only_board()
    if normalized_variant == "random_army":
        return create_random_army_board()
    if normalized_variant == "pawn_rush":
        return create_pawn_rush_board()
    return create_starting_board()


def castling_rights_for_variant(variant_name: str) -> dict[str, bool]:
    """Return starting castling rights for a variant."""
    castling_enabled = normalize_game_variant(variant_name) == STANDARD_VARIANT
    return {
        "white_kingside": castling_enabled,
        "white_queenside": castling_enabled,
        "black_kingside": castling_enabled,
        "black_queenside": castling_enabled,
    }
