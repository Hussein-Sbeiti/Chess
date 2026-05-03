"""Tests for chess clock behavior."""
import unittest

from game.game_models import GameTimer


class GameTimerTests(unittest.TestCase):
    """Verify the match timer display and countdown behavior."""

    def test_timer_counts_down_and_resets(self) -> None:
        """Timer should format time, pause, resume, expire, and reset cleanly."""
        timer = GameTimer()

        self.assertEqual(timer.white_remaining, 300)
        self.assertEqual(timer.black_remaining, 300)
        self.assertTrue(timer.is_active)
        self.assertEqual(timer.format_time(300), "5:00")
        self.assertEqual(timer.format_time(65), "1:05")
        self.assertEqual(timer.format_time(3665), "1:01:05")

        timer.decrement_active_player("white")
        self.assertEqual(timer.white_remaining, 299)
        self.assertEqual(timer.black_remaining, 300)

        timer.decrement_active_player("black")
        self.assertEqual(timer.white_remaining, 299)
        self.assertEqual(timer.black_remaining, 299)

        timer.pause()
        timer.decrement_active_player("white")
        self.assertEqual(timer.white_remaining, 299)

        timer.resume()
        timer.decrement_active_player("white")
        self.assertEqual(timer.white_remaining, 298)

        timer.white_remaining = 0
        self.assertTrue(timer.has_time_expired())
        self.assertEqual(timer.get_expired_player(), "white")

        timer.reset(600)
        self.assertEqual(timer.white_remaining, 600)
        self.assertEqual(timer.black_remaining, 600)
        self.assertTrue(timer.is_active)


if __name__ == "__main__":
    unittest.main()
