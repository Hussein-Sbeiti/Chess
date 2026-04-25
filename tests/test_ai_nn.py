import tempfile
import unittest
from pathlib import Path

from game.ai import all_legal_moves, choose_nn_move, choose_nn_search_move
from game.encoding import encode_state
from game.game_models import MatchState
from game.nn_model import TinyChessNet


class NeuralAiTests(unittest.TestCase):
    """Verify the neural evaluator can score, persist, and choose legal moves."""

    def test_neural_ai_returns_legal_move(self) -> None:
        state = MatchState(current_turn="black")
        model = TinyChessNet()

        move = choose_nn_move(state, "black", model)

        self.assertIn(move, all_legal_moves(state, "black"))

    def test_neural_search_ai_returns_legal_move(self) -> None:
        state = MatchState(current_turn="black")
        model = TinyChessNet()

        move = choose_nn_search_move(state, "black", model, depth=1)

        self.assertIn(move, all_legal_moves(state, "black"))

    def test_model_save_and_load_preserves_prediction(self) -> None:
        model = TinyChessNet()
        features = encode_state(MatchState())
        before = model.predict(features)

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "weights.json"
            model.save(path)
            loaded = TinyChessNet()
            loaded.load(path)

        self.assertAlmostEqual(loaded.predict(features), before)

    def test_train_step_changes_prediction_without_crashing(self) -> None:
        model = TinyChessNet()
        features = encode_state(MatchState())
        before = model.predict(features)

        model.train_step(features, 0.5, lr=0.001)

        self.assertNotEqual(model.predict(features), before)


if __name__ == "__main__":
    unittest.main()
