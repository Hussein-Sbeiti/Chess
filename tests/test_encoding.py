import unittest

from game.board import create_empty_board, set_piece
from game.coords import algebraic_to_index
from game.encoding import ENCODED_STATE_SIZE, encode_board_only, encode_state
from game.game_models import MatchState
from game.pieces import make_piece


class EncodingTests(unittest.TestCase):
    """Verify board positions convert into stable numeric features."""

    def test_encode_state_returns_expected_length(self) -> None:
        self.assertEqual(len(encode_state(MatchState())), ENCODED_STATE_SIZE)

    def test_encode_board_maps_piece_values(self) -> None:
        board = create_empty_board()
        set_piece(board, algebraic_to_index("a1"), make_piece("white", "king"))
        set_piece(board, algebraic_to_index("h8"), make_piece("black", "queen"))

        values = encode_board_only(MatchState(board=board))

        self.assertEqual(values[algebraic_to_index("a1")[0] * 8 + algebraic_to_index("a1")[1]], 6.0)
        self.assertEqual(values[algebraic_to_index("h8")[0] * 8 + algebraic_to_index("h8")[1]], -5.0)

    def test_encode_state_includes_turn_castling_and_en_passant(self) -> None:
        state = MatchState(current_turn="black", en_passant_target=algebraic_to_index("e3"))
        state.castling_rights["white_kingside"] = False

        values = encode_state(state)

        self.assertEqual(values[64], -1.0)
        self.assertEqual(values[65:69], [0.0, 1.0, 1.0, 1.0])
        self.assertEqual(values[69], 1.0)


if __name__ == "__main__":
    unittest.main()
