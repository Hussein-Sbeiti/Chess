import unittest
from io import StringIO

from game.encoding import encode_state
from game.game_models import MatchState
from train.train_supervised import train_model_with_history


class TrainSupervisedTests(unittest.TestCase):
    """Verify supervised training helpers expose useful progress details."""

    def test_train_model_with_history_can_report_example_progress(self) -> None:
        features = encode_state(MatchState())
        dataset = [(features, 0.0), (features, 0.1)]
        progress = StringIO()

        _model, loss_history = train_model_with_history(
            dataset,
            epochs=1,
            lr=0.0001,
            progress_every=1,
            progress_stream=progress,
        )

        self.assertEqual(len(loss_history), 1)
        self.assertIn("training progress: epoch=1/1 examples=1/2", progress.getvalue())
        self.assertIn("training progress: epoch=1/1 examples=2/2", progress.getvalue())


if __name__ == "__main__":
    unittest.main()
