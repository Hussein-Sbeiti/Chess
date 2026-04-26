"""Tests for ai behavior."""
from unittest.mock import patch

import unittest

from game.ai import (
    AI_PERSONALITY_LABELS,
    ai_difficulty_for_personality,
    ai_personality_for_difficulty,
    all_legal_moves,
    choose_ai_move,
    choose_ai_move_for_difficulty,
)
from game.board import create_empty_board, set_piece
from game.coords import algebraic_to_index
from game.game_models import MatchState
from game.pieces import make_piece


class AiTests(unittest.TestCase):
    """Verify the lightweight AI helpers choose valid moves."""

    def test_random_ai_returns_a_legal_move(self) -> None:
        """Verify random ai returns a legal move."""
        state = MatchState(current_turn="black")
        move = choose_ai_move(state, "black", "random")

        self.assertIsNotNone(move)
        self.assertIn(move, all_legal_moves(state, "black"))

    def test_aggressive_ai_prefers_a_high_value_capture(self) -> None:
        """Verify aggressive ai prefers a high value capture."""
        board = create_empty_board()
        set_piece(board, algebraic_to_index("a1"), make_piece("white", "king"))
        set_piece(board, algebraic_to_index("h8"), make_piece("black", "king"))
        set_piece(board, algebraic_to_index("d5"), make_piece("black", "queen"))
        set_piece(board, algebraic_to_index("d1"), make_piece("white", "rook"))
        set_piece(board, algebraic_to_index("a5"), make_piece("white", "pawn"))

        state = MatchState(board=board, current_turn="black")
        move = choose_ai_move(state, "black", "aggressive")

        self.assertEqual(move[:2], (algebraic_to_index("d5"), algebraic_to_index("d1")))

    def test_all_personalities_return_legal_moves(self) -> None:
        """Verify all personalities return legal moves."""
        board = create_empty_board()
        set_piece(board, algebraic_to_index("a1"), make_piece("white", "king"))
        set_piece(board, algebraic_to_index("h8"), make_piece("black", "king"))
        set_piece(board, algebraic_to_index("d5"), make_piece("black", "queen"))
        set_piece(board, algebraic_to_index("c4"), make_piece("white", "bishop"))

        state = MatchState(board=board, current_turn="black")
        legal_moves = all_legal_moves(state, "black")

        for personality in AI_PERSONALITY_LABELS:
            move = choose_ai_move(state, "black", personality)
            self.assertIn(move, legal_moves)

    def test_difficulty_mapping_uses_expected_ai_modes(self) -> None:
        """Verify difficulty mapping uses expected ai modes."""
        self.assertEqual(ai_personality_for_difficulty("easy"), "random")
        self.assertEqual(ai_personality_for_difficulty("medium"), "neural")
        self.assertEqual(ai_personality_for_difficulty("hard"), "neural_search")

    def test_legacy_personality_maps_to_closest_difficulty(self) -> None:
        """Verify legacy personality maps to closest difficulty."""
        self.assertEqual(ai_difficulty_for_personality("random"), "easy")
        self.assertEqual(ai_difficulty_for_personality("aggressive"), "easy")
        self.assertEqual(ai_difficulty_for_personality("neural"), "medium")
        self.assertEqual(ai_difficulty_for_personality("neural_search"), "hard")

    def test_choose_ai_move_for_difficulty_dispatches_to_personality(self) -> None:
        """Verify choose ai move for difficulty dispatches to personality."""
        state = MatchState(current_turn="black")

        with patch("game.ai.choose_ai_move") as choose_ai_move_mock:
            choose_ai_move_mock.return_value = None
            choose_ai_move_for_difficulty(state, "black", "hard")

        choose_ai_move_mock.assert_called_once_with(state, "black", "neural_search")


if __name__ == "__main__":
    unittest.main()
