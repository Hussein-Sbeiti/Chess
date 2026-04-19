import tempfile
import unittest
from pathlib import Path

from app.app_models import AppState
from app.persistence import has_saved_match, load_app_state, save_app_state
from game.board import piece_at
from game.coords import algebraic_to_index
from game.rules import legal_moves_for_piece, make_move


class PersistenceTests(unittest.TestCase):
    """Verify saved matches can round-trip back into app state."""

    def test_save_and_load_round_trip_restores_match_state(self) -> None:
        state = AppState()
        state.piece_theme = "mint"
        state.screen_message = "Resume this match."

        make_move(state.match, algebraic_to_index("e2"), algebraic_to_index("e4"))
        make_move(state.match, algebraic_to_index("c7"), algebraic_to_index("c5"))
        state.match.selected_square = algebraic_to_index("g1")
        state.match.highlighted_moves = legal_moves_for_piece(state.match, state.match.selected_square)

        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "match.json"

            save_app_state(state, save_path)
            loaded_state = load_app_state(save_path)

        self.assertEqual(loaded_state.piece_theme, "mint")
        self.assertEqual(loaded_state.screen_message, "Resume this match.")
        self.assertEqual(loaded_state.match.current_turn, state.match.current_turn)
        self.assertEqual(loaded_state.match.selected_square, algebraic_to_index("g1"))
        self.assertEqual(loaded_state.match.highlighted_moves, state.match.highlighted_moves)
        self.assertEqual(len(loaded_state.match.move_history), 2)
        self.assertEqual(loaded_state.match.move_history[-1].notation, "c5")
        self.assertEqual(piece_at(loaded_state.match.board, algebraic_to_index("e4")).symbol, "P")
        self.assertEqual(piece_at(loaded_state.match.board, algebraic_to_index("c5")).symbol, "p")

    def test_has_saved_match_tracks_custom_save_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "match.json"
            self.assertFalse(has_saved_match(save_path))

            save_app_state(AppState(), save_path)

            self.assertTrue(has_saved_match(save_path))


if __name__ == "__main__":
    unittest.main()
