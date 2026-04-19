import unittest

from app.ui_app import compute_initial_window_size, compute_min_window_size


class AppWindowTests(unittest.TestCase):
    """Verify cross-platform window sizing helpers stay within screen limits."""

    def test_initial_window_size_fits_the_screen(self) -> None:
        width, height = compute_initial_window_size(1280, 800)

        self.assertLessEqual(width, 1280 - 80)
        self.assertLessEqual(height, 800 - 110)
        self.assertGreaterEqual(width, 980)
        self.assertGreaterEqual(height, 690)

    def test_min_window_size_stays_reasonable_for_smaller_screens(self) -> None:
        width, height = compute_min_window_size(1024, 700)

        self.assertGreaterEqual(width, 720)
        self.assertGreaterEqual(height, 520)
        self.assertLessEqual(width, 820)
        self.assertLessEqual(height, 620)


if __name__ == "__main__":
    unittest.main()
