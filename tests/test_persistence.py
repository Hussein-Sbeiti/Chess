import tempfile
import unittest
from pathlib import Path

from app.app_models import AppState
from app.persistence import app_state_from_data, app_state_to_data, has_saved_match, load_app_state, save_app_state
from game.board import piece_at
from game.coords import algebraic_to_index
from game.rules import legal_moves_for_piece, make_move


class PersistenceTests(unittest.TestCase):
    """Verify saved matches can round-trip back into app state."""

    def test_save_and_load_round_trip_restores_match_state(self) -> None:
        state = AppState()
        state.mode = "ai_vs_ai"
        state.piece_theme = "mint"
        state.board_theme = "ocean"
        state.ai_personality = "aggressive"
        state.ai_difficulty = "hard"
        state.ai_player_color = "black"
        state.screen_message = "Resume this match."

        make_move(state.match, algebraic_to_index("e2"), algebraic_to_index("e4"))
        make_move(state.match, algebraic_to_index("c7"), algebraic_to_index("c5"))
        state.match.selected_square = algebraic_to_index("g1")
        state.match.highlighted_moves = legal_moves_for_piece(state.match, state.match.selected_square)
        state.match.halfmove_clock = 12
        state.match.position_counts = {"position-a": 1, "position-b": 2}

        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "match.json"

            save_app_state(state, save_path)
            loaded_state = load_app_state(save_path)

        self.assertEqual(loaded_state.mode, "ai_vs_ai")
        self.assertEqual(loaded_state.piece_theme, "mint")
        self.assertEqual(loaded_state.board_theme, "ocean")
        self.assertEqual(loaded_state.ai_personality, "aggressive")
        self.assertEqual(loaded_state.ai_difficulty, "hard")
        self.assertEqual(loaded_state.ai_player_color, "black")
        self.assertEqual(loaded_state.screen_message, "Resume this match.")
        self.assertEqual(loaded_state.match.current_turn, state.match.current_turn)
        self.assertEqual(loaded_state.match.selected_square, algebraic_to_index("g1"))
        self.assertEqual(loaded_state.match.highlighted_moves, state.match.highlighted_moves)
        self.assertEqual(loaded_state.match.halfmove_clock, 12)
        self.assertEqual(loaded_state.match.position_counts, {"position-a": 1, "position-b": 2})
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

    def test_old_save_without_ai_difficulty_infers_from_personality(self) -> None:
        state = AppState()
        state.mode = "ai"
        state.ai_personality = "neural_search"
        data = app_state_to_data(state)
        del data["ai_difficulty"]

        loaded_state = app_state_from_data(data)

        self.assertEqual(loaded_state.ai_difficulty, "hard")

    def test_unknown_saved_mode_falls_back_to_local(self) -> None:
        state = AppState()
        data = app_state_to_data(state)
        data["mode"] = "mystery"

        loaded_state = app_state_from_data(data)

        self.assertEqual(loaded_state.mode, "local")


if __name__ == "__main__":
    unittest.main()
