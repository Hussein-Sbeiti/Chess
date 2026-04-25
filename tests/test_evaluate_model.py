import json
import tempfile
import unittest
from pathlib import Path

from train.evaluate_model import (
    append_evaluation_history,
    build_history_record,
    format_history,
    format_report,
    load_evaluation_history,
    run_evaluation,
)


class EvaluateModelTests(unittest.TestCase):
    """Verify the model evaluation helper returns useful report data."""

    def test_run_evaluation_returns_scores_checks_and_latency(self) -> None:
        report = run_evaluation(iterations=1)

        self.assertIn("summary", report)
        self.assertIn("material_pairs", report)
        self.assertIn("even_positions", report)
        self.assertIn("checks", report)
        self.assertIn("latency_ms", report)
        self.assertGreaterEqual(report["summary"]["passed"], 0)
        self.assertGreater(report["summary"]["total"], 0)
        self.assertGreaterEqual(len(report["material_pairs"]), 3)
        self.assertIn("fairness_gap", report["material_pairs"][0])
        self.assertIsInstance(report["checks"]["scores_are_finite"], bool)
        self.assertGreaterEqual(report["latency_ms"]["medium"], 0.0)
        self.assertGreaterEqual(report["latency_ms"]["hard"], 0.0)

    def test_format_report_includes_core_sections(self) -> None:
        report = run_evaluation(iterations=1)
        text = format_report(report)

        self.assertIn("Model path:", text)
        self.assertIn("Evaluation summary:", text)
        self.assertIn("Material pairs:", text)
        self.assertIn("Neutral positions:", text)
        self.assertIn("Checks:", text)
        self.assertIn("Latency:", text)

    def test_build_history_record_includes_training_metadata(self) -> None:
        report = run_evaluation(iterations=1)

        with tempfile.TemporaryDirectory() as temp_dir:
            metadata_path = Path(temp_dir) / "metadata.json"
            metadata_path.write_text(
                json.dumps(
                    {
                        "generated_at": "2026-04-25T12:00:00",
                        "final_training_loss": 0.12,
                        "epochs": 3,
                        "learning_rate": 0.001,
                        "result_weight": 0.4,
                        "material_weight": 0.6,
                        "material_calibration_examples": 9,
                        "import_summary": {
                            "attempted_games": 10,
                            "imported_games": 9,
                            "skipped_games": 1,
                        },
                        "dataset": {"example_count": 123},
                    }
                ),
                encoding="utf-8",
            )

            record = build_history_record(report, metadata_path=metadata_path)

        self.assertEqual(record["training"]["final_training_loss"], 0.12)
        self.assertEqual(record["training"]["imported_games"], 9)
        self.assertEqual(record["training"]["dataset_examples"], 123)
        self.assertIn("queen_advantage", record["material_fairness_gaps"])
        self.assertIn("checks", record)

    def test_append_evaluation_history_writes_jsonl_record(self) -> None:
        report = run_evaluation(iterations=1)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            history_path = root / "history.jsonl"
            metadata_path = root / "metadata.json"
            metadata_path.write_text("{}", encoding="utf-8")

            record = append_evaluation_history(report, history_path=history_path, metadata_path=metadata_path)
            rows = history_path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(len(rows), 1)
        self.assertEqual(json.loads(rows[0])["evaluated_at"], record["evaluated_at"])
        self.assertIn("latency_ms", record)

    def test_load_evaluation_history_reads_jsonl_records(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            history_path = Path(temp_dir) / "history.jsonl"
            history_path.write_text(
                '{"evaluated_at":"one","checks_passed":1,"checks_total":2}\n'
                '{"evaluated_at":"two","checks_passed":2,"checks_total":2}\n',
                encoding="utf-8",
            )

            records = load_evaluation_history(history_path)

        self.assertEqual(len(records), 2)
        self.assertEqual(records[-1]["evaluated_at"], "two")

    def test_format_history_prints_recent_comparison_rows(self) -> None:
        records = [
            {
                "evaluated_at": "older",
                "checks_passed": 12,
                "checks_total": 13,
                "training": {"imported_games": 5000, "dataset_examples": 99029, "final_training_loss": 0.145},
                "material_fairness_gaps": {
                    "queen_advantage": 0.09,
                    "rook_advantage": 0.01,
                    "pawn_advantage": 0.05,
                },
                "latency_ms": {"medium": 8.0, "hard": 90.0},
                "moves": {"hard_capture_choice": "d5->d1"},
            },
            {
                "evaluated_at": "newer",
                "checks_passed": 13,
                "checks_total": 13,
                "training": {"imported_games": 10000, "dataset_examples": 195232, "final_training_loss": 0.146},
                "material_fairness_gaps": {
                    "queen_advantage": 0.04,
                    "rook_advantage": 0.03,
                    "pawn_advantage": 0.04,
                },
                "latency_ms": {"medium": 7.0, "hard": 80.0},
                "moves": {"hard_capture_choice": "d5->d1"},
            },
        ]

        text = format_history(records, limit=1)

        self.assertIn("evaluated_at", text)
        self.assertNotIn("older", text)
        self.assertIn("newer", text)
        self.assertIn("10000", text)
        self.assertIn("queen_gap", text)


if __name__ == "__main__":
    unittest.main()
