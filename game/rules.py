from __future__ import annotations

# game/rules.py
# Chess Project - move generation and move application
# Created: 2026-04-15

"""
This file contains the chess rules layer used by the current app.

Right now it provides:
- piece ownership helpers
- pseudo-legal move generation for each piece type
- king-safety filtering for fully legal moves
- check, checkmate, and stalemate detection
- move application and turn switching
- automatic queen promotion for pawns

This version deliberately stops short of full chess legality.
Future phases will add:
- castling
- en passant
- player-chosen promotion
"""

from game.board import Board, copy_board, move_piece, piece_at, set_piece
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

    if occupant.color != color and occupant.kind != "king":
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


def _ray_attacks(board: Board, origin: Coord, directions: list[Coord]) -> list[Coord]:
    """Generate attacked squares for sliding pieces until a blocker is reached."""
    row, col = origin
    attacks: list[Coord] = []

    for row_step, col_step in directions:
        next_row = row + row_step
        next_col = col + col_step

        while is_in_bounds((next_row, next_col)):
            target = (next_row, next_col)
            attacks.append(target)
            if piece_at(board, target) is not None:
                break
            next_row += row_step
            next_col += col_step

    return attacks


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
            if target_piece is not None and target_piece.color != piece.color and target_piece.kind != "king":
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


def attacked_squares_for_piece(board: Board, origin: Coord) -> list[Coord]:
    """Return the squares a piece attacks regardless of whether moving there is legal."""
    piece = piece_at(board, origin)
    if piece is None:
        return []

    row, col = origin

    if piece.kind == "pawn":
        direction = -1 if piece.color == "white" else 1
        attacks: list[Coord] = []
        for capture_col in (col - 1, col + 1):
            target = (row + direction, capture_col)
            if is_in_bounds(target):
                attacks.append(target)
        return attacks

    if piece.kind == "knight":
        attacks: list[Coord] = []
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
            target = (row + row_step, col + col_step)
            if is_in_bounds(target):
                attacks.append(target)
        return attacks

    if piece.kind == "bishop":
        return _ray_attacks(board, origin, [(-1, -1), (-1, 1), (1, -1), (1, 1)])

    if piece.kind == "rook":
        return _ray_attacks(board, origin, [(-1, 0), (1, 0), (0, -1), (0, 1)])

    if piece.kind == "queen":
        return _ray_attacks(
            board,
            origin,
            [(-1, -1), (-1, 1), (1, -1), (1, 1), (-1, 0), (1, 0), (0, -1), (0, 1)],
        )

    if piece.kind == "king":
        attacks: list[Coord] = []
        for row_step in (-1, 0, 1):
            for col_step in (-1, 0, 1):
                if row_step == 0 and col_step == 0:
                    continue
                target = (row + row_step, col + col_step)
                if is_in_bounds(target):
                    attacks.append(target)
        return attacks

    return []


def find_king(board: Board, color: str) -> Coord | None:
    """Return the given side's king location, or None when absent."""
    for row in range(8):
        for col in range(8):
            piece = board[row][col]
            if piece is not None and piece.color == color and piece.kind == "king":
                return row, col
    return None


def is_square_attacked(board: Board, square: Coord, by_color: str) -> bool:
    """Return True when the target square is attacked by the given side."""
    for row in range(8):
        for col in range(8):
            piece = board[row][col]
            if piece is None or piece.color != by_color:
                continue
            if square in attacked_squares_for_piece(board, (row, col)):
                return True
    return False


def is_in_check(board: Board, color: str) -> bool:
    """Return True when the given side's king is under attack."""
    king_square = find_king(board, color)
    if king_square is None:
        return False
    return is_square_attacked(board, king_square, other_color(color))


def _board_after_move(board: Board, origin: Coord, target: Coord) -> Board:
    """Return a copied board showing the result of the move."""
    next_board = copy_board(board)
    move_piece(next_board, origin, target)

    moved_piece = piece_at(next_board, target)
    if moved_piece is not None and moved_piece.kind == "pawn" and target[0] in (0, 7):
        set_piece(next_board, target, make_piece(moved_piece.color, "queen"))

    return next_board


def legal_moves_for_piece(board: Board, origin: Coord) -> list[Coord]:
    """Return only the moves that keep the moving side's king safe."""
    moving_piece = piece_at(board, origin)
    if moving_piece is None:
        return []

    legal_moves: list[Coord] = []
    for target in candidate_moves_for_piece(board, origin):
        next_board = _board_after_move(board, origin, target)
        if not is_in_check(next_board, moving_piece.color):
            legal_moves.append(target)
    return legal_moves


def player_has_legal_move(board: Board, color: str) -> bool:
    """Return True when the side to move has at least one legal move available."""
    for row in range(8):
        for col in range(8):
            piece = board[row][col]
            if piece is None or piece.color != color:
                continue
            if legal_moves_for_piece(board, (row, col)):
                return True
    return False


def make_move(state: MatchState, origin: Coord, target: Coord) -> tuple[bool, str]:
    """
    Try to apply a move.

    Returns:
    - success flag
    - user-facing status message
    """
    if state.winner:
        return False, f"Match already finished. Winner: {state.winner.title()}."
    if state.is_draw:
        return False, "Match already finished. The game ended in a draw."

    moving_piece = piece_at(state.board, origin)
    if moving_piece is None:
        return False, "There is no piece on the selected square."

    if moving_piece.color != state.current_turn:
        return False, f"It is {state.current_turn}'s turn."

    candidate_targets = candidate_moves_for_piece(state.board, origin)
    if target not in candidate_targets:
        return False, "That move is not legal for that piece."
    if target not in legal_moves_for_piece(state.board, origin):
        return False, "That move would leave your king in check."

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

    next_turn = other_color(moving_piece.color)
    state.current_turn = next_turn

    if is_in_check(state.board, next_turn):
        if player_has_legal_move(state.board, next_turn):
            state.status_message = f"{next_turn.title()} is in check. {next_turn.title()} to move."
            return True, state.status_message

        state.winner = moving_piece.color
        state.status_message = f"{moving_piece.color.title()} wins by checkmate."
        return True, state.status_message

    if not player_has_legal_move(state.board, next_turn):
        state.is_draw = True
        state.status_message = "Stalemate. The game is a draw."
        return True, state.status_message

    state.status_message = f"{state.current_turn.title()} to move."
    return True, state.status_message
