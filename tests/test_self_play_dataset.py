import tempfile
import unittest
from pathlib import Path

from game.ai import all_legal_moves
from game.game_models import MatchState
from game.self_play import play_self_play_game
from game.nn_model import TinyChessNet
from train.self_play_dataset import (
    load_dataset_metadata,
    load_examples,
    save_dataset_metadata,
    save_examples,
    self_play_history_to_examples,
    summarize_examples,
)
from train.train_self_play import build_arg_parser, generate_self_play_examples, run_self_play_pipeline


class SelfPlayDatasetTests(unittest.TestCase):
    """Verify self-play histories can become persistent training data."""

    def test_self_play_game_returns_seen_positions_and_result(self) -> None:
        def first_legal_move(state):
            return all_legal_moves(state, state.current_turn)[0]

        history, result = play_self_play_game(
            MatchState,
            first_legal_move,
            first_legal_move,
            max_turns=2,
        )

        self.assertEqual(len(history), 2)
        self.assertEqual(result, 0.0)

    def test_self_play_history_round_trips_as_jsonl_examples(self) -> None:
        examples = self_play_history_to_examples([MatchState()], 1.0)

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "self_play.jsonl"
            save_examples(examples, path=path, append=False)
            loaded = load_examples(path)

        self.assertEqual(len(loaded), 1)
        self.assertEqual(len(loaded[0][0]), 70)
        self.assertEqual(loaded[0][1], 1.0)

    def test_save_examples_appends_when_requested(self) -> None:
        examples = self_play_history_to_examples([MatchState()], -1.0)

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "self_play.jsonl"
            save_examples(examples, path=path, append=False)
            save_examples(examples, path=path, append=True)
            loaded = load_examples(path)

        self.assertEqual(len(loaded), 2)

    def test_summarize_examples_counts_result_targets(self) -> None:
        state = MatchState()
        examples = (
            self_play_history_to_examples([state], 1.0)
            + self_play_history_to_examples([state], -1.0)
            + self_play_history_to_examples([state], 0.0)
        )

        summary = summarize_examples(examples)

        self.assertEqual(summary["example_count"], 3)
        self.assertEqual(summary["white_result_examples"], 1)
        self.assertEqual(summary["black_result_examples"], 1)
        self.assertEqual(summary["draw_examples"], 1)

    def test_dataset_metadata_round_trips(self) -> None:
        metadata = {"games_requested": 2, "difficulty": "easy"}

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "metadata.json"
            save_dataset_metadata(metadata, path)
            loaded = load_dataset_metadata(path)

        self.assertEqual(loaded, metadata)

    def test_self_play_generation_respects_max_turns(self) -> None:
        examples = generate_self_play_examples(
            TinyChessNet(),
            games=1,
            max_turns=2,
            difficulty="easy",
        )

        self.assertLessEqual(len(examples), 2)
        self.assertGreater(len(examples), 0)

    def test_arg_parser_accepts_training_controls(self) -> None:
        args = build_arg_parser().parse_args(
            [
                "--games",
                "3",
                "--max-turns",
                "4",
                "--difficulty",
                "hard",
                "--generate-only",
                "--overwrite",
            ]
        )

        self.assertEqual(args.games, 3)
        self.assertEqual(args.max_turns, 4)
        self.assertEqual(args.difficulty, "hard")
        self.assertTrue(args.generate_only)
        self.assertTrue(args.overwrite)

    def test_generate_only_pipeline_writes_dataset_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            args = build_arg_parser().parse_args(
                [
                    "--games",
                    "1",
                    "--max-turns",
                    "2",
                    "--difficulty",
                    "easy",
                    "--generate-only",
                    "--overwrite",
                    "--dataset-path",
                    str(root / "self_play.jsonl"),
                    "--metadata-path",
                    str(root / "metadata.json"),
                    "--model-path",
                    str(root / "weights.json"),
                ]
            )

            metadata = run_self_play_pipeline(args)
            loaded_examples = load_examples(root / "self_play.jsonl")
            loaded_metadata = load_dataset_metadata(root / "metadata.json")

        self.assertGreater(metadata["generated_examples"], 0)
        self.assertEqual(len(loaded_examples), metadata["generated_examples"])
        self.assertFalse(metadata["trained"])
        self.assertEqual(loaded_metadata["difficulty"], "easy")


if __name__ == "__main__":
    unittest.main()
