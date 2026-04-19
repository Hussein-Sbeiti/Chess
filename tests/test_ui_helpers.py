import unittest

from app.ui_screen import (
    BOARD_THEME_PRESETS,
    CHECK_SQUARE,
    LAST_MOVE_FROM_SQUARE,
    LAST_MOVE_TO_SQUARE,
    MAX_SQUARE_SIZE,
    MIN_SQUARE_SIZE,
    compute_board_metrics,
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


if __name__ == "__main__":
    unittest.main()
