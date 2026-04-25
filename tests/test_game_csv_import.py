import tempfile
import unittest
from pathlib import Path

from game.coords import algebraic_to_index
from game.game_models import MatchState
from train.game_csv_import import examples_from_san_game, load_game_csv_examples, parse_san_move
from train.self_play_dataset import load_training_examples


class GameCsvImportTests(unittest.TestCase):
    """Verify raw chess game CSV rows can become training examples."""

    def test_parse_basic_pawn_san_move(self) -> None:
        move = parse_san_move(MatchState(), "e4")

        self.assertEqual(move[:2], (algebraic_to_index("e2"), algebraic_to_index("e4")))

    def test_parse_piece_move_with_check_suffix(self) -> None:
        state = MatchState()
        for san in ("e4", "e5", "Bc4", "Nc6"):
            origin, target, promotion_choice = parse_san_move(state, san)
            from game.rules import make_move

            make_move(state, origin, target, promotion_choice=promotion_choice)

        move = parse_san_move(state, "Qh5+")

        self.assertEqual(move[:2], (algebraic_to_index("d1"), algebraic_to_index("h5")))

    def test_parse_castling_move(self) -> None:
        state = MatchState()
        for san in ("e4", "e5", "Nf3", "Nc6", "Bc4", "Bc5"):
            origin, target, promotion_choice = parse_san_move(state, san)
            from game.rules import make_move

            make_move(state, origin, target, promotion_choice=promotion_choice)

        move = parse_san_move(state, "O-O")

        self.assertEqual(move[:2], (algebraic_to_index("e1"), algebraic_to_index("g1")))

    def test_examples_from_san_game_labels_every_position(self) -> None:
        examples = examples_from_san_game("e4 e5 Nf3 Nc6", "white")

        self.assertEqual(len(examples), 4)
        self.assertEqual(examples[0][1], 1.0)

    def test_load_game_csv_examples_imports_raw_game_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "games.csv"
            path.write_text(
                "id,winner,moves\n"
                "one,white,e4 e5 Nf3 Nc6\n"
                "two,black,d4 d5 c4 c6\n",
                encoding="utf-8",
            )

            examples = load_game_csv_examples(path)

        self.assertEqual(len(examples), 8)
        self.assertEqual(examples[0][1], 1.0)
        self.assertEqual(examples[-1][1], -1.0)

    def test_load_training_examples_auto_detects_raw_game_csv(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "games.csv"
            path.write_text("winner,moves\nwhite,e4 e5\n", encoding="utf-8")

            examples = load_training_examples(path, max_games=1, max_positions_per_game=1)

        self.assertEqual(len(examples), 1)


if __name__ == "__main__":
    unittest.main()
