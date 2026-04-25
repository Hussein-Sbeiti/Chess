import tempfile
import unittest
from pathlib import Path

from game.ai import all_legal_moves
from game.game_models import MatchState
from game.self_play import play_self_play_game
from train.self_play_dataset import load_examples, save_examples, self_play_history_to_examples


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


if __name__ == "__main__":
    unittest.main()
