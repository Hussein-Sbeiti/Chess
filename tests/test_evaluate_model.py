import unittest

from train.evaluate_model import format_report, run_evaluation


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


if __name__ == "__main__":
    unittest.main()
