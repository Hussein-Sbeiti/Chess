"""JSON save/load helpers for active chess matches."""
from __future__ import annotations

import json
from pathlib import Path

from app.app_models import AppState
from app.paths import user_data_path
from game.ai import ai_difficulty_for_personality, normalize_ai_difficulty
from game.board import Board, create_empty_board
from game.coords import Coord
from game.game_models import MatchState, MoveRecord
from game.pieces import Piece, make_piece
from game.variants import normalize_game_variant


SAVE_DIR = user_data_path("saves")
# The app keeps one resumable match at a time.
SAVE_FILE = SAVE_DIR / "last_match.json"
# Save files store castling rights by explicit key so old/new saves stay readable.
CASTLING_KEYS = (
    "white_kingside",
    "white_queenside",
    "black_kingside",
    "black_queenside",
)


def coord_to_data(coord: Coord | None) -> list[int] | None:
    """Convert one board coordinate into a JSON-safe list."""
    # JSON has no tuple type, so coordinates are saved as two-item lists.
    if coord is None:
        return None
    return [coord[0], coord[1]]


def coord_from_data(data) -> Coord | None:
    """Convert saved coordinate data back into a board coordinate."""
    # None means "no selected square" or "no en-passant target."
    if data is None:
        return None
    # Validate shape, type, and board bounds before returning a coordinate tuple.
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
    # Empty squares are stored as null in JSON.
    if piece is None:
        return None
    return {"color": piece.color, "kind": piece.kind}


def piece_from_data(data) -> Piece | None:
    """Rebuild a piece from saved JSON data."""
    # null in the board grid means the square is empty.
    if data is None:
        return None
    if not isinstance(data, dict):
        raise ValueError("Saved piece data is invalid.")
    color = data.get("color")
    kind = data.get("kind")
    # Color/kind validation keeps corrupted save files from creating invalid pieces.
    if color not in {"white", "black"}:
        raise ValueError("Saved piece color is invalid.")
    if not isinstance(kind, str):
        raise ValueError("Saved piece kind is invalid.")
    return make_piece(color, kind)


def board_to_data(board: Board) -> list[list[dict[str, str] | None]]:
    """Convert the full board into JSON-safe nested lists."""
    # Preserve the 8x8 row/column shape exactly.
    return [[piece_to_data(piece) for piece in row] for row in board]


def board_from_data(data) -> Board:
    """Rebuild a board from saved JSON data."""
    if not isinstance(data, list) or len(data) != 8:
        raise ValueError("Saved board data is invalid.")

    board = create_empty_board()
    for row_index, row in enumerate(data):
        # Each saved board row must contain exactly eight squares.
        if not isinstance(row, list) or len(row) != 8:
            raise ValueError("Saved board row is invalid.")
        for col_index, piece_data in enumerate(row):
            board[row_index][col_index] = piece_from_data(piece_data)

    return board


def move_record_to_data(record: MoveRecord) -> dict[str, object]:
    """Convert one move record into a JSON-safe dictionary."""
    # Keep both machine-readable squares and display-friendly notation.
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
    # Move records are optional history, so validate each entry independently.
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
    # Store both chess state and UI state so loading feels exactly like resuming.
    return {
        "board": board_to_data(match.board),
        "game_variant": match.game_variant,
        "current_turn": match.current_turn,
        "selected_square": coord_to_data(match.selected_square),
        "highlighted_moves": [coord_to_data(square) for square in match.highlighted_moves],
        "winner": match.winner,
        "is_draw": match.is_draw,
        "result_recorded": match.result_recorded,
        "castling_rights": dict(match.castling_rights),
        "en_passant_target": coord_to_data(match.en_passant_target),
        "halfmove_clock": match.halfmove_clock,
        "position_counts": dict(match.position_counts),
        "status_message": match.status_message,
        "move_history": [move_record_to_data(record) for record in match.move_history],
    }


def match_from_data(data) -> MatchState:
    """Rebuild the active match state from saved JSON data."""
    # Reject non-object saves before reading individual fields.
    if not isinstance(data, dict):
        raise ValueError("Saved match data is invalid.")

    current_turn = data.get("current_turn", "white")
    if current_turn not in {"white", "black"}:
        raise ValueError("Saved current turn is invalid.")

    game_variant = data.get("game_variant", "standard")
    if not isinstance(game_variant, str):
        raise ValueError("Saved game variant is invalid.")

    winner = data.get("winner")
    if winner not in {None, "white", "black"}:
        raise ValueError("Saved winner is invalid.")

    castling_rights = data.get("castling_rights", {})
    if not isinstance(castling_rights, dict):
        raise ValueError("Saved castling rights are invalid.")
    normalized_castling_rights = {}
    for key in CASTLING_KEYS:
        # Missing rights default to False so partial/corrupt saves fail safely.
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

    halfmove_clock = data.get("halfmove_clock", 0)
    if not isinstance(halfmove_clock, int) or halfmove_clock < 0:
        raise ValueError("Saved halfmove clock is invalid.")

    position_counts = data.get("position_counts", {})
    if not isinstance(position_counts, dict):
        raise ValueError("Saved position counts are invalid.")
    normalized_position_counts: dict[str, int] = {}
    for key, value in position_counts.items():
        # Repetition counts must be positive integers keyed by position signature.
        if not isinstance(key, str) or not isinstance(value, int) or value < 1:
            raise ValueError("Saved position counts are invalid.")
        normalized_position_counts[key] = value

    status_message = data.get("status_message", "White to move.")
    if not isinstance(status_message, str):
        raise ValueError("Saved status message is invalid.")

    return MatchState(
        # MatchState.__post_init__ will seed repetition counts if a legacy save omitted them.
        game_variant=normalize_game_variant(game_variant),
        board=board_from_data(data.get("board")),
        current_turn=current_turn,
        selected_square=coord_from_data(data.get("selected_square")),
        highlighted_moves=[coord_from_data(square) for square in highlighted_data],
        winner=winner,
        is_draw=bool(data.get("is_draw", False)),
        result_recorded=bool(data.get("result_recorded", False)),
        castling_rights=normalized_castling_rights,
        en_passant_target=coord_from_data(data.get("en_passant_target")),
        halfmove_clock=halfmove_clock,
        position_counts=normalized_position_counts,
        status_message=status_message,
        move_history=[move_record_from_data(record) for record in move_history_data],
    )


def app_state_to_data(state: AppState) -> dict[str, object]:
    """Convert the full app state into JSON-safe data."""
    # AppState includes user preferences plus the active match payload.
    return {
        "mode": state.mode,
        "screen_message": state.screen_message,
        "piece_theme": state.piece_theme,
        "board_theme": state.board_theme,
        "sound_enabled": state.sound_enabled,
        "game_variant": state.game_variant,
        "ai_personality": state.ai_personality,
        "ai_difficulty": state.ai_difficulty,
        "ai_player_color": state.ai_player_color,
        "match": match_to_data(state.match),
    }


def app_state_from_data(data) -> AppState:
    """Rebuild the full app state from saved JSON data."""
    # The top-level save must be an object with metadata and a nested match.
    if not isinstance(data, dict):
        raise ValueError("Saved app state is invalid.")

    mode = data.get("mode", "local")
    screen_message = data.get("screen_message", "Welcome to Chess.")
    piece_theme = data.get("piece_theme", "black_white")
    board_theme = data.get("board_theme", "black_white")
    sound_enabled = data.get("sound_enabled", False)
    game_variant = data.get("game_variant", "standard")
    ai_personality = data.get("ai_personality", "random")
    # Old saves may not include difficulty, so infer it from the legacy personality.
    ai_difficulty = data.get("ai_difficulty", ai_difficulty_for_personality(ai_personality))
    ai_player_color = data.get("ai_player_color", "white")
    if (
        not isinstance(mode, str)
        or not isinstance(screen_message, str)
        or not isinstance(piece_theme, str)
        or not isinstance(board_theme, str)
        or not isinstance(sound_enabled, bool)
        or not isinstance(game_variant, str)
        or not isinstance(ai_personality, str)
        or not isinstance(ai_difficulty, str)
        or not isinstance(ai_player_color, str)
    ):
        raise ValueError("Saved app metadata is invalid.")

    if mode not in {"local", "ai", "ai_vs_ai"}:
        # Unknown future/invalid modes fall back to local play rather than blocking load.
        mode = "local"

    match = match_from_data(data.get("match"))
    if "game_variant" not in data:
        game_variant = match.game_variant
    game_variant = normalize_game_variant(game_variant)
    match.game_variant = game_variant

    return AppState(
        mode=mode,
        screen_message=screen_message,
        piece_theme=piece_theme,
        board_theme=board_theme,
        sound_enabled=sound_enabled,
        game_variant=normalize_game_variant(game_variant),
        ai_personality=ai_personality,
        ai_difficulty=normalize_ai_difficulty(ai_difficulty),
        ai_player_color=ai_player_color,
        match=match,
    )


def has_saved_match(file_path: Path = SAVE_FILE) -> bool:
    """Return whether a saved match file currently exists."""
    return file_path.exists()


def delete_saved_match(file_path: Path = SAVE_FILE) -> bool:
    """Delete a saved match file when present and report whether anything changed."""
    # Returning False for missing files makes reset operations idempotent.
    if not file_path.exists():
        return False

    file_path.unlink()
    return True


def save_app_state(state: AppState, file_path: Path = SAVE_FILE) -> Path:
    """Write the current app state to disk as JSON."""
    # Create saves/ lazily so a fresh checkout does not need the folder yet.
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as save_file:
        json.dump(app_state_to_data(state), save_file, indent=2)
    return file_path


def load_app_state(file_path: Path = SAVE_FILE) -> AppState:
    """Load a previously saved app state from disk."""
    # JSON parsing and validation happen before a new AppState is returned.
    with file_path.open("r", encoding="utf-8") as save_file:
        return app_state_from_data(json.load(save_file))
