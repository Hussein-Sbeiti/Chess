from __future__ import annotations

# app/scoreboard.py
# Chess Project - persistent scoreboard and ranking helpers
# Created: 2026-04-19

"""
This file stores long-term match statistics for the chess app.

It is separate from save/load match persistence because a scoreboard is meant to
survive across many matches, not just resume one board position.
"""

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path

from game.game_models import MatchState


SCOREBOARD_DIR = Path(__file__).resolve().parent.parent / "saves"
SCOREBOARD_FILE = SCOREBOARD_DIR / "scoreboard.json"
MAX_RECENT_MATCHES = 6
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
class RecentMatchRecord:
    """Compact persistent summary for one completed match."""

    finished_at: str
    mode_label: str
    result_label: str
    move_count: int = 0

    def summary(self) -> str:
        """Return a one-line summary suitable for the welcome/result screens."""
        move_text = ""
        if self.move_count > 0:
            noun = "move" if self.move_count == 1 else "moves"
            move_text = f" | {self.move_count} {noun}"
        return f"{self.finished_at} | {self.mode_label} | {self.result_label}{move_text}"


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
    recent_matches: list[RecentMatchRecord] = None

    def copy(self) -> "Scoreboard":
        """Return a plain mutable copy."""
        return Scoreboard(
            total_games=self.total_games,
            local_games=self.local_games,
            ai_games=self.ai_games,
            white_wins=self.white_wins,
            black_wins=self.black_wins,
            draws=self.draws,
            human_wins=self.human_wins,
            human_losses=self.human_losses,
            human_draws=self.human_draws,
            ranking_points=self.ranking_points,
            current_streak=self.current_streak,
            best_streak=self.best_streak,
            recent_matches=[
                RecentMatchRecord(
                    finished_at=entry.finished_at,
                    mode_label=entry.mode_label,
                    result_label=entry.result_label,
                    move_count=entry.move_count,
                )
                for entry in (self.recent_matches or [])
            ],
        )

    def __post_init__(self) -> None:
        """Normalize mutable defaults when loading or creating a scoreboard."""
        if self.recent_matches is None:
            self.recent_matches = []


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
    return {
        "total_games": scoreboard.total_games,
        "local_games": scoreboard.local_games,
        "ai_games": scoreboard.ai_games,
        "white_wins": scoreboard.white_wins,
        "black_wins": scoreboard.black_wins,
        "draws": scoreboard.draws,
        "human_wins": scoreboard.human_wins,
        "human_losses": scoreboard.human_losses,
        "human_draws": scoreboard.human_draws,
        "ranking_points": scoreboard.ranking_points,
        "current_streak": scoreboard.current_streak,
        "best_streak": scoreboard.best_streak,
        "recent_matches": [
            {
                "finished_at": entry.finished_at,
                "mode_label": entry.mode_label,
                "result_label": entry.result_label,
                "move_count": entry.move_count,
            }
            for entry in scoreboard.recent_matches
        ],
    }


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

    recent_matches = data.get("recent_matches", [])
    if not isinstance(recent_matches, list):
        raise ValueError("Saved scoreboard data is invalid.")

    parsed_recent_matches: list[RecentMatchRecord] = []
    for entry in recent_matches[:MAX_RECENT_MATCHES]:
        if not isinstance(entry, dict):
            raise ValueError("Saved scoreboard data is invalid.")

        finished_at = entry.get("finished_at", "")
        mode_label = entry.get("mode_label", "")
        result_label = entry.get("result_label", "")
        move_count = entry.get("move_count", 0)

        if (
            not isinstance(finished_at, str)
            or not isinstance(mode_label, str)
            or not isinstance(result_label, str)
            or not isinstance(move_count, int)
            or move_count < 0
        ):
            raise ValueError("Saved scoreboard data is invalid.")

        parsed_recent_matches.append(
            RecentMatchRecord(
                finished_at=finished_at,
                mode_label=mode_label,
                result_label=result_label,
                move_count=move_count,
            )
        )

    return Scoreboard(**values, recent_matches=parsed_recent_matches)


def _build_recent_match_record(
    match: MatchState,
    mode: str,
    human_color: str,
    finished_at: str,
) -> RecentMatchRecord:
    """Build one concise recent-match entry from the completed match state."""
    if mode == "ai_vs_ai":
        mode_label = "AI vs AI"
    elif mode == "ai":
        mode_label = "Vs AI"
    else:
        mode_label = "Local"
    move_count = (len(match.move_history) + 1) // 2

    if match.is_draw:
        result_label = "Draw"
    elif mode == "ai_vs_ai" and match.winner in {"white", "black"}:
        result_label = f"{match.winner.title()} AI won"
    elif mode == "ai":
        if match.winner == human_color:
            result_label = f"You won as {human_color.title()}"
        else:
            result_label = f"Computer won as {match.winner.title()}"
    elif match.winner in {"white", "black"}:
        result_label = f"{match.winner.title()} won"
    else:
        result_label = "Match ended"

    return RecentMatchRecord(
        finished_at=finished_at,
        mode_label=mode_label,
        result_label=result_label,
        move_count=move_count,
    )


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
    finished_at: str | None = None,
) -> Scoreboard:
    """Return updated persistent stats for one finished match."""
    updated = scoreboard.copy()
    updated.total_games += 1
    if finished_at is None:
        finished_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    if mode in {"ai", "ai_vs_ai"}:
        updated.ai_games += 1
    else:
        updated.local_games += 1

    if match.is_draw:
        updated.draws += 1
        if mode == "ai":
            updated.human_draws += 1
            updated.ranking_points += 1
            updated.current_streak = 0
        updated.recent_matches.insert(
            0,
            _build_recent_match_record(match, mode, human_color, finished_at),
        )
        updated.recent_matches = updated.recent_matches[:MAX_RECENT_MATCHES]
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

    updated.recent_matches.insert(
        0,
        _build_recent_match_record(match, mode, human_color, finished_at),
    )
    updated.recent_matches = updated.recent_matches[:MAX_RECENT_MATCHES]
    return updated
