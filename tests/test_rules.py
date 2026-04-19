import unittest

from game.board import create_empty_board, piece_at, set_piece
from game.coords import algebraic_to_index
from game.game_models import MatchState
from game.pieces import make_piece
from game.rules import candidate_moves_for_piece, legal_moves_for_piece, make_move


class RuleTests(unittest.TestCase):
    """Verify the starter chess rules behave as expected."""

    def test_white_pawn_can_advance_one_or_two_from_start(self) -> None:
        state = MatchState()
        moves = candidate_moves_for_piece(state.board, algebraic_to_index("e2"))
        self.assertIn(algebraic_to_index("e3"), moves)
        self.assertIn(algebraic_to_index("e4"), moves)

    def test_knight_can_jump_over_blocking_pieces(self) -> None:
        state = MatchState()
        moves = candidate_moves_for_piece(state.board, algebraic_to_index("g1"))
        self.assertIn(algebraic_to_index("f3"), moves)
        self.assertIn(algebraic_to_index("h3"), moves)
        self.assertNotIn(algebraic_to_index("e2"), moves)

    def test_rook_is_blocked_at_the_start(self) -> None:
        state = MatchState()
        moves = candidate_moves_for_piece(state.board, algebraic_to_index("a1"))
        self.assertEqual(moves, [])

    def test_make_move_switches_turn_and_updates_board(self) -> None:
        state = MatchState()
        success, _message = make_move(state, algebraic_to_index("e2"), algebraic_to_index("e4"))

        self.assertTrue(success)
        self.assertEqual(state.current_turn, "black")
        self.assertIsNone(piece_at(state.board, algebraic_to_index("e2")))
        self.assertEqual(piece_at(state.board, algebraic_to_index("e4")).symbol, "P")

    def test_wrong_color_cannot_move_on_white_turn(self) -> None:
        state = MatchState()
        success, message = make_move(state, algebraic_to_index("e7"), algebraic_to_index("e5"))

        self.assertFalse(success)
        self.assertIn("white", message)

    def test_pinned_piece_cannot_leave_its_king_exposed(self) -> None:
        board = create_empty_board()
        set_piece(board, algebraic_to_index("e1"), make_piece("white", "king"))
        set_piece(board, algebraic_to_index("e2"), make_piece("white", "rook"))
        set_piece(board, algebraic_to_index("a8"), make_piece("black", "king"))
        set_piece(board, algebraic_to_index("e8"), make_piece("black", "rook"))

        state = MatchState(board=board)
        moves = legal_moves_for_piece(state.board, algebraic_to_index("e2"))

        self.assertNotIn(algebraic_to_index("d2"), moves)
        self.assertIn(algebraic_to_index("e3"), moves)

    def test_move_rejected_when_it_would_leave_king_in_check(self) -> None:
        board = create_empty_board()
        set_piece(board, algebraic_to_index("e1"), make_piece("white", "king"))
        set_piece(board, algebraic_to_index("e2"), make_piece("white", "rook"))
        set_piece(board, algebraic_to_index("a8"), make_piece("black", "king"))
        set_piece(board, algebraic_to_index("e8"), make_piece("black", "rook"))

        state = MatchState(board=board)
        success, message = make_move(state, algebraic_to_index("e2"), algebraic_to_index("d2"))

        self.assertFalse(success)
        self.assertIn("leave your king in check", message)

    def test_checkmate_sets_winner(self) -> None:
        board = create_empty_board()
        set_piece(board, algebraic_to_index("h8"), make_piece("black", "king"))
        set_piece(board, algebraic_to_index("f6"), make_piece("white", "king"))
        set_piece(board, algebraic_to_index("g6"), make_piece("white", "queen"))

        state = MatchState(board=board)
        success, message = make_move(state, algebraic_to_index("g6"), algebraic_to_index("g7"))

        self.assertTrue(success)
        self.assertEqual(state.winner, "white")
        self.assertIn("checkmate", message.lower())

    def test_stalemate_sets_draw_flag(self) -> None:
        board = create_empty_board()
        set_piece(board, algebraic_to_index("h8"), make_piece("black", "king"))
        set_piece(board, algebraic_to_index("f7"), make_piece("white", "king"))
        set_piece(board, algebraic_to_index("g5"), make_piece("white", "queen"))

        state = MatchState(board=board)
        success, message = make_move(state, algebraic_to_index("g5"), algebraic_to_index("g6"))

        self.assertTrue(success)
        self.assertTrue(state.is_draw)
        self.assertIsNone(state.winner)
        self.assertIn("stalemate", message.lower())


if __name__ == "__main__":
    unittest.main()
