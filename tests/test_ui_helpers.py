import unittest

from app.ui_screen import (
    BOARD_THEME_PRESETS,
    CHECK_SQUARE,
    LAST_MOVE_FROM_SQUARE,
    LAST_MOVE_TO_SQUARE,
    MAX_SQUARE_SIZE,
    MIN_SQUARE_SIZE,
    compute_board_metrics,
    format_move_history,
    format_captured_pieces,
    get_board_square_colors,
    get_checked_king_square,
    get_square_background,
    normalize_board_theme_name,
)
from game.board import create_empty_board, set_piece
from game.coords import algebraic_to_index
from game.game_models import MatchState, MoveRecord
from game.pieces import make_piece


class UiHelperTests(unittest.TestCase):
    """Verify pure board-highlighting helpers used by the UI."""

    def test_board_metrics_scale_between_small_and_large_windows(self) -> None:
        small = compute_board_metrics(980, 720)
        large = compute_board_metrics(1600, 1000)

        self.assertGreaterEqual(small["square_size"], MIN_SQUARE_SIZE)
        self.assertLessEqual(large["square_size"], MAX_SQUARE_SIZE)
        self.assertGreater(large["square_size"], small["square_size"])

    def test_board_theme_helpers_fall_back_and_return_palette(self) -> None:
        self.assertEqual(normalize_board_theme_name("unknown"), "classic")
        light_square, dark_square = get_board_square_colors("ocean")
        self.assertEqual(light_square, BOARD_THEME_PRESETS["ocean"]["light"])
        self.assertEqual(dark_square, BOARD_THEME_PRESETS["ocean"]["dark"])

    def test_checked_king_square_is_found(self) -> None:
        board = create_empty_board()
        set_piece(board, algebraic_to_index("e1"), make_piece("white", "king"))
        set_piece(board, algebraic_to_index("e8"), make_piece("black", "king"))
        set_piece(board, algebraic_to_index("e7"), make_piece("black", "rook"))

        match = MatchState(board=board)

        self.assertEqual(get_checked_king_square(match), algebraic_to_index("e1"))

    def test_last_move_squares_get_distinct_highlights(self) -> None:
        match = MatchState()
        match.move_history.append(
            MoveRecord(
                start=algebraic_to_index("e2"),
                end=algebraic_to_index("e4"),
                piece_symbol="P",
                notation="e4",
            )
        )

        self.assertEqual(get_square_background(algebraic_to_index("e2"), match, "walnut"), LAST_MOVE_FROM_SQUARE)
        self.assertEqual(get_square_background(algebraic_to_index("e4"), match, "walnut"), LAST_MOVE_TO_SQUARE)

    def test_check_highlight_overrides_last_move_highlight(self) -> None:
        board = create_empty_board()
        set_piece(board, algebraic_to_index("e1"), make_piece("white", "king"))
        set_piece(board, algebraic_to_index("e8"), make_piece("black", "king"))
        set_piece(board, algebraic_to_index("e7"), make_piece("black", "rook"))

        match = MatchState(board=board)
        match.move_history.append(
            MoveRecord(
                start=algebraic_to_index("a7"),
                end=algebraic_to_index("e1"),
                piece_symbol="r",
                notation="Re1+",
            )
        )

        self.assertEqual(get_square_background(algebraic_to_index("e1"), match), CHECK_SQUARE)

    def test_move_history_is_grouped_by_full_turn(self) -> None:
        match = MatchState()
        match.move_history.extend(
            [
                MoveRecord(
                    start=algebraic_to_index("e2"),
                    end=algebraic_to_index("e4"),
                    piece_symbol="P",
                    notation="e4",
                ),
                MoveRecord(
                    start=algebraic_to_index("e7"),
                    end=algebraic_to_index("e5"),
                    piece_symbol="p",
                    notation="e5",
                ),
                MoveRecord(
                    start=algebraic_to_index("g1"),
                    end=algebraic_to_index("f3"),
                    piece_symbol="N",
                    notation="Nf3",
                ),
            ]
        )

        self.assertEqual(format_move_history(match), "1. e4  e5\n2. Nf3")

    def test_captured_pieces_wrap_to_multiple_lines(self) -> None:
        match = MatchState()
        for index in range(10):
            match.move_history.append(
                MoveRecord(
                    start=algebraic_to_index("a2"),
                    end=algebraic_to_index("a3"),
                    piece_symbol="P",
                    captured_symbol="p" if index % 2 == 0 else "n",
                    notation="axb3",
                )
            )

        captured_text = format_captured_pieces(match, "white", max_per_line=4)

        self.assertEqual(len(captured_text.splitlines()), 3)
        self.assertEqual(captured_text.splitlines()[0], "P N P N")


if __name__ == "__main__":
    unittest.main()
