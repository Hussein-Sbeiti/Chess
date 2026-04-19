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
        self.assertEqual(len(state.move_history), 1)

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
        moves = legal_moves_for_piece(state, algebraic_to_index("e2"))

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

    def test_castling_move_is_available_when_path_is_clear(self) -> None:
        board = create_empty_board()
        set_piece(board, algebraic_to_index("e1"), make_piece("white", "king"))
        set_piece(board, algebraic_to_index("h1"), make_piece("white", "rook"))
        set_piece(board, algebraic_to_index("a8"), make_piece("black", "king"))

        state = MatchState(board=board)
        moves = legal_moves_for_piece(state, algebraic_to_index("e1"))

        self.assertIn(algebraic_to_index("g1"), moves)

    def test_castling_moves_rook_and_clears_rights(self) -> None:
        board = create_empty_board()
        set_piece(board, algebraic_to_index("e1"), make_piece("white", "king"))
        set_piece(board, algebraic_to_index("h1"), make_piece("white", "rook"))
        set_piece(board, algebraic_to_index("a8"), make_piece("black", "king"))

        state = MatchState(board=board)
        success, _message = make_move(state, algebraic_to_index("e1"), algebraic_to_index("g1"))

        self.assertTrue(success)
        self.assertEqual(piece_at(state.board, algebraic_to_index("g1")).symbol, "K")
        self.assertEqual(piece_at(state.board, algebraic_to_index("f1")).symbol, "R")
        self.assertFalse(state.castling_rights["white_kingside"])
        self.assertFalse(state.castling_rights["white_queenside"])
        self.assertIn("castled", state.move_history[-1].note)

    def test_castling_blocked_when_king_would_pass_through_check(self) -> None:
        board = create_empty_board()
        set_piece(board, algebraic_to_index("e1"), make_piece("white", "king"))
        set_piece(board, algebraic_to_index("h1"), make_piece("white", "rook"))
        set_piece(board, algebraic_to_index("a8"), make_piece("black", "king"))
        set_piece(board, algebraic_to_index("f8"), make_piece("black", "rook"))

        state = MatchState(board=board)
        moves = legal_moves_for_piece(state, algebraic_to_index("e1"))

        self.assertNotIn(algebraic_to_index("g1"), moves)

    def test_en_passant_target_created_after_double_pawn_step(self) -> None:
        state = MatchState()
        success, _message = make_move(state, algebraic_to_index("e2"), algebraic_to_index("e4"))

        self.assertTrue(success)
        self.assertEqual(state.en_passant_target, algebraic_to_index("e3"))

    def test_en_passant_capture_is_available_and_removes_pawn(self) -> None:
        board = create_empty_board()
        set_piece(board, algebraic_to_index("e1"), make_piece("white", "king"))
        set_piece(board, algebraic_to_index("e8"), make_piece("black", "king"))
        set_piece(board, algebraic_to_index("e5"), make_piece("white", "pawn"))
        set_piece(board, algebraic_to_index("d5"), make_piece("black", "pawn"))

        state = MatchState(board=board, current_turn="white", en_passant_target=algebraic_to_index("d6"))
        moves = legal_moves_for_piece(state, algebraic_to_index("e5"))

        self.assertIn(algebraic_to_index("d6"), moves)

        success, _message = make_move(state, algebraic_to_index("e5"), algebraic_to_index("d6"))

        self.assertTrue(success)
        self.assertEqual(piece_at(state.board, algebraic_to_index("d6")).symbol, "P")
        self.assertIsNone(piece_at(state.board, algebraic_to_index("d5")))
        self.assertIn("en passant", state.move_history[-1].note)

    def test_en_passant_target_expires_after_non_pawn_reply(self) -> None:
        board = create_empty_board()
        set_piece(board, algebraic_to_index("e1"), make_piece("white", "king"))
        set_piece(board, algebraic_to_index("e8"), make_piece("black", "king"))
        set_piece(board, algebraic_to_index("g1"), make_piece("white", "knight"))

        state = MatchState(board=board, current_turn="white", en_passant_target=algebraic_to_index("d6"))
        success, _message = make_move(state, algebraic_to_index("g1"), algebraic_to_index("f3"))

        self.assertTrue(success)
        self.assertIsNone(state.en_passant_target)

    def test_pawn_can_promote_to_chosen_piece(self) -> None:
        board = create_empty_board()
        set_piece(board, algebraic_to_index("e1"), make_piece("white", "king"))
        set_piece(board, algebraic_to_index("h6"), make_piece("black", "king"))
        set_piece(board, algebraic_to_index("a7"), make_piece("white", "pawn"))

        state = MatchState(board=board)
        success, message = make_move(
            state,
            algebraic_to_index("a7"),
            algebraic_to_index("a8"),
            promotion_choice="rook",
        )

        self.assertTrue(success)
        self.assertEqual(piece_at(state.board, algebraic_to_index("a8")).symbol, "R")
        self.assertIn("promoted to rook", state.move_history[-1].note)
        self.assertEqual(state.move_history[-1].notation, "a8=R")
        self.assertEqual(message, "Black to move.")

    def test_invalid_promotion_choice_is_rejected(self) -> None:
        board = create_empty_board()
        set_piece(board, algebraic_to_index("e1"), make_piece("white", "king"))
        set_piece(board, algebraic_to_index("h6"), make_piece("black", "king"))
        set_piece(board, algebraic_to_index("a7"), make_piece("white", "pawn"))

        state = MatchState(board=board)
        success, message = make_move(
            state,
            algebraic_to_index("a7"),
            algebraic_to_index("a8"),
            promotion_choice="king",
        )

        self.assertFalse(success)
        self.assertIn("Invalid promotion choice", message)
        self.assertEqual(piece_at(state.board, algebraic_to_index("a7")).symbol, "P")

    def test_checkmate_sets_winner(self) -> None:
        board = create_empty_board()
        set_piece(board, algebraic_to_index("h8"), make_piece("black", "king"))
        set_piece(board, algebraic_to_index("f6"), make_piece("white", "king"))
        set_piece(board, algebraic_to_index("g6"), make_piece("white", "queen"))

        state = MatchState(board=board)
        success, message = make_move(state, algebraic_to_index("g6"), algebraic_to_index("g7"))

        self.assertTrue(success)
        self.assertEqual(state.winner, "white")
        self.assertEqual(state.move_history[-1].notation, "Qg7#")
        self.assertIn("checkmate", message.lower())

    def test_capture_notation_uses_capture_marker(self) -> None:
        board = create_empty_board()
        set_piece(board, algebraic_to_index("e1"), make_piece("white", "king"))
        set_piece(board, algebraic_to_index("h8"), make_piece("black", "king"))
        set_piece(board, algebraic_to_index("d1"), make_piece("white", "queen"))
        set_piece(board, algebraic_to_index("h5"), make_piece("black", "pawn"))

        state = MatchState(board=board)
        success, _message = make_move(state, algebraic_to_index("d1"), algebraic_to_index("h5"))

        self.assertTrue(success)
        self.assertEqual(state.move_history[-1].notation, "Qxh5+")

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

    def test_insufficient_material_sets_draw_flag(self) -> None:
        board = create_empty_board()
        set_piece(board, algebraic_to_index("e1"), make_piece("white", "king"))
        set_piece(board, algebraic_to_index("e8"), make_piece("black", "king"))
        set_piece(board, algebraic_to_index("c1"), make_piece("white", "bishop"))

        state = MatchState(board=board)
        success, message = make_move(state, algebraic_to_index("c1"), algebraic_to_index("d2"))

        self.assertTrue(success)
        self.assertTrue(state.is_draw)
        self.assertIn("insufficient material", message.lower())

    def test_fifty_move_rule_sets_draw_flag(self) -> None:
        board = create_empty_board()
        set_piece(board, algebraic_to_index("e1"), make_piece("white", "king"))
        set_piece(board, algebraic_to_index("e8"), make_piece("black", "king"))
        set_piece(board, algebraic_to_index("a1"), make_piece("white", "rook"))

        state = MatchState(board=board, halfmove_clock=99)
        success, message = make_move(state, algebraic_to_index("a1"), algebraic_to_index("a2"))

        self.assertTrue(success)
        self.assertTrue(state.is_draw)
        self.assertEqual(state.halfmove_clock, 100)
        self.assertIn("fifty-move", message.lower())

    def test_threefold_repetition_sets_draw_flag(self) -> None:
        board = create_empty_board()
        set_piece(board, algebraic_to_index("e1"), make_piece("white", "king"))
        set_piece(board, algebraic_to_index("e8"), make_piece("black", "king"))
        set_piece(board, algebraic_to_index("g1"), make_piece("white", "knight"))
        set_piece(board, algebraic_to_index("g8"), make_piece("black", "knight"))

        state = MatchState(board=board)
        moves = (
            ("g1", "f3"),
            ("g8", "f6"),
            ("f3", "g1"),
            ("f6", "g8"),
            ("g1", "f3"),
            ("g8", "f6"),
            ("f3", "g1"),
            ("f6", "g8"),
        )

        final_message = ""
        for origin, target in moves:
            success, final_message = make_move(state, algebraic_to_index(origin), algebraic_to_index(target))
            self.assertTrue(success)

        self.assertTrue(state.is_draw)
        self.assertIn("threefold repetition", final_message.lower())


if __name__ == "__main__":
    unittest.main()
