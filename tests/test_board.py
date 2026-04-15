import unittest

from game.board import create_starting_board
from game.coords import algebraic_to_index


class BoardTests(unittest.TestCase):
    """Verify the board starts in the standard chess layout."""

    def test_starting_board_has_expected_kings(self) -> None:
        board = create_starting_board()

        self.assertEqual(board[algebraic_to_index("e1")[0]][algebraic_to_index("e1")[1]].symbol, "K")
        self.assertEqual(board[algebraic_to_index("e8")[0]][algebraic_to_index("e8")[1]].symbol, "k")

    def test_starting_board_has_32_pieces(self) -> None:
        board = create_starting_board()
        piece_count = sum(1 for row in board for piece in row if piece is not None)
        self.assertEqual(piece_count, 32)


if __name__ == "__main__":
    unittest.main()
