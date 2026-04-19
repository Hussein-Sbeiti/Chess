import unittest

from app.app_models import AppState
from game.coords import algebraic_to_index
from game.rules import make_move


class AppStateTests(unittest.TestCase):
    """Verify the top-level app state can reset cleanly."""

    def test_reset_for_new_game_restores_defaults(self) -> None:
        state = AppState()
        make_move(state.match, algebraic_to_index("e2"), algebraic_to_index("e4"))
        state.mode = "ai"
        state.screen_message = "Changed"
        state.piece_theme = "royal"
        state.board_theme = "walnut"
        state.ai_personality = "defensive"
        state.ai_player_color = "black"
        state.match.winner = "white"
        state.match.is_draw = True
        state.match.castling_rights["white_kingside"] = False
        state.match.en_passant_target = algebraic_to_index("e3")
        state.match.halfmove_clock = 12
        state.match.position_counts = {"custom-position": 2}

        state.reset_for_new_game()

        self.assertEqual(state.mode, "ai")
        self.assertEqual(state.screen_message, "White to move.")
        self.assertEqual(state.piece_theme, "royal")
        self.assertEqual(state.board_theme, "walnut")
        self.assertEqual(state.ai_personality, "defensive")
        self.assertEqual(state.ai_player_color, "black")
        self.assertEqual(state.match.current_turn, "white")
        self.assertIsNone(state.match.winner)
        self.assertFalse(state.match.is_draw)
        self.assertTrue(state.match.castling_rights["white_kingside"])
        self.assertIsNone(state.match.en_passant_target)
        self.assertEqual(state.match.halfmove_clock, 0)
        self.assertEqual(len(state.match.position_counts), 1)
        self.assertEqual(len(state.match.move_history), 0)


if __name__ == "__main__":
    unittest.main()
