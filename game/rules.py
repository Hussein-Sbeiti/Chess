from __future__ import annotations

# game/rules.py
# Chess Project - basic move generation and move application
# Created: 2026-04-15

"""
This file contains the chess rules layer used by the current scaffold.

Right now it provides:
- piece ownership helpers
- candidate move generation for each piece type
- basic move application
- turn switching
- automatic queen promotion for pawns

This version deliberately stops short of full chess legality.
Future phases will add:
- check detection
- checkmate
- stalemate
- castling
- en passant
- player-chosen promotion
"""

from game.board import Board, move_piece, piece_at, set_piece
from game.coords import Coord, is_in_bounds
from game.game_models import MatchState, MoveRecord
from game.pieces import make_piece


def other_color(color: str) -> str:
    """Return the opposite side."""
    return "black" if color == "white" else "white"


def piece_belongs_to_player(piece, player_color: str) -> bool:
    """Return True when the piece belongs to the player whose turn it is."""
    return piece is not None and piece.color == player_color


def _add_move_if_valid(board: Board, moves: list[Coord], color: str, target: Coord) -> bool:
    """
    Add a square when it is on the board and not occupied by a friendly piece.

    Returns True when ray-tracing can continue beyond this square.
    """
    if not is_in_bounds(target):
        return False

    occupant = piece_at(board, target)
    if occupant is None:
        moves.append(target)
        return True

    if occupant.color != color:
        moves.append(target)
    return False


def _ray_moves(board: Board, origin: Coord, directions: list[Coord]) -> list[Coord]:
    """Generate sliding-piece moves for bishops, rooks, and queens."""
    piece = piece_at(board, origin)
    if piece is None:
        return []

    row, col = origin
    moves: list[Coord] = []

    for row_step, col_step in directions:
        next_row = row + row_step
        next_col = col + col_step

        while True:
            target = (next_row, next_col)
            can_continue = _add_move_if_valid(board, moves, piece.color, target)
            if not can_continue:
                break
            next_row += row_step
            next_col += col_step

    return moves


def candidate_moves_for_piece(board: Board, origin: Coord) -> list[Coord]:
    """
    Return pseudo-legal moves for the piece on the origin square.

    These moves respect movement patterns and blocking pieces, but they do not
    yet check whether the move leaves the moving side's king in check.
    """
    piece = piece_at(board, origin)
    if piece is None:
        return []

    row, col = origin
    moves: list[Coord] = []

    if piece.kind == "pawn":
        direction = -1 if piece.color == "white" else 1
        start_row = 6 if piece.color == "white" else 1

        one_forward = (row + direction, col)
        if is_in_bounds(one_forward) and piece_at(board, one_forward) is None:
            moves.append(one_forward)

            two_forward = (row + (2 * direction), col)
            if row == start_row and piece_at(board, two_forward) is None:
                moves.append(two_forward)

        for capture_col in (col - 1, col + 1):
            capture_square = (row + direction, capture_col)
            if not is_in_bounds(capture_square):
                continue

            target_piece = piece_at(board, capture_square)
            if target_piece is not None and target_piece.color != piece.color:
                moves.append(capture_square)

        return moves

    if piece.kind == "knight":
        for row_step, col_step in (
            (-2, -1),
            (-2, 1),
            (-1, -2),
            (-1, 2),
            (1, -2),
            (1, 2),
            (2, -1),
            (2, 1),
        ):
            _add_move_if_valid(board, moves, piece.color, (row + row_step, col + col_step))
        return moves

    if piece.kind == "bishop":
        return _ray_moves(board, origin, [(-1, -1), (-1, 1), (1, -1), (1, 1)])

    if piece.kind == "rook":
        return _ray_moves(board, origin, [(-1, 0), (1, 0), (0, -1), (0, 1)])

    if piece.kind == "queen":
        return _ray_moves(
            board,
            origin,
            [(-1, -1), (-1, 1), (1, -1), (1, 1), (-1, 0), (1, 0), (0, -1), (0, 1)],
        )

    if piece.kind == "king":
        for row_step in (-1, 0, 1):
            for col_step in (-1, 0, 1):
                if row_step == 0 and col_step == 0:
                    continue
                _add_move_if_valid(board, moves, piece.color, (row + row_step, col + col_step))
        return moves

    return moves


def make_move(state: MatchState, origin: Coord, target: Coord) -> tuple[bool, str]:
    """
    Try to apply a move.

    Returns:
    - success flag
    - user-facing status message
    """
    if state.winner:
        return False, f"Match already finished. Winner: {state.winner.title()}."

    moving_piece = piece_at(state.board, origin)
    if moving_piece is None:
        return False, "There is no piece on the selected square."

    if moving_piece.color != state.current_turn:
        return False, f"It is {state.current_turn}'s turn."

    legal_targets = candidate_moves_for_piece(state.board, origin)
    if target not in legal_targets:
        return False, "That move is not legal in the current starter rule set."

    captured_piece = piece_at(state.board, target)
    move_piece(state.board, origin, target)

    note = ""
    placed_piece = piece_at(state.board, target)
    if placed_piece is not None and placed_piece.kind == "pawn" and target[0] in (0, 7):
        promoted_piece = make_piece(placed_piece.color, "queen")
        set_piece(state.board, target, promoted_piece)
        placed_piece = promoted_piece
        note = "auto-promoted to queen"

    state.move_history.append(
        MoveRecord(
            start=origin,
            end=target,
            piece_symbol=moving_piece.symbol,
            captured_symbol=captured_piece.symbol if captured_piece else None,
            note=note,
        )
    )
    state.selected_square = None
    state.highlighted_moves.clear()

    if captured_piece is not None and captured_piece.kind == "king":
        state.winner = moving_piece.color
        state.status_message = (
            f"{moving_piece.color.title()} wins in the scaffold flow. "
            "Proper checkmate handling is planned next."
        )
        return True, state.status_message

    state.current_turn = other_color(state.current_turn)
    state.status_message = f"{state.current_turn.title()} to move."
    return True, state.status_message
