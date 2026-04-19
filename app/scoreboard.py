from __future__ import annotations

# app/scoreboard.py
# Chess Project - persistent scoreboard and ranking helpers
# Created: 2026-04-19

"""
This file stores long-term match statistics for the chess app.

It is separate from save/load match persistence because a scoreboard is meant to
survive across many matches, not just resume one board position.
"""

from dataclasses import asdict, dataclass
import json
from pathlib import Path

from game.game_models import MatchState


SCOREBOARD_DIR = Path(__file__).resolve().parent.parent / "saves"
SCOREBOARD_FILE = SCOREBOARD_DIR / "scoreboard.json"
RANK_TIERS = (
    ("Unranked", 0),
    ("Bronze", 3),
    ("Silver", 9),
    ("Gold", 18),
    ("Platinum", 30),
    ("Diamond", 45),
    ("Master", 65),
)


@dataclass
class Scoreboard:
    """Persistent stats for completed matches."""

    total_games: int = 0
    local_games: int = 0
    ai_games: int = 0
    white_wins: int = 0
    black_wins: int = 0
    draws: int = 0
    human_wins: int = 0
    human_losses: int = 0
    human_draws: int = 0
    ranking_points: int = 0
    current_streak: int = 0
    best_streak: int = 0

    def copy(self) -> "Scoreboard":
        """Return a plain mutable copy."""
        return Scoreboard(**asdict(self))


def rank_for_points(points: int) -> str:
    """Return the current rank name for the given point total."""
    current_rank = RANK_TIERS[0][0]
    for rank_name, minimum_points in RANK_TIERS:
        if points >= minimum_points:
            current_rank = rank_name
        else:
            break
    return current_rank


def rank_window(points: int) -> tuple[str, str | None, int, int | None]:
    """Return current and next rank metadata for progress display."""
    previous_name, previous_floor = RANK_TIERS[0]
    for rank_name, minimum_points in RANK_TIERS[1:]:
        if points < minimum_points:
            return previous_name, rank_name, previous_floor, minimum_points
        previous_name, previous_floor = rank_name, minimum_points
    return previous_name, None, previous_floor, None


def scoreboard_to_data(scoreboard: Scoreboard) -> dict[str, int]:
    """Convert scoreboard stats into JSON-safe data."""
    return asdict(scoreboard)


def scoreboard_from_data(data) -> Scoreboard:
    """Rebuild a scoreboard from saved JSON data."""
    if not isinstance(data, dict):
        raise ValueError("Saved scoreboard data is invalid.")

    values: dict[str, int] = {}
    for field_name in (
        "total_games",
        "local_games",
        "ai_games",
        "white_wins",
        "black_wins",
        "draws",
        "human_wins",
        "human_losses",
        "human_draws",
        "ranking_points",
        "current_streak",
        "best_streak",
    ):
        value = data.get(field_name, 0)
        if not isinstance(value, int) or value < 0:
            raise ValueError("Saved scoreboard data is invalid.")
        values[field_name] = value

    return Scoreboard(**values)


def load_scoreboard(file_path: Path = SCOREBOARD_FILE) -> Scoreboard:
    """Load the saved scoreboard, or return a clean one when no file exists yet."""
    if not file_path.exists():
        return Scoreboard()

    with file_path.open("r", encoding="utf-8") as save_file:
        return scoreboard_from_data(json.load(save_file))


def save_scoreboard(scoreboard: Scoreboard, file_path: Path = SCOREBOARD_FILE) -> Path:
    """Write the scoreboard to disk as JSON."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as save_file:
        json.dump(scoreboard_to_data(scoreboard), save_file, indent=2)
    return file_path


def record_completed_match(
    scoreboard: Scoreboard,
    match: MatchState,
    mode: str,
    human_color: str,
) -> Scoreboard:
    """Return updated persistent stats for one finished match."""
    updated = scoreboard.copy()
    updated.total_games += 1

    if mode == "ai":
        updated.ai_games += 1
    else:
        updated.local_games += 1

    if match.is_draw:
        updated.draws += 1
        if mode == "ai":
            updated.human_draws += 1
            updated.ranking_points += 1
            updated.current_streak = 0
        return updated

    if match.winner == "white":
        updated.white_wins += 1
    elif match.winner == "black":
        updated.black_wins += 1

    if mode == "ai" and match.winner in {"white", "black"}:
        if match.winner == human_color:
            updated.human_wins += 1
            updated.ranking_points += 3
            updated.current_streak += 1
            updated.best_streak = max(updated.best_streak, updated.current_streak)
        else:
            updated.human_losses += 1
            updated.current_streak = 0

    return updated
