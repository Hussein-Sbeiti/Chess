"""Self-play helpers for generating chess training examples."""
from __future__ import annotations


# game/self_play.py
# Chess Project - simple self-play data generation

from copy import deepcopy
from typing import Callable

from game.ai import apply_simulated_move
from game.game_models import MatchState


# Move functions return origin, target, and optional promotion choice.
MoveFn = Callable[[MatchState], tuple[tuple[int, int], tuple[int, int], str | None] | None]


def play_self_play_game(
    start_state_factory: Callable[[], MatchState],
    white_move_fn: MoveFn,
    black_move_fn: MoveFn,
    max_turns: int = 200,
) -> tuple[list[MatchState], float]:
    """Play one AI-vs-AI game and return seen positions plus final result."""
    # Start from a factory so callers can supply fresh or customized positions.
    state = start_state_factory()
    history: list[MatchState] = []

    for _ in range(max_turns):
        # Stop when normal chess rules have already ended the match.
        if state.winner or state.is_draw:
            break
        # Store a copy before the move so the training example describes the decision point.
        history.append(deepcopy(state))
        # Dispatch to the move function for the side whose turn it currently is.
        move = white_move_fn(state) if state.current_turn == "white" else black_move_fn(state)
        if move is None:
            break
        # Simulate on a copied state so previous history entries remain unchanged.
        state = apply_simulated_move(state, move)

    # Training targets are from White's perspective: win=1, loss=-1, draw=0.
    if state.winner == "white":
        result = 1.0
    elif state.winner == "black":
        result = -1.0
    else:
        result = 0.0
    return history, result
