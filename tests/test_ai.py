"""Tests for ai behavior."""
from unittest.mock import patch

import unittest

from game.ai import (
    AI_PERSONALITY_LABELS,
    _choose_near_best_move,
    ai_difficulty_for_personality,
    ai_personality_for_difficulty,
    all_legal_moves,
    choose_ai_move,
    choose_ai_move_for_difficulty,
    minimax_nn,
)
from game.board import create_empty_board, set_piece
from game.coords import algebraic_to_index
from game.game_models import MatchState
from game.nn_model import TinyChessNet
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

    def test_neural_search_scores_terminal_draw_as_even_result(self) -> None:
        """Verify neural search scores a completed draw as an even result."""
        state = MatchState(is_draw=True)
        model = TinyChessNet()

        score, move = minimax_nn(
            state,
            depth=2,
            alpha=float("-inf"),
            beta=float("inf"),
            maximizing_color="white",
            model=model,
            current_color="white",
        )

        self.assertEqual(score, 0.0)
        self.assertIsNone(move)

    def test_near_best_choice_allows_close_scored_moves_only(self) -> None:
        """Verify near-best choice keeps variety inside the score margin."""
        close_move = (algebraic_to_index("c2"), algebraic_to_index("c4"), None)
        best_move = (algebraic_to_index("g1"), algebraic_to_index("f3"), None)
        far_move = (algebraic_to_index("h2"), algebraic_to_index("h4"), None)

        with patch("game.ai.random.choice") as choice_mock:
            choice_mock.side_effect = lambda moves: moves[-1]
            selected = _choose_near_best_move(
                [
                    (0.5, best_move),
                    (0.495, close_move),
                    (0.1, far_move),
                ],
                margin=0.01,
            )

        self.assertEqual(selected, close_move)
        choice_mock.assert_called_once_with([best_move, close_move])


if __name__ == "__main__":
    unittest.main()
