import unittest

from game.ai import AI_PERSONALITY_LABELS, all_legal_moves, choose_ai_move
from game.board import create_empty_board, set_piece
from game.coords import algebraic_to_index
from game.game_models import MatchState
from game.pieces import make_piece


class AiTests(unittest.TestCase):
    """Verify the lightweight AI helpers choose valid moves."""

    def test_random_ai_returns_a_legal_move(self) -> None:
        state = MatchState(current_turn="black")
        move = choose_ai_move(state, "black", "random")

        self.assertIsNotNone(move)
        self.assertIn(move, all_legal_moves(state, "black"))

    def test_aggressive_ai_prefers_a_high_value_capture(self) -> None:
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


if __name__ == "__main__":
    unittest.main()
