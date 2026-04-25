from __future__ import annotations

# game/self_play.py
# Chess Project - simple self-play data generation

from copy import deepcopy
from typing import Callable

from game.ai import apply_simulated_move
from game.game_models import MatchState


MoveFn = Callable[[MatchState], tuple[tuple[int, int], tuple[int, int], str | None] | None]


def play_self_play_game(
    start_state_factory: Callable[[], MatchState],
    white_move_fn: MoveFn,
    black_move_fn: MoveFn,
    max_turns: int = 200,
) -> tuple[list[MatchState], float]:
    """Play one AI-vs-AI game and return seen positions plus final result."""
    state = start_state_factory()
    history: list[MatchState] = []

    for _ in range(max_turns):
        if state.winner or state.is_draw:
            break
        history.append(deepcopy(state))
        move = white_move_fn(state) if state.current_turn == "white" else black_move_fn(state)
        if move is None:
            break
        state = apply_simulated_move(state, move)

    if state.winner == "white":
        result = 1.0
    elif state.winner == "black":
        result = -1.0
    else:
        result = 0.0
    return history, result
