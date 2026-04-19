import unittest

from app.app_models import AppState
from game.coords import algebraic_to_index
from game.rules import make_move


class AppStateTests(unittest.TestCase):
    """Verify the top-level app state can reset cleanly."""

    def test_reset_for_new_game_restores_defaults(self) -> None:
        state = AppState()
        make_move(state.match, algebraic_to_index("e2"), algebraic_to_index("e4"))
        state.mode = "custom"
        state.screen_message = "Changed"
        state.match.winner = "white"
        state.match.is_draw = True

        state.reset_for_new_game()

        self.assertEqual(state.mode, "local")
        self.assertEqual(state.screen_message, "White to move.")
        self.assertEqual(state.match.current_turn, "white")
        self.assertIsNone(state.match.winner)
        self.assertFalse(state.match.is_draw)
        self.assertEqual(len(state.match.move_history), 0)


if __name__ == "__main__":
    unittest.main()
