"""Tests for game csv import behavior."""
import tempfile

import unittest
from io import StringIO
from pathlib import Path

from game.coords import algebraic_to_index
from game.game_models import MatchState
from train.game_csv_import import (
    examples_from_san_game,
    load_game_csv_examples,
    load_game_csv_examples_with_stats,
    parse_san_move,
)
from train.self_play_dataset import load_training_examples


class GameCsvImportTests(unittest.TestCase):
    """Verify raw chess game CSV rows can become training examples."""

    def test_parse_basic_pawn_san_move(self) -> None:
        """Verify parse basic pawn san move."""
        move = parse_san_move(MatchState(), "e4")

        self.assertEqual(move[:2], (algebraic_to_index("e2"), algebraic_to_index("e4")))

    def test_parse_piece_move_with_check_suffix(self) -> None:
        """Verify parse piece move with check suffix."""
        state = MatchState()
        for san in ("e4", "e5", "Bc4", "Nc6"):
            origin, target, promotion_choice = parse_san_move(state, san)
            from game.rules import make_move

            make_move(state, origin, target, promotion_choice=promotion_choice)

        move = parse_san_move(state, "Qh5+")

        self.assertEqual(move[:2], (algebraic_to_index("d1"), algebraic_to_index("h5")))

    def test_parse_castling_move(self) -> None:
        """Verify parse castling move."""
        state = MatchState()
        for san in ("e4", "e5", "Nf3", "Nc6", "Bc4", "Bc5"):
            origin, target, promotion_choice = parse_san_move(state, san)
            from game.rules import make_move

            make_move(state, origin, target, promotion_choice=promotion_choice)

        move = parse_san_move(state, "O-O")

        self.assertEqual(move[:2], (algebraic_to_index("e1"), algebraic_to_index("g1")))

    def test_examples_from_san_game_labels_every_position(self) -> None:
        """Verify examples from san game labels every position."""
        examples = examples_from_san_game("e4 e5 Nf3 Nc6", "white")

        self.assertEqual(len(examples), 4)
        self.assertEqual(examples[0][1], 1.0)

    def test_examples_from_san_game_can_blend_material_target(self) -> None:
        """Verify examples from san game can blend material target."""
        result_only = examples_from_san_game("e4 d5 exd5", "black")
        blended = examples_from_san_game(
            "e4 d5 exd5",
            "black",
            result_weight=0.5,
            material_weight=0.5,
        )

        self.assertEqual(result_only[-1][1], -1.0)
        self.assertGreater(blended[-1][1], -1.0)

    def test_load_game_csv_examples_imports_raw_game_rows(self) -> None:
        """Verify load game csv examples imports raw game rows."""
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

    def test_load_game_csv_examples_with_stats_reports_skips_and_progress(self) -> None:
        """Verify load game csv examples with stats reports skips and progress."""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "games.csv"
            path.write_text(
                "id,winner,moves\n"
                "one,white,e4 e5\n"
                "bad,white,not-a-move\n",
                encoding="utf-8",
            )
            progress = StringIO()

            result = load_game_csv_examples_with_stats(path, progress_every=1, progress_stream=progress)

        self.assertEqual(len(result.examples), 2)
        self.assertEqual(result.attempted_games, 2)
        self.assertEqual(result.imported_games, 1)
        self.assertEqual(result.skipped_games, 1)
        self.assertEqual(result.summary()["examples_generated"], 2)
        self.assertIn("import progress", progress.getvalue())
        self.assertIn("import complete", progress.getvalue())

    def test_load_training_examples_auto_detects_raw_game_csv(self) -> None:
        """Verify load training examples auto detects raw game csv."""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "games.csv"
            path.write_text("winner,moves\nwhite,e4 e5\n", encoding="utf-8")

            examples = load_training_examples(path, max_games=1, max_positions_per_game=1)

        self.assertEqual(len(examples), 1)


if __name__ == "__main__":
    unittest.main()
