"""Chess move generation, legality checking, and game-result rules."""
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
- draw detection for repetition, insufficient material, and long quiet stretches
- move application and turn switching
- configurable pawn promotion

This version is designed to cover the core legal rules used by the app.
"""

from game.board import Board, copy_board, move_piece, piece_at, set_piece
from game.coords import Coord, FILES, index_to_algebraic, is_in_bounds
from game.game_models import MatchState, MoveRecord, board_position_key
from game.pieces import PROMOTION_CHOICES, make_piece


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
    # Stop immediately when a ray or jump points off the board.
    if not is_in_bounds(target):
        return False

    occupant = piece_at(board, target)
    if occupant is None:
        # Empty squares are legal destinations and sliding pieces may continue through them.
        moves.append(target)
        return True

    # Enemy kings are excluded because kings are checked, not captured, in legal chess.
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
        # Step one square at a time until a blocker or board edge appears.
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
        # Attacks include the blocker square, then stop behind it.
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


def _castle_rights_keys(color: str) -> tuple[str, str]:
    """Return the castling-rights keys for kingside and queenside."""
    return f"{color}_kingside", f"{color}_queenside"


def _add_castling_moves(state: MatchState, origin: Coord, moves: list[Coord]) -> None:
    """Append castling destinations when rights and board conditions allow it."""
    if state.game_variant != "standard":
        return

    # Castling can only be considered from the king's original square.
    piece = piece_at(state.board, origin)
    if piece is None or piece.kind != "king":
        return

    color = piece.color
    home_row = 7 if color == "white" else 0
    if origin != (home_row, 4):
        return

    kingside_key, queenside_key = _castle_rights_keys(color)
    enemy_color = other_color(color)

    if state.castling_rights.get(kingside_key, False):
        # Kingside castling requires the rook, an empty path, and no attacked king path.
        rook_square = (home_row, 7)
        rook_piece = piece_at(state.board, rook_square)
        path = [(home_row, 5), (home_row, 6)]
        if (
            rook_piece is not None
            and rook_piece.color == color
            and rook_piece.kind == "rook"
            and all(piece_at(state.board, square) is None for square in path)
            and not is_in_check(state.board, color)
            and not any(is_square_attacked(state.board, square, enemy_color) for square in path)
        ):
            moves.append((home_row, 6))

    if state.castling_rights.get(queenside_key, False):
        # Queenside castling has three empty squares, but the king only crosses two.
        rook_square = (home_row, 0)
        rook_piece = piece_at(state.board, rook_square)
        empty_path = [(home_row, 1), (home_row, 2), (home_row, 3)]
        king_path = [(home_row, 3), (home_row, 2)]
        if (
            rook_piece is not None
            and rook_piece.color == color
            and rook_piece.kind == "rook"
            and all(piece_at(state.board, square) is None for square in empty_path)
            and not is_in_check(state.board, color)
            and not any(is_square_attacked(state.board, square, enemy_color) for square in king_path)
        ):
            moves.append((home_row, 2))


def _random_movement_kind(state: MatchState | None, origin: Coord, piece) -> str:
    """Return the active movement pattern for Random Moves games."""
    if state is None or state.game_variant != "random_moves" or piece.kind == "king":
        return piece.kind

    movement_pool = ("pawn", "knight", "bishop", "rook", "queen")
    row, col = origin
    turn_offset = len(state.move_history)
    seed = (row * 17) + (col * 31) + (turn_offset * 7) + (0 if piece.color == "white" else 3)
    return movement_pool[seed % len(movement_pool)]


def candidate_moves_for_piece(board: Board, origin: Coord, state: MatchState | None = None) -> list[Coord]:
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
    movement_kind = _random_movement_kind(state, origin, piece)

    if movement_kind == "pawn":
        # White pawns move toward lower row numbers; black pawns toward higher rows.
        direction = -1 if piece.color == "white" else 1
        start_row = 6 if piece.color == "white" else 1

        # Pawns move forward only into empty squares.
        one_forward = (row + direction, col)
        if is_in_bounds(one_forward) and piece_at(board, one_forward) is None:
            moves.append(one_forward)

            # The two-square move is only available from the pawn's starting row.
            two_forward = (row + (2 * direction), col)
            if row == start_row and piece_at(board, two_forward) is None:
                moves.append(two_forward)

        # Diagonal pawn moves are captures only, except en passant below.
        for capture_col in (col - 1, col + 1):
            capture_square = (row + direction, capture_col)
            if not is_in_bounds(capture_square):
                continue

            target_piece = piece_at(board, capture_square)
            if target_piece is not None and target_piece.color != piece.color and target_piece.kind != "king":
                moves.append(capture_square)

        if piece.kind == "pawn" and state is not None and state.en_passant_target is not None:
            # En passant captures the adjacent pawn while moving to the empty target square.
            target_row, target_col = state.en_passant_target
            if target_row == row + direction and abs(target_col - col) == 1 and piece_at(board, state.en_passant_target) is None:
                adjacent_piece = piece_at(board, (row, target_col))
                if adjacent_piece is not None and adjacent_piece.color != piece.color and adjacent_piece.kind == "pawn":
                    moves.append(state.en_passant_target)

        return moves

    if movement_kind == "knight":
        # Knights jump in fixed L-shapes and ignore intervening pieces.
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

    if movement_kind == "bishop":
        return _ray_moves(board, origin, [(-1, -1), (-1, 1), (1, -1), (1, 1)])

    if movement_kind == "rook":
        return _ray_moves(board, origin, [(-1, 0), (1, 0), (0, -1), (0, 1)])

    if movement_kind == "queen":
        return _ray_moves(
            board,
            origin,
            [(-1, -1), (-1, 1), (1, -1), (1, 1), (-1, 0), (1, 0), (0, -1), (0, 1)],
        )

    if movement_kind == "king":
        # Kings can move one square in any direction.
        for row_step in (-1, 0, 1):
            for col_step in (-1, 0, 1):
                if row_step == 0 and col_step == 0:
                    continue
                _add_move_if_valid(board, moves, piece.color, (row + row_step, col + col_step))
        if state is not None:
            # Castling is generated with the king moves because it moves the king two squares.
            _add_castling_moves(state, origin, moves)
        return moves

    return moves


def attacked_squares_for_piece(board: Board, origin: Coord, state: MatchState | None = None) -> list[Coord]:
    """Return the squares a piece attacks regardless of whether moving there is legal."""
    piece = piece_at(board, origin)
    if piece is None:
        return []

    row, col = origin
    movement_kind = _random_movement_kind(state, origin, piece)

    if movement_kind == "pawn":
        # Pawn attacks are diagonal even when the target square is empty.
        direction = -1 if piece.color == "white" else 1
        attacks: list[Coord] = []
        for capture_col in (col - 1, col + 1):
            target = (row + direction, capture_col)
            if is_in_bounds(target):
                attacks.append(target)
        return attacks

    if movement_kind == "knight":
        # Attack maps use the same L-shape as movement, but do not care about friendly blockers.
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

    if movement_kind == "bishop":
        return _ray_attacks(board, origin, [(-1, -1), (-1, 1), (1, -1), (1, 1)])

    if movement_kind == "rook":
        return _ray_attacks(board, origin, [(-1, 0), (1, 0), (0, -1), (0, 1)])

    if movement_kind == "queen":
        return _ray_attacks(
            board,
            origin,
            [(-1, -1), (-1, 1), (1, -1), (1, 1), (-1, 0), (1, 0), (0, -1), (0, 1)],
        )

    if movement_kind == "king":
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
    # Tests and imported positions can temporarily omit a king, so return None safely.
    for row in range(8):
        for col in range(8):
            piece = board[row][col]
            if piece is not None and piece.color == color and piece.kind == "king":
                return row, col
    return None


def is_square_attacked(board: Board, square: Coord, by_color: str, state: MatchState | None = None) -> bool:
    """Return True when the target square is attacked by the given side."""
    # Scan every enemy piece and ask for its attack map.
    for row in range(8):
        for col in range(8):
            piece = board[row][col]
            if piece is None or piece.color != by_color:
                continue
            if square in attacked_squares_for_piece(board, (row, col), state):
                return True
    return False


def is_in_check(board: Board, color: str, state: MatchState | None = None) -> bool:
    """Return True when the given side's king is under attack."""
    king_square = find_king(board, color)
    if king_square is None:
        return False
    return is_square_attacked(board, king_square, other_color(color), state)


def _is_castling_move(piece, origin: Coord, target: Coord) -> bool:
    """Return True when the move is a castle."""
    return piece is not None and piece.kind == "king" and origin[0] == target[0] and abs(target[1] - origin[1]) == 2


def _is_en_passant_move(board: Board, state: MatchState, piece, origin: Coord, target: Coord) -> bool:
    """Return True when the move is an en passant capture."""
    return (
        piece is not None
        and piece.kind == "pawn"
        and state.en_passant_target == target
        and origin[1] != target[1]
        and piece_at(board, target) is None
    )


def is_promotion_move(board: Board, origin: Coord, target: Coord) -> bool:
    """Return True when the move would send a pawn to the last rank."""
    moving_piece = piece_at(board, origin)
    return moving_piece is not None and moving_piece.kind == "pawn" and target[0] in (0, 7)


def _board_after_move(state: MatchState, origin: Coord, target: Coord) -> Board:
    """Return a copied board showing the result of the move."""
    # Legal-move filtering works on a copy so it cannot disturb the real match.
    next_board = copy_board(state.board)
    moving_piece = piece_at(next_board, origin)

    if _is_en_passant_move(next_board, state, moving_piece, origin, target):
        # En passant removes the pawn beside the origin, not the empty target square.
        capture_square = (origin[0], target[1])
        set_piece(next_board, capture_square, None)

    move_piece(next_board, origin, target)

    moved_piece = piece_at(next_board, target)
    if _is_castling_move(moved_piece, origin, target):
        # Simulate the rook hop that accompanies the king's castle.
        rook_origin = (origin[0], 7 if target[1] > origin[1] else 0)
        rook_target = (origin[0], 5 if target[1] > origin[1] else 3)
        move_piece(next_board, rook_origin, rook_target)

    if is_promotion_move(next_board, target, target):
        # Simulation can use queen promotion because only king safety matters here.
        set_piece(next_board, target, make_piece(moved_piece.color, "queen"))

    return next_board


def legal_moves_for_piece(state: MatchState, origin: Coord) -> list[Coord]:
    """Return only the moves that keep the moving side's king safe."""
    moving_piece = piece_at(state.board, origin)
    if moving_piece is None:
        return []

    legal_moves: list[Coord] = []
    for target in candidate_moves_for_piece(state.board, origin, state):
        # A pseudo-legal move becomes legal only if the king is safe afterward.
        next_board = _board_after_move(state, origin, target)
        if not is_in_check(next_board, moving_piece.color):
            legal_moves.append(target)
    return legal_moves


def player_has_legal_move(state: MatchState, color: str) -> bool:
    """Return True when the side to move has at least one legal move available."""
    # Early return keeps checkmate/stalemate checks inexpensive in common positions.
    for row in range(8):
        for col in range(8):
            piece = state.board[row][col]
            if piece is None or piece.color != color:
                continue
            if legal_moves_for_piece(state, (row, col)):
                return True
    return False


def _update_castling_rights_after_move(state: MatchState, moving_piece, origin: Coord, target: Coord, captured_piece) -> None:
    """Disable castling rights when kings or home rooks move or are captured."""
    # Moving a king permanently removes both castling options for that side.
    if moving_piece.kind == "king":
        kingside_key, queenside_key = _castle_rights_keys(moving_piece.color)
        state.castling_rights[kingside_key] = False
        state.castling_rights[queenside_key] = False
    elif moving_piece.kind == "rook":
        # Moving a rook from its original corner removes that side's matching right.
        if moving_piece.color == "white":
            if origin == (7, 0):
                state.castling_rights["white_queenside"] = False
            elif origin == (7, 7):
                state.castling_rights["white_kingside"] = False
        else:
            if origin == (0, 0):
                state.castling_rights["black_queenside"] = False
            elif origin == (0, 7):
                state.castling_rights["black_kingside"] = False

    if captured_piece is not None and captured_piece.kind == "rook":
        # Capturing a rook on its original square also removes the opponent's right.
        if target == (7, 0):
            state.castling_rights["white_queenside"] = False
        elif target == (7, 7):
            state.castling_rights["white_kingside"] = False
        elif target == (0, 0):
            state.castling_rights["black_queenside"] = False
        elif target == (0, 7):
            state.castling_rights["black_kingside"] = False


def _build_move_notation(
    moving_piece,
    origin: Coord,
    target: Coord,
    captured_piece,
    promotion_kind: str | None,
    is_castling: bool,
    is_check: bool,
    is_checkmate: bool,
) -> str:
    """Build a compact chess-style move string for the sidebar."""
    if is_castling:
        # Castling notation depends on whether the king moved toward h-file or a-file.
        notation = "O-O" if target[1] > origin[1] else "O-O-O"
    else:
        destination = index_to_algebraic(target)
        is_capture = captured_piece is not None

        if moving_piece.kind == "pawn":
            # Pawn captures include their origin file; quiet pawn moves show only destination.
            if is_capture:
                notation = f"{FILES[origin[1]]}x{destination}"
            else:
                notation = destination
        else:
            # Other pieces use their uppercase piece letter, plus x when capturing.
            piece_letter = moving_piece.symbol.upper()
            notation = f"{piece_letter}{'x' if is_capture else ''}{destination}"

        if promotion_kind is not None:
            # Promotion suffix shows the piece that replaced the pawn.
            notation += f"={make_piece(moving_piece.color, promotion_kind).symbol.upper()}"

    # Checkmate marker takes precedence over a normal check marker.
    if is_checkmate:
        notation += "#"
    elif is_check:
        notation += "+"

    return notation


def _square_color(square: Coord) -> int:
    """Return 0 or 1 for the board color of one square."""
    return (square[0] + square[1]) % 2


def is_insufficient_material(board: Board) -> bool:
    """Return True when neither side has enough material to force mate."""
    remaining: list[tuple[object, Coord]] = []
    # Kings are ignored because every legal position has them and they cannot force mate alone.
    for row in range(8):
        for col in range(8):
            piece = board[row][col]
            if piece is None or piece.kind == "king":
                continue
            remaining.append((piece, (row, col)))

    if not remaining:
        # King versus king is an automatic draw.
        return True

    if len(remaining) == 1:
        # King plus a single bishop or knight cannot force mate.
        lone_piece = remaining[0][0]
        return lone_piece.kind in {"bishop", "knight"}

    if all(piece.kind == "bishop" for piece, _square in remaining):
        # Bishops all on the same color cannot cover enough squares to force mate.
        return len({_square_color(square) for _piece, square in remaining}) == 1

    return False


def _record_position(state: MatchState) -> int:
    """Store the new position for repetition tracking and return its occurrence count."""
    # Include turn, castling, and en-passant rights because they affect legal replies.
    position_key = board_position_key(
        state.board,
        state.current_turn,
        state.castling_rights,
        state.en_passant_target,
    )
    next_count = state.position_counts.get(position_key, 0) + 1
    # Store the updated count back on the match for future repetition checks.
    state.position_counts[position_key] = next_count
    return next_count


def make_move(state: MatchState, origin: Coord, target: Coord, promotion_choice: str | None = None) -> tuple[bool, str]:
    """
    Try to apply a move.

    Returns:
    - success flag
    - user-facing status message
    """
    if state.winner:
        # Finished games reject further moves so the board cannot change after a result.
        return False, f"Match already finished. Winner: {state.winner.title()}."
    if state.is_draw:
        return False, "Match already finished. The game ended in a draw."

    moving_piece = piece_at(state.board, origin)
    # A move must start on a square with a piece.
    if moving_piece is None:
        return False, "There is no piece on the selected square."

    if moving_piece.color != state.current_turn:
        # Enforce turn order before doing any expensive legality work.
        return False, f"It is {state.current_turn}'s turn."

    candidate_targets = candidate_moves_for_piece(state.board, origin, state)
    # First validate piece movement, then king safety, then optional promotion input.
    if target not in candidate_targets:
        return False, "That move is not legal for that piece."
    if target not in legal_moves_for_piece(state, origin):
        return False, "That move would leave your king in check."
    if promotion_choice is not None and promotion_choice not in PROMOTION_CHOICES:
        return False, f"Invalid promotion choice: {promotion_choice}."

    captured_piece = piece_at(state.board, target)
    note_parts: list[str] = []
    promotion_kind: str | None = None

    if _is_en_passant_move(state.board, state, moving_piece, origin, target):
        # Capture the pawn behind the en-passant target before moving the pawn.
        capture_square = (origin[0], target[1])
        captured_piece = piece_at(state.board, capture_square)
        set_piece(state.board, capture_square, None)
        note_parts.append("en passant")

    # Apply the primary piece movement after all early validation succeeds.
    move_piece(state.board, origin, target)

    placed_piece = piece_at(state.board, target)
    if _is_castling_move(placed_piece, origin, target):
        # Castling moves the rook to the square next to the king.
        rook_origin = (origin[0], 7 if target[1] > origin[1] else 0)
        rook_target = (origin[0], 5 if target[1] > origin[1] else 3)
        move_piece(state.board, rook_origin, rook_target)
        note_parts.append("castled")

    if is_promotion_move(state.board, target, target):
        # Default to queen promotion if the caller does not choose a piece.
        promotion_kind = promotion_choice or "queen"
        promoted_piece = make_piece(placed_piece.color, promotion_kind)
        set_piece(state.board, target, promoted_piece)
        placed_piece = promoted_piece
        note_parts.append(f"promoted to {promotion_kind}")

    _update_castling_rights_after_move(state, moving_piece, origin, target, captured_piece)

    state.en_passant_target = None
    if moving_piece.kind == "pawn" and abs(target[0] - origin[0]) == 2:
        # Store the square behind a double-moved pawn for the opponent's next move.
        state.en_passant_target = ((origin[0] + target[0]) // 2, origin[1])
    if moving_piece.kind == "pawn" or captured_piece is not None:
        # Pawn moves and captures reset the fifty-move counter.
        state.halfmove_clock = 0
    else:
        state.halfmove_clock += 1

    # Clear UI selection state now that the move is complete.
    state.selected_square = None
    state.highlighted_moves.clear()

    next_turn = other_color(moving_piece.color)
    state.current_turn = next_turn
    # Record the resulting position after the turn changes.
    repetition_count = _record_position(state)
    is_check = is_in_check(state.board, next_turn)
    has_reply = player_has_legal_move(state, next_turn)
    is_checkmate = is_check and not has_reply
    notation = _build_move_notation(
        moving_piece,
        origin,
        target,
        captured_piece,
        promotion_kind,
        _is_castling_move(placed_piece, origin, target),
        is_check,
        is_checkmate,
    )

    state.move_history.append(
        # Keep enough detail for sidebar history, captures, saves, and recent-match summaries.
        MoveRecord(
            start=origin,
            end=target,
            piece_symbol=moving_piece.symbol,
            notation=notation,
            captured_symbol=captured_piece.symbol if captured_piece else None,
            note=", ".join(note_parts),
        )
    )

    if is_check:
        # Checkmate is check with no legal reply; otherwise play continues.
        if has_reply:
            state.status_message = f"{next_turn.title()} is in check. {next_turn.title()} to move."
            return True, state.status_message

        state.winner = moving_piece.color
        state.status_message = f"{moving_piece.color.title()} wins by checkmate."
        return True, state.status_message

    if not has_reply:
        # No check plus no legal reply is stalemate.
        state.is_draw = True
        state.status_message = "Stalemate. The game is a draw."
        return True, state.status_message

    if is_insufficient_material(state.board):
        # Detect automatic material draws after the move is applied.
        state.is_draw = True
        state.status_message = "Draw by insufficient material."
        return True, state.status_message

    if state.halfmove_clock >= 100:
        # The fifty-move rule uses halfmoves, so 100 halfmoves equals 50 moves per side.
        state.is_draw = True
        state.status_message = "Draw by fifty-move rule."
        return True, state.status_message

    if repetition_count >= 3:
        # Three occurrences of the same legal-position key create a draw.
        state.is_draw = True
        state.status_message = "Draw by threefold repetition."
        return True, state.status_message

    state.status_message = f"{state.current_turn.title()} to move."
    return True, state.status_message
