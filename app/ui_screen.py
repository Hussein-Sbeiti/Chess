from __future__ import annotations

# app/ui_screen.py
# Chess Project - all UI screens
# Created: 2026-04-15

"""
This file contains the visual screens for the Chess project.

WelcomeScreen
- shows match setup, themes, and progress
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
from game.ai import (
    AI_DIFFICULTY_LABELS,
    choose_ai_move_for_difficulty,
    normalize_ai_difficulty,
)
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
BUTTON_DISABLED_BG = "#6D7480"
BUTTON_DISABLED_FG = "#D7DEE6"
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
BOARD_THEME_PRESETS = {
    "classic": {"label": "Classic", "light": "#EEE8D5", "dark": "#7A9E7E"},
    "walnut": {"label": "Walnut", "light": "#E8D7BB", "dark": "#8A5A44"},
    "slate": {"label": "Slate", "light": "#DCE4EC", "dark": "#60758E"},
    "rosewood": {"label": "Rosewood", "light": "#F0D8D6", "dark": "#9A6671"},
    "desert": {"label": "Desert", "light": "#F2E1BB", "dark": "#B88A47"},
    "ocean": {"label": "Ocean", "light": "#DCECF6", "dark": "#46779F"},
}


def clamp_int(value: int, minimum: int, maximum: int) -> int:
    """Clamp one integer into an inclusive range."""
    return max(minimum, min(maximum, value))


def blend_hex(color: str, other: str, amount: float) -> str:
    """Blend two hex colors together for hover styling."""
    color = color.lstrip("#")
    other = other.lstrip("#")
    r1, g1, b1 = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
    r2, g2, b2 = int(other[0:2], 16), int(other[2:4], 16), int(other[4:6], 16)
    r = round(r1 + (r2 - r1) * amount)
    g = round(g1 + (g2 - g1) * amount)
    b = round(b1 + (b2 - b1) * amount)
    return f"#{r:02x}{g:02x}{b:02x}"


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


def normalize_board_theme_name(theme_name: str) -> str:
    """Return a known board theme name, falling back to the default."""
    return theme_name if theme_name in BOARD_THEME_PRESETS else "classic"


def get_board_square_colors(board_theme_name: str) -> tuple[str, str]:
    """Return the light and dark square colors for one board palette."""
    theme = BOARD_THEME_PRESETS[normalize_board_theme_name(board_theme_name)]
    return theme["light"], theme["dark"]


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


def load_board_preview_images() -> dict[str, ImageTk.PhotoImage]:
    """Build compact preview swatches for the selectable board palettes."""
    if not PIL_AVAILABLE:
        return {}

    previews: dict[str, ImageTk.PhotoImage] = {}
    preview_width = 92
    preview_height = 48
    square_size = 16

    for theme_name, theme_data in BOARD_THEME_PRESETS.items():
        light_square = theme_data["light"]
        dark_square = theme_data["dark"]
        canvas = Image.new("RGBA", (preview_width, preview_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        draw.rounded_rectangle(
            (0, 0, preview_width - 1, preview_height - 1),
            radius=16,
            fill=THEME_PANEL_BG,
        )
        draw.rounded_rectangle(
            (6, 7, preview_width - 7, preview_height - 7),
            radius=12,
            fill=PANEL_DEEP_BG,
            outline=blend_hex(dark_square, "#ffffff", 0.18),
            width=2,
        )

        board_left = 14
        board_top = 9
        for row in range(2):
            for col in range(4):
                x0 = board_left + (col * square_size)
                y0 = board_top + (row * square_size)
                x1 = x0 + square_size
                y1 = y0 + square_size
                square_color = light_square if (row + col) % 2 == 0 else dark_square
                draw.rectangle((x0, y0, x1, y1), fill=square_color)

        previews[theme_name] = ImageTk.PhotoImage(canvas)

    return previews


def make_empty_square_image(square_size: int = DEFAULT_SQUARE_SIZE) -> ImageTk.PhotoImage:
    """Create a transparent placeholder image so Tk sizes squares by pixels."""
    if not PIL_AVAILABLE:
        return None
    return ImageTk.PhotoImage(Image.new("RGBA", (square_size, square_size), (0, 0, 0, 0)))


class ColorButton(tk.Label):
    """Custom clickable label that keeps app colors consistent across platforms."""

    def __init__(
        self,
        parent: tk.Widget,
        *,
        command=None,
        state: str = "normal",
        activebackground: str | None = None,
        activeforeground: str | None = None,
        disabledbackground: str = BUTTON_DISABLED_BG,
        disabledforeground: str = BUTTON_DISABLED_FG,
        cursor: str = "hand2",
        **kwargs,
    ) -> None:
        bg = kwargs.get("bg", BUTTON_BG)
        fg = kwargs.get("fg", TEXT_PRIMARY)
        super().__init__(parent, cursor=cursor, **kwargs)
        self._command = command
        self._normal_cursor = cursor
        self._enabled = state != "disabled"
        self._hovered = False
        self._default_bg = bg
        self._default_fg = fg
        self._active_bg = activebackground or blend_hex(bg, "#ffffff", 0.10)
        self._active_fg = activeforeground or fg
        self._disabled_bg = disabledbackground
        self._disabled_fg = disabledforeground

        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

        self._apply_visual_state()

    def _on_click(self, _event=None) -> None:
        """Run the widget command when the control is enabled."""
        if self._enabled and self._command is not None:
            self._command()

    def _on_enter(self, _event=None) -> None:
        """Apply hover styling."""
        self._hovered = True
        self._apply_visual_state()

    def _on_leave(self, _event=None) -> None:
        """Restore the resting visual style."""
        self._hovered = False
        self._apply_visual_state()

    def configure(self, cnf=None, **kwargs):
        """Accept button-like config options while rendering as a label."""
        if cnf:
            kwargs.update(cnf)

        if "command" in kwargs:
            self._command = kwargs.pop("command")
        if "state" in kwargs:
            self._enabled = kwargs.pop("state") != "disabled"
        if "cursor" in kwargs:
            self._normal_cursor = kwargs["cursor"]
        if "bg" in kwargs:
            self._default_bg = kwargs["bg"]
        if "fg" in kwargs:
            self._default_fg = kwargs["fg"]
        if "activebackground" in kwargs:
            self._active_bg = kwargs.pop("activebackground")
        if "activeforeground" in kwargs:
            self._active_fg = kwargs.pop("activeforeground")
        if "disabledbackground" in kwargs:
            self._disabled_bg = kwargs.pop("disabledbackground")
        if "disabledforeground" in kwargs:
            self._disabled_fg = kwargs.pop("disabledforeground")

        result = super().configure(**kwargs)
        self._apply_visual_state()
        return result

    config = configure

    def cget(self, key: str):
        """Expose the custom state option alongside standard label keys."""
        if key == "state":
            return "normal" if self._enabled else "disabled"
        return super().cget(key)

    def _apply_visual_state(self) -> None:
        """Apply the correct visual colors for normal, hover, and disabled states."""
        if self._enabled:
            bg = self._active_bg if self._hovered else self._default_bg
            fg = self._active_fg if self._hovered else self._default_fg
            cursor = self._normal_cursor
        else:
            bg = self._disabled_bg
            fg = self._disabled_fg
            cursor = "arrow"

        super().configure(bg=bg, fg=fg, cursor=cursor)


def make_button(parent: tk.Widget, text: str, command, bg: str = BUTTON_BG) -> ColorButton:
    """Create a consistently styled button for the starter UI."""
    return ColorButton(
        parent,
        text=text,
        command=command,
        bg=bg,
        fg="white",
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


class ScrollableColumn(tk.Frame):
    """Vertical scrolling container for taller desktop screens and smaller windows."""

    def __init__(self, parent: tk.Widget, bg: str = SCREEN_BG) -> None:
        super().__init__(parent, bg=bg)
        self._platform = platform.system()
        self._canvas = tk.Canvas(
            self,
            bg=bg,
            highlightthickness=0,
            bd=0,
            relief="flat",
            yscrollincrement=18,
        )
        self._scrollbar = tk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._scrollbar.set)
        self.content = tk.Frame(self._canvas, bg=bg)
        self._content_window = self._canvas.create_window((0, 0), window=self.content, anchor="nw")

        self._canvas.pack(side="left", fill="both", expand=True)
        self._scrollbar.pack(side="right", fill="y")

        self.content.bind("<Configure>", self._sync_scroll_region)
        self._canvas.bind("<Configure>", self._sync_content_width)
        self.bind("<Unmap>", self._unbind_mousewheel, add="+")
        self.bind("<Destroy>", self._unbind_mousewheel, add="+")

        for widget in (self._canvas, self.content):
            widget.bind("<Enter>", self._bind_mousewheel, add="+")
            widget.bind("<Leave>", self._unbind_mousewheel, add="+")

    def _sync_scroll_region(self, _event=None) -> None:
        """Keep the canvas scrollable area aligned with the full content height."""
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _sync_content_width(self, event) -> None:
        """Stretch the embedded content frame to the visible canvas width."""
        self._canvas.itemconfigure(self._content_window, width=event.width)

    def _bind_mousewheel(self, _event=None) -> None:
        """Enable wheel and trackpad scrolling while the pointer is over the screen."""
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self._canvas.bind_all("<Button-4>", self._on_mousewheel)
        self._canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _unbind_mousewheel(self, _event=None) -> None:
        """Release global wheel bindings when the pointer leaves the scroll area."""
        self._canvas.unbind_all("<MouseWheel>")
        self._canvas.unbind_all("<Button-4>")
        self._canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event) -> None:
        """Scroll with platform-appropriate wheel deltas."""
        if getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        elif self._platform == "Darwin":
            delta = -int(event.delta)
        else:
            delta = -int(event.delta / 120) if event.delta else 0

        if delta != 0:
            self._canvas.yview_scroll(delta, "units")


def format_move_history(match) -> str:
    """Build a short move-history summary for the right-hand panel."""
    if not match.move_history:
        return "No moves yet."

    entries: list[str] = []
    for turn_index in range(0, len(match.move_history), 2):
        move_number = (turn_index // 2) + 1
        white_record = match.move_history[turn_index]
        white_text = white_record.notation or (
            f"{index_to_algebraic(white_record.start)} -> {index_to_algebraic(white_record.end)}"
        )
        black_text = ""
        if turn_index + 1 < len(match.move_history):
            black_record = match.move_history[turn_index + 1]
            black_text = black_record.notation or (
                f"{index_to_algebraic(black_record.start)} -> {index_to_algebraic(black_record.end)}"
            )
        entries.append(f"{move_number}. {white_text}" if not black_text else f"{move_number}. {white_text}  {black_text}")

    return "\n".join(entries[-8:])


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


def format_recent_match_history(scoreboard) -> str:
    """Build a compact multi-line summary of recent completed matches."""
    if not scoreboard.recent_matches:
        return "No completed matches yet."
    return "\n".join(entry.summary() for entry in scoreboard.recent_matches[:6])


def format_recent_match_snapshot(scoreboard) -> str:
    """Build a shorter welcome-screen summary of recent completed matches."""
    if not scoreboard.recent_matches:
        return "No completed matches yet."
    return "\n".join(entry.summary() for entry in scoreboard.recent_matches[:3])


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


def get_square_background(square: Coord, match, board_theme_name: str = "classic") -> str:
    """Choose the board-square background color from the current match state."""
    row, col = square
    light_square, dark_square = get_board_square_colors(board_theme_name)
    base_bg = light_square if (row + col) % 2 == 0 else dark_square
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
        self.appearance_tab = "pieces"
        self.mode_buttons: dict[str, ColorButton] = {}
        self.difficulty_buttons: dict[str, ColorButton] = {}
        self.side_buttons: dict[str, ColorButton] = {}
        self.theme_buttons: dict[str, ColorButton] = {}
        self.board_theme_buttons: dict[str, ColorButton] = {}
        self.appearance_tab_buttons: dict[str, ColorButton] = {}
        self.theme_preview_images = load_theme_preview_images()
        self.board_preview_images = load_board_preview_images()
        self.hero_badge_var = tk.StringVar(value="Fresh Start")
        self.scoreboard_var = tk.StringVar(value="No completed matches yet.")
        self.rank_var = tk.StringVar(value="Rank: Unranked")
        self.recent_matches_var = tk.StringVar(value="No completed matches yet.")
        self.appearance_hint_var = tk.StringVar(
            value="Preview the piece palettes and pick the one you want for the board."
        )

        self.scroll_area = ScrollableColumn(self, bg=SCREEN_BG)
        self.scroll_area.pack(fill="both", expand=True)

        page = tk.Frame(self.scroll_area.content, bg=SCREEN_BG, padx=16, pady=14)
        page.pack(fill="both", expand=True)
        page.grid_rowconfigure(0, weight=1)
        page.grid_columnconfigure(0, weight=1)

        card = make_surface(page, bg=CARD_BG, padx=24, pady=24)
        card.grid(row=0, column=0, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(2, weight=1)

        hero = tk.Frame(card, bg=CARD_BG)
        hero.grid(row=0, column=0, sticky="ew")
        hero.grid_columnconfigure(0, weight=1)

        title_stack = tk.Frame(hero, bg=CARD_BG)
        title_stack.grid(row=0, column=0, sticky="w")

        tk.Label(
            title_stack,
            text="Chess",
            font=ui_font(31, "bold"),
            bg=CARD_BG,
            fg=TEXT_PRIMARY,
        ).pack(anchor="w")

        tk.Label(
            title_stack,
            text="A compact desktop chess app with local play, computer opponents, themes, and save/load.",
            font=ui_font(12),
            bg=CARD_BG,
            fg=TEXT_MUTED,
            wraplength=760,
            justify="left",
        ).pack(anchor="w", pady=(8, 0))

        tk.Label(
            hero,
            textvariable=self.hero_badge_var,
            font=ui_font(10, "bold"),
            bg=PANEL_SOFT_BG,
            fg=TEXT_PRIMARY,
            padx=14,
            pady=8,
        ).grid(row=0, column=1, sticky="ne")

        overview = tk.Frame(card, bg=CARD_BG)
        overview.grid(row=1, column=0, sticky="ew", pady=(20, 18))
        overview.grid_columnconfigure(0, weight=4)
        overview.grid_columnconfigure(1, weight=3)
        overview.grid_columnconfigure(2, weight=4)

        scoreboard_panel = make_surface(overview, bg=PANEL_DEEP_BG, padx=16, pady=16)
        scoreboard_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
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
        ).pack(anchor="w", pady=(10, 0))

        rank_panel = make_surface(overview, bg=PANEL_SOFT_BG, padx=16, pady=16)
        rank_panel.grid(row=0, column=1, sticky="nsew", padx=8)
        tk.Label(
            rank_panel,
            text="Rank Progress",
            font=ui_font(14, "bold"),
            bg=PANEL_SOFT_BG,
            fg=TEXT_PRIMARY,
        ).pack(anchor="w")
        tk.Label(
            rank_panel,
            textvariable=self.rank_var,
            font=ui_font(10, "bold"),
            bg=PANEL_SOFT_BG,
            fg=TEXT_PRIMARY,
            justify="left",
            anchor="w",
        ).pack(anchor="w", pady=(10, 0))

        recent_matches_panel = make_surface(overview, bg=PANEL_DEEP_BG, padx=16, pady=16)
        recent_matches_panel.grid(row=0, column=2, sticky="nsew", padx=(8, 0))
        tk.Label(
            recent_matches_panel,
            text="Recent Matches",
            font=ui_font(14, "bold"),
            bg=PANEL_DEEP_BG,
            fg=TEXT_PRIMARY,
        ).pack(anchor="w")
        tk.Label(
            recent_matches_panel,
            textvariable=self.recent_matches_var,
            font=ui_font(9, mono=True),
            bg=PANEL_DEEP_BG,
            fg=TEXT_MUTED,
            justify="left",
            anchor="w",
        ).pack(anchor="w", pady=(10, 0))

        body = tk.Frame(card, bg=CARD_BG)
        body.grid(row=2, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=4)
        body.grid_columnconfigure(1, weight=5)
        body.grid_rowconfigure(0, weight=1)

        setup_card = make_surface(body, bg=PANEL_DEEP_BG, padx=18, pady=18)
        setup_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        tk.Label(
            setup_card,
            text="Match Setup",
            font=ui_font(18, "bold"),
            bg=PANEL_DEEP_BG,
            fg=TEXT_PRIMARY,
        ).pack(anchor="w")

        self.mode_status_label = tk.Label(
            setup_card,
            text="Current mode: Local Two-Player",
            font=ui_font(10),
            bg=PANEL_DEEP_BG,
            fg=TEXT_SOFT,
        )
        self.mode_status_label.pack(anchor="w", pady=(6, 14))

        setup_grid = tk.Frame(setup_card, bg=PANEL_DEEP_BG)
        setup_grid.pack(fill="x")
        setup_grid.grid_columnconfigure(0, minsize=90)
        setup_grid.grid_columnconfigure(1, weight=1)

        tk.Label(
            setup_grid,
            text="Mode",
            font=ui_font(11, "bold"),
            bg=PANEL_DEEP_BG,
            fg=TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="nw", pady=(0, 14))

        mode_buttons = tk.Frame(setup_grid, bg=PANEL_DEEP_BG)
        mode_buttons.grid(row=0, column=1, sticky="w", pady=(0, 14))

        for mode_name, label in (
            ("local", "Local Two-Player"),
            ("ai", "Vs Computer"),
            ("ai_vs_ai", "AI vs AI"),
        ):
            button = ColorButton(
                mode_buttons,
                text=label,
                command=lambda selected=mode_name: self.app.set_mode(selected),
                padx=18,
                pady=12,
                cursor="hand2",
                font=ui_font(10, "bold"),
                bg=MODE_CARD_BG,
                fg=TEXT_PRIMARY,
                activebackground=MODE_CARD_BG,
                activeforeground=TEXT_PRIMARY,
            )
            button.pack(side="left", padx=(0, 8))
            self.mode_buttons[mode_name] = button

        tk.Label(
            setup_grid,
            text="Difficulty",
            font=ui_font(11, "bold"),
            bg=PANEL_DEEP_BG,
            fg=TEXT_PRIMARY,
        ).grid(row=1, column=0, sticky="nw", pady=(0, 14))

        difficulty_row = tk.Frame(setup_grid, bg=PANEL_DEEP_BG)
        difficulty_row.grid(row=1, column=1, sticky="w", pady=(0, 14))

        for difficulty, label in AI_DIFFICULTY_LABELS.items():
            button = ColorButton(
                difficulty_row,
                text=label,
                command=lambda selected=difficulty: self.app.set_ai_difficulty(selected),
                padx=14,
                pady=10,
                cursor="hand2",
                font=ui_font(10, "bold"),
                bg=MODE_CARD_BG,
                fg=TEXT_PRIMARY,
                activebackground=MODE_CARD_BG,
                activeforeground=TEXT_PRIMARY,
            )
            button.pack(side="left", padx=(0, 8))
            self.difficulty_buttons[difficulty] = button

        tk.Label(
            setup_grid,
            text="Your Side",
            font=ui_font(11, "bold"),
            bg=PANEL_DEEP_BG,
            fg=TEXT_PRIMARY,
        ).grid(row=2, column=0, sticky="nw")

        side_row = tk.Frame(setup_grid, bg=PANEL_DEEP_BG)
        side_row.grid(row=2, column=1, sticky="w")

        for color, label in (("white", "White / 1st"), ("black", "Black / 2nd")):
            button = ColorButton(
                side_row,
                text=label,
                command=lambda selected=color: self.app.set_ai_player_color(selected),
                padx=14,
                pady=10,
                cursor="hand2",
                font=ui_font(10, "bold"),
                bg=MODE_CARD_BG,
                fg=TEXT_PRIMARY,
                activebackground=MODE_CARD_BG,
                activeforeground=TEXT_PRIMARY,
            )
            button.pack(side="left", padx=(0, 8))
            self.side_buttons[color] = button

        tk.Label(
            setup_card,
            text="Choose your mode, tune the AI difficulty, and decide whether you play first as white or second as black.",
            font=ui_font(10),
            bg=PANEL_DEEP_BG,
            fg=TEXT_MUTED,
            wraplength=360,
            justify="left",
        ).pack(anchor="w", pady=(16, 0))

        appearance_card = make_surface(body, bg=PANEL_SOFT_BG, padx=18, pady=18)
        appearance_card.grid(row=0, column=1, sticky="nsew")

        appearance_header = tk.Frame(appearance_card, bg=PANEL_SOFT_BG)
        appearance_header.pack(fill="x")
        appearance_header.grid_columnconfigure(0, weight=1)

        tk.Label(
            appearance_header,
            text="Appearance Studio",
            font=ui_font(18, "bold"),
            bg=PANEL_SOFT_BG,
            fg=TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w")

        tk.Label(
            appearance_header,
            text="Live Preview",
            font=ui_font(10, "bold"),
            bg=THEME_CARD_BG,
            fg=TEXT_PRIMARY,
            padx=12,
            pady=6,
        ).grid(row=0, column=1, sticky="e")

        status_row = tk.Frame(appearance_card, bg=PANEL_SOFT_BG)
        status_row.pack(fill="x", pady=(12, 10))

        self.theme_status_label = tk.Label(
            status_row,
            text="Pieces: Classic",
            font=ui_font(10, "bold"),
            bg=THEME_CARD_BG,
            fg=TEXT_PRIMARY,
            padx=12,
            pady=6,
        )
        self.theme_status_label.pack(side="left")

        self.board_theme_status_label = tk.Label(
            status_row,
            text="Board: Classic",
            font=ui_font(10, "bold"),
            bg=THEME_CARD_BG,
            fg=TEXT_PRIMARY,
            padx=12,
            pady=6,
        )
        self.board_theme_status_label.pack(side="left", padx=(8, 0))

        tab_row = tk.Frame(appearance_card, bg=PANEL_SOFT_BG)
        tab_row.pack(fill="x")

        for tab_name, label in (("pieces", "Piece Themes"), ("board", "Board Colors")):
            button = ColorButton(
                tab_row,
                text=label,
                command=lambda selected=tab_name: self._set_appearance_tab(selected),
                padx=16,
                pady=9,
                cursor="hand2",
                font=ui_font(10, "bold"),
                bg=MODE_CARD_BG,
                fg=TEXT_PRIMARY,
                activebackground=MODE_CARD_BG,
                activeforeground=TEXT_PRIMARY,
            )
            button.pack(side="left", padx=(0, 8))
            self.appearance_tab_buttons[tab_name] = button

        tk.Label(
            appearance_card,
            textvariable=self.appearance_hint_var,
            font=ui_font(10),
            bg=PANEL_SOFT_BG,
            fg=TEXT_MUTED,
            wraplength=500,
            justify="left",
        ).pack(anchor="w", pady=(12, 12))

        appearance_stage = tk.Frame(appearance_card, bg=PANEL_SOFT_BG)
        appearance_stage.pack(fill="both", expand=True)

        self.piece_theme_panel = tk.Frame(appearance_stage, bg=PANEL_SOFT_BG)
        for column in range(3):
            self.piece_theme_panel.grid_columnconfigure(column, weight=1)

        for index, (theme_name, theme_data) in enumerate(THEME_PRESETS.items()):
            preview_image = self.theme_preview_images.get(theme_name, "")
            button = ColorButton(
                self.piece_theme_panel,
                text=theme_data["label"],
                image=preview_image,
                compound="top" if preview_image else "none",
                command=lambda selected=theme_name: self.app.set_piece_theme(selected),
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
            button.grid(row=index // 3, column=index % 3, padx=5, pady=5, sticky="nsew")
            self.theme_buttons[theme_name] = button

        self.board_theme_panel = tk.Frame(appearance_stage, bg=PANEL_SOFT_BG)
        for column in range(3):
            self.board_theme_panel.grid_columnconfigure(column, weight=1)

        for index, (theme_name, theme_data) in enumerate(BOARD_THEME_PRESETS.items()):
            preview_image = self.board_preview_images.get(theme_name, "")
            button = ColorButton(
                self.board_theme_panel,
                text=theme_data["label"],
                image=preview_image,
                compound="top" if preview_image else "none",
                command=lambda selected=theme_name: self.app.set_board_theme(selected),
                padx=8,
                pady=8,
                cursor="hand2",
                wraplength=76,
                justify="center",
                font=ui_font(9, "bold"),
                bg=THEME_CARD_BG,
                fg=TEXT_PRIMARY,
                activebackground=THEME_CARD_BG,
                activeforeground=TEXT_PRIMARY,
            )
            button.grid(row=index // 3, column=index % 3, padx=5, pady=5, sticky="nsew")
            self.board_theme_buttons[theme_name] = button

        self._set_appearance_tab("pieces")

        controls = tk.Frame(card, bg=CARD_BG)
        controls.grid(row=3, column=0, sticky="ew", pady=(18, 0))
        for column in range(3):
            controls.grid_columnconfigure(column, weight=1)

        make_button(controls, "Start Match", self.app.start_new_game).grid(row=0, column=0, sticky="ew")
        self.load_button = make_button(
            controls,
            "Load Saved Match",
            self._load_saved_match,
            bg=BUTTON_SUCCESS_BG,
        )
        self.load_button.grid(row=0, column=1, sticky="ew", padx=8)
        make_button(
            controls,
            "Result Screen Preview",
            lambda: self.app.open_result_screen("Result screen scaffold ready for future checkmate flow."),
            bg=BUTTON_ALT_BG,
        ).grid(row=0, column=2, sticky="ew")

    def _set_appearance_tab(self, tab_name: str) -> None:
        """Swap between piece and board appearance selectors."""
        if tab_name not in {"pieces", "board"}:
            return

        self.appearance_tab = tab_name
        self.piece_theme_panel.pack_forget()
        self.board_theme_panel.pack_forget()

        if tab_name == "pieces":
            self.appearance_hint_var.set(
                "Preview the piece palettes and pick the one you want for the board."
            )
            self.piece_theme_panel.pack(fill="both", expand=True)
        else:
            self.appearance_hint_var.set(
                "Pick the light and dark board palette used during the match."
            )
            self.board_theme_panel.pack(fill="both", expand=True)

        for name, button in self.appearance_tab_buttons.items():
            is_active = name == tab_name
            button.config(
                bg=MODE_CARD_ACTIVE_BG if is_active else MODE_CARD_BG,
                activebackground=MODE_CARD_ACTIVE_BG if is_active else MODE_CARD_BG,
            )

    def refresh(self) -> None:
        """Welcome screen stays mostly static, but the hook keeps screen switching consistent."""
        current_mode = self.app.state.mode if self.app.state.mode in {"local", "ai", "ai_vs_ai"} else "local"
        current_difficulty = normalize_ai_difficulty(self.app.state.ai_difficulty)
        current_side = self.app.state.ai_player_color if self.app.state.ai_player_color in {"white", "black"} else "white"
        current_theme = normalize_theme_name(self.app.state.piece_theme)
        current_board_theme = normalize_board_theme_name(self.app.state.board_theme)
        if current_mode == "ai":
            side_text = "White / 1st" if current_side == "white" else "Black / 2nd"
            mode_text = f"Current mode: Vs Computer ({AI_DIFFICULTY_LABELS[current_difficulty]}, {side_text})"
        elif current_mode == "ai_vs_ai":
            mode_text = f"Current mode: AI vs AI ({AI_DIFFICULTY_LABELS[current_difficulty]})"
        else:
            mode_text = "Current mode: Local Two-Player"
        self.mode_status_label.config(text=mode_text)
        self.theme_status_label.config(text=f"Pieces: {THEME_PRESETS[current_theme]['label']}")
        self.board_theme_status_label.config(text=f"Board: {BOARD_THEME_PRESETS[current_board_theme]['label']}")
        saved_match_available = has_saved_match()
        self.hero_badge_var.set("Saved Match Ready" if saved_match_available else "Fresh Start")
        self.load_button.config(state="normal" if saved_match_available else "disabled")
        self.scoreboard_var.set(format_scoreboard_summary(self.app.scoreboard))
        self.rank_var.set(format_rank_summary(self.app.scoreboard))
        self.recent_matches_var.set(format_recent_match_snapshot(self.app.scoreboard))

        for mode_name, button in self.mode_buttons.items():
            is_active = mode_name == current_mode
            button.config(
                bg=MODE_CARD_ACTIVE_BG if is_active else MODE_CARD_BG,
                activebackground=MODE_CARD_ACTIVE_BG if is_active else MODE_CARD_BG,
                state="normal",
            )

        difficulty_state = "normal" if current_mode in {"ai", "ai_vs_ai"} else "disabled"
        for difficulty, button in self.difficulty_buttons.items():
            is_active = difficulty == current_difficulty
            button.config(
                bg=MODE_CARD_ACTIVE_BG if is_active and current_mode in {"ai", "ai_vs_ai"} else MODE_CARD_BG,
                activebackground=MODE_CARD_ACTIVE_BG if is_active and current_mode in {"ai", "ai_vs_ai"} else MODE_CARD_BG,
                state=difficulty_state,
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

        for theme_name, button in self.board_theme_buttons.items():
            is_active = theme_name == current_board_theme
            button.config(
                bg=THEME_CARD_ACTIVE_BG if is_active else THEME_CARD_BG,
                fg=TEXT_PRIMARY,
                activebackground=THEME_CARD_ACTIVE_BG if is_active else THEME_CARD_BG,
                activeforeground=TEXT_PRIMARY,
            )

        self._set_appearance_tab(self.appearance_tab)
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
        self.board_buttons: dict[Coord, ColorButton] = {}
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
                else:
                    button_kwargs["text"] = " "
                    button_kwargs["width"] = max(2, self.square_size // 18)
                    button_kwargs["height"] = max(1, self.square_size // 28)

                button = ColorButton(
                    board_shell,
                    bg=PANEL_BG,
                    fg=TEXT_PRIMARY,
                    activebackground=PANEL_BG,
                    activeforeground=TEXT_PRIMARY,
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
            if self.empty_square_image is None:
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
            button = ColorButton(
                choices,
                text=kind.title(),
                image=piece_image,
                compound="top" if piece_image else "none",
                bg=PANEL_BG,
                fg=TEXT_PRIMARY,
                activebackground=PANEL_BG,
                activeforeground=TEXT_PRIMARY,
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
            difficulty = normalize_ai_difficulty(self.app.state.ai_difficulty)
            match.status_message = (
                f"Computer ({AI_DIFFICULTY_LABELS[difficulty]}) is thinking."
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

        if self.app.state.mode == "ai_vs_ai":
            current_mode = "AI vs AI"
        elif self.app.state.mode == "ai":
            current_mode = "Vs Computer"
        else:
            current_mode = "Local"
        current_board_theme = normalize_board_theme_name(self.app.state.board_theme)
        fullmove_number = (len(match.move_history) // 2) + 1
        side_summary = ""
        if self.app.state.mode == "ai":
            side_summary = " | You: White" if self.app.state.ai_player_color == "white" else " | You: Black"
        self.meta_var.set(
            f"{current_mode}{side_summary} | Move {fullmove_number} | Pieces: {THEME_PRESETS[current_theme]['label']} | "
            f"Board: {BOARD_THEME_PRESETS[current_board_theme]['label']}"
        )
        self.status_label.config(text=match.status_message)
        self.history_var.set(format_move_history(match))
        self.white_captures_var.set(format_captured_pieces(match, "white"))
        self.black_captures_var.set(format_captured_pieces(match, "black"))
        self.load_button.config(state="normal" if has_saved_match() else "disabled")

        for square, button in self.board_buttons.items():
            piece = piece_at(match.board, square)
            bg = get_square_background(square, match, current_board_theme)

            if piece is not None and (piece.color, piece.kind) in self.piece_images:
                button.config(
                    image=self.piece_images[(piece.color, piece.kind)],
                    text="",
                    bg=bg,
                    fg=TEXT_PRIMARY,
                    activebackground=bg,
                    activeforeground=TEXT_PRIMARY,
                )
            else:
                if self.empty_square_image is not None:
                    button.config(
                        image=self.empty_square_image,
                        text=piece.symbol if piece else " ",
                        bg=bg,
                        fg=TEXT_PRIMARY,
                        activebackground=bg,
                        activeforeground=TEXT_PRIMARY,
                    )
                else:
                    fg = "#1D2430" if piece is not None and piece.color == "black" else "#F7F4EC"
                    button.config(
                        image="",
                        text=piece.symbol if piece else " ",
                        bg=bg,
                        fg=fg,
                        activebackground=bg,
                        activeforeground=fg,
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
        if self.app.state.mode not in {"ai", "ai_vs_ai"}:
            self.cancel_pending_ai_turn()
            return
        if not self._is_ai_turn() or match.winner or match.is_draw or self.ai_after_id is not None:
            return
        difficulty = normalize_ai_difficulty(self.app.state.ai_difficulty)
        match.status_message = (
            f"Computer ({AI_DIFFICULTY_LABELS[difficulty]}) is thinking."
        )
        self.status_label.config(text=match.status_message)
        self.ai_after_id = self.after(450, self._run_ai_turn)

    def _run_ai_turn(self) -> None:
        """Ask the AI for a move and apply it to the live match."""
        self.ai_after_id = None
        match = self.app.state.match
        if self.app.state.mode not in {"ai", "ai_vs_ai"} or not self._is_ai_turn() or match.winner or match.is_draw:
            return

        difficulty = normalize_ai_difficulty(self.app.state.ai_difficulty)
        ai_move = choose_ai_move_for_difficulty(match, match.current_turn, difficulty)
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
                f"Computer ({AI_DIFFICULTY_LABELS[difficulty]}) played "
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
        if self.app.state.mode == "ai_vs_ai":
            return True
        return self.app.state.mode == "ai" and self.app.state.match.current_turn == self._get_ai_color()


class ResultScreen(tk.Frame):
    """Simple result screen reserved for end-of-match flow."""

    def __init__(self, parent: tk.Widget, app) -> None:
        super().__init__(parent, bg=SCREEN_BG)
        self.app = app
        self.scoreboard_var = tk.StringVar(value="No completed matches yet.")
        self.rank_var = tk.StringVar(value="Rank: Unranked")
        self.recent_matches_var = tk.StringVar(value="No completed matches yet.")

        page = tk.Frame(self, bg=SCREEN_BG, padx=32, pady=28)
        page.pack(fill="both", expand=True)

        card = make_surface(page, bg=CARD_BG, padx=28, pady=28)
        card.pack(fill="both", expand=True)

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

        recent_matches_panel = make_surface(card, bg=PANEL_BG, padx=16, pady=14)
        recent_matches_panel.pack(fill="x", pady=(0, 20))

        tk.Label(
            recent_matches_panel,
            text="Recent Matches",
            font=ui_font(14, "bold"),
            bg=PANEL_BG,
            fg=TEXT_PRIMARY,
        ).pack(anchor="w")

        tk.Label(
            recent_matches_panel,
            textvariable=self.recent_matches_var,
            font=ui_font(9, mono=True),
            bg=PANEL_BG,
            fg=TEXT_MUTED,
            justify="left",
            anchor="w",
        ).pack(anchor="w", pady=(8, 0))

        controls = tk.Frame(card, bg=CARD_BG)
        controls.pack()

        make_button(controls, "Play Again", self.app.start_new_game).pack(side="left", padx=8)
        make_button(controls, "Return Home", self.app.return_home, bg=BUTTON_ALT_BG).pack(side="left", padx=8)

    def refresh(self) -> None:
        """Update the screen with the latest app-level result message."""
        self.message_label.config(text=self.app.state.screen_message)
        self.scoreboard_var.set(format_scoreboard_summary(self.app.scoreboard))
        self.rank_var.set(format_rank_summary(self.app.scoreboard))
        self.recent_matches_var.set(format_recent_match_history(self.app.scoreboard))
