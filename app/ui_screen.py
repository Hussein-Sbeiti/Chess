"""Tkinter screen layouts and interaction handlers for the chess UI."""
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
from tkinter import messagebox
import platform
from pathlib import Path

try:
    from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps, ImageTk

    PIL_AVAILABLE = True
except ImportError:
    Image = None
    ImageChops = None
    ImageDraw = None
    ImageFilter = None
    ImageOps = None
    ImageTk = None
    PIL_AVAILABLE = False

from app.persistence import has_saved_match
from app.scoreboard import rank_window
from app.sound import play_sound
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


SCREEN_BG = "#02050C"
CARD_BG = "#02050C"
PANEL_BG = "#030812"
PANEL_SOFT_BG = "#050A12"
PANEL_DEEP_BG = "#02050C"
LIGHT_SQUARE = "#D8B56A"
DARK_SQUARE = "#4A2A0A"
SELECTED_SQUARE = "#FFB13B"
MOVE_HINT_SQUARE = "#31D4FF"
LAST_MOVE_FROM_SQUARE = "#1C6DD0"
LAST_MOVE_TO_SQUARE = "#FF6B20"
CHECK_SQUARE = "#FF3B30"
TEXT_PRIMARY = "#F7E7C3"
TEXT_MUTED = "#D2C2A3"
TEXT_SOFT = "#A9956E"
BUTTON_BG = "#9A6518"
BUTTON_ALT_BG = "#2B1807"
BUTTON_SUCCESS_BG = "#3A220A"
BUTTON_DANGER_BG = "#761313"
BORDER_COLOR = "#1A4A78"
NEON_BLUE = "#0EA5FF"
NEON_CYAN = "#22D3EE"
NEON_ORANGE = "#D99A32"
NEON_GOLD = "#F5C46B"
NEON_RED = "#FF2D20"
MIN_SQUARE_SIZE = 42
MAX_SQUARE_SIZE = 70
DEFAULT_SQUARE_SIZE = 64
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSET_PIECE_DIR = PROJECT_ROOT / "assets" / "pieces"
CLASSIC_3D_DIR = ASSET_PIECE_DIR / "classic_3d"
VISIBLE_ALPHA_THRESHOLD = 24
COORD_TEXT = "#9FB7CA"
THEME_PANEL_BG = "#211204"
THEME_CARD_BG = "#241306"
THEME_CARD_ACTIVE_BG = "#75410D"
MODE_CARD_BG = "#241306"
MODE_CARD_ACTIVE_BG = "#8A5A14"
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
        "label": "Black & White",
        "white_low": "#B8B8B8",
        "white_high": "#C4C4C4",
        "black_low": "#080808",
        "black_high": "#242424",
    },
    "wood": {
        "label": "Natural Wood",
        "white_low": "#8A4F18",
        "white_high": "#A86A2A",
        "black_low": "#241006",
        "black_high": "#4F240F",
    },
    "royal": {
        "label": "Gold",
        "white_low": "#7A4D0D",
        "white_high": "#A8751F",
        "black_low": "#3A2506",
        "black_high": "#65400D",
    },
    "forest": {
        "label": "Ivory",
        "white_low": "#A89262",
        "white_high": "#BCA875",
        "black_low": "#6F4F26",
        "black_high": "#8C6735",
    },
    "frost": {
        "label": "Silver",
        "white_low": "#8A8A8A",
        "white_high": "#A3A3A3",
        "black_low": "#333333",
        "black_high": "#5A5A5A",
    },
    "ruby": {
        "label": "Ruby",
        "white_low": "#3A0811",
        "white_high": "#B8324C",
        "black_low": "#160205",
        "black_high": "#5F1020",
    },
    "mint": {
        "label": "Emerald",
        "white_low": "#0B4A2B",
        "white_high": "#24985A",
        "black_low": "#041E13",
        "black_high": "#0F5C35",
    },
    "ember": {
        "label": "Copper",
        "white_low": "#6A2E0F",
        "white_high": "#9A4F22",
        "black_low": "#241006",
        "black_high": "#4F210D",
    },
}
THEME_ALIASES = {
    "black_white": "classic",
    "natural_wood": "wood",
    "gold": "royal",
    "ivory": "forest",
    "silver": "frost",
    "emerald": "mint",
    "copper": "ember",
}
BOARD_THEME_PRESETS = {
    "monochrome": {
        "label": "Black & White",
        "light": "#E8E8E8",
        "dark": "#2B2B2B",
    },
    "classic": {
        "label": "Classic",
        "light": "#F1E6C8",
        "dark": "#6F8F72",
    },
    "walnut": {
        "label": "Walnut",
        "light": "#E6C89F",
        "dark": "#7A4A2B",
    },
    "slate": {
        "label": "Slate",
        "light": "#D8E0E8",
        "dark": "#53687D",
    },
    "rosewood": {
        "label": "Rosewood",
        "light": "#EFD1CF",
        "dark": "#8F5662",
    },
    "desert": {
        "label": "Desert",
        "light": "#F0D69B",
        "dark": "#A87332",
    },
    "ocean": {
        "label": "Ocean",
        "light": "#D8EEF8",
        "dark": "#356F9A",
    },
}
BOARD_THEME_ALIASES = {
    "black_white": "monochrome",
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
    board_height_budget = max(380, safe_height - 310)
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
        "icon_size": clamp_int(int(square_size * 0.90), 32, 78),
        "piece_font_size": clamp_int(int(square_size * 0.40), 16, 28),
        "coord_font_size": clamp_int(int(square_size * 0.18), 8, 13),
    }


def normalize_theme_name(theme_name: str) -> str:
    """Return a known theme name, falling back to the default."""
    normalized_name = THEME_ALIASES.get(theme_name, theme_name)
    return normalized_name if normalized_name in THEME_PRESETS else "classic"


def normalize_board_theme_name(theme_name: str) -> str:
    """Return a known board theme name, falling back to the default."""
    normalized_name = BOARD_THEME_ALIASES.get(theme_name, theme_name)
    return normalized_name if normalized_name in BOARD_THEME_PRESETS else "classic"


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


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    """Convert #RRGGBB or #RGB to integer RGB tuple."""
    color = color.strip().lstrip("#")
    if len(color) == 3:
        color = "".join(channel * 2 for channel in color)
    if len(color) != 6:
        return 255, 255, 255
    return tuple(int(color[index:index + 2], 16) for index in (0, 2, 4))


def _relative_luminance(rgb: tuple[int, int, int]) -> float:
    """Return WCAG relative luminance for one RGB tuple."""
    def linearize(channel: int) -> float:
        srgb = channel / 255.0
        if srgb <= 0.04045:
            return srgb / 12.92
        return ((srgb + 0.055) / 1.055) ** 2.4

    red, green, blue = (linearize(value) for value in rgb)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _contrast_ratio(foreground_hex: str, background_hex: str) -> float:
    """Return contrast ratio between two hex colors."""
    fg_luminance = _relative_luminance(_hex_to_rgb(foreground_hex))
    bg_luminance = _relative_luminance(_hex_to_rgb(background_hex))
    lighter = max(fg_luminance, bg_luminance)
    darker = min(fg_luminance, bg_luminance)
    return (lighter + 0.05) / (darker + 0.05)


def _widen_piece_image(piece_image: Image.Image, icon_size: int) -> Image.Image:
    """Slightly widen thin pieces so they read better on the board."""
    if Image is None:
        return piece_image
    resampling = getattr(Image, "Resampling", Image)
    target_width = min(icon_size, max(piece_image.width, int(round(piece_image.width * 1.10))))
    if target_width <= piece_image.width:
        return piece_image
    return piece_image.resize((target_width, piece_image.height), resampling.LANCZOS)


def _outlined_piece_image(
    piece_image: Image.Image,
    outline_rgb: tuple[int, int, int],
    thickness: int,
    opacity: int,
) -> Image.Image:
    """Disabled outline effect. Return clean piece image only."""
    return piece_image


def _piece_contrast_variant(theme_name: str, piece_color: str, square_bg: str) -> str:
    """Always use the clean base image. No extra outline/shade."""
    return "base"


def _prepare_themed_piece_image(
    theme_name: str,
    color: str,
    kind: str,
    icon_size: int,
) -> Image.Image | None:
    """Load, crop, tint, and scale one piece image for a theme."""
    theme = THEME_PRESETS[normalize_theme_name(theme_name)]
    candidate_names = (
        f"{kind}.png",
        f"{kind} {color}.png",
        f"{kind}_{color}.png",
    )
    candidate_dirs = (
        CLASSIC_3D_DIR,
        ASSET_PIECE_DIR,
    )

    image_path: Path | None = None
    for directory in candidate_dirs:
        for name in candidate_names:
            candidate = directory / name
            if candidate.exists():
                image_path = candidate
                break
        if image_path is not None:
            break

    if image_path is None:
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
    return _widen_piece_image(image, icon_size)


def load_piece_images(
    theme_name: str,
    square_size: int = DEFAULT_SQUARE_SIZE,
    icon_size: int | None = None,
) -> dict[tuple[str, str] | tuple[str, str, str], ImageTk.PhotoImage]:
    """Load clean piece art with no outline and no shadow."""
    if not PIL_AVAILABLE:
        return {}

    if icon_size is None:
        icon_size = clamp_int(int(square_size * 0.90), 32, 78)

    images: dict[tuple[str, str] | tuple[str, str, str], ImageTk.PhotoImage] = {}

    for color in ("white", "black"):
        for kind in ("king", "queen", "rook", "bishop", "knight", "pawn"):
            piece_image = _prepare_themed_piece_image(theme_name, color, kind, icon_size)

            if piece_image is None:
                continue

            canvas = Image.new("RGBA", (square_size, square_size), (0, 0, 0, 0))

            offset_x = (square_size - piece_image.width) // 2
            offset_y = square_size - piece_image.height - max(2, square_size // 14)

            canvas.paste(piece_image, (offset_x, offset_y), piece_image)

            photo_image = ImageTk.PhotoImage(canvas)

            images[(color, kind)] = photo_image
            images[(color, kind, "base")] = photo_image

    return images



def load_theme_preview_images() -> dict[str, ImageTk.PhotoImage]:
    """Build luxury piece-preview cards like the target menu design."""
    if not PIL_AVAILABLE:
        return {}

    previews: dict[str, ImageTk.PhotoImage] = {}
    preview_width = 132
    preview_height = 62
    sample_sizes = {"king": 38, "queen": 36, "rook": 33, "pawn": 29}

    for theme_name in THEME_PRESETS:
        canvas = Image.new("RGBA", (preview_width, preview_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        draw.rounded_rectangle(
            (2, 2, preview_width - 3, preview_height - 3),
            radius=8,
            fill="#050911",
            outline="#8A6426",
            width=1,
        )
        draw.ellipse((18, 42, preview_width - 18, 58), fill=(0, 0, 0, 115), outline="#4D3511")

        placements = (
            ("king", 28, 13),
            ("queen", 55, 15),
            ("rook", 82, 18),
            ("pawn", 106, 22),
        )
        any_piece = False
        for kind, x, y in placements:
            piece_image = _prepare_themed_piece_image(theme_name, "white", kind, sample_sizes[kind])
            if piece_image is not None:
                canvas.paste(piece_image, (x - piece_image.width // 2, y), piece_image)
                any_piece = True

        if not any_piece:
            draw.text((24, 18), "♔ ♕ ♖ ♙", fill="#F2E6D2")

        previews[theme_name] = ImageTk.PhotoImage(canvas)

    return previews


def load_board_preview_images() -> dict[str, ImageTk.PhotoImage]:
    """Build compact board preview swatches."""
    if not PIL_AVAILABLE:
        return {}

    previews: dict[str, ImageTk.PhotoImage] = {}
    preview_width = 112
    preview_height = 54
    square_size = 9

    for theme_name, theme_data in BOARD_THEME_PRESETS.items():
        light_square = theme_data["light"]
        dark_square = theme_data["dark"]
        canvas = Image.new("RGBA", (preview_width, preview_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        draw.rounded_rectangle(
            (2, 2, preview_width - 3, preview_height - 3),
            radius=8,
            fill="#050911",
            outline="#8A6426",
            width=1,
        )
        board_left = 28
        board_top = 9
        for row in range(4):
            for col in range(6):
                square_color = light_square if (row + col) % 2 == 0 else dark_square
                draw.rectangle(
                    (
                        board_left + col * square_size,
                        board_top + row * square_size,
                        board_left + (col + 1) * square_size,
                        board_top + (row + 1) * square_size,
                    ),
                    fill=square_color,
                    outline="#222222",
                )
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


def format_move_history(match, limit: int | None = None) -> str:
    """Build a move-history summary for the right-hand panel."""
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

    if limit is not None:
        entries = entries[-max(1, limit) :]
    return "\n".join(entries)


def format_captured_pieces(match, capturer_color: str, max_per_line: int = 8) -> str:
    """Build a compact text summary of the pieces captured by one side."""
    captured: list[str] = []
    for record in match.move_history:
        if record.captured_symbol is None:
            continue
        mover_color = "white" if record.piece_symbol.isupper() else "black"
        if mover_color == capturer_color:
            captured.append(record.captured_symbol.upper())

    if not captured:
        return "None"

    line_size = max(1, max_per_line)
    shown = [
        " ".join(captured[index : index + line_size])
        for index in range(0, min(len(captured), line_size * 2), line_size)
    ]
    remaining = len(captured) - (line_size * 2)
    if remaining > 0:
        shown.append(f"+{remaining} more")
    return "\n".join(shown)


def count_captured_pieces(match, capturer_color: str) -> int:
    """Return how many pieces one side has captured."""
    count = 0
    for record in match.move_history:
        if record.captured_symbol is None:
            continue
        mover_color = "white" if record.piece_symbol.isupper() else "black"
        if mover_color == capturer_color:
            count += 1
    return count


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
    """Tournament-style animated main menu for the chess studio."""

    def __init__(self, parent: tk.Widget, app) -> None:
        super().__init__(parent, bg=SCREEN_BG)
        self.app = app
        self.appearance_tab = "pieces"
        self.mode_buttons: dict[str, ColorButton] = {}
        self.difficulty_buttons: dict[str, ColorButton] = {}
        self.side_buttons: dict[str, ColorButton] = {}
        self.sound_button: ColorButton | None = None
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
            value="Choose a piece color. Black & White is first; all choices use the same photo chess shapes."
        )
        self._shine_step = 0
        self._shine_job = None
        self.sparkle_labels: list[tk.Label] = []

        outer = tk.Frame(self, bg=SCREEN_BG, padx=6, pady=6)
        outer.pack(fill="both", expand=True)
        outer.grid_rowconfigure(0, weight=1)
        outer.grid_columnconfigure(0, weight=1)

        shell = tk.Frame(
            outer,
            bg=CARD_BG,
            padx=16,
            pady=12,
            highlightbackground=BORDER_COLOR,
            highlightthickness=2,
        )
        shell.grid(row=0, column=0, sticky="nsew")
        shell.grid_columnconfigure(0, weight=1)
        shell.grid_rowconfigure(2, weight=1)

        # Visible background board layer in open spaces.
        self.visible_board_background = tk.Canvas(shell, bg=CARD_BG, highlightthickness=0, bd=0)
        self.visible_board_background.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.visible_board_background.tk.call("lower", self.visible_board_background._w)
        self.visible_board_background.bind("<Configure>", lambda _event: self._draw_visible_board_background())

        # Header / hero area
        hero = tk.Frame(shell, bg=CARD_BG)
        hero.grid(row=0, column=0, sticky="ew")
        hero.grid_columnconfigure(0, weight=1)

        title_stack = tk.Frame(hero, bg=CARD_BG)
        title_stack.grid(row=0, column=0, sticky="nw")

        tk.Label(
            title_stack,
            text="♛  CHESS STUDIO",
            font=ui_font(32, "bold"),
            bg=CARD_BG,
            fg=TEXT_PRIMARY,
        ).pack(anchor="w")
        tk.Label(
            title_stack,
            text="COMPETE. STRATEGIZE. CONQUER.",
            font=ui_font(11, "bold"),
            bg=CARD_BG,
            fg=NEON_GOLD,
        ).pack(anchor="w", pady=(2, 0))
        tk.Label(
            title_stack,
            text="Set up a tournament-style chess match with bold colors, readable pieces, clear borders, and sound.",
            font=ui_font(10),
            bg=CARD_BG,
            fg=TEXT_MUTED,
            wraplength=720,
            justify="left",
        ).pack(anchor="w", pady=(8, 0))

        hero_right = tk.Frame(hero, bg=CARD_BG)
        hero_right.grid(row=0, column=1, sticky="ne")
        self.preview_canvas = tk.Canvas(
            hero_right,
            width=250,
            height=92,
            bg=CARD_BG,
            highlightthickness=0,
            bd=0,
        )
        self.preview_canvas.pack(side="left", padx=(0, 16))
        self._draw_tournament_preview()

        ColorButton(
            hero_right,
            textvariable=self.hero_badge_var,
            command=self.app.start_new_game,
            bg="#3A220A",
            fg=TEXT_PRIMARY,
            activebackground=NEON_ORANGE,
            activeforeground="#FFFFFF",
            font=ui_font(10, "bold"),
            padx=22,
            pady=14,
            highlightbackground=NEON_ORANGE,
            highlightthickness=1,
        ).pack(side="left", anchor="ne")

        # Animated shine line under title.
        self.shine_canvas = tk.Canvas(shell, height=14, bg=CARD_BG, highlightthickness=0, bd=0)
        self.shine_canvas.grid(row=1, column=0, sticky="ew", pady=(4, 8))
        self.shine_canvas.bind("<Configure>", lambda _event: self._draw_shine_line())

        # Score/rank/recent panels
        overview = tk.Frame(shell, bg=CARD_BG)
        overview.grid(row=2, column=0, sticky="nsew")
        overview.grid_columnconfigure(0, weight=3)
        overview.grid_columnconfigure(1, weight=3)
        overview.grid_columnconfigure(2, weight=5)
        overview.grid_rowconfigure(1, weight=1)

        scoreboard_panel = self._make_neon_panel(overview, title="🏆  SCOREBOARD", accent=NEON_GOLD)
        scoreboard_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 10))
        tk.Label(
            scoreboard_panel,
            textvariable=self.scoreboard_var,
            font=ui_font(10),
            bg=PANEL_DEEP_BG,
            fg=TEXT_MUTED,
            justify="left",
            anchor="w",
        ).pack(anchor="w", pady=(8, 0))

        rank_panel = self._make_neon_panel(overview, title="⭐  RANK PROGRESS", accent=NEON_GOLD)
        rank_panel.grid(row=0, column=1, sticky="nsew", padx=8, pady=(0, 10))
        tk.Label(
            rank_panel,
            textvariable=self.rank_var,
            font=ui_font(10, "bold"),
            bg=PANEL_DEEP_BG,
            fg=TEXT_PRIMARY,
            justify="left",
            anchor="w",
        ).pack(anchor="w", pady=(8, 0))
        self.rank_progress = tk.Canvas(rank_panel, height=10, bg=PANEL_DEEP_BG, highlightthickness=0)
        self.rank_progress.pack(fill="x", pady=(8, 0))

        recent_matches_panel = self._make_neon_panel(overview, title="◷  RECENT MATCHES", accent=NEON_ORANGE)
        recent_matches_panel.grid(row=0, column=2, sticky="nsew", padx=(8, 0), pady=(0, 10))
        tk.Label(
            recent_matches_panel,
            textvariable=self.recent_matches_var,
            font=ui_font(9, mono=True),
            bg=PANEL_DEEP_BG,
            fg=TEXT_MUTED,
            justify="left",
            anchor="w",
        ).pack(anchor="w", pady=(8, 0))
        ColorButton(
            recent_matches_panel,
            text="VIEW ALL MATCH HISTORY  ❯",
            command=lambda: self.app.open_result_screen("Recent match history preview."),
            bg="#5A2B08",
            fg=NEON_GOLD,
            activebackground="#8A3E0A",
            activeforeground="#FFFFFF",
            font=ui_font(8, "bold"),
            padx=12,
            pady=5,
        ).pack(anchor="e", pady=(8, 0))

        # Middle body: setup, center trophy, appearance studio.
        body = tk.Frame(overview, bg=CARD_BG)
        body.grid(row=1, column=0, columnspan=3, sticky="nsew")
        body.grid_columnconfigure(0, weight=4)
        body.grid_columnconfigure(1, weight=1)
        body.grid_columnconfigure(2, weight=5)
        body.grid_rowconfigure(0, weight=1)

        setup_card = self._make_neon_panel(body, title="⚔  MATCH SETUP", accent=NEON_GOLD)
        setup_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self.mode_status_label = tk.Label(
            setup_card,
            text="Current mode: Local Two-Player",
            font=ui_font(10),
            bg=PANEL_DEEP_BG,
            fg=NEON_GOLD,
        )
        self.mode_status_label.pack(anchor="w", pady=(0, 12))

        setup_grid = tk.Frame(setup_card, bg=PANEL_DEEP_BG)
        setup_grid.pack(fill="x")
        setup_grid.grid_columnconfigure(0, minsize=88)
        setup_grid.grid_columnconfigure(1, weight=1)

        self._setup_label(setup_grid, "MODE", 0)
        mode_buttons = tk.Frame(setup_grid, bg=PANEL_DEEP_BG)
        mode_buttons.grid(row=0, column=1, sticky="w", pady=(0, 12))
        for mode_name, label in (
            ("local", "LOCAL TWO-PLAYER"),
            ("ai", "VS COMPUTER"),
            ("ai_vs_ai", "AI VS AI"),
        ):
            button = self._mode_button(mode_buttons, label, lambda selected=mode_name: self.app.set_mode(selected))
            button.pack(side="left", padx=(0, 8))
            self.mode_buttons[mode_name] = button

        self._setup_label(setup_grid, "DIFFICULTY", 1)
        difficulty_row = tk.Frame(setup_grid, bg=PANEL_DEEP_BG)
        difficulty_row.grid(row=1, column=1, sticky="w", pady=(0, 12))
        for difficulty, label in AI_DIFFICULTY_LABELS.items():
            button = self._mode_button(difficulty_row, label.upper(), lambda selected=difficulty: self.app.set_ai_difficulty(selected), compact=True)
            button.pack(side="left", padx=(0, 8))
            self.difficulty_buttons[difficulty] = button

        self._setup_label(setup_grid, "YOUR SIDE", 2)
        side_row = tk.Frame(setup_grid, bg=PANEL_DEEP_BG)
        side_row.grid(row=2, column=1, sticky="w", pady=(0, 12))
        for color, label in (("white", "WHITE / 1ST"), ("black", "BLACK / 2ND")):
            button = self._mode_button(side_row, label, lambda selected=color: self.app.set_ai_player_color(selected), compact=True)
            button.pack(side="left", padx=(0, 8))
            self.side_buttons[color] = button

        self._setup_label(setup_grid, "SOUND", 3, pady=(0, 0))
        sound_row = tk.Frame(setup_grid, bg=PANEL_DEEP_BG)
        sound_row.grid(row=3, column=1, sticky="w")
        self.sound_button = self._mode_button(sound_row, "SOUND OFF", self._toggle_sound, compact=True)
        self.sound_button.pack(side="left", padx=(0, 8))

        tk.Label(
            setup_card,
            text="Choose your mode, tune the AI difficulty, and decide whether you play first as white or second as black.",
            font=ui_font(10),
            bg=PANEL_DEEP_BG,
            fg=TEXT_MUTED,
            wraplength=390,
            justify="left",
        ).pack(anchor="w", pady=(18, 0))

        center_stage = tk.Frame(body, bg=CARD_BG)
        center_stage.grid(row=0, column=1, sticky="nsew", padx=4)
        center_stage.grid_rowconfigure(0, weight=1)
        center_stage.grid_columnconfigure(0, weight=1)
        self.trophy_canvas = tk.Canvas(center_stage, width=135, height=330, bg=CARD_BG, highlightthickness=0, bd=0)
        self.trophy_canvas.grid(row=0, column=0, sticky="nsew")
        self.trophy_canvas.bind("<Configure>", lambda _event: self._draw_center_king())

        appearance_card = self._make_neon_panel(body, title="✦  APPEARANCE STUDIO", accent=NEON_ORANGE)
        appearance_card.grid(row=0, column=2, sticky="nsew", padx=(8, 0))

        live_label = tk.Label(
            appearance_card,
            text="●  LIVE PREVIEW",
            font=ui_font(8, "bold"),
            bg="#4A2108",
            fg=NEON_ORANGE,
            padx=12,
            pady=5,
        )
        live_label.pack(anchor="ne")

        status_row = tk.Frame(appearance_card, bg=PANEL_DEEP_BG)
        status_row.pack(fill="x", pady=(4, 8))
        self.theme_status_label = tk.Label(
            status_row,
            text="PIECE COLOR: CLASSIC",
            font=ui_font(8, "bold"),
            bg="#2A1706",
            fg=TEXT_PRIMARY,
            padx=12,
            pady=6,
            highlightbackground=NEON_ORANGE,
            highlightthickness=1,
        )
        self.theme_status_label.pack(side="left")
        self.board_theme_status_label = tk.Label(
            status_row,
            text="BOARD: CLASSIC",
            font=ui_font(8, "bold"),
            bg="#2A1706",
            fg=TEXT_PRIMARY,
            padx=12,
            pady=6,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
        )
        self.board_theme_status_label.pack(side="left", padx=(10, 0))

        tab_row = tk.Frame(appearance_card, bg=PANEL_DEEP_BG)
        tab_row.pack(fill="x")
        for tab_name, label in (("pieces", "PIECE COLORS"), ("board", "BOARD COLORS")):
            button = self._mode_button(tab_row, label, lambda selected=tab_name: self._set_appearance_tab(selected), compact=True)
            button.pack(side="left", padx=(0, 8))
            self.appearance_tab_buttons[tab_name] = button

        tk.Label(
            appearance_card,
            textvariable=self.appearance_hint_var,
            font=ui_font(9),
            bg=PANEL_DEEP_BG,
            fg=TEXT_MUTED,
            wraplength=510,
            justify="left",
        ).pack(anchor="w", pady=(8, 8))

        appearance_stage = tk.Frame(appearance_card, bg=PANEL_DEEP_BG, width=520, height=245)
        appearance_stage.pack(fill="both", expand=True)
        appearance_stage.pack_propagate(False)
        appearance_stage.grid_rowconfigure(0, weight=1)
        appearance_stage.grid_columnconfigure(0, weight=1)

        self.piece_theme_panel = tk.Frame(appearance_stage, bg=PANEL_DEEP_BG)
        self.piece_theme_panel.grid(row=0, column=0, sticky="nsew")
        for column in range(4):
            self.piece_theme_panel.grid_columnconfigure(column, weight=1)
        for row in range(2):
            self.piece_theme_panel.grid_rowconfigure(row, weight=1, uniform="appearance_rows")
        for index, (theme_name, theme_data) in enumerate(THEME_PRESETS.items()):
            preview_image = self.theme_preview_images.get(theme_name, "")
            button = ColorButton(
                self.piece_theme_panel,
                text=theme_data["label"].upper(),
                image=preview_image,
                compound="top" if preview_image else "none",
                command=lambda selected=theme_name: self.app.set_piece_theme(selected),
                padx=5,
                pady=5,
                cursor="hand2",
                wraplength=120,
                justify="center",
                font=ui_font(8, "bold"),
                bg=THEME_CARD_BG,
                fg=TEXT_PRIMARY,
                activebackground="#1A2A42",
                activeforeground=TEXT_PRIMARY,
                highlightbackground=BORDER_COLOR,
                highlightthickness=1,
            )
            button.grid(row=index // 4, column=index % 4, padx=5, pady=5, sticky="nsew")
            self.theme_buttons[theme_name] = button

        self.board_theme_panel = tk.Frame(appearance_stage, bg=PANEL_DEEP_BG)
        self.board_theme_panel.grid(row=0, column=0, sticky="nsew")
        for column in range(3):
            self.board_theme_panel.grid_columnconfigure(column, weight=1)
        board_rows = max(1, (len(BOARD_THEME_PRESETS) + 2) // 3)
        for row in range(board_rows):
            self.board_theme_panel.grid_rowconfigure(row, weight=1, uniform="board_rows")
        for index, (theme_name, theme_data) in enumerate(BOARD_THEME_PRESETS.items()):
            preview_image = self.board_preview_images.get(theme_name, "")
            button = ColorButton(
                self.board_theme_panel,
                text=theme_data["label"].upper(),
                image=preview_image,
                compound="top" if preview_image else "none",
                command=lambda selected=theme_name: self.app.set_board_theme(selected),
                padx=5,
                pady=0,
                cursor="hand2",
                wraplength=120,
                justify="center",
                font=ui_font(8, "bold"),
                bg=THEME_CARD_BG,
                fg=TEXT_PRIMARY,
                activebackground="#1A2A42",
                activeforeground=TEXT_PRIMARY,
                highlightbackground=BORDER_COLOR,
                highlightthickness=1,
            )
            button.grid(row=index // 3, column=index % 3, padx=4, pady=4, sticky="nsew")
            self.board_theme_buttons[theme_name] = button

        # Bottom action bar
        controls = tk.Frame(shell, bg=CARD_BG)
        controls.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        for column in range(3):
            controls.grid_columnconfigure(column, weight=1)

        self.start_button = ColorButton(
            controls,
            text="⚡  START MATCH",
            command=self.app.start_new_game,
            bg="#7A4A12",
            fg="#FFFFFF",
            activebackground=NEON_BLUE,
            activeforeground="#FFFFFF",
            font=ui_font(11, "bold"),
            padx=14,
            pady=11,
            highlightbackground=NEON_BLUE,
            highlightthickness=1,
        )
        self.start_button.grid(row=0, column=0, sticky="ew")

        self.load_button = ColorButton(
            controls,
            text="▰  LOAD SAVED MATCH",
            command=self._load_saved_match,
            bg="#141C28",
            fg=TEXT_MUTED,
            activebackground="#253349",
            activeforeground="#FFFFFF",
            font=ui_font(11, "bold"),
            padx=14,
            pady=11,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
        )
        self.load_button.grid(row=0, column=1, sticky="ew", padx=8)

        ColorButton(
            controls,
            text="◉  RESULT SCREEN PREVIEW",
            command=lambda: self.app.open_result_screen("Result screen scaffold ready for future checkmate flow."),
            bg="#141C28",
            fg=TEXT_MUTED,
            activebackground="#253349",
            activeforeground="#FFFFFF",
            font=ui_font(11, "bold"),
            padx=14,
            pady=11,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
        ).grid(row=0, column=2, sticky="ew")

        ColorButton(
            controls,
            text="↻  RESET SAVES & RANK",
            command=self._confirm_reset_saved_data,
            bg="#3A0707",
            fg="#FFD2D2",
            activebackground=NEON_RED,
            activeforeground="#FFFFFF",
            font=ui_font(10, "bold"),
            padx=14,
            pady=10,
            highlightbackground=NEON_RED,
            highlightthickness=1,
        ).grid(row=1, column=0, columnspan=3, sticky="ew", pady=(8, 0))

        self._create_visible_sparkles(shell)
        self._set_appearance_tab("pieces")
        self._draw_center_king()
        self._animate_shine()

    def _draw_visible_board_background(self) -> None:
        """Draw a brighter animated star/glitter background for the welcome screen."""
        if not hasattr(self, "visible_board_background"):
            return

        c = self.visible_board_background
        c.delete("all")

        width = max(c.winfo_width(), 900)
        height = max(c.winfo_height(), 640)
        step = getattr(self, "_shine_step", 0)

        # Deep dark background.
        c.create_rectangle(0, 0, width, height, fill="#02050C", outline="")

        # Large soft gold glows.
        c.create_oval(
            -300,
            -260,
            520,
            420,
            fill="#120B03",
            outline="#5A3A0A",
            width=2,
        )
        c.create_oval(
            width - 520,
            height - 480,
            width + 300,
            height + 260,
            fill="#0B1018",
            outline="#5A3A0A",
            width=2,
        )
        c.create_oval(
            width // 2 - 360,
            height // 2 - 300,
            width // 2 + 360,
            height // 2 + 300,
            outline="#2A1B07",
            width=2,
        )

        # Moving diagonal gold/blue light streaks.
        diagonal_shift = (step * 18) % 280
        for i in range(-5, 10):
            x0 = i * 260 + diagonal_shift - 390
            c.create_line(
                x0,
                height + 90,
                x0 + 500,
                -90,
                fill="#24364A",
                width=1,
            )
            c.create_line(
                x0 + 28,
                height + 90,
                x0 + 528,
                -90,
                fill="#7A4A12",
                width=1,
            )

        # Floating gold particles and stars.
        for i in range(95):
            speed = 1 + (i % 5)
            x = int((i * 113 + step * speed * 8) % width)
            y = int((i * 71 + step * (speed + 3)) % height)

            twinkle = (step + i * 7) % 24
            radius = 1 if twinkle < 10 else 2
            color = "#FFF0B8" if twinkle < 8 else "#F5C46B"

            c.create_oval(
                x - radius,
                y - radius,
                x + radius,
                y + radius,
                fill=color,
                outline="",
            )

            if i % 5 == 0:
                shine = 5 if twinkle < 10 else 3
                c.create_line(x - shine, y, x + shine, y, fill="#FFD978", width=1)
                c.create_line(x, y - shine, x, y + shine, fill="#FFD978", width=1)

        # Subtle chess silhouettes.
        symbols = ("♔", "♕", "♖", "♗", "♘", "♙")
        for i, symbol in enumerate(symbols * 3):
            x = int((i * 257 + step * (5 + i % 3)) % width)
            y = int((i * 173 + step * (3 + i % 2)) % height)
            c.create_text(
                x,
                y,
                text=symbol,
                fill="#07101A" if i % 2 else "#0A0804",
                font=ui_font(30 + (i % 3) * 6, "bold"),
            )

        # Soft readability overlay; not too strong so glitter still shows.
        c.create_rectangle(0, 0, width, height, fill="#000000", stipple="gray25", outline="")

        # Animated gold border shine.
        shine_x = (step * 30) % max(width, 1)
        shine_y = (step * 22) % max(height, 1)

        c.create_line(0, 2, width, 2, fill="#5A3A0A", width=2)
        c.create_line(0, height - 3, width, height - 3, fill="#5A3A0A", width=2)
        c.create_line(2, 0, 2, height, fill="#5A3A0A", width=2)
        c.create_line(width - 3, 0, width - 3, height, fill="#5A3A0A", width=2)

        c.create_line(shine_x - 120, 2, shine_x + 120, 2, fill="#FFE8A3", width=3)
        c.create_line(width - 3, shine_y - 120, width - 3, shine_y + 120, fill="#FFE8A3", width=3)


    def _make_neon_panel(self, parent: tk.Widget, *, title: str, accent: str) -> tk.Frame:
        """Create a dark glass panel with a colored tournament border."""
        panel = tk.Frame(
            parent,
            bg=PANEL_DEEP_BG,
            padx=16,
            pady=12,
            highlightbackground=accent,
            highlightthickness=1,
        )
        tk.Label(
            panel,
            text=title,
            font=ui_font(13, "bold"),
            bg=PANEL_DEEP_BG,
            fg=TEXT_PRIMARY,
        ).pack(anchor="w")
        return panel

    def _setup_label(self, parent: tk.Widget, text: str, row: int, pady: tuple[int, int] = (0, 12)) -> None:
        tk.Label(
            parent,
            text=text,
            font=ui_font(10, "bold"),
            bg=PANEL_DEEP_BG,
            fg=TEXT_PRIMARY,
        ).grid(row=row, column=0, sticky="w", pady=pady)

    def _mode_button(self, parent: tk.Widget, text: str, command, compact: bool = False) -> ColorButton:
        return ColorButton(
            parent,
            text=text,
            command=command,
            padx=12 if compact else 16,
            pady=8 if compact else 10,
            cursor="hand2",
            font=ui_font(9 if compact else 10, "bold"),
            bg=MODE_CARD_BG,
            fg=TEXT_PRIMARY,
            activebackground="#7A4A12",
            activeforeground=TEXT_PRIMARY,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
        )

    def _draw_tournament_preview(self) -> None:
        """Draw a clean, simple preview card without overlapping artwork."""
        c = self.preview_canvas
        c.delete("all")
        width = max(c.winfo_width(), 250)
        height = max(c.winfo_height(), 92)

        c.create_rectangle(8, 8, width - 8, height - 8, outline=BORDER_COLOR, width=1, fill="#050911")
        c.create_text(18, 21, text="TOURNAMENT PREVIEW", fill=NEON_GOLD, anchor="w", font=ui_font(8, "bold"))

        board_left = 38
        board_top = 36
        square = 12
        for row in range(3):
            for col in range(5):
                fill = "#F4F1E8" if (row + col) % 2 == 0 else "#141414"
                c.create_rectangle(board_left + col * square, board_top + row * square,
                                   board_left + (col + 1) * square, board_top + (row + 1) * square,
                                   fill=fill, outline="#2A2A2A")

        # Keep WHITE / VS / BLACK readable at different window widths.
        matchup_font = ui_font(10, "bold")
        tmp_white = c.create_text(0, 0, text="WHITE", font=matchup_font, anchor="w")
        tmp_vs = c.create_text(0, 0, text="VS", font=matchup_font, anchor="w")
        tmp_black = c.create_text(0, 0, text="BLACK", font=matchup_font, anchor="w")
        bbox_white = c.bbox(tmp_white)
        bbox_vs = c.bbox(tmp_vs)
        bbox_black = c.bbox(tmp_black)
        c.delete(tmp_white)
        c.delete(tmp_vs)
        c.delete(tmp_black)

        white_w = (bbox_white[2] - bbox_white[0]) if bbox_white else 44
        vs_w = (bbox_vs[2] - bbox_vs[0]) if bbox_vs else 16
        black_w = (bbox_black[2] - bbox_black[0]) if bbox_black else 48
        min_gap = 6
        preferred_gap = 10
        total_text_w = white_w + vs_w + black_w
        left_bound = board_left + (square * 5) + 18
        right_bound = width - 22
        available = max(0, right_bound - left_bound)
        if available >= total_text_w + (preferred_gap * 2):
            gap = preferred_gap
        elif available >= total_text_w + (min_gap * 2):
            gap = min_gap
        else:
            gap = max(3, (available - total_text_w) // 2)

        block_w = total_text_w + (gap * 2)
        start_x = max(left_bound, right_bound - block_w)
        y = 52
        c.create_text(start_x, y, text="WHITE", fill="#F4E8D2", font=matchup_font, anchor="w")
        c.create_text(start_x + white_w + gap, y, text="VS", fill=NEON_GOLD, font=matchup_font, anchor="w")
        c.create_text(start_x + white_w + gap + vs_w + gap, y, text="BLACK", fill="#C48A47", font=matchup_font, anchor="w")
        c.create_line(18, height - 16, width - 18, height - 16, fill="#503A18", width=2)

    def _draw_center_king(self) -> None:
        """Draw one left-shifted gold king centerpiece with a brighter gold shine."""
        c = self.trophy_canvas
        c.delete("all")

        w = max(c.winfo_width(), 180)
        h = max(c.winfo_height(), 300)

        # Move the full king area a little to the left.
        king_x = (w // 2) - 20
        king_y = int(h * 0.42)

        # Move the shine platform up so the text has room.
        platform_y = h - 96
        pulse = getattr(self, "_shine_step", 0) % 20
        glow_width = 2 + (pulse // 8)

        c.create_oval(
            king_x - 88,
            platform_y - 12,
            king_x + 88,
            platform_y + 38,
            outline="#3A2A0D",
            width=2,
        )
        c.create_oval(
            king_x - 72,
            platform_y - 4,
            king_x + 72,
            platform_y + 28,
            outline=NEON_GOLD,
            width=glow_width,
        )
        c.create_oval(
            king_x - 54,
            platform_y + 3,
            king_x + 54,
            platform_y + 21,
            outline="#FFD978",
            width=2,
        )

        sparkle_color = "#FFE8A3"
        for x, y, size in (
            (king_x - 62, int(h * 0.21), 4),
            (king_x + 62, int(h * 0.24), 3),
            (king_x - 48, int(h * 0.59), 3),
            (king_x + 50, int(h * 0.56), 4),
        ):
            c.create_line(x - size, y, x + size, y, fill=sparkle_color, width=2)
            c.create_line(x, y - size, x, y + size, fill=sparkle_color, width=2)

        if PIL_AVAILABLE:
            for candidate in (
                CLASSIC_3D_DIR / "king.png",
                ASSET_PIECE_DIR / "king white.png",
                ASSET_PIECE_DIR / "king_white.png",
                ASSET_PIECE_DIR / "white_king.png",
                ASSET_PIECE_DIR / "king black.png",
                ASSET_PIECE_DIR / "king_black.png",
                ASSET_PIECE_DIR / "black_king.png",
            ):
                if candidate.exists():
                    try:
                        resampling = getattr(Image, "Resampling", Image)
                        image = Image.open(candidate).convert("RGBA")
                        alpha = image.getchannel("A")
                        bbox = alpha.point(lambda a: 255 if a >= VISIBLE_ALPHA_THRESHOLD else 0).getbbox() or alpha.getbbox()
                        if bbox is not None:
                            image = image.crop(bbox)

                        # Tint the center king gold.
                        image = _tint_piece_image(image, "#A86D16", "#FFD96A")

                        image.thumbnail((max(120, int(w * 0.78)), max(230, int(h * 0.66))), resampling.LANCZOS)

                        self.trophy_king_image = ImageTk.PhotoImage(image)
                        c.create_image(king_x, king_y, image=self.trophy_king_image, anchor="center")
                        c.create_text(
                            king_x,
                            h - 48,
                            text="KING OF THE BOARD",
                            fill="#F5C46B",
                            font=ui_font(8, "bold"),
                        )
                        return
                    except Exception:
                        self.trophy_king_image = None

        # Fallback symbol king, also left-shifted and gold.
        c.create_text(king_x + 5, king_y + 7, text="♔", fill="#5A3808", font=ui_font(138, "bold"))
        c.create_text(king_x, king_y, text="♔", fill="#FFD96A", font=ui_font(138, "bold"))
        c.create_text(king_x - 3, king_y - 5, text="♔", fill="#FFF0A8", font=ui_font(124, "bold"))
        c.create_text(
            king_x,
            h - 48,
            text="KING OF THE BOARD",
            fill="#F5C46B",
            font=ui_font(8, "bold"),
        )


    def _draw_shine_line(self) -> None:
        """Draw an animated gold shine below the title."""
        c = self.shine_canvas
        c.delete("all")
        width = max(c.winfo_width(), 600)
        y = 7
        c.create_line(0, y, width, y, fill="#2A1B07", width=2)
        c.create_line(0, y, width, y, fill="#8A6426", width=2)
        shine_x = (self._shine_step * 18) % max(width, 1)
        c.create_line(shine_x - 52, y, shine_x + 52, y, fill="#FFF4D6", width=3)

    def _create_visible_sparkles(self, parent: tk.Widget) -> None:
        """Create many tiny visible glitter dots above the welcome screen panels."""
        if self.sparkle_labels:
            return

        # Tiny glitter only. No big star symbols.
        for _ in range(42):
            label = tk.Label(
                parent,
                text="•",
                bg=CARD_BG,
                fg="#F5C46B",
                font=ui_font(8, "bold"),
                bd=0,
                padx=0,
                pady=0,
            )
            label.place(x=-100, y=-100)
            self.sparkle_labels.append(label)

    def _animate_visible_sparkles(self) -> None:
        """Move many tiny glitter dots on top of the welcome screen."""
        if not self.sparkle_labels:
            return

        step = getattr(self, "_shine_step", 0)
        parent = self.sparkle_labels[0].master
        width = max(parent.winfo_width(), 900)
        height = max(parent.winfo_height(), 640)
        safe_height = max(360, height - 80)

        colors = ("#FFF0B8", "#F5C46B", "#D99A32", "#FFE8A3")

        for i, label in enumerate(self.sparkle_labels):
            # More glitter, but very small.
            x = int((20 + i * 73 + step * (2 + i % 5)) % max(width - 30, 1))
            y = int((50 + i * 47 + step * (1 + i % 4)) % max(safe_height - 30, 1))

            twinkle = (step + i * 3) % 30
            font_size = 5 if twinkle < 12 else 6

            label.configure(
                text="•",
                fg=colors[(twinkle // 8) % len(colors)],
                font=ui_font(font_size, "bold"),
            )
            label.place(x=x, y=y)

            try:
                label.lift()
            except tk.TclError:
                pass



    def _animate_welcome_widgets(self) -> None:
        """Make the welcome screen visibly animated even when panels cover the background."""
        step = getattr(self, "_shine_step", 0)

        # Pulsing gold/blue border colors.
        border_cycle = (
            "#1A4A78",
            "#2B6FA3",
            "#D99A32",
            "#F5C46B",
            "#D99A32",
            "#2B6FA3",
        )
        border_color = border_cycle[(step // 3) % len(border_cycle)]

        # Small glow colors for active UI accents.
        gold_glow = "#F5C46B" if (step // 4) % 2 == 0 else "#D99A32"
        dark_gold = "#4A2507" if (step // 6) % 2 == 0 else "#5A2B08"

        def walk(widget: tk.Widget) -> None:
            for child in widget.winfo_children():
                try:
                    thickness = int(child.cget("highlightthickness"))
                    if thickness > 0:
                        child.configure(highlightbackground=border_color)
                except Exception:
                    pass

                # Keep buttons alive with a soft pulse.
                if isinstance(child, ColorButton):
                    try:
                        current_text = str(child.cget("text"))
                        if "START MATCH" in current_text:
                            child.configure(bg=gold_glow)
                        elif "LIVE PREVIEW" in current_text:
                            child.configure(bg=dark_gold)
                    except Exception:
                        pass

                walk(child)

        walk(self)

        # Status labels pulse gently.
        if hasattr(self, "theme_status_label"):
            self.theme_status_label.configure(highlightbackground=gold_glow)
        if hasattr(self, "board_theme_status_label"):
            self.board_theme_status_label.configure(highlightbackground=border_color)

    def _animate_shine(self) -> None:
        """Animate the welcome screen background, glitter, borders, center king, and buttons."""
        self._shine_step = (self._shine_step + 1) % 10000

        self._draw_shine_line()

        if hasattr(self, "visible_board_background"):
            self._draw_visible_board_background()

        if hasattr(self, "trophy_canvas"):
            self._draw_center_king()

        self._animate_welcome_widgets()
        self._animate_visible_sparkles()

        # Faster refresh so movement is visible.
        self._shine_job = self.after(80, self._animate_shine)


    def _set_appearance_tab(self, tab_name: str) -> None:
        """Swap between piece and board appearance selectors."""
        if tab_name not in {"pieces", "board"}:
            return

        self.appearance_tab = tab_name

        if tab_name == "pieces":
            self.appearance_hint_var.set(
                "Choose a piece color. Black & White is first; all choices use the same photo chess shapes."
            )
            self.piece_theme_panel.tkraise()
        else:
            self.appearance_hint_var.set(
                "Pick the light and dark board palette used during the match."
            )
            self.board_theme_panel.tkraise()

        for name, button in self.appearance_tab_buttons.items():
            is_active = name == tab_name
            button.config(
                bg=NEON_ORANGE if is_active else MODE_CARD_BG,
                fg="#FFFFFF" if is_active else TEXT_PRIMARY,
                activebackground=NEON_ORANGE if is_active else "#18304A",
            )

    def _toggle_sound(self) -> None:
        """Toggle optional sound effects without playing audio on the setup screen."""
        self.app.toggle_sound_enabled()

    def refresh(self) -> None:
        """Refresh button states, selected themes, scoreboard, and rank text."""
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
        self.theme_status_label.config(text=f"PIECE COLOR: {THEME_PRESETS[current_theme]['label'].upper()}")
        self.board_theme_status_label.config(text=f"BOARD: {BOARD_THEME_PRESETS[current_board_theme]['label'].upper()}")
        saved_match_available = has_saved_match()
        self.hero_badge_var.set("SAVED MATCH READY" if saved_match_available else "FRESH START")
        self.load_button.config(state="normal" if saved_match_available else "disabled")
        self.scoreboard_var.set(format_scoreboard_summary(self.app.scoreboard))
        self.rank_var.set(format_rank_summary(self.app.scoreboard))
        self.recent_matches_var.set(format_recent_match_snapshot(self.app.scoreboard))
        self._draw_rank_progress()

        for mode_name, button in self.mode_buttons.items():
            is_active = mode_name == current_mode
            button.config(
                bg=MODE_CARD_ACTIVE_BG if is_active else MODE_CARD_BG,
                fg="#FFFFFF" if is_active else TEXT_PRIMARY,
                activebackground=NEON_GOLD if is_active else "#1A1308",
                state="normal",
            )

        difficulty_state = "normal" if current_mode in {"ai", "ai_vs_ai"} else "disabled"
        for difficulty, button in self.difficulty_buttons.items():
            is_active = difficulty == current_difficulty and current_mode in {"ai", "ai_vs_ai"}
            button.config(
                bg=MODE_CARD_ACTIVE_BG if is_active else MODE_CARD_BG,
                fg="#FFFFFF" if is_active else TEXT_PRIMARY,
                activebackground=NEON_GOLD if is_active else "#1A1308",
                state=difficulty_state,
            )

        side_state = "normal" if current_mode == "ai" else "disabled"
        for color, button in self.side_buttons.items():
            is_active = color == current_side and current_mode == "ai"
            button.config(
                bg=MODE_CARD_ACTIVE_BG if is_active else MODE_CARD_BG,
                fg="#FFFFFF" if is_active else TEXT_PRIMARY,
                activebackground=NEON_GOLD if is_active else "#1A1308",
                state=side_state,
            )

        if self.sound_button is not None:
            sound_active = self.app.state.sound_enabled
            self.sound_button.config(
                text="SOUND ON" if sound_active else "SOUND OFF",
                bg=MODE_CARD_ACTIVE_BG if sound_active else MODE_CARD_BG,
                fg="#FFFFFF" if sound_active else TEXT_PRIMARY,
                activebackground=NEON_GOLD if sound_active else "#1A1308",
                state="normal",
            )

        for theme_name, button in self.theme_buttons.items():
            is_active = theme_name == current_theme
            button.config(
                bg="#4B2507" if is_active else THEME_CARD_BG,
                fg="#FFFFFF" if is_active else TEXT_PRIMARY,
                activebackground=NEON_ORANGE if is_active else "#1A2A42",
                activeforeground="#FFFFFF" if is_active else TEXT_PRIMARY,
                highlightbackground=NEON_ORANGE if is_active else BORDER_COLOR,
            )

        for theme_name, button in self.board_theme_buttons.items():
            is_active = theme_name == current_board_theme
            button.config(
                bg="#4B2507" if is_active else THEME_CARD_BG,
                fg="#FFFFFF" if is_active else TEXT_PRIMARY,
                activebackground=NEON_ORANGE if is_active else "#1A2A42",
                activeforeground="#FFFFFF" if is_active else TEXT_PRIMARY,
                highlightbackground=NEON_ORANGE if is_active else BORDER_COLOR,
            )

        self._set_appearance_tab(self.appearance_tab)
        if hasattr(self, "visible_board_background"):
            self._draw_visible_board_background()
        return None

    def _draw_rank_progress(self) -> None:
        """Draw a compact blue/orange progress bar for the current rank."""
        if not hasattr(self, "rank_progress"):
            return
        c = self.rank_progress
        c.delete("all")
        width = max(c.winfo_width(), 100)
        points = self.app.scoreboard.ranking_points
        current_rank, next_rank, current_floor, next_floor = rank_window(points)
        if next_floor is None:
            ratio = 1.0
        else:
            ratio = max(0.0, min(1.0, (points - current_floor) / max(1, next_floor - current_floor)))
        c.create_rectangle(0, 2, width, 8, fill="#0A1422", outline=BORDER_COLOR)
        c.create_rectangle(0, 2, int(width * ratio), 8, fill=NEON_GOLD, outline="")
        c.create_line(int(width * ratio), 1, int(width * ratio), 9, fill=NEON_GOLD)

    def _load_saved_match(self) -> None:
        """Load the latest saved match from the welcome screen."""
        success, message = self.app.load_match()
        if not success:
            self.app.state.screen_message = message
            self.app.state.match.status_message = message
            self.refresh()

    def _confirm_reset_saved_data(self) -> None:
        """Confirm and clear saved match/ranking data from the welcome screen."""
        confirmed = messagebox.askyesno(
            "Reset saved data?",
            "Reset saved matches, recent match history, and ranking progress?",
            parent=self,
        )
        if not confirmed:
            return

        self.app.reset_saved_matches_and_ranking()


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
        self.icon_size = clamp_int(int(DEFAULT_SQUARE_SIZE * 0.90), 32, 78)
        self.piece_font_size = clamp_int(int(DEFAULT_SQUARE_SIZE * 0.40), 16, 28)
        self.coord_font_size = clamp_int(int(DEFAULT_SQUARE_SIZE * 0.18), 8, 13)
        self.loaded_theme = normalize_theme_name(self.app.state.piece_theme)
        self.piece_images = load_piece_images(self.loaded_theme, self.square_size, self.icon_size)
        self.empty_square_image = make_empty_square_image(self.square_size)
        self.history_var = tk.StringVar(value="No moves yet.")
        self.white_captures_var = tk.StringVar(value="None")
        self.black_captures_var = tk.StringVar(value="None")
        self.white_capture_count_var = tk.StringVar(value="0 captured")
        self.black_capture_count_var = tk.StringVar(value="0 captured")
        self.white_time_var = tk.StringVar(value="5:00")
        self.black_time_var = tk.StringVar(value="5:00")
        self.meta_var = tk.StringVar(value="")
        self.history_text: tk.Text | None = None
        self.timer_after_id: str | None = None

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
        info_column.grid_rowconfigure(1, weight=1)

        captures_panel = make_surface(info_column, bg=CARD_BG, padx=16, pady=12)
        captures_panel.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        tk.Label(
            captures_panel,
            text="Captured Pieces",
            font=ui_font(13, "bold"),
            bg=CARD_BG,
            fg=TEXT_PRIMARY,
        ).pack(anchor="w")

        # Timer panel
        timer_panel = tk.Frame(captures_panel, bg=CARD_BG)
        timer_panel.pack(fill="x", pady=(8, 8))
        timer_panel.grid_columnconfigure(0, weight=1)
        timer_panel.grid_columnconfigure(1, weight=1)

        white_timer_frame = make_surface(timer_panel, bg=PANEL_BG, padx=10, pady=8)
        white_timer_frame.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        tk.Label(
            white_timer_frame,
            text="⏱ White",
            font=ui_font(8, "bold"),
            bg=PANEL_BG,
            fg=TEXT_SOFT,
        ).pack(anchor="w")
        tk.Label(
            white_timer_frame,
            textvariable=self.white_time_var,
            font=ui_font(16, "bold", mono=True),
            bg=PANEL_BG,
            fg=TEXT_PRIMARY,
        ).pack(anchor="w", pady=(3, 0))

        black_timer_frame = make_surface(timer_panel, bg=PANEL_BG, padx=10, pady=8)
        black_timer_frame.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        tk.Label(
            black_timer_frame,
            text="⏱ Black",
            font=ui_font(8, "bold"),
            bg=PANEL_BG,
            fg=TEXT_SOFT,
        ).pack(anchor="w")
        tk.Label(
            black_timer_frame,
            textvariable=self.black_time_var,
            font=ui_font(16, "bold", mono=True),
            bg=PANEL_BG,
            fg=TEXT_PRIMARY,
        ).pack(anchor="w", pady=(3, 0))

        captures_grid = tk.Frame(captures_panel, bg=CARD_BG)
        captures_grid.pack(fill="x", pady=(10, 0))
        captures_grid.grid_columnconfigure(0, weight=1)
        captures_grid.grid_columnconfigure(1, weight=1)

        white_panel = make_surface(captures_grid, bg=PANEL_BG, padx=12, pady=10)
        white_panel.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        white_panel.grid_propagate(False)
        white_panel.configure(width=164, height=92)
        tk.Label(
            white_panel,
            text="White",
            font=ui_font(10, "bold"),
            bg=PANEL_BG,
            fg=TEXT_SOFT,
        ).pack(anchor="w")
        tk.Label(
            white_panel,
            textvariable=self.white_capture_count_var,
            font=ui_font(8, "bold"),
            bg=PANEL_BG,
            fg=TEXT_SOFT,
        ).pack(anchor="w", pady=(2, 0))
        tk.Label(
            white_panel,
            textvariable=self.white_captures_var,
            font=ui_font(10, "bold", mono=True),
            bg=PANEL_BG,
            fg=TEXT_PRIMARY,
            justify="left",
            anchor="w",
            wraplength=136,
        ).pack(anchor="w", pady=(5, 0))

        black_panel = make_surface(captures_grid, bg=PANEL_BG, padx=12, pady=10)
        black_panel.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        black_panel.grid_propagate(False)
        black_panel.configure(width=164, height=92)
        tk.Label(
            black_panel,
            text="Black",
            font=ui_font(10, "bold"),
            bg=PANEL_BG,
            fg=TEXT_SOFT,
        ).pack(anchor="w")
        tk.Label(
            black_panel,
            textvariable=self.black_capture_count_var,
            font=ui_font(8, "bold"),
            bg=PANEL_BG,
            fg=TEXT_SOFT,
        ).pack(anchor="w", pady=(2, 0))
        tk.Label(
            black_panel,
            textvariable=self.black_captures_var,
            font=ui_font(10, "bold", mono=True),
            bg=PANEL_BG,
            fg=TEXT_PRIMARY,
            justify="left",
            anchor="w",
            wraplength=136,
        ).pack(anchor="w", pady=(5, 0))

        history_panel = make_surface(info_column, bg=CARD_BG, padx=16, pady=14)
        history_panel.grid(row=1, column=0, sticky="nsew")

        tk.Label(
            history_panel,
            text="Recent Moves",
            font=ui_font(13, "bold"),
            bg=CARD_BG,
            fg=TEXT_PRIMARY,
        ).pack(anchor="w")

        history_box = tk.Frame(history_panel, bg=PANEL_BG)
        history_box.pack(fill="both", expand=True, pady=(10, 12))
        history_box.grid_rowconfigure(0, weight=1)
        history_box.grid_columnconfigure(0, weight=1)
        self.history_text = tk.Text(
            history_box,
            font=ui_font(10, mono=True),
            bg=PANEL_BG,
            fg=TEXT_PRIMARY,
            relief="flat",
            bd=0,
            highlightthickness=0,
            padx=12,
            pady=10,
            wrap="none",
            width=26,
            height=12,
            state="disabled",
            insertwidth=0,
        )
        history_scrollbar = tk.Scrollbar(history_box, orient="vertical", command=self.history_text.yview)
        self.history_text.configure(yscrollcommand=history_scrollbar.set)
        self.history_text.grid(row=0, column=0, sticky="nsew")
        history_scrollbar.grid(row=0, column=1, sticky="ns")

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
        """Create the board square widgets and coordinate labels."""
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
        width = top.winfo_width() if top.winfo_width() > 1 else min(980, top.winfo_screenwidth())
        height = top.winfo_height() if top.winfo_height() > 1 else min(720, top.winfo_screenheight())
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

        # Clear old Tk image references from board buttons before replacing PhotoImage objects.
        # On macOS/Tk, resizing can otherwise leave a button pointing at a deleted
        # internal image name such as "pyimage28", which raises TclError.
        for button in self.board_buttons.values():
            try:
                button.config(image="")
            except tk.TclError:
                pass

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

    def _set_history_text(self, text: str) -> None:
        """Update the contained move-history viewer without resizing the sidebar."""
        if self.history_text is None:
            self.history_var.set(text)
            return
        self.history_text.configure(state="normal")
        self.history_text.delete("1.0", "end")
        self.history_text.insert("1.0", text)
        self.history_text.configure(state="disabled")
        self.history_text.yview_moveto(1.0)

    def _choose_promotion_kind(self, color: str) -> str | None:
        """Open a small modal dialog so the player can choose a promotion piece."""
        dialog = tk.Toplevel(self)
        dialog.withdraw()
        dialog.title("Choose Promotion")
        dialog.configure(bg=CARD_BG, padx=18, pady=18)
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())

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
        choices.pack(padx=0, pady=0)

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
        dialog.bind("<Escape>", lambda _event: dialog.destroy())

        dialog.update_idletasks()

        root = self.winfo_toplevel()
        dialog_width = dialog.winfo_reqwidth()
        dialog_height = dialog.winfo_reqheight()
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()

        x = root.winfo_rootx() + (root.winfo_width() - dialog_width) // 2
        y = root.winfo_rooty() + (root.winfo_height() - dialog_height) // 2

        x = max(0, min(x, screen_width - dialog_width))
        y = max(0, min(y, screen_height - dialog_height))

        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        dialog.deiconify()
        dialog.lift()
        dialog.focus_force()
        dialog.wait_visibility()
        dialog.grab_set()
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
        if success:
            self._play_latest_move_sound()
        self.refresh()

        if success and (match.winner or match.is_draw):
            self.cancel_timer_tick()
            self.app.after(250, lambda: self.app.open_result_screen(match.status_message))
            return

        if success:
            self._start_timer_tick()
            self._schedule_ai_turn_if_needed()

    def _play_latest_move_sound(self) -> None:
        """Play the right effect for the most recent completed move."""
        if not self.app.state.sound_enabled:
            return

        match = self.app.state.match
        if match.winner or match.is_draw:
            play_sound(self.app, "game_end")
            return

        last_move = match.move_history[-1] if match.move_history else None
        if last_move is not None and last_move.captured_symbol is not None:
            play_sound(self.app, "capture")
            return

        if any(is_in_check(match.board, color) for color in ("white", "black")):
            play_sound(self.app, "check")
            return

        play_sound(self.app, "move")

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
        self._update_timer_display()
        self._set_history_text(format_move_history(match))
        white_capture_count = count_captured_pieces(match, "white")
        black_capture_count = count_captured_pieces(match, "black")
        self.white_capture_count_var.set(f"{white_capture_count} captured")
        self.black_capture_count_var.set(f"{black_capture_count} captured")
        self.white_captures_var.set(format_captured_pieces(match, "white", max_per_line=6))
        self.black_captures_var.set(format_captured_pieces(match, "black", max_per_line=6))
        self.load_button.config(state="normal" if has_saved_match() else "disabled")

        for square, button in self.board_buttons.items():
            piece = piece_at(match.board, square)
            bg = get_square_background(square, match, current_board_theme)

            if piece is not None and (piece.color, piece.kind) in self.piece_images:
                contrast_variant = _piece_contrast_variant(current_theme, piece.color, bg)
                image_key: tuple[str, str] | tuple[str, str, str] = (piece.color, piece.kind, contrast_variant)
                if image_key not in self.piece_images:
                    image_key = (piece.color, piece.kind)
                button.config(
                    image=self.piece_images[image_key],
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
        self.cancel_timer_tick()
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
            self._play_latest_move_sound()
            if match.winner or match.is_draw:
                self.cancel_timer_tick()
                self.refresh()
                self.app.after(250, lambda: self.app.open_result_screen(match.status_message))
                return
            match.status_message = (
                f"Computer ({AI_DIFFICULTY_LABELS[difficulty]}) played "
                f"{match.move_history[-1].notation}. {match.current_turn.title()} to move."
            )
            self._start_timer_tick()
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

    def _update_timer_display(self) -> None:
        """Update the timer display labels with current time values."""
        match = self.app.state.match
        self.white_time_var.set(match.timer.get_white_display())
        self.black_time_var.set(match.timer.get_black_display())

    def _tick_timer(self) -> None:
        """Decrement the active player's timer and update the display."""
        match = self.app.state.match
        if match.winner or match.is_draw:
            self.cancel_timer_tick()
            return

        match.timer.decrement_active_player(match.current_turn)
        self._update_timer_display()

        # Check if time expired
        expired_player = match.timer.get_expired_player()
        if expired_player:
            self.cancel_timer_tick()
            match.status_message = f"{expired_player.title()} ran out of time. {('Black' if expired_player == 'white' else 'White')} wins!"
            match.winner = "black" if expired_player == "white" else "white"
            if self.app.state.sound_enabled:
                play_sound(self.app, "game_end")
            self.refresh()
            self.app.after(250, lambda: self.app.open_result_screen(match.status_message))
            return

        # Schedule next tick
        self.timer_after_id = self.after(1000, self._tick_timer)

    def _start_timer_tick(self) -> None:
        """Start the timer countdown if not already running."""
        if self.timer_after_id is not None:
            return
        self._tick_timer()

    def cancel_timer_tick(self) -> None:
        """Cancel the active timer countdown."""
        if self.timer_after_id is not None:
            self.after_cancel(self.timer_after_id)
            self.timer_after_id = None


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
        make_button(
            controls,
            "Reset Saves & Rank",
            self._confirm_reset_saved_data,
            bg=BUTTON_DANGER_BG,
        ).pack(side="left", padx=8)

    def refresh(self) -> None:
        """Update the screen with the latest app-level result message."""
        self.message_label.config(text=self.app.state.screen_message)
        self.scoreboard_var.set(format_scoreboard_summary(self.app.scoreboard))
        self.rank_var.set(format_rank_summary(self.app.scoreboard))
        self.recent_matches_var.set(format_recent_match_history(self.app.scoreboard))

    def _confirm_reset_saved_data(self) -> None:
        """Confirm and clear saved match/ranking data from the result screen."""
        confirmed = messagebox.askyesno(
            "Reset saved data?",
            "Reset saved matches, recent match history, and ranking progress?",
            parent=self,
        )
        if not confirmed:
            return

        self.app.reset_saved_matches_and_ranking()
