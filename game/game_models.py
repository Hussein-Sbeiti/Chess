from __future__ import annotations

# game/game_models.py
# Chess Project - shared match state
# Created: 2026-04-15

"""
This file stores the pure data models that describe an active chess match.

MoveRecord
- stores what moved, from where, to where, and whether something was captured

MatchState
- stores the board
- tracks whose turn it is
- tracks which square is selected in the UI
- stores short status text and move history

There is intentionally no Tkinter code here.
"""

from dataclasses import dataclass, field

from game.board import Board, create_starting_board
from game.coords import Coord, index_to_algebraic


CASTLING_KEYS = (
    "white_kingside",
    "white_queenside",
    "black_kingside",
    "black_queenside",
)
CASTLING_KEY_SYMBOLS = {
    "white_kingside": "K",
    "white_queenside": "Q",
    "black_kingside": "k",
    "black_queenside": "q",
}


def board_position_key(
    board: Board,
    current_turn: str,
    castling_rights: dict[str, bool],
    en_passant_target: Coord | None,
) -> str:
    """Return a compact position signature for repetition tracking."""
    board_text = "/".join(
        "".join(piece.symbol if piece is not None else "." for piece in row) for row in board
    )
    castling_text = "".join(
        CASTLING_KEY_SYMBOLS[key] for key in CASTLING_KEYS if castling_rights.get(key, False)
    ) or "-"
    en_passant_text = "-" if en_passant_target is None else index_to_algebraic(en_passant_target)
    return f"{board_text}|{current_turn}|{castling_text}|{en_passant_text}"


@dataclass(frozen=True)
class MoveRecord:
    """History entry for one completed move."""

    start: Coord
    end: Coord
    piece_symbol: str
    notation: str = ""
    captured_symbol: str | None = None
    note: str = ""


@dataclass
class GameTimer:
    """Tracks remaining time for each player in a match.
    
    Times are stored in seconds. Common time controls:
    - Bullet: 1-3 minutes per player
    - Blitz: 3-5 minutes per player
    - Rapid: 10-25 minutes per player
    - Classical: 30+ minutes per player
    """

    white_remaining: int = 300  # 5 minutes default
    black_remaining: int = 300  # 5 minutes default
    is_active: bool = True
    
    def format_time(self, seconds: int) -> str:
        """Format seconds as MM:SS or H:MM:SS for display."""
        if seconds < 0:
            seconds = 0
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"
    
    def get_white_display(self) -> str:
        """Return formatted white time for UI display."""
        return self.format_time(self.white_remaining)
    
    def get_black_display(self) -> str:
        """Return formatted black time for UI display."""
        return self.format_time(self.black_remaining)
    
    def decrement_active_player(self, current_turn: str) -> None:
        """Decrement the active player's time by 1 second."""
        if not self.is_active:
            return
        if current_turn == "white":
            if self.white_remaining > 0:
                self.white_remaining -= 1
        else:
            if self.black_remaining > 0:
                self.black_remaining -= 1
    
    def has_time_expired(self) -> bool:
        """Return True if either player has run out of time."""
        return self.white_remaining <= 0 or self.black_remaining <= 0
    
    def get_expired_player(self) -> str | None:
        """Return the color of the player who ran out of time, if any."""
        if self.white_remaining <= 0:
            return "white"
        if self.black_remaining <= 0:
            return "black"
        return None
    
    def pause(self) -> None:
        """Pause the timer."""
        self.is_active = False
    
    def resume(self) -> None:
        """Resume the timer."""
        self.is_active = True
    
    def reset(self, initial_time: int = 300) -> None:
        """Reset both players' times to the initial value."""
        self.white_remaining = initial_time
        self.black_remaining = initial_time
        self.is_active = True


@dataclass
class MatchState:
    """All data needed to describe one active match."""

    board: Board = field(default_factory=create_starting_board)
    current_turn: str = "white"
    selected_square: Coord | None = None
    highlighted_moves: list[Coord] = field(default_factory=list)
    winner: str | None = None
    is_draw: bool = False
    result_recorded: bool = False
    castling_rights: dict[str, bool] = field(
        default_factory=lambda: {
            "white_kingside": True,
            "white_queenside": True,
            "black_kingside": True,
            "black_queenside": True,
        }
    )
    en_passant_target: Coord | None = None
    halfmove_clock: int = 0
    position_counts: dict[str, int] = field(default_factory=dict)
    status_message: str = "White to move."
    move_history: list[MoveRecord] = field(default_factory=list)
    timer: GameTimer = field(default_factory=GameTimer)

    def __post_init__(self) -> None:
        """Seed repetition tracking when a match is created from any position."""
        if not self.position_counts:
            self.position_counts = {
                board_position_key(
                    self.board,
                    self.current_turn,
                    self.castling_rights,
                    self.en_passant_target,
                ): 1
            }

    def reset(self) -> None:
        """Reset the match to a fresh starting position."""
        self.board = create_starting_board()
        self.current_turn = "white"
        self.selected_square = None
        self.highlighted_moves.clear()
        self.winner = None
        self.is_draw = False
        self.result_recorded = False
        self.castling_rights = {
            "white_kingside": True,
            "white_queenside": True,
            "black_kingside": True,
            "black_queenside": True,
        }
        self.en_passant_target = None
        self.halfmove_clock = 0
        self.position_counts = {
            board_position_key(
                self.board,
                self.current_turn,
                self.castling_rights,
                self.en_passant_target,
            ): 1
        }
        self.status_message = "White to move."
        self.move_history.clear()
        self.timer.reset()
