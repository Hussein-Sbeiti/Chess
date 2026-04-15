import unittest

from game.coords import algebraic_to_index, index_to_algebraic


class CoordinateTests(unittest.TestCase):
    """Verify algebraic notation helpers stay consistent."""

    def test_algebraic_to_index(self) -> None:
        self.assertEqual(algebraic_to_index("a1"), (7, 0))
        self.assertEqual(algebraic_to_index("e2"), (6, 4))
        self.assertEqual(algebraic_to_index("h8"), (0, 7))

    def test_index_to_algebraic(self) -> None:
        self.assertEqual(index_to_algebraic((7, 0)), "a1")
        self.assertEqual(index_to_algebraic((6, 4)), "e2")
        self.assertEqual(index_to_algebraic((0, 7)), "h8")


if __name__ == "__main__":
    unittest.main()
