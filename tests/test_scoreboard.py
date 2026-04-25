import tempfile
import unittest
from pathlib import Path

from app.scoreboard import (
    MAX_RECENT_MATCHES,
    RecentMatchRecord,
    Scoreboard,
    load_scoreboard,
    rank_for_points,
    record_completed_match,
    save_scoreboard,
)
from game.game_models import MatchState


class ScoreboardTests(unittest.TestCase):
    """Verify persistent scoreboard and ranking helpers."""

    def test_ai_win_updates_points_rank_and_streak(self) -> None:
        scoreboard = Scoreboard()
        match = MatchState(winner="white")

        updated = record_completed_match(scoreboard, match, "ai", "white")

        self.assertEqual(updated.total_games, 1)
        self.assertEqual(updated.ai_games, 1)
        self.assertEqual(updated.white_wins, 1)
        self.assertEqual(updated.human_wins, 1)
        self.assertEqual(updated.ranking_points, 3)
        self.assertEqual(updated.current_streak, 1)
        self.assertEqual(updated.best_streak, 1)
        self.assertEqual(rank_for_points(updated.ranking_points), "Bronze")
        self.assertEqual(len(updated.recent_matches), 1)
        self.assertIn("You won as White", updated.recent_matches[0].summary())

    def test_ai_draw_adds_one_point_and_resets_streak(self) -> None:
        scoreboard = Scoreboard(current_streak=2, best_streak=4)
        match = MatchState(is_draw=True)

        updated = record_completed_match(scoreboard, match, "ai", "black", finished_at="2026-04-19 14:12")

        self.assertEqual(updated.draws, 1)
        self.assertEqual(updated.human_draws, 1)
        self.assertEqual(updated.ranking_points, 1)
        self.assertEqual(updated.current_streak, 0)
        self.assertEqual(updated.best_streak, 4)
        self.assertEqual(updated.recent_matches[0].finished_at, "2026-04-19 14:12")
        self.assertEqual(updated.recent_matches[0].result_label, "Draw")

    def test_local_result_updates_overall_scoreboard_only(self) -> None:
        scoreboard = Scoreboard()
        match = MatchState(winner="black")

        updated = record_completed_match(scoreboard, match, "local", "white")

        self.assertEqual(updated.total_games, 1)
        self.assertEqual(updated.local_games, 1)
        self.assertEqual(updated.black_wins, 1)
        self.assertEqual(updated.human_wins, 0)
        self.assertEqual(updated.ranking_points, 0)
        self.assertEqual(updated.recent_matches[0].result_label, "Black won")

    def test_ai_vs_ai_counts_as_ai_without_human_points(self) -> None:
        scoreboard = Scoreboard()
        match = MatchState(winner="white")

        updated = record_completed_match(scoreboard, match, "ai_vs_ai", "white")

        self.assertEqual(updated.total_games, 1)
        self.assertEqual(updated.ai_games, 1)
        self.assertEqual(updated.local_games, 0)
        self.assertEqual(updated.white_wins, 1)
        self.assertEqual(updated.human_wins, 0)
        self.assertEqual(updated.ranking_points, 0)
        self.assertEqual(updated.recent_matches[0].mode_label, "AI vs AI")
        self.assertEqual(updated.recent_matches[0].result_label, "White AI won")

    def test_recent_match_history_is_capped(self) -> None:
        scoreboard = Scoreboard(
            recent_matches=[
                RecentMatchRecord(
                    finished_at=f"2026-04-18 1{i}:00",
                    mode_label="Local",
                    result_label="White won",
                    move_count=10 + i,
                )
                for i in range(MAX_RECENT_MATCHES)
            ]
        )
        match = MatchState(winner="white")

        updated = record_completed_match(scoreboard, match, "local", "white", finished_at="2026-04-19 15:00")

        self.assertEqual(len(updated.recent_matches), MAX_RECENT_MATCHES)
        self.assertEqual(updated.recent_matches[0].finished_at, "2026-04-19 15:00")

    def test_scoreboard_can_round_trip_through_json(self) -> None:
        scoreboard = Scoreboard(
            total_games=5,
            ai_games=3,
            white_wins=2,
            black_wins=2,
            draws=1,
            human_wins=2,
            human_losses=1,
            human_draws=0,
            ranking_points=6,
            current_streak=2,
            best_streak=3,
            recent_matches=[
                RecentMatchRecord(
                    finished_at="2026-04-19 13:40",
                    mode_label="Vs AI",
                    result_label="You won as White",
                    move_count=18,
                )
            ],
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "scoreboard.json"
            save_scoreboard(scoreboard, save_path)
            loaded = load_scoreboard(save_path)

        self.assertEqual(loaded.total_games, 5)
        self.assertEqual(loaded.ai_games, 3)
        self.assertEqual(loaded.human_wins, 2)
        self.assertEqual(loaded.ranking_points, 6)
        self.assertEqual(loaded.best_streak, 3)
        self.assertEqual(len(loaded.recent_matches), 1)
        self.assertEqual(loaded.recent_matches[0].mode_label, "Vs AI")


if __name__ == "__main__":
    unittest.main()
