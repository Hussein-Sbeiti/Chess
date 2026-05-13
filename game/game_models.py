"""Shared dataclasses that represent timers, moves, and active match state."""
from __future__ import annotations

from dataclasses import dataclass, field

from game.board import Board, create_starting_board
from game.coords import Coord, index_to_algebraic
from game.variants import STANDARD_VARIANT, castling_rights_for_variant, create_board_for_variant, normalize_game_variant


CASTLING_KEYS = (
    # Store castling rights in a fixed order so position keys are deterministic.
    "white_kingside",
    "white_queenside",
    "black_kingside",
    "black_queenside",
)
CASTLING_KEY_SYMBOLS = {
    # These symbols mirror FEN castling notation: KQ for white, kq for black.
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
    # Use one character per square so different boards always produce different text.
    board_text = "/".join(
        "".join(piece.symbol if piece is not None else "." for piece in row) for row in board
    )
    # A player can repeat the same board shape with different castling rights, so include them.
    castling_text = "".join(
        CASTLING_KEY_SYMBOLS[key] for key in CASTLING_KEYS if castling_rights.get(key, False)
    ) or "-"
    # En passant availability also changes legal moves, so it belongs in the key.
    en_passant_text = "-" if en_passant_target is None else index_to_algebraic(en_passant_target)
    return f"{board_text}|{current_turn}|{castling_text}|{en_passant_text}"


@dataclass(frozen=True)
class MoveRecord:
    """History entry for one completed move."""

    # Original square and destination square in internal (row, col) coordinates.
    start: Coord
    end: Coord
    # Store the symbol as moved so the history can survive later board changes.
    piece_symbol: str
    # Human-readable notation is filled by the rules module after a legal move.
    notation: str = ""
    # Captured pieces are optional because many moves land on an empty square.
    captured_symbol: str | None = None
    # Notes are used for special moves such as castling, en passant, and promotion.
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

    # The app starts with a five-minute clock for each side.
    white_remaining: int = 300
    black_remaining: int = 300
    # Pausing flips this flag without changing the saved clock values.
    is_active: bool = True
    
    def format_time(self, seconds: int) -> str:
        """Format seconds as MM:SS or H:MM:SS for display."""
        # Clamp negative values so the UI never shows confusing countdown text.
        if seconds < 0:
            seconds = 0
        # Split raw seconds into display-friendly time units.
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        # Longer games include hours, shorter games stay in compact minute form.
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
        # A paused clock keeps both players' remaining time frozen.
        if not self.is_active:
            return
        # Only the side whose turn it is loses a second.
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
        # White is checked first only because both players should not expire at once in normal play.
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

    # Variant changes the starting board and, for Random Moves, movement rules.
    game_variant: str = STANDARD_VARIANT
    # Board and turn data describe the position itself.
    board: Board = field(default_factory=create_starting_board)
    current_turn: str = "white"
    # Selection/highlight state is UI-facing, but kept here so saves can restore it.
    selected_square: Coord | None = None
    highlighted_moves: list[Coord] = field(default_factory=list)
    # End-state flags are set by the rules engine when a match concludes.
    winner: str | None = None
    is_draw: bool = False
    # The scoreboard uses this to avoid counting a finished match twice.
    result_recorded: bool = False
    # Castling rights start available and are removed as kings/rooks move.
    castling_rights: dict[str, bool] = field(
        default_factory=lambda: castling_rights_for_variant(STANDARD_VARIANT)
    )
    # This is set only on the turn immediately after a two-square pawn advance.
    en_passant_target: Coord | None = None
    # Halfmove clock supports the fifty-move rule.
    halfmove_clock: int = 0
    # Position counts power threefold-repetition detection.
    position_counts: dict[str, int] = field(default_factory=dict)
    # Status text is intentionally stored with the match for save/load continuity.
    status_message: str = "White to move."
    # Move history drives notation, recent moves, captured pieces, and saved matches.
    move_history: list[MoveRecord] = field(default_factory=list)
    # The timer belongs to the match so saved games can keep clock state later.
    timer: GameTimer = field(default_factory=GameTimer)

    def __post_init__(self) -> None:
        """Seed repetition tracking when a match is created from any position."""
        self.game_variant = normalize_game_variant(self.game_variant)
        # Loaded positions may already have counts; fresh/custom boards need an initial key.
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
        # Restore pure board state first.
        self.game_variant = normalize_game_variant(self.game_variant)
        self.board = create_board_for_variant(self.game_variant)
        self.current_turn = "white"
        # Clear transient selection and result data from the previous match.
        self.selected_square = None
        self.highlighted_moves.clear()
        self.winner = None
        self.is_draw = False
        self.result_recorded = False
        # A new game always begins with all castling rights available.
        self.castling_rights = castling_rights_for_variant(self.game_variant)
        # Reset draw-rule and special-move trackers.
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
        # Reset UI-facing text/history and restart the clock.
        self.status_message = "White to move."
        self.move_history.clear()
        self.timer.reset()
