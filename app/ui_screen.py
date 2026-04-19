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
from pathlib import Path

from PIL import Image, ImageTk

from game.board import piece_at
from game.coords import Coord, FILES, index_to_algebraic
from game.pieces import PROMOTION_CHOICES
from game.rules import is_promotion_move, legal_moves_for_piece, make_move, piece_belongs_to_player


SCREEN_BG = "#102033"
CARD_BG = "#17304A"
PANEL_BG = "#1D3D5C"
LIGHT_SQUARE = "#EEE8D5"
DARK_SQUARE = "#7A9E7E"
SELECTED_SQUARE = "#F4C95D"
MOVE_HINT_SQUARE = "#A5D6A7"
TEXT_PRIMARY = "#F5F7FA"
TEXT_MUTED = "#BDD4E7"
BUTTON_BG = "#3A6EA5"
BUTTON_ALT_BG = "#6C8EAD"
SQUARE_SIZE = 84
PIECE_ICON_SIZE = 68
ICON_DIR = Path(__file__).resolve().parent.parent / "icons"
VISIBLE_ALPHA_THRESHOLD = 24
COORD_TEXT = "#9FB7CA"


def load_piece_images() -> dict[tuple[str, str], ImageTk.PhotoImage]:
    """Load and center piece art on a square transparent canvas."""
    images: dict[tuple[str, str], ImageTk.PhotoImage] = {}
    resampling = getattr(Image, "Resampling", Image)

    for color in ("white", "black"):
        for kind in ("king", "queen", "rook", "bishop", "knight", "pawn"):
            image_path = ICON_DIR / f"{kind} {color}.png"
            if not image_path.exists():
                continue

            image = Image.open(image_path).convert("RGBA")
            alpha_channel = image.getchannel("A")
            visible_mask = alpha_channel.point(
                lambda alpha: 255 if alpha >= VISIBLE_ALPHA_THRESHOLD else 0
            )
            visible_box = visible_mask.getbbox() or alpha_channel.getbbox()
            if visible_box is not None:
                image = image.crop(visible_box)

            image.thumbnail((PIECE_ICON_SIZE, PIECE_ICON_SIZE), resampling.LANCZOS)

            canvas = Image.new("RGBA", (SQUARE_SIZE, SQUARE_SIZE), (0, 0, 0, 0))
            offset = ((SQUARE_SIZE - image.width) // 2, (SQUARE_SIZE - image.height) // 2)
            canvas.paste(image, offset, image)
            images[(color, kind)] = ImageTk.PhotoImage(canvas)

    return images


def make_empty_square_image() -> ImageTk.PhotoImage:
    """Create a transparent placeholder image so Tk sizes squares by pixels."""
    return ImageTk.PhotoImage(Image.new("RGBA", (SQUARE_SIZE, SQUARE_SIZE), (0, 0, 0, 0)))


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
        padx=14,
        pady=8,
        cursor="hand2",
    )


def make_coord_label(parent: tk.Widget, text: str) -> tk.Label:
    """Create a small board-coordinate label."""
    return tk.Label(
        parent,
        text=text,
        bg=PANEL_BG,
        fg=COORD_TEXT,
        font=("Helvetica", 10, "bold"),
        width=2,
        height=1,
    )


def format_move_history(match) -> str:
    """Build a short move-history summary for the right-hand panel."""
    if not match.move_history:
        return "No moves yet."

    entries: list[str] = []
    for index, record in enumerate(match.move_history[-8:], start=max(1, len(match.move_history) - 7)):
        text = (
            f"{index}. {index_to_algebraic(record.start)} -> "
            f"{index_to_algebraic(record.end)} ({record.piece_symbol})"
        )
        if record.captured_symbol:
            text += f" x {record.captured_symbol}"
        if record.note:
            text += f" [{record.note}]"
        entries.append(text)

    return "\n".join(entries)


class WelcomeScreen(tk.Frame):
    """Intro screen that starts the local chess scaffold."""

    def __init__(self, parent: tk.Widget, app) -> None:
        super().__init__(parent, bg=SCREEN_BG)
        self.app = app

        card = tk.Frame(self, bg=CARD_BG, padx=28, pady=28)
        card.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            card,
            text="Chess",
            font=("Helvetica", 34, "bold"),
            bg=CARD_BG,
            fg=TEXT_PRIMARY,
        ).pack(pady=(0, 10))

        tk.Label(
            card,
            text="Battleship-style project scaffold with separated UI, rules, and tests.",
            font=("Helvetica", 13),
            bg=CARD_BG,
            fg=TEXT_MUTED,
            wraplength=560,
            justify="center",
        ).pack(pady=(0, 18))

        tk.Label(
            card,
            text=(
                "Current foundation:\n"
                "- starting board setup\n"
                "- click-to-move local play\n"
                "- legal move filtering with check detection\n"
                "- castling and en passant support\n"
                "- room for player promotion choice, AI, and polish next"
            ),
            font=("Helvetica", 12),
            bg=CARD_BG,
            fg=TEXT_PRIMARY,
            justify="left",
        ).pack(pady=(0, 20))

        controls = tk.Frame(card, bg=CARD_BG)
        controls.pack()

        make_button(controls, "Start Local Match", self.app.start_new_game).pack(side="left", padx=8)
        make_button(
            controls,
            "Result Screen Preview",
            lambda: self.app.open_result_screen("Result screen scaffold ready for future checkmate flow."),
            bg=BUTTON_ALT_BG,
        ).pack(side="left", padx=8)

    def refresh(self) -> None:
        """Welcome screen stays mostly static, but the hook keeps screen switching consistent."""
        return None


class GameScreen(tk.Frame):
    """Main board screen for the starter chess prototype."""

    def __init__(self, parent: tk.Widget, app) -> None:
        super().__init__(parent, bg=SCREEN_BG)
        self.app = app
        self.board_buttons: dict[Coord, tk.Button] = {}
        self.piece_images = load_piece_images()
        self.empty_square_image = make_empty_square_image()
        self.history_var = tk.StringVar(value="No moves yet.")

        header = tk.Frame(self, bg=SCREEN_BG)
        header.pack(fill="x", padx=24, pady=(24, 8))

        self.title_label = tk.Label(
            header,
            text="Chess Board",
            font=("Helvetica", 24, "bold"),
            bg=SCREEN_BG,
            fg=TEXT_PRIMARY,
        )
        self.title_label.pack(anchor="w")

        self.status_label = tk.Label(
            header,
            text="White to move.",
            font=("Helvetica", 12),
            bg=SCREEN_BG,
            fg=TEXT_MUTED,
        )
        self.status_label.pack(anchor="w", pady=(6, 0))

        content = tk.Frame(self, bg=SCREEN_BG)
        content.pack(fill="both", expand=True, padx=24, pady=16)
        content.grid_columnconfigure(0, weight=3)
        content.grid_columnconfigure(1, weight=2)
        content.grid_rowconfigure(0, weight=1)

        board_card = tk.Frame(content, bg=CARD_BG, padx=18, pady=18)
        board_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        info_card = tk.Frame(content, bg=CARD_BG, padx=18, pady=18)
        info_card.grid(row=0, column=1, sticky="nsew")

        self._build_board(board_card)
        self._build_sidebar(info_card)

    def _build_board(self, parent: tk.Widget) -> None:
        board_shell = tk.Frame(parent, bg=PANEL_BG, padx=10, pady=10)
        board_shell.pack()

        for col, file_char in enumerate(FILES, start=1):
            top_label = make_coord_label(board_shell, file_char)
            top_label.grid(row=0, column=col, padx=1, pady=(0, 4))

            bottom_label = make_coord_label(board_shell, file_char)
            bottom_label.grid(row=9, column=col, padx=1, pady=(4, 0))

        for row in range(8):
            rank_text = str(8 - row)
            left_label = make_coord_label(board_shell, rank_text)
            left_label.grid(row=row + 1, column=0, padx=(0, 4), pady=1)

            right_label = make_coord_label(board_shell, rank_text)
            right_label.grid(row=row + 1, column=9, padx=(4, 0), pady=1)

        for row in range(8):
            for col in range(8):
                button = tk.Button(
                    board_shell,
                    text="",
                    image=self.empty_square_image,
                    font=("Helvetica", 18, "bold"),
                    relief="flat",
                    bd=0,
                    highlightthickness=0,
                    padx=0,
                    pady=0,
                    compound="center",
                    cursor="hand2",
                    command=lambda r=row, c=col: self.on_square_clicked((r, c)),
                )
                button.grid(row=row + 1, column=col + 1, padx=1, pady=1)
                self.board_buttons[(row, col)] = button

    def _build_sidebar(self, parent: tk.Widget) -> None:
        tk.Label(
            parent,
            text="Match Notes",
            font=("Helvetica", 18, "bold"),
            bg=CARD_BG,
            fg=TEXT_PRIMARY,
        ).pack(anchor="w")

        tk.Label(
            parent,
            text=(
                "This build supports legal move filtering, check, checkmate,\n"
                "stalemate, castling, and en passant."
            ),
            font=("Helvetica", 11),
            bg=CARD_BG,
            fg=TEXT_MUTED,
            justify="left",
            wraplength=280,
        ).pack(anchor="w", pady=(8, 16))

        tk.Label(
            parent,
            text="Recent Moves",
            font=("Helvetica", 14, "bold"),
            bg=CARD_BG,
            fg=TEXT_PRIMARY,
        ).pack(anchor="w")

        tk.Label(
            parent,
            textvariable=self.history_var,
            font=("Courier", 11),
            bg=PANEL_BG,
            fg=TEXT_PRIMARY,
            justify="left",
            anchor="nw",
            width=34,
            height=12,
            padx=12,
            pady=10,
        ).pack(fill="x", pady=(8, 16))

        controls = tk.Frame(parent, bg=CARD_BG)
        controls.pack(anchor="w")

        make_button(controls, "Reset Match", self.app.start_new_game).pack(fill="x", pady=4)
        make_button(controls, "Return Home", self.app.return_home, bg=BUTTON_ALT_BG).pack(fill="x", pady=4)

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
            font=("Helvetica", 16, "bold"),
            bg=CARD_BG,
            fg=TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, 8))

        tk.Label(
            dialog,
            text="Choose the piece for the promoted pawn.",
            font=("Helvetica", 11),
            bg=CARD_BG,
            fg=TEXT_MUTED,
        ).pack(anchor="w", pady=(0, 14))

        choices = tk.Frame(dialog, bg=CARD_BG)
        choices.pack()

        for kind in PROMOTION_CHOICES:
            button = tk.Button(
                choices,
                text=kind.title(),
                image=self.piece_images.get((color, kind), self.empty_square_image),
                compound="top",
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

    def refresh(self) -> None:
        """Redraw the board and sidebar from the current match state."""
        match = self.app.state.match
        self.status_label.config(text=match.status_message)
        self.history_var.set(format_move_history(match))

        for square, button in self.board_buttons.items():
            row, col = square
            piece = piece_at(match.board, square)
            base_bg = LIGHT_SQUARE if (row + col) % 2 == 0 else DARK_SQUARE

            if square == match.selected_square:
                bg = SELECTED_SQUARE
            elif square in match.highlighted_moves:
                bg = MOVE_HINT_SQUARE
            else:
                bg = base_bg

            if piece is not None and (piece.color, piece.kind) in self.piece_images:
                button.config(
                    image=self.piece_images[(piece.color, piece.kind)],
                    text="",
                    bg=bg,
                    activebackground=bg,
                )
            else:
                button.config(
                    image=self.empty_square_image,
                    text=piece.symbol if piece else " ",
                    bg=bg,
                    activebackground=bg,
                )


class ResultScreen(tk.Frame):
    """Simple result screen reserved for end-of-match flow."""

    def __init__(self, parent: tk.Widget, app) -> None:
        super().__init__(parent, bg=SCREEN_BG)
        self.app = app

        card = tk.Frame(self, bg=CARD_BG, padx=28, pady=28)
        card.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            card,
            text="Match Result",
            font=("Helvetica", 30, "bold"),
            bg=CARD_BG,
            fg=TEXT_PRIMARY,
        ).pack(pady=(0, 12))

        self.message_label = tk.Label(
            card,
            text="Game result summary goes here.",
            font=("Helvetica", 13),
            bg=CARD_BG,
            fg=TEXT_MUTED,
            wraplength=540,
            justify="center",
        )
        self.message_label.pack(pady=(0, 20))

        controls = tk.Frame(card, bg=CARD_BG)
        controls.pack()

        make_button(controls, "Play Again", self.app.start_new_game).pack(side="left", padx=8)
        make_button(controls, "Return Home", self.app.return_home, bg=BUTTON_ALT_BG).pack(side="left", padx=8)

    def refresh(self) -> None:
        """Update the screen with the latest app-level result message."""
        self.message_label.config(text=self.app.state.screen_message)
