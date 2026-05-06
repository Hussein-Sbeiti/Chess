"""Tests for board behavior."""
import unittest


from game.board import create_pawn_rush_board, create_pawns_only_board, create_random_army_board, create_starting_board
from game.coords import algebraic_to_index


class BoardTests(unittest.TestCase):
    """Verify the board starts in the standard chess layout."""

    def test_starting_board_has_expected_kings(self) -> None:
        """Verify starting board has expected kings."""
        board = create_starting_board()

        self.assertEqual(board[algebraic_to_index("e1")[0]][algebraic_to_index("e1")[1]].symbol, "K")
        self.assertEqual(board[algebraic_to_index("e8")[0]][algebraic_to_index("e8")[1]].symbol, "k")

    def test_starting_board_has_32_pieces(self) -> None:
        """Verify starting board has 32 pieces."""
        board = create_starting_board()
        piece_count = sum(1 for row in board for piece in row if piece is not None)
        self.assertEqual(piece_count, 32)

    def test_pawns_only_board_has_only_kings_and_pawns(self) -> None:
        """Verify all-pawns variant keeps kings and pawn armies."""
        board = create_pawns_only_board()
        kinds = {piece.kind for row in board for piece in row if piece is not None}

        self.assertEqual(kinds, {"king", "pawn"})
        self.assertEqual(board[7][4].symbol, "K")
        self.assertEqual(board[0][4].symbol, "k")

    def test_pawn_rush_board_has_extra_pawn_lines(self) -> None:
        """Verify pawn rush starts with two pawn ranks for each side."""
        board = create_pawn_rush_board()
        piece_count = sum(1 for row in board for piece in row if piece is not None)

        self.assertEqual(piece_count, 34)
        self.assertTrue(all(piece is not None and piece.kind == "pawn" for piece in board[5]))
        self.assertTrue(all(piece is not None and piece.kind == "pawn" for piece in board[2]))

    def test_random_army_board_is_deterministic_with_kings(self) -> None:
        """Verify random army setup is repeatable and keeps kings on e-files."""
        first = create_random_army_board()
        second = create_random_army_board()

        self.assertEqual([[piece.symbol if piece else "." for piece in row] for row in first], [[piece.symbol if piece else "." for piece in row] for row in second])
        self.assertEqual(first[7][4].symbol, "K")
        self.assertEqual(first[0][4].symbol, "k")


if __name__ == "__main__":
    unittest.main()
