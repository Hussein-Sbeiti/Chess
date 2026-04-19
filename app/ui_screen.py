from __future__ import annotations

# app/ui_screen.py
# Chess Project - all UI screens
# Created: 2026-04-15

"""
This file contains the visual screens for the Chess project.

WelcomeScreen
- explains the project foundation
- starts a new local match

GameScreen
- renders the board
- handles click-to-select and click-to-move interaction
- asks the rules module for legal move candidates
- updates status text and move history

ResultScreen
- shows an end-of-game summary
- provides buttons to play again or return home

The important architectural rule is the same as Battleship:
the screens should call game helpers for rules instead of hard-coding
chess logic directly into Tkinter button callbacks.
"""

import tkinter as tk
import platform
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageOps, ImageTk

    PIL_AVAILABLE = True
except ImportError:
    Image = None
    ImageDraw = None
    ImageOps = None
    ImageTk = None
    PIL_AVAILABLE = False

from app.persistence import has_saved_match
from app.scoreboard import rank_window
from game.ai import AI_PERSONALITY_LABELS, choose_ai_move, normalize_ai_personality
from game.board import piece_at
from game.coords import Coord, FILES, index_to_algebraic
from game.game_models import MoveRecord
from game.pieces import PROMOTION_CHOICES
from game.rules import (
    find_king,
    is_in_check,
    is_promotion_move,
    legal_moves_for_piece,
    make_move,
    piece_belongs_to_player,
)


SCREEN_BG = "#0D2236"
CARD_BG = "#132A40"
PANEL_BG = "#1C3D5B"
PANEL_SOFT_BG = "#244B6A"
PANEL_DEEP_BG = "#102B42"
LIGHT_SQUARE = "#EEE8D5"
DARK_SQUARE = "#7A9E7E"
SELECTED_SQUARE = "#F4C95D"
MOVE_HINT_SQUARE = "#A5D6A7"
LAST_MOVE_FROM_SQUARE = "#7FA7C9"
LAST_MOVE_TO_SQUARE = "#D8B35D"
CHECK_SQUARE = "#D66A5F"
TEXT_PRIMARY = "#F5F7FA"
TEXT_MUTED = "#BDD4E7"
TEXT_SOFT = "#8FA9BF"
BUTTON_BG = "#3A6EA5"
BUTTON_ALT_BG = "#6C8EAD"
BUTTON_SUCCESS_BG = "#3B7D5F"
BORDER_COLOR = "#345B79"
MIN_SQUARE_SIZE = 42
MAX_SQUARE_SIZE = 84
DEFAULT_SQUARE_SIZE = 64
ICON_DIR = Path(__file__).resolve().parent.parent / "icons"
VISIBLE_ALPHA_THRESHOLD = 24
COORD_TEXT = "#9FB7CA"
THEME_PANEL_BG = "#1A3C58"
THEME_CARD_BG = "#274C6B"
THEME_CARD_ACTIVE_BG = "#3C6FA4"
MODE_CARD_BG = "#234763"
MODE_CARD_ACTIVE_BG = "#3A6EA5"
PRIMARY_FONT_FAMILY = {
    "Darwin": "Helvetica Neue",
    "Windows": "Segoe UI",
    "Linux": "DejaVu Sans",
}.get(platform.system(), "Arial")
MONO_FONT_FAMILY = {
    "Darwin": "Menlo",
    "Windows": "Consolas",
    "Linux": "DejaVu Sans Mono",
}.get(platform.system(), "Courier New")
THEME_PRESETS = {
    "classic": {
        "label": "Classic",
        "white_low": "#C9C2B3",
        "white_high": "#FFF9EF",
        "black_low": "#1D2430",
        "black_high": "#5A667A",
    },
    "royal": {
        "label": "Royal",
        "white_low": "#D5B15A",
        "white_high": "#FFF3C2",
        "black_low": "#1F2457",
        "black_high": "#6673D1",
    },
    "forest": {
        "label": "Forest",
        "white_low": "#C7DCCB",
        "white_high": "#F5FFF6",
        "black_low": "#3B2A20",
        "black_high": "#7A5A3D",
    },
    "ruby": {
        "label": "Ruby",
        "white_low": "#E2C7D1",
        "white_high": "#FFF3F8",
        "black_low": "#4A1623",
        "black_high": "#B54966",
    },
    "frost": {
        "label": "Frost",
        "white_low": "#D7ECF7",
        "white_high": "#FFFFFF",
        "black_low": "#1F3B4D",
        "black_high": "#6DB6DC",
    },
    "sunset": {
        "label": "Sunset",
        "white_low": "#F0CDA9",
        "white_high": "#FFF4DD",
        "black_low": "#4A2B22",
        "black_high": "#D67646",
    },
    "violet": {
        "label": "Violet",
        "white_low": "#DCCBF0",
        "white_high": "#FCF7FF",
        "black_low": "#2F214A",
        "black_high": "#8E73D9",
    },
    "ember": {
        "label": "Ember",
        "white_low": "#E9C6B0",
        "white_high": "#FFF5E9",
        "black_low": "#3E1710",
        "black_high": "#C8572D",
    },
    "mint": {
        "label": "Mint",
        "white_low": "#D4F1E3",
        "white_high": "#FBFFFD",
        "black_low": "#1D4C41",
        "black_high": "#56C3A8",
    },
}


def clamp_int(value: int, minimum: int, maximum: int) -> int:
    """Clamp one integer into an inclusive range."""
    return max(minimum, min(maximum, value))


def ui_font(size: int, weight: str = "normal", mono: bool = False) -> tuple[str, int, str]:
    """Return a font tuple that behaves more consistently across desktop platforms."""
    family = MONO_FONT_FAMILY if mono else PRIMARY_FONT_FAMILY
    return family, size, weight


def compute_board_metrics(window_width: int, window_height: int) -> dict[str, int]:
    """Return responsive board and font sizes based on the current window size."""
    safe_width = max(780, window_width)
    safe_height = max(620, window_height)

    board_width_budget = max(420, int((safe_width - 72) * 0.60))
    board_height_budget = max(360, safe_height - 230)
    coord_and_padding_budget = 44

    square_size = clamp_int(
        min(
            (board_width_budget - coord_and_padding_budget) // 8,
            (board_height_budget - coord_and_padding_budget) // 8,
        ),
        MIN_SQUARE_SIZE,
        MAX_SQUARE_SIZE,
    )

    return {
        "square_size": square_size,
        "icon_size": clamp_int(int(square_size * 0.82), 30, 72),
        "piece_font_size": clamp_int(int(square_size * 0.40), 16, 28),
        "coord_font_size": clamp_int(int(square_size * 0.18), 8, 13),
    }


def normalize_theme_name(theme_name: str) -> str:
    """Return a known theme name, falling back to the default."""
    return theme_name if theme_name in THEME_PRESETS else "classic"


def _tint_piece_image(image: Image.Image, low_color: str, high_color: str) -> Image.Image:
    """Tint the grayscale piece art while preserving alpha transparency."""
    alpha_channel = image.getchannel("A")
    grayscale = ImageOps.grayscale(image)
    tinted = ImageOps.colorize(grayscale, black=low_color, white=high_color).convert("RGBA")
    tinted.putalpha(alpha_channel)
    return tinted


def _prepare_themed_piece_image(
    theme_name: str,
    color: str,
    kind: str,
    icon_size: int,
) -> Image.Image | None:
    """Load, crop, tint, and scale one piece image for a theme."""
    theme = THEME_PRESETS[normalize_theme_name(theme_name)]
    image_path = ICON_DIR / f"{kind} {color}.png"
    if not image_path.exists():
        return None

    resampling = getattr(Image, "Resampling", Image)
    image = Image.open(image_path).convert("RGBA")
    alpha_channel = image.getchannel("A")
    visible_mask = alpha_channel.point(
        lambda alpha: 255 if alpha >= VISIBLE_ALPHA_THRESHOLD else 0
    )
    visible_box = visible_mask.getbbox() or alpha_channel.getbbox()
    if visible_box is not None:
        image = image.crop(visible_box)

    image = _tint_piece_image(
        image,
        theme[f"{color}_low"],
        theme[f"{color}_high"],
    )
    image.thumbnail((icon_size, icon_size), resampling.LANCZOS)
    return image


def load_piece_images(
    theme_name: str,
    square_size: int = DEFAULT_SQUARE_SIZE,
    icon_size: int | None = None,
) -> dict[tuple[str, str], ImageTk.PhotoImage]:
    """Load and center piece art on a square transparent canvas."""
    if not PIL_AVAILABLE:
        return {}

    if icon_size is None:
        icon_size = clamp_int(int(square_size * 0.82), 30, 72)

    images: dict[tuple[str, str], ImageTk.PhotoImage] = {}

    for color in ("white", "black"):
        for kind in ("king", "queen", "rook", "bishop", "knight", "pawn"):
            image = _prepare_themed_piece_image(theme_name, color, kind, icon_size)
            if image is None:
                continue

            canvas = Image.new("RGBA", (square_size, square_size), (0, 0, 0, 0))
            offset = ((square_size - image.width) // 2, (square_size - image.height) // 2)
            canvas.paste(image, offset, image)
            images[(color, kind)] = ImageTk.PhotoImage(canvas)

    return images


def load_theme_preview_images() -> dict[str, ImageTk.PhotoImage]:
    """Build small preview images for each selectable theme."""
    if not PIL_AVAILABLE:
        return {}

    previews: dict[str, ImageTk.PhotoImage] = {}
    preview_width = 132
    preview_height = 74
    sample_size = 24

    for theme_name in THEME_PRESETS:
        canvas = Image.new("RGBA", (preview_width, preview_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        draw.rounded_rectangle(
            (0, 0, preview_width - 1, preview_height - 1),
            radius=16,
            fill=THEME_PANEL_BG,
        )

        square_size = 28
        board_left = 12
        board_top = 16
        for row in range(2):
            for col in range(4):
                x0 = board_left + (col * square_size)
                y0 = board_top + (row * square_size)
                x1 = x0 + square_size
                y1 = y0 + square_size
                square_color = LIGHT_SQUARE if (row + col) % 2 == 0 else DARK_SQUARE
                draw.rectangle((x0, y0, x1, y1), fill=square_color)

        white_piece = _prepare_themed_piece_image(theme_name, "white", "queen", sample_size)
        black_piece = _prepare_themed_piece_image(theme_name, "black", "king", sample_size)
        white_knight = _prepare_themed_piece_image(theme_name, "white", "knight", sample_size)
        black_bishop = _prepare_themed_piece_image(theme_name, "black", "bishop", sample_size)

        for piece_image, offset in (
            (white_piece, (16, 18)),
            (black_piece, (44, 18)),
            (white_knight, (72, 18)),
            (black_bishop, (100, 18)),
        ):
            if piece_image is not None:
                canvas.paste(piece_image, offset, piece_image)

        previews[theme_name] = ImageTk.PhotoImage(canvas)

    return previews


def make_empty_square_image(square_size: int = DEFAULT_SQUARE_SIZE) -> ImageTk.PhotoImage:
    """Create a transparent placeholder image so Tk sizes squares by pixels."""
    if not PIL_AVAILABLE:
        return None
    return ImageTk.PhotoImage(Image.new("RGBA", (square_size, square_size), (0, 0, 0, 0)))


def make_button(parent: tk.Widget, text: str, command, bg: str = BUTTON_BG) -> tk.Button:
    """Create a consistently styled button for the starter UI."""
    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=bg,
        fg="white",
        activebackground=bg,
        activeforeground="white",
        relief="flat",
        bd=0,
        highlightthickness=0,
        font=ui_font(10, "bold"),
        padx=14,
        pady=9,
        cursor="hand2",
    )


def make_coord_label(parent: tk.Widget, text: str) -> tk.Label:
    """Create a small board-coordinate label."""
    return tk.Label(
        parent,
        text=text,
        bg=PANEL_BG,
        fg=COORD_TEXT,
        font=ui_font(10, "bold"),
        width=2,
        height=1,
    )


def make_surface(parent: tk.Widget, bg: str = PANEL_BG, padx: int = 14, pady: int = 14) -> tk.Frame:
    """Create a bordered panel used across the UI."""
    return tk.Frame(
        parent,
        bg=bg,
        padx=padx,
        pady=pady,
        highlightbackground=BORDER_COLOR,
        highlightthickness=1,
    )


def format_move_history(match) -> str:
    """Build a short move-history summary for the right-hand panel."""
    if not match.move_history:
        return "No moves yet."

    entries: list[str] = []
    for index, record in enumerate(match.move_history[-8:], start=max(1, len(match.move_history) - 7)):
        text = record.notation or f"{index_to_algebraic(record.start)} -> {index_to_algebraic(record.end)}"
        entries.append(f"{index}. {text}")

    return "\n".join(entries)


def format_captured_pieces(match, capturer_color: str) -> str:
    """Build a compact text summary of the pieces captured by one side."""
    captured: list[str] = []
    for record in match.move_history:
        if record.captured_symbol is None:
            continue
        mover_color = "white" if record.piece_symbol.isupper() else "black"
        if mover_color == capturer_color:
            captured.append(record.captured_symbol.upper())

    return " ".join(captured) if captured else "None"


def format_scoreboard_summary(scoreboard) -> str:
    """Build a compact summary of long-term scoreboard results."""
    return (
        f"Total games: {scoreboard.total_games}\n"
        f"White wins: {scoreboard.white_wins} | Black wins: {scoreboard.black_wins}\n"
        f"Draws: {scoreboard.draws}\n"
        f"Local matches: {scoreboard.local_games} | AI matches: {scoreboard.ai_games}\n"
        f"Vs AI record: {scoreboard.human_wins}-{scoreboard.human_losses}-{scoreboard.human_draws} (W-L-D)"
    )


def format_rank_summary(scoreboard) -> str:
    """Build a simple progress summary for the ranking system."""
    current_rank, next_rank, current_floor, next_floor = rank_window(scoreboard.ranking_points)
    if next_rank is None or next_floor is None:
        progress_text = "Top rank reached."
    else:
        progress_total = next_floor - current_floor
        progress_done = scoreboard.ranking_points - current_floor
        progress_text = (
            f"Next: {next_rank} in {next_floor - scoreboard.ranking_points} pts "
            f"({progress_done}/{progress_total})"
        )

    return (
        f"Rank: {current_rank}\n"
        f"Points: {scoreboard.ranking_points}\n"
        f"Current streak: {scoreboard.current_streak} | Best: {scoreboard.best_streak}\n"
        f"{progress_text}"
    )


def get_last_move_squares(match) -> tuple[Coord | None, Coord | None]:
    """Return the start and end squares for the most recent move."""
    if not match.move_history:
        return None, None

    last_record: MoveRecord = match.move_history[-1]
    return last_record.start, last_record.end


def get_checked_king_square(match) -> Coord | None:
    """Return the king square that should be highlighted for check."""
    for color in ("white", "black"):
        if is_in_check(match.board, color):
            return find_king(match.board, color)
    return None


def get_square_background(square: Coord, match) -> str:
    """Choose the board-square background color from the current match state."""
    row, col = square
    base_bg = LIGHT_SQUARE if (row + col) % 2 == 0 else DARK_SQUARE
    last_from, last_to = get_last_move_squares(match)
    checked_king_square = get_checked_king_square(match)

    if square == checked_king_square:
        return CHECK_SQUARE
    if square == match.selected_square:
        return SELECTED_SQUARE
    if square in match.highlighted_moves:
        return MOVE_HINT_SQUARE
    if square == last_to:
        return LAST_MOVE_TO_SQUARE
    if square == last_from:
        return LAST_MOVE_FROM_SQUARE
    return base_bg


class WelcomeScreen(tk.Frame):
    """Intro screen that starts the local chess scaffold."""

    def __init__(self, parent: tk.Widget, app) -> None:
        super().__init__(parent, bg=SCREEN_BG)
        self.app = app
        self.mode_buttons: dict[str, tk.Button] = {}
        self.personality_buttons: dict[str, tk.Button] = {}
        self.side_buttons: dict[str, tk.Button] = {}
        self.theme_buttons: dict[str, tk.Button] = {}
        self.theme_preview_images = load_theme_preview_images()
        self.scoreboard_var = tk.StringVar(value="No completed matches yet.")
        self.rank_var = tk.StringVar(value="Rank: Unranked")

        page = tk.Frame(self, bg=SCREEN_BG, padx=30, pady=24)
        page.pack(fill="both", expand=True)

        card = make_surface(page, bg=CARD_BG, padx=24, pady=24)
        card.pack(expand=True)

        tk.Label(
            card,
            text="Chess",
            font=ui_font(31, "bold"),
            bg=CARD_BG,
            fg=TEXT_PRIMARY,
        ).pack(anchor="w")

        tk.Label(
            card,
            text="A compact desktop chess app with local play, computer opponents, themes, and save/load.",
            font=ui_font(12),
            bg=CARD_BG,
            fg=TEXT_MUTED,
            wraplength=760,
            justify="left",
        ).pack(anchor="w", pady=(6, 16))

        body = tk.Frame(card, bg=CARD_BG)
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=0)
        body.grid_columnconfigure(1, weight=1)

        left_column = tk.Frame(body, bg=CARD_BG)
        left_column.grid(row=0, column=0, sticky="n", padx=(0, 16))

        right_column = tk.Frame(body, bg=CARD_BG)
        right_column.grid(row=0, column=1, sticky="nsew")

        intro_panel = make_surface(left_column, bg=PANEL_DEEP_BG, padx=16, pady=16)
        intro_panel.pack(fill="x", pady=(0, 14))

        tk.Label(
            intro_panel,
            text="Quick Start",
            font=ui_font(14, "bold"),
            bg=PANEL_DEEP_BG,
            fg=TEXT_PRIMARY,
        ).pack(anchor="w")

        tk.Label(
            intro_panel,
            text="Legal rules, special moves, AI personalities, move history, captured pieces, and board highlights are all ready.",
            font=ui_font(10),
            bg=PANEL_DEEP_BG,
            fg=TEXT_MUTED,
            wraplength=250,
            justify="left",
        ).pack(anchor="w", pady=(8, 0))

        scoreboard_panel = make_surface(left_column, bg=PANEL_DEEP_BG, padx=16, pady=16)
        scoreboard_panel.pack(fill="x", pady=(0, 14))

        tk.Label(
            scoreboard_panel,
            text="Scoreboard",
            font=ui_font(14, "bold"),
            bg=PANEL_DEEP_BG,
            fg=TEXT_PRIMARY,
        ).pack(anchor="w")

        tk.Label(
            scoreboard_panel,
            textvariable=self.scoreboard_var,
            font=ui_font(10),
            bg=PANEL_DEEP_BG,
            fg=TEXT_MUTED,
            justify="left",
            anchor="w",
        ).pack(anchor="w", pady=(8, 8))

        tk.Label(
            scoreboard_panel,
            textvariable=self.rank_var,
            font=ui_font(10, "bold"),
            bg=PANEL_DEEP_BG,
            fg=TEXT_PRIMARY,
            justify="left",
            anchor="w",
        ).pack(anchor="w")

        tk.Label(
            left_column,
            text="Play Setup",
            font=ui_font(15, "bold"),
            bg=CARD_BG,
            fg=TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, 8))

        self.mode_status_label = tk.Label(
            left_column,
            text="Current mode: Local Two-Player",
            font=ui_font(10),
            bg=CARD_BG,
            fg=TEXT_SOFT,
        )
        self.mode_status_label.pack(anchor="w", pady=(0, 8))

        mode_panel = make_surface(left_column, bg=THEME_PANEL_BG, padx=14, pady=12)
        mode_panel.pack(fill="x")

        mode_grid = tk.Frame(mode_panel, bg=THEME_PANEL_BG)
        mode_grid.pack(anchor="w")

        tk.Label(
            mode_grid,
            text="Mode",
            font=ui_font(11, "bold"),
            bg=THEME_PANEL_BG,
            fg=TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w", padx=(0, 14), pady=6)

        mode_buttons = tk.Frame(mode_grid, bg=THEME_PANEL_BG)
        mode_buttons.grid(row=0, column=1, sticky="w", pady=6)

        for mode_name, label in (("local", "Local Two-Player"), ("ai", "Vs Computer")):
            button = tk.Button(
                mode_buttons,
                text=label,
                command=lambda selected=mode_name: self.app.set_mode(selected),
                relief="flat",
                bd=0,
                highlightthickness=0,
                padx=14,
                pady=10,
                cursor="hand2",
                font=ui_font(10, "bold"),
                bg=MODE_CARD_BG,
                fg=TEXT_PRIMARY,
                activebackground=MODE_CARD_BG,
                activeforeground=TEXT_PRIMARY,
            )
            button.pack(side="left", padx=6)
            self.mode_buttons[mode_name] = button

        tk.Label(
            mode_grid,
            text="AI Style",
            font=ui_font(11, "bold"),
            bg=THEME_PANEL_BG,
            fg=TEXT_PRIMARY,
        ).grid(row=1, column=0, sticky="w", padx=(0, 14), pady=6)

        personality_row = tk.Frame(mode_grid, bg=THEME_PANEL_BG)
        personality_row.grid(row=1, column=1, sticky="w", pady=6)

        for personality, label in AI_PERSONALITY_LABELS.items():
            button = tk.Button(
                personality_row,
                text=label,
                command=lambda selected=personality: self.app.set_ai_personality(selected),
                relief="flat",
                bd=0,
                highlightthickness=0,
                padx=12,
                pady=8,
                cursor="hand2",
                font=ui_font(10, "bold"),
                bg=MODE_CARD_BG,
                fg=TEXT_PRIMARY,
                activebackground=MODE_CARD_BG,
                activeforeground=TEXT_PRIMARY,
            )
            button.pack(side="left", padx=5)
            self.personality_buttons[personality] = button

        tk.Label(
            mode_grid,
            text="Your Side",
            font=ui_font(11, "bold"),
            bg=THEME_PANEL_BG,
            fg=TEXT_PRIMARY,
        ).grid(row=2, column=0, sticky="w", padx=(0, 14), pady=6)

        side_row = tk.Frame(mode_grid, bg=THEME_PANEL_BG)
        side_row.grid(row=2, column=1, sticky="w", pady=6)

        for color, label in (("white", "White / 1st"), ("black", "Black / 2nd")):
            button = tk.Button(
                side_row,
                text=label,
                command=lambda selected=color: self.app.set_ai_player_color(selected),
                relief="flat",
                bd=0,
                highlightthickness=0,
                padx=12,
                pady=8,
                cursor="hand2",
                font=ui_font(10, "bold"),
                bg=MODE_CARD_BG,
                fg=TEXT_PRIMARY,
                activebackground=MODE_CARD_BG,
                activeforeground=TEXT_PRIMARY,
            )
            button.pack(side="left", padx=5)
            self.side_buttons[color] = button

        tk.Label(
            right_column,
            text="Piece Theme",
            font=ui_font(15, "bold"),
            bg=CARD_BG,
            fg=TEXT_PRIMARY,
        ).pack(anchor="w")

        self.theme_status_label = tk.Label(
            right_column,
            text="Current theme: Classic",
            font=ui_font(10),
            bg=CARD_BG,
            fg=TEXT_SOFT,
        )
        self.theme_status_label.pack(anchor="w", pady=(6, 8))

        theme_panel = make_surface(right_column, bg=THEME_PANEL_BG, padx=12, pady=12)
        theme_panel.pack(fill="x")

        tk.Label(
            theme_panel,
            text="Preview the piece palettes and pick the one you want for the board.",
            font=ui_font(10),
            bg=THEME_PANEL_BG,
            fg=TEXT_MUTED,
            wraplength=500,
            justify="center",
        ).pack(pady=(0, 10))

        theme_grid = tk.Frame(theme_panel, bg=THEME_PANEL_BG)
        theme_grid.pack()

        for index, (theme_name, theme_data) in enumerate(THEME_PRESETS.items()):
            preview_image = self.theme_preview_images.get(theme_name, "")
            button = tk.Button(
                theme_grid,
                text=theme_data["label"],
                image=preview_image,
                compound="top" if preview_image else "none",
                command=lambda selected=theme_name: self.app.set_piece_theme(selected),
                relief="flat",
                bd=0,
                highlightthickness=0,
                padx=10,
                pady=10,
                cursor="hand2",
                wraplength=110,
                justify="center",
                font=ui_font(10, "bold"),
                bg=THEME_CARD_BG,
                fg=TEXT_PRIMARY,
                activebackground=THEME_CARD_BG,
                activeforeground=TEXT_PRIMARY,
            )
            button.grid(row=index // 3, column=index % 3, padx=5, pady=5)
            self.theme_buttons[theme_name] = button

        controls = tk.Frame(card, bg=CARD_BG)
        controls.pack(fill="x", pady=(18, 0))

        make_button(controls, "Start Match", self.app.start_new_game).pack(side="left")
        self.load_button = make_button(
            controls,
            "Load Saved Match",
            self._load_saved_match,
            bg=BUTTON_SUCCESS_BG,
        )
        self.load_button.pack(side="left", padx=8)
        make_button(
            controls,
            "Result Screen Preview",
            lambda: self.app.open_result_screen("Result screen scaffold ready for future checkmate flow."),
            bg=BUTTON_ALT_BG,
        ).pack(side="left")

    def refresh(self) -> None:
        """Welcome screen stays mostly static, but the hook keeps screen switching consistent."""
        current_mode = "ai" if self.app.state.mode == "ai" else "local"
        current_personality = normalize_ai_personality(self.app.state.ai_personality)
        current_side = self.app.state.ai_player_color if self.app.state.ai_player_color in {"white", "black"} else "white"
        current_theme = normalize_theme_name(self.app.state.piece_theme)
        if current_mode == "ai":
            side_text = "White / 1st" if current_side == "white" else "Black / 2nd"
            mode_text = f"Current mode: Vs Computer ({AI_PERSONALITY_LABELS[current_personality]}, {side_text})"
        else:
            mode_text = "Current mode: Local Two-Player"
        self.mode_status_label.config(text=mode_text)
        self.theme_status_label.config(text=f"Current theme: {THEME_PRESETS[current_theme]['label']}")
        self.load_button.config(state="normal" if has_saved_match() else "disabled")
        self.scoreboard_var.set(format_scoreboard_summary(self.app.scoreboard))
        self.rank_var.set(format_rank_summary(self.app.scoreboard))

        for mode_name, button in self.mode_buttons.items():
            is_active = mode_name == current_mode
            button.config(
                bg=MODE_CARD_ACTIVE_BG if is_active else MODE_CARD_BG,
                activebackground=MODE_CARD_ACTIVE_BG if is_active else MODE_CARD_BG,
                state="normal",
            )

        personality_state = "normal" if current_mode == "ai" else "disabled"
        for personality, button in self.personality_buttons.items():
            is_active = personality == current_personality
            button.config(
                bg=MODE_CARD_ACTIVE_BG if is_active and current_mode == "ai" else MODE_CARD_BG,
                activebackground=MODE_CARD_ACTIVE_BG if is_active and current_mode == "ai" else MODE_CARD_BG,
                state=personality_state,
            )

        side_state = "normal" if current_mode == "ai" else "disabled"
        for color, button in self.side_buttons.items():
            is_active = color == current_side
            button.config(
                bg=MODE_CARD_ACTIVE_BG if is_active and current_mode == "ai" else MODE_CARD_BG,
                activebackground=MODE_CARD_ACTIVE_BG if is_active and current_mode == "ai" else MODE_CARD_BG,
                state=side_state,
            )

        for theme_name, button in self.theme_buttons.items():
            is_active = theme_name == current_theme
            button.config(
                bg=THEME_CARD_ACTIVE_BG if is_active else THEME_CARD_BG,
                fg=TEXT_PRIMARY,
                activebackground=THEME_CARD_ACTIVE_BG if is_active else THEME_CARD_BG,
                activeforeground=TEXT_PRIMARY,
            )
        return None

    def _load_saved_match(self) -> None:
        """Load the latest saved match from the welcome screen."""
        success, message = self.app.load_match()
        if not success:
            self.app.state.screen_message = message
            self.app.state.match.status_message = message
            self.refresh()


class GameScreen(tk.Frame):
    """Main board screen for the starter chess prototype."""

    def __init__(self, parent: tk.Widget, app) -> None:
        super().__init__(parent, bg=SCREEN_BG)
        self.app = app
        self.ai_after_id: str | None = None
        self._resize_after_id: str | None = None
        self.board_buttons: dict[Coord, tk.Button] = {}
        self.coord_labels: list[tk.Label] = []
        self.square_size = DEFAULT_SQUARE_SIZE
        self.icon_size = clamp_int(int(DEFAULT_SQUARE_SIZE * 0.82), 30, 72)
        self.piece_font_size = clamp_int(int(DEFAULT_SQUARE_SIZE * 0.40), 16, 28)
        self.coord_font_size = clamp_int(int(DEFAULT_SQUARE_SIZE * 0.18), 8, 13)
        self.loaded_theme = normalize_theme_name(self.app.state.piece_theme)
        self.piece_images = load_piece_images(self.loaded_theme, self.square_size, self.icon_size)
        self.empty_square_image = make_empty_square_image(self.square_size)
        self.history_var = tk.StringVar(value="No moves yet.")
        self.white_captures_var = tk.StringVar(value="None")
        self.black_captures_var = tk.StringVar(value="None")
        self.meta_var = tk.StringVar(value="")

        header = tk.Frame(self, bg=SCREEN_BG)
        header.pack(fill="x", padx=24, pady=(22, 8))

        title_row = tk.Frame(header, bg=SCREEN_BG)
        title_row.pack(fill="x")

        self.title_label = tk.Label(
            title_row,
            text="Chess Match",
            font=ui_font(24, "bold"),
            bg=SCREEN_BG,
            fg=TEXT_PRIMARY,
        )
        self.title_label.pack(side="left")

        self.meta_label = tk.Label(
            title_row,
            textvariable=self.meta_var,
            font=ui_font(10, "bold"),
            bg=PANEL_SOFT_BG,
            fg=TEXT_PRIMARY,
            padx=12,
            pady=6,
        )
        self.meta_label.pack(side="right")

        status_strip = make_surface(header, bg=PANEL_DEEP_BG, padx=14, pady=10)
        status_strip.pack(fill="x", pady=(10, 0))

        self.status_label = tk.Label(
            status_strip,
            text="White to move.",
            font=ui_font(12),
            bg=PANEL_DEEP_BG,
            fg=TEXT_MUTED,
            anchor="w",
            justify="left",
        )
        self.status_label.pack(fill="x")

        content = tk.Frame(self, bg=SCREEN_BG)
        content.pack(fill="both", expand=True, padx=24, pady=14)
        content.grid_columnconfigure(0, weight=5)
        content.grid_columnconfigure(1, weight=3)
        content.grid_rowconfigure(0, weight=1)

        board_card = make_surface(content, bg=CARD_BG, padx=16, pady=16)
        board_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        info_column = tk.Frame(content, bg=SCREEN_BG)
        info_column.grid(row=0, column=1, sticky="nsew")
        info_column.grid_rowconfigure(2, weight=1)

        info_header = make_surface(info_column, bg=CARD_BG, padx=16, pady=14)
        info_header.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        tk.Label(
            info_header,
            text="Match Notes",
            font=ui_font(17, "bold"),
            bg=CARD_BG,
            fg=TEXT_PRIMARY,
        ).pack(anchor="w")

        tk.Label(
            info_header,
            text="Track captures, recent moves, and quick actions without crowding the board.",
            font=ui_font(10),
            bg=CARD_BG,
            fg=TEXT_MUTED,
            wraplength=280,
            justify="left",
        ).pack(anchor="w", pady=(6, 0))

        captures_panel = make_surface(info_column, bg=CARD_BG, padx=16, pady=14)
        captures_panel.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        tk.Label(
            captures_panel,
            text="Captured Pieces",
            font=ui_font(13, "bold"),
            bg=CARD_BG,
            fg=TEXT_PRIMARY,
        ).pack(anchor="w")

        captures_grid = tk.Frame(captures_panel, bg=CARD_BG)
        captures_grid.pack(fill="x", pady=(10, 0))
        captures_grid.grid_columnconfigure(0, weight=1)
        captures_grid.grid_columnconfigure(1, weight=1)

        white_panel = make_surface(captures_grid, bg=PANEL_BG, padx=12, pady=10)
        white_panel.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        tk.Label(
            white_panel,
            text="White",
            font=ui_font(10, "bold"),
            bg=PANEL_BG,
            fg=TEXT_SOFT,
        ).pack(anchor="w")
        tk.Label(
            white_panel,
            textvariable=self.white_captures_var,
            font=ui_font(12, "bold", mono=True),
            bg=PANEL_BG,
            fg=TEXT_PRIMARY,
            justify="left",
            anchor="w",
        ).pack(anchor="w", pady=(6, 0))

        black_panel = make_surface(captures_grid, bg=PANEL_BG, padx=12, pady=10)
        black_panel.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        tk.Label(
            black_panel,
            text="Black",
            font=ui_font(10, "bold"),
            bg=PANEL_BG,
            fg=TEXT_SOFT,
        ).pack(anchor="w")
        tk.Label(
            black_panel,
            textvariable=self.black_captures_var,
            font=ui_font(12, "bold", mono=True),
            bg=PANEL_BG,
            fg=TEXT_PRIMARY,
            justify="left",
            anchor="w",
        ).pack(anchor="w", pady=(6, 0))

        history_panel = make_surface(info_column, bg=CARD_BG, padx=16, pady=14)
        history_panel.grid(row=2, column=0, sticky="nsew")

        tk.Label(
            history_panel,
            text="Recent Moves",
            font=ui_font(13, "bold"),
            bg=CARD_BG,
            fg=TEXT_PRIMARY,
        ).pack(anchor="w")

        tk.Label(
            history_panel,
            textvariable=self.history_var,
            font=ui_font(11, mono=True),
            bg=PANEL_BG,
            fg=TEXT_PRIMARY,
            justify="left",
            anchor="nw",
            padx=12,
            pady=10,
        ).pack(fill="both", expand=True, pady=(10, 12))

        controls_panel = tk.Frame(history_panel, bg=CARD_BG)
        controls_panel.pack(fill="x")
        controls_panel.grid_columnconfigure(0, weight=1)
        controls_panel.grid_columnconfigure(1, weight=1)

        self.save_button = make_button(controls_panel, "Save Match", self.on_save_match, bg=BUTTON_SUCCESS_BG)
        self.save_button.grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=(0, 6))
        self.load_button = make_button(controls_panel, "Load Match", self.on_load_match, bg=BUTTON_ALT_BG)
        self.load_button.grid(row=0, column=1, sticky="ew", padx=(6, 0), pady=(0, 6))
        make_button(controls_panel, "Reset Match", self.app.start_new_game).grid(
            row=1,
            column=0,
            sticky="ew",
            padx=(0, 6),
        )
        make_button(controls_panel, "Return Home", self.app.return_home, bg=BUTTON_ALT_BG).grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(6, 0),
        )

        self._build_board(board_card)
        self.bind("<Configure>", self._on_configure)
        self.after_idle(self._apply_responsive_layout)

    def _build_board(self, parent: tk.Widget) -> None:
        tk.Label(
            parent,
            text="Board",
            font=ui_font(14, "bold"),
            bg=CARD_BG,
            fg=TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, 10))

        board_shell = make_surface(parent, bg=PANEL_BG, padx=10, pady=10)
        board_shell.pack()

        for col, file_char in enumerate(FILES, start=1):
            top_label = make_coord_label(board_shell, file_char)
            top_label.grid(row=0, column=col, padx=1, pady=(0, 4))
            self.coord_labels.append(top_label)

            bottom_label = make_coord_label(board_shell, file_char)
            bottom_label.grid(row=9, column=col, padx=1, pady=(4, 0))
            self.coord_labels.append(bottom_label)

        for row in range(8):
            rank_text = str(8 - row)
            left_label = make_coord_label(board_shell, rank_text)
            left_label.grid(row=row + 1, column=0, padx=(0, 4), pady=1)
            self.coord_labels.append(left_label)

            right_label = make_coord_label(board_shell, rank_text)
            right_label.grid(row=row + 1, column=9, padx=(4, 0), pady=1)
            self.coord_labels.append(right_label)

        for row in range(8):
            for col in range(8):
                button_kwargs = {
                    "text": "",
                    "font": ui_font(self.piece_font_size, "bold"),
                    "relief": "flat",
                    "bd": 0,
                    "highlightthickness": 0,
                    "padx": 0,
                    "pady": 0,
                    "compound": "center",
                    "cursor": "hand2",
                    "command": lambda r=row, c=col: self.on_square_clicked((r, c)),
                }
                if self.empty_square_image is not None:
                    button_kwargs["image"] = self.empty_square_image
                    button_kwargs["width"] = self.square_size
                    button_kwargs["height"] = self.square_size
                else:
                    button_kwargs["text"] = " "
                    button_kwargs["width"] = max(2, self.square_size // 18)
                    button_kwargs["height"] = max(1, self.square_size // 28)

                button = tk.Button(
                    board_shell,
                    **button_kwargs,
                )
                button.grid(row=row + 1, column=col + 1, padx=1, pady=1)
                self.board_buttons[(row, col)] = button

    def _on_configure(self, _event=None) -> None:
        """Debounce resize work so the board only re-renders after the window settles."""
        if self._resize_after_id is not None:
            self.after_cancel(self._resize_after_id)
        self._resize_after_id = self.after(30, self._apply_responsive_layout)

    def _apply_responsive_layout(self) -> None:
        """Resize the board so it fits cleanly across different platforms and DPIs."""
        self._resize_after_id = None
        top = self.winfo_toplevel()
        width = max(top.winfo_width(), top.winfo_reqwidth(), 980)
        height = max(top.winfo_height(), top.winfo_reqheight(), 720)
        metrics = compute_board_metrics(width, height)

        if (
            metrics["square_size"] == self.square_size
            and metrics["icon_size"] == self.icon_size
            and metrics["piece_font_size"] == self.piece_font_size
            and metrics["coord_font_size"] == self.coord_font_size
        ):
            return

        self.square_size = metrics["square_size"]
        self.icon_size = metrics["icon_size"]
        self.piece_font_size = metrics["piece_font_size"]
        self.coord_font_size = metrics["coord_font_size"]

        current_theme = normalize_theme_name(self.app.state.piece_theme)
        self.loaded_theme = current_theme
        self.piece_images = load_piece_images(current_theme, self.square_size, self.icon_size)
        self.empty_square_image = make_empty_square_image(self.square_size)

        for label in self.coord_labels:
            label.config(font=ui_font(self.coord_font_size, "bold"))

        for button in self.board_buttons.values():
            config = {"font": ui_font(self.piece_font_size, "bold")}
            if self.empty_square_image is not None:
                config["width"] = self.square_size
                config["height"] = self.square_size
            else:
                config["width"] = max(2, self.square_size // 18)
                config["height"] = max(1, self.square_size // 28)
            button.config(**config)

        self.refresh()

    def _choose_promotion_kind(self, color: str) -> str | None:
        """Open a small modal dialog so the player can choose a promotion piece."""
        dialog = tk.Toplevel(self)
        dialog.title("Choose Promotion")
        dialog.configure(bg=CARD_BG, padx=18, pady=18)
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        selection: dict[str, str | None] = {"kind": None}

        tk.Label(
            dialog,
            text=f"{color.title()} pawn promotion",
            font=ui_font(16, "bold"),
            bg=CARD_BG,
            fg=TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, 8))

        tk.Label(
            dialog,
            text="Choose the piece for the promoted pawn.",
            font=ui_font(11),
            bg=CARD_BG,
            fg=TEXT_MUTED,
        ).pack(anchor="w", pady=(0, 14))

        choices = tk.Frame(dialog, bg=CARD_BG)
        choices.pack()

        for kind in PROMOTION_CHOICES:
            piece_image = self.piece_images.get((color, kind), "")
            button = tk.Button(
                choices,
                text=kind.title(),
                image=piece_image,
                compound="top" if piece_image else "none",
                bg=PANEL_BG,
                fg=TEXT_PRIMARY,
                activebackground=PANEL_BG,
                activeforeground=TEXT_PRIMARY,
                relief="flat",
                bd=0,
                highlightthickness=0,
                padx=8,
                pady=8,
                cursor="hand2",
                command=lambda selected=kind: selection.update(kind=selected) or dialog.destroy(),
            )
            button.pack(side="left", padx=6)

        make_button(dialog, "Cancel", dialog.destroy, bg=BUTTON_ALT_BG).pack(pady=(16, 0))

        dialog.update_idletasks()
        root = self.winfo_toplevel()
        x = root.winfo_rootx() + (root.winfo_width() - dialog.winfo_width()) // 2
        y = root.winfo_rooty() + (root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        self.wait_window(dialog)
        return selection["kind"]

    def on_square_clicked(self, square: Coord) -> None:
        """Handle selection and move attempts using the shared match state."""
        match = self.app.state.match
        if self._is_ai_turn():
            match.status_message = (
                f"Computer ({AI_PERSONALITY_LABELS[normalize_ai_personality(self.app.state.ai_personality)]}) is thinking."
            )
            self.refresh()
            return
        clicked_piece = piece_at(match.board, square)

        if match.selected_square is None:
            if clicked_piece and piece_belongs_to_player(clicked_piece, match.current_turn):
                match.selected_square = square
                match.highlighted_moves = legal_moves_for_piece(match, square)
                if match.highlighted_moves:
                    match.status_message = (
                        f"Selected {clicked_piece.color} {clicked_piece.kind} at {index_to_algebraic(square)}."
                    )
                else:
                    match.status_message = (
                        f"Selected {clicked_piece.color} {clicked_piece.kind} at "
                        f"{index_to_algebraic(square)}. No legal moves available."
                    )
            else:
                match.status_message = f"{match.current_turn.title()} must select one of their own pieces."
            self.refresh()
            return

        if square == match.selected_square:
            match.selected_square = None
            match.highlighted_moves.clear()
            match.status_message = f"{match.current_turn.title()} selection cleared."
            self.refresh()
            return

        if clicked_piece and piece_belongs_to_player(clicked_piece, match.current_turn):
            match.selected_square = square
            match.highlighted_moves = legal_moves_for_piece(match, square)
            if match.highlighted_moves:
                match.status_message = (
                    f"Selected {clicked_piece.color} {clicked_piece.kind} at {index_to_algebraic(square)}."
                )
            else:
                match.status_message = (
                    f"Selected {clicked_piece.color} {clicked_piece.kind} at "
                    f"{index_to_algebraic(square)}. No legal moves available."
                )
            self.refresh()
            return

        promotion_choice: str | None = None
        if square in match.highlighted_moves and is_promotion_move(match.board, match.selected_square, square):
            promoting_piece = piece_at(match.board, match.selected_square)
            if promoting_piece is not None:
                promotion_choice = self._choose_promotion_kind(promoting_piece.color)
                if promotion_choice is None:
                    match.status_message = "Promotion canceled."
                    self.refresh()
                    return

        success, message = make_move(match, match.selected_square, square, promotion_choice=promotion_choice)
        match.status_message = message
        self.refresh()

        if success and (match.winner or match.is_draw):
            self.app.after(250, lambda: self.app.open_result_screen(match.status_message))
            return

        if success:
            self._schedule_ai_turn_if_needed()

    def refresh(self) -> None:
        """Redraw the board and sidebar from the current match state."""
        match = self.app.state.match
        current_theme = normalize_theme_name(self.app.state.piece_theme)
        if current_theme != self.loaded_theme:
            self.loaded_theme = current_theme
            self.piece_images = load_piece_images(current_theme, self.square_size, self.icon_size)

        current_mode = "Vs Computer" if self.app.state.mode == "ai" else "Local"
        side_summary = ""
        if self.app.state.mode == "ai":
            side_summary = " | You: White" if self.app.state.ai_player_color == "white" else " | You: Black"
        self.meta_var.set(f"{current_mode}{side_summary} | Theme: {THEME_PRESETS[current_theme]['label']}")
        self.status_label.config(text=match.status_message)
        self.history_var.set(format_move_history(match))
        self.white_captures_var.set(format_captured_pieces(match, "white"))
        self.black_captures_var.set(format_captured_pieces(match, "black"))
        self.load_button.config(state="normal" if has_saved_match() else "disabled")

        for square, button in self.board_buttons.items():
            piece = piece_at(match.board, square)
            bg = get_square_background(square, match)

            if piece is not None and (piece.color, piece.kind) in self.piece_images:
                button.config(
                    image=self.piece_images[(piece.color, piece.kind)],
                    text="",
                    bg=bg,
                    activebackground=bg,
                )
            else:
                if self.empty_square_image is not None:
                    button.config(
                        image=self.empty_square_image,
                        text=piece.symbol if piece else " ",
                        bg=bg,
                        activebackground=bg,
                    )
                else:
                    button.config(
                        image="",
                        text=piece.symbol if piece else " ",
                        bg=bg,
                        activebackground=bg,
                    )

        self._schedule_ai_turn_if_needed()

    def on_save_match(self) -> None:
        """Save the current match and refresh the sidebar message."""
        _, message = self.app.save_match()
        self.app.state.match.status_message = message
        self.refresh()

    def on_load_match(self) -> None:
        """Load the last saved match and refresh this screen if needed."""
        success, message = self.app.load_match()
        if not success:
            self.app.state.match.status_message = message
            self.refresh()

    def cancel_pending_ai_turn(self) -> None:
        """Cancel any queued AI move callback."""
        if self.ai_after_id is not None:
            self.after_cancel(self.ai_after_id)
            self.ai_after_id = None

    def _schedule_ai_turn_if_needed(self) -> None:
        """Queue the computer's turn when the active mode needs it."""
        match = self.app.state.match
        if self.app.state.mode != "ai":
            self.cancel_pending_ai_turn()
            return
        if not self._is_ai_turn() or match.winner or match.is_draw or self.ai_after_id is not None:
            return
        match.status_message = (
            f"Computer ({AI_PERSONALITY_LABELS[normalize_ai_personality(self.app.state.ai_personality)]}) is thinking."
        )
        self.status_label.config(text=match.status_message)
        self.ai_after_id = self.after(450, self._run_ai_turn)

    def _run_ai_turn(self) -> None:
        """Ask the AI for a move and apply it to the live match."""
        self.ai_after_id = None
        match = self.app.state.match
        if self.app.state.mode != "ai" or not self._is_ai_turn() or match.winner or match.is_draw:
            return

        personality = normalize_ai_personality(self.app.state.ai_personality)
        ai_move = choose_ai_move(match, self._get_ai_color(), personality)
        if ai_move is None:
            return

        origin, target, promotion_choice = ai_move
        success, message = make_move(match, origin, target, promotion_choice=promotion_choice)
        if success:
            if match.winner or match.is_draw:
                self.refresh()
                self.app.after(250, lambda: self.app.open_result_screen(match.status_message))
                return
            match.status_message = (
                f"Computer ({AI_PERSONALITY_LABELS[personality]}) played "
                f"{match.move_history[-1].notation}. {match.current_turn.title()} to move."
            )
        else:
            match.status_message = message
        self.refresh()

    def _get_ai_color(self) -> str:
        """Return the computer side for the current AI game."""
        return "black" if self.app.state.ai_player_color == "white" else "white"

    def _is_ai_turn(self) -> bool:
        """Return whether the computer should move right now."""
        return self.app.state.mode == "ai" and self.app.state.match.current_turn == self._get_ai_color()


class ResultScreen(tk.Frame):
    """Simple result screen reserved for end-of-match flow."""

    def __init__(self, parent: tk.Widget, app) -> None:
        super().__init__(parent, bg=SCREEN_BG)
        self.app = app
        self.scoreboard_var = tk.StringVar(value="No completed matches yet.")
        self.rank_var = tk.StringVar(value="Rank: Unranked")

        card = make_surface(self, bg=CARD_BG, padx=28, pady=28)
        card.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            card,
            text="Match Result",
            font=ui_font(30, "bold"),
            bg=CARD_BG,
            fg=TEXT_PRIMARY,
        ).pack(pady=(0, 12))

        self.message_label = tk.Label(
            card,
            text="Game result summary goes here.",
            font=ui_font(13),
            bg=CARD_BG,
            fg=TEXT_MUTED,
            wraplength=540,
            justify="center",
        )
        self.message_label.pack(pady=(0, 20))

        scoreboard_panel = make_surface(card, bg=PANEL_BG, padx=16, pady=14)
        scoreboard_panel.pack(fill="x", pady=(0, 20))

        tk.Label(
            scoreboard_panel,
            text="Career Board",
            font=ui_font(14, "bold"),
            bg=PANEL_BG,
            fg=TEXT_PRIMARY,
        ).pack(anchor="w")

        tk.Label(
            scoreboard_panel,
            textvariable=self.scoreboard_var,
            font=ui_font(10),
            bg=PANEL_BG,
            fg=TEXT_MUTED,
            justify="left",
            anchor="w",
        ).pack(anchor="w", pady=(8, 8))

        tk.Label(
            scoreboard_panel,
            textvariable=self.rank_var,
            font=ui_font(10, "bold"),
            bg=PANEL_BG,
            fg=TEXT_PRIMARY,
            justify="left",
            anchor="w",
        ).pack(anchor="w")

        controls = tk.Frame(card, bg=CARD_BG)
        controls.pack()

        make_button(controls, "Play Again", self.app.start_new_game).pack(side="left", padx=8)
        make_button(controls, "Return Home", self.app.return_home, bg=BUTTON_ALT_BG).pack(side="left", padx=8)

    def refresh(self) -> None:
        """Update the screen with the latest app-level result message."""
        self.message_label.config(text=self.app.state.screen_message)
        self.scoreboard_var.set(format_scoreboard_summary(self.app.scoreboard))
        self.rank_var.set(format_rank_summary(self.app.scoreboard))
