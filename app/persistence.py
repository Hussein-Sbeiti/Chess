from __future__ import annotations

# app/persistence.py
# Chess Project - save/load helpers
# Created: 2026-04-19

"""
This file handles lightweight JSON persistence for the chess app.

It keeps serialization concerns out of the Tkinter screens so the UI can
simply ask to save or load a match.
"""

import json
from pathlib import Path

from app.app_models import AppState
from game.board import Board, create_empty_board
from game.coords import Coord
from game.game_models import MatchState, MoveRecord
from game.pieces import Piece, make_piece


SAVE_DIR = Path(__file__).resolve().parent.parent / "saves"
SAVE_FILE = SAVE_DIR / "last_match.json"
CASTLING_KEYS = (
    "white_kingside",
    "white_queenside",
    "black_kingside",
    "black_queenside",
)


def coord_to_data(coord: Coord | None) -> list[int] | None:
    """Convert one board coordinate into a JSON-safe list."""
    if coord is None:
        return None
    return [coord[0], coord[1]]


def coord_from_data(data) -> Coord | None:
    """Convert saved coordinate data back into a board coordinate."""
    if data is None:
        return None
    if not isinstance(data, list) or len(data) != 2:
        raise ValueError("Saved coordinate data is invalid.")
    row, col = data
    if not isinstance(row, int) or not isinstance(col, int):
        raise ValueError("Saved coordinate data is invalid.")
    if row not in range(8) or col not in range(8):
        raise ValueError("Saved coordinate is out of bounds.")
    return (row, col)


def piece_to_data(piece: Piece | None) -> dict[str, str] | None:
    """Convert a piece into a JSON-safe dictionary."""
    if piece is None:
        return None
    return {"color": piece.color, "kind": piece.kind}


def piece_from_data(data) -> Piece | None:
    """Rebuild a piece from saved JSON data."""
    if data is None:
        return None
    if not isinstance(data, dict):
        raise ValueError("Saved piece data is invalid.")
    color = data.get("color")
    kind = data.get("kind")
    if color not in {"white", "black"}:
        raise ValueError("Saved piece color is invalid.")
    if not isinstance(kind, str):
        raise ValueError("Saved piece kind is invalid.")
    return make_piece(color, kind)


def board_to_data(board: Board) -> list[list[dict[str, str] | None]]:
    """Convert the full board into JSON-safe nested lists."""
    return [[piece_to_data(piece) for piece in row] for row in board]


def board_from_data(data) -> Board:
    """Rebuild a board from saved JSON data."""
    if not isinstance(data, list) or len(data) != 8:
        raise ValueError("Saved board data is invalid.")

    board = create_empty_board()
    for row_index, row in enumerate(data):
        if not isinstance(row, list) or len(row) != 8:
            raise ValueError("Saved board row is invalid.")
        for col_index, piece_data in enumerate(row):
            board[row_index][col_index] = piece_from_data(piece_data)

    return board


def move_record_to_data(record: MoveRecord) -> dict[str, object]:
    """Convert one move record into a JSON-safe dictionary."""
    return {
        "start": coord_to_data(record.start),
        "end": coord_to_data(record.end),
        "piece_symbol": record.piece_symbol,
        "notation": record.notation,
        "captured_symbol": record.captured_symbol,
        "note": record.note,
    }


def move_record_from_data(data) -> MoveRecord:
    """Rebuild one move record from saved JSON data."""
    if not isinstance(data, dict):
        raise ValueError("Saved move record is invalid.")
    piece_symbol = data.get("piece_symbol")
    notation = data.get("notation", "")
    captured_symbol = data.get("captured_symbol")
    note = data.get("note", "")
    if not isinstance(piece_symbol, str):
        raise ValueError("Saved move piece symbol is invalid.")
    if not isinstance(notation, str) or not isinstance(note, str):
        raise ValueError("Saved move text is invalid.")
    if captured_symbol is not None and not isinstance(captured_symbol, str):
        raise ValueError("Saved captured symbol is invalid.")
    return MoveRecord(
        start=coord_from_data(data.get("start")),
        end=coord_from_data(data.get("end")),
        piece_symbol=piece_symbol,
        notation=notation,
        captured_symbol=captured_symbol,
        note=note,
    )


def match_to_data(match: MatchState) -> dict[str, object]:
    """Convert the active match state into JSON-safe data."""
    return {
        "board": board_to_data(match.board),
        "current_turn": match.current_turn,
        "selected_square": coord_to_data(match.selected_square),
        "highlighted_moves": [coord_to_data(square) for square in match.highlighted_moves],
        "winner": match.winner,
        "is_draw": match.is_draw,
        "result_recorded": match.result_recorded,
        "castling_rights": dict(match.castling_rights),
        "en_passant_target": coord_to_data(match.en_passant_target),
        "status_message": match.status_message,
        "move_history": [move_record_to_data(record) for record in match.move_history],
    }


def match_from_data(data) -> MatchState:
    """Rebuild the active match state from saved JSON data."""
    if not isinstance(data, dict):
        raise ValueError("Saved match data is invalid.")

    current_turn = data.get("current_turn", "white")
    if current_turn not in {"white", "black"}:
        raise ValueError("Saved current turn is invalid.")

    winner = data.get("winner")
    if winner not in {None, "white", "black"}:
        raise ValueError("Saved winner is invalid.")

    castling_rights = data.get("castling_rights", {})
    if not isinstance(castling_rights, dict):
        raise ValueError("Saved castling rights are invalid.")
    normalized_castling_rights = {}
    for key in CASTLING_KEYS:
        value = castling_rights.get(key, False)
        if not isinstance(value, bool):
            raise ValueError("Saved castling rights are invalid.")
        normalized_castling_rights[key] = value

    highlighted_data = data.get("highlighted_moves", [])
    if not isinstance(highlighted_data, list):
        raise ValueError("Saved highlighted moves are invalid.")

    move_history_data = data.get("move_history", [])
    if not isinstance(move_history_data, list):
        raise ValueError("Saved move history is invalid.")

    status_message = data.get("status_message", "White to move.")
    if not isinstance(status_message, str):
        raise ValueError("Saved status message is invalid.")

    return MatchState(
        board=board_from_data(data.get("board")),
        current_turn=current_turn,
        selected_square=coord_from_data(data.get("selected_square")),
        highlighted_moves=[coord_from_data(square) for square in highlighted_data],
        winner=winner,
        is_draw=bool(data.get("is_draw", False)),
        result_recorded=bool(data.get("result_recorded", False)),
        castling_rights=normalized_castling_rights,
        en_passant_target=coord_from_data(data.get("en_passant_target")),
        status_message=status_message,
        move_history=[move_record_from_data(record) for record in move_history_data],
    )


def app_state_to_data(state: AppState) -> dict[str, object]:
    """Convert the full app state into JSON-safe data."""
    return {
        "mode": state.mode,
        "screen_message": state.screen_message,
        "piece_theme": state.piece_theme,
        "board_theme": state.board_theme,
        "ai_personality": state.ai_personality,
        "ai_player_color": state.ai_player_color,
        "match": match_to_data(state.match),
    }


def app_state_from_data(data) -> AppState:
    """Rebuild the full app state from saved JSON data."""
    if not isinstance(data, dict):
        raise ValueError("Saved app state is invalid.")

    mode = data.get("mode", "local")
    screen_message = data.get("screen_message", "Welcome to Chess.")
    piece_theme = data.get("piece_theme", "classic")
    board_theme = data.get("board_theme", "classic")
    ai_personality = data.get("ai_personality", "random")
    ai_player_color = data.get("ai_player_color", "white")
    if (
        not isinstance(mode, str)
        or not isinstance(screen_message, str)
        or not isinstance(piece_theme, str)
        or not isinstance(board_theme, str)
        or not isinstance(ai_personality, str)
        or not isinstance(ai_player_color, str)
    ):
        raise ValueError("Saved app metadata is invalid.")

    return AppState(
        mode=mode,
        screen_message=screen_message,
        piece_theme=piece_theme,
        board_theme=board_theme,
        ai_personality=ai_personality,
        ai_player_color=ai_player_color,
        match=match_from_data(data.get("match")),
    )


def has_saved_match(file_path: Path = SAVE_FILE) -> bool:
    """Return whether a saved match file currently exists."""
    return file_path.exists()


def save_app_state(state: AppState, file_path: Path = SAVE_FILE) -> Path:
    """Write the current app state to disk as JSON."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as save_file:
        json.dump(app_state_to_data(state), save_file, indent=2)
    return file_path


def load_app_state(file_path: Path = SAVE_FILE) -> AppState:
    """Load a previously saved app state from disk."""
    with file_path.open("r", encoding="utf-8") as save_file:
        return app_state_from_data(json.load(save_file))
