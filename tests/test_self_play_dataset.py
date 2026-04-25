import tempfile
import unittest
from pathlib import Path

from game.ai import all_legal_moves
from game.game_models import MatchState
from game.self_play import play_self_play_game
from game.nn_model import TinyChessNet
from train.self_play_dataset import (
    blended_target,
    load_dataset_metadata,
    load_examples,
    load_training_examples,
    load_training_examples_with_summary,
    generate_material_calibration_examples,
    material_score,
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

    def test_material_score_sees_obvious_material_advantage(self) -> None:
        state = MatchState()
        state.board[0][3] = None

        self.assertGreater(material_score(state), 0.0)

    def test_material_calibration_examples_include_both_sides(self) -> None:
        examples = generate_material_calibration_examples(repeats=1)
        targets = [target for _features, target in examples]

        self.assertGreater(len(examples), 0)
        self.assertTrue(any(target > 0.0 for target in targets))
        self.assertTrue(any(target < 0.0 for target in targets))

    def test_blended_target_mixes_result_and_material(self) -> None:
        state = MatchState()
        state.board[0][3] = None

        target = blended_target(state, -1.0, result_weight=0.5, material_weight=0.5)

        self.assertGreater(target, -1.0)
        self.assertLess(target, 0.0)

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
                    "--result-weight",
                    "0.6",
                    "--material-weight",
                    "0.4",
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
        self.assertEqual(metadata["training_loss_history"], [])
        self.assertIsNone(metadata["final_training_loss"])
        self.assertEqual(metadata["result_weight"], 0.6)
        self.assertEqual(metadata["material_weight"], 0.4)
        self.assertEqual(loaded_metadata["difficulty"], "easy")

    def test_load_training_examples_accepts_jsonl(self) -> None:
        examples = self_play_history_to_examples([MatchState()], 0.5)

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "external.jsonl"
            save_examples(examples, path=path, append=False)
            loaded = load_training_examples(path)

        self.assertEqual(loaded, examples)

    def test_load_training_examples_with_summary_counts_raw_game_csv(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "games.csv"
            path.write_text(
                "winner,moves\n"
                "white,e4 e5\n"
                "black,not-a-move\n",
                encoding="utf-8",
            )

            loaded, summary = load_training_examples_with_summary(path)

        self.assertEqual(len(loaded), 2)
        self.assertEqual(summary["attempted_games"], 2)
        self.assertEqual(summary["imported_games"], 1)
        self.assertEqual(summary["skipped_games"], 1)
        self.assertEqual(summary["examples_generated"], 2)

    def test_load_training_examples_accepts_csv_feature_columns(self) -> None:
        features = [0.0 for _ in range(70)]

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "external.csv"
            header = ["target"] + [f"f{index}" for index in range(70)]
            row = ["-0.75"] + [str(value) for value in features]
            path.write_text(",".join(header) + "\n" + ",".join(row) + "\n", encoding="utf-8")
            loaded = load_training_examples(path)

        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0][0], features)
        self.assertEqual(loaded[0][1], -0.75)

    def test_load_training_examples_accepts_csv_json_features(self) -> None:
        features = [0.0 for _ in range(70)]
        features[0] = 6.0

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "external.csv"
            path.write_text(
                'target,features\n1.0,"[' + ",".join(str(value) for value in features) + ']"\n',
                encoding="utf-8",
            )
            loaded = load_training_examples(path)

        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0][0], features)
        self.assertEqual(loaded[0][1], 1.0)

    def test_pipeline_imports_external_dataset_before_training(self) -> None:
        examples = self_play_history_to_examples([MatchState()], 1.0)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            import_path = root / "external.jsonl"
            save_examples(examples, path=import_path, append=False)
            args = build_arg_parser().parse_args(
                [
                    "--train-only",
                    "--epochs",
                    "1",
                    "--fresh-model",
                    "--overwrite",
                    "--import-dataset",
                    str(import_path),
                    "--import-max-games",
                    "3",
                    "--import-max-positions-per-game",
                    "4",
                    "--result-weight",
                    "0.7",
                    "--material-weight",
                    "0.3",
                    "--material-calibration-repeats",
                    "2",
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

        self.assertTrue(metadata["trained"])
        self.assertTrue(metadata["fresh_model"])
        self.assertEqual(metadata["imported_examples"], 1)
        self.assertEqual(metadata["import_max_games"], 3)
        self.assertEqual(metadata["import_max_positions_per_game"], 4)
        self.assertEqual(metadata["result_weight"], 0.7)
        self.assertEqual(metadata["material_weight"], 0.3)
        self.assertGreater(metadata["material_calibration_examples"], 0)
        self.assertEqual(metadata["material_calibration_repeats"], 2)
        self.assertEqual(len(metadata["training_loss_history"]), 1)
        self.assertIsInstance(metadata["final_training_loss"], float)
        self.assertGreater(len(loaded_examples), 1)

    def test_train_only_import_respects_overwrite(self) -> None:
        examples = self_play_history_to_examples([MatchState()], 1.0)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset_path = root / "self_play.jsonl"
            import_path = root / "external.jsonl"
            save_examples(examples + examples, path=dataset_path, append=False)
            save_examples(examples, path=import_path, append=False)
            args = build_arg_parser().parse_args(
                [
                    "--train-only",
                    "--epochs",
                    "1",
                    "--overwrite",
                    "--import-dataset",
                    str(import_path),
                    "--dataset-path",
                    str(dataset_path),
                    "--metadata-path",
                    str(root / "metadata.json"),
                    "--model-path",
                    str(root / "weights.json"),
                ]
            )

            run_self_play_pipeline(args)
            loaded_examples = load_examples(dataset_path)

        self.assertEqual(len(loaded_examples), 1)

    def test_train_only_import_reuses_matching_cached_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset_path = root / "self_play.jsonl"
            metadata_path = root / "metadata.json"
            model_path = root / "weights.json"
            import_path = root / "games.csv"
            import_path.write_text("winner,moves\nwhite,e4 e5\n", encoding="utf-8")
            first_args = build_arg_parser().parse_args(
                [
                    "--train-only",
                    "--epochs",
                    "1",
                    "--fresh-model",
                    "--overwrite",
                    "--import-dataset",
                    str(import_path),
                    "--import-max-games",
                    "1",
                    "--import-max-positions-per-game",
                    "1",
                    "--material-calibration-repeats",
                    "1",
                    "--dataset-path",
                    str(dataset_path),
                    "--metadata-path",
                    str(metadata_path),
                    "--model-path",
                    str(model_path),
                    "--import-progress-every",
                    "0",
                ]
            )
            second_args = build_arg_parser().parse_args(
                [
                    "--train-only",
                    "--epochs",
                    "1",
                    "--fresh-model",
                    "--import-dataset",
                    str(import_path),
                    "--import-max-games",
                    "1",
                    "--import-max-positions-per-game",
                    "1",
                    "--material-calibration-repeats",
                    "1",
                    "--dataset-path",
                    str(dataset_path),
                    "--metadata-path",
                    str(metadata_path),
                    "--model-path",
                    str(model_path),
                    "--import-progress-every",
                    "0",
                ]
            )

            first_metadata = run_self_play_pipeline(first_args)
            first_count = len(load_examples(dataset_path))
            second_metadata = run_self_play_pipeline(second_args)
            second_count = len(load_examples(dataset_path))

        self.assertFalse(first_metadata["cache_used"])
        self.assertTrue(second_metadata["cache_used"])
        self.assertEqual(second_metadata["import_summary"]["attempted_games"], 1)
        self.assertEqual(first_count, second_count)


if __name__ == "__main__":
    unittest.main()
