"""Computer move-selection strategies and AI difficulty helpers."""
from __future__ import annotations


# game/ai.py
# Chess Project - lightweight AI personalities
# Created: 2026-04-19

"""
This file provides simple computer-move selection for the chess app.

The goal is not to build a strong engine yet. Instead, it gives us three
distinct personalities that pick from legal moves in noticeably different ways.
"""

from copy import deepcopy
from pathlib import Path
import random

from game.board import piece_at
from game.coords import Coord
from game.encoding import encode_state
from game.nn_model import TinyChessNet
from game.rules import is_in_check, is_promotion_move, legal_moves_for_piece, make_move, other_color


AI_PERSONALITY_LABELS = {
    # These internal names are what the UI and saved app state store.
    "random": "Random",
    "aggressive": "Aggressive",
    "defensive": "Defensive",
    "neural": "Neural",
    "neural_search": "Neural Search",
}
AI_DIFFICULTY_LABELS = {
    # Difficulty labels are user-facing; personalities are implementation details.
    "easy": "Easy",
    "medium": "Medium",
    "hard": "Hard",
}
AI_DIFFICULTY_PERSONALITIES = {
    # Easy is intentionally simple, while harder levels use the evaluator model.
    "easy": "random",
    "medium": "neural",
    "hard": "neural_search",
}
PIECE_VALUES = {
    # Material values are rough heuristics for personality scoring and tie-breaks.
    "pawn": 1,
    "knight": 3,
    "bishop": 3,
    "rook": 5,
    "queen": 9,
    "king": 0,
}
# Saved weights are optional; the app can still run with deterministic fresh weights.
DEFAULT_MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "chess_eval_weights.json"
NEAR_BEST_SCORE_MARGIN = 0.01
_DEFAULT_MODEL: TinyChessNet | None = None


def normalize_ai_personality(personality: str) -> str:
    """Return a supported AI personality name."""
    return personality if personality in AI_PERSONALITY_LABELS else "random"


def normalize_ai_difficulty(difficulty: str) -> str:
    """Return a supported AI difficulty name."""
    return difficulty if difficulty in AI_DIFFICULTY_LABELS else "easy"


def ai_personality_for_difficulty(difficulty: str) -> str:
    """Return the move-selection strategy used by one difficulty level."""
    return AI_DIFFICULTY_PERSONALITIES[normalize_ai_difficulty(difficulty)]


def ai_difficulty_for_personality(personality: str) -> str:
    """Map legacy personality saves to the closest current difficulty."""
    # Older saves stored personalities directly, so translate them into the newer UI levels.
    normalized = normalize_ai_personality(personality)
    if normalized == "neural_search":
        return "hard"
    if normalized == "neural":
        return "medium"
    return "easy"


def _promotion_choice_for_move(state, origin: Coord, target: Coord) -> str | None:
    """Return the AI's promotion choice for a move when needed."""
    # Keep AI promotion simple and strong by always choosing a queen.
    if is_promotion_move(state.board, origin, target):
        return "queen"
    return None


def all_legal_moves(state, color: str) -> list[tuple[Coord, Coord, str | None]]:
    """Collect every legal move available for one side."""
    moves: list[tuple[Coord, Coord, str | None]] = []
    # Scan every square because the board model is intentionally just a simple grid.
    for row in range(8):
        for col in range(8):
            piece = state.board[row][col]
            # Skip empty squares and enemy pieces.
            if piece is None or piece.color != color:
                continue
            origin = (row, col)
            # legal_moves_for_piece filters out moves that would leave the king in check.
            for target in legal_moves_for_piece(state, origin):
                moves.append((origin, target, _promotion_choice_for_move(state, origin, target)))
    return moves


def choose_random_move(state, color: str) -> tuple[Coord, Coord, str | None] | None:
    """Pick any legal move for one side."""
    # Returning None lets callers handle checkmate/stalemate/no-move states.
    legal_moves = all_legal_moves(state, color)
    if not legal_moves:
        return None
    return random.choice(legal_moves)


def get_default_model() -> TinyChessNet:
    """Return the saved evaluator when available, otherwise a deterministic fresh model."""
    global _DEFAULT_MODEL
    # Cache the model so repeated AI moves do not reload weights from disk.
    if _DEFAULT_MODEL is None:
        _DEFAULT_MODEL = TinyChessNet()
        if DEFAULT_MODEL_PATH.exists():
            _DEFAULT_MODEL.load(DEFAULT_MODEL_PATH)
    return _DEFAULT_MODEL


def evaluate_with_model(state, model: TinyChessNet, perspective: str = "white") -> float:
    """Score a position from one side's perspective."""
    # TinyChessNet scores from White's perspective, so black perspective flips the sign.
    score = model.predict(encode_state(state))
    return score if perspective == "white" else -score


def _terminal_score(state, perspective: str) -> float | None:
    """Return a true game-result score for terminal states, or None for ongoing play."""
    if state.is_draw:
        return 0.0
    if state.winner == perspective:
        return 1_000_000.0
    if state.winner in {"white", "black"}:
        return -1_000_000.0
    return None


def _position_score(state, color: str, model: TinyChessNet) -> float:
    """Score a position for AI search, respecting completed game results first."""
    terminal_score = _terminal_score(state, color)
    if terminal_score is not None:
        return terminal_score
    score = evaluate_with_model(state, model, perspective=color)
    score += 0.05 * _material_score_for_color(state, color)
    return score


def _choose_near_best_move(
    scored_moves: list[tuple[float, tuple[Coord, Coord, str | None]]],
    margin: float = NEAR_BEST_SCORE_MARGIN,
) -> tuple[Coord, Coord, str | None] | None:
    """Choose randomly among moves whose scores are very close to the best score."""
    if not scored_moves:
        return None

    best_score = max(score for score, _move in scored_moves)
    cutoff = best_score - margin
    # Preserve clearly superior moves, but avoid replaying the same tiny-score preference forever.
    near_best_moves = [move for score, move in scored_moves if score >= cutoff]
    return random.choice(near_best_moves)


def apply_simulated_move(state, move: tuple[Coord, Coord, str | None]):
    """Return a copied state after applying a legal move."""
    # Simulations must not mutate the real game state while the AI searches.
    origin, target, promotion_choice = move
    simulated_state = deepcopy(state)
    success, _message = make_move(simulated_state, origin, target, promotion_choice=promotion_choice)
    # all_legal_moves should prevent this, so an illegal simulation is a programming error.
    if not success:
        raise ValueError("Cannot simulate illegal move.")
    return simulated_state


def _material_score_for_color(state, color: str) -> float:
    """Return a small material fallback score from one side's perspective."""
    score = 0.0
    # Positive score means the requested color is ahead in material.
    for row in state.board:
        for piece in row:
            if piece is None:
                continue
            value = PIECE_VALUES.get(piece.kind, 0)
            score += value if piece.color == color else -value
    # Normalize into roughly the same small range as the neural evaluator.
    return max(-1.0, min(1.0, score / 20.0))


def choose_nn_move(state, color: str, model: TinyChessNet | None = None) -> tuple[Coord, Coord, str | None] | None:
    """Choose the legal move whose resulting position the evaluator likes best."""
    model = model or get_default_model()
    legal_moves = all_legal_moves(state, color)
    if not legal_moves:
        return None

    scored_moves: list[tuple[float, tuple[Coord, Coord, str | None]]] = []
    for move in legal_moves:
        # Evaluate the board after the candidate move, not the current board.
        simulated_state = apply_simulated_move(state, move)
        # Completed games use real result scores; ongoing games use model + material.
        score = _position_score(simulated_state, color, model)
        scored_moves.append((score, move))

    return _choose_near_best_move(scored_moves)


def minimax_nn(
    state,
    depth: int,
    alpha: float,
    beta: float,
    maximizing_color: str,
    model: TinyChessNet,
    current_color: str,
) -> tuple[float, tuple[Coord, Coord, str | None] | None]:
    """Run a shallow alpha-beta search using the evaluator at leaf nodes."""
    terminal_score = _terminal_score(state, maximizing_color)
    if terminal_score is not None:
        return terminal_score, None

    # Leaf nodes are scored directly by the neural evaluator plus the material fallback.
    if depth == 0:
        return _position_score(state, maximizing_color, model), None

    legal_moves = all_legal_moves(state, current_color)
    if not legal_moves:
        # No legal moves means the state is terminal or effectively terminal for search.
        return _position_score(state, maximizing_color, model), None

    next_color = other_color(current_color)
    if current_color == maximizing_color:
        # Maximizing side tries to raise the evaluation score.
        best_score = float("-inf")
        best_move = None
        for move in legal_moves:
            score, _ = minimax_nn(
                apply_simulated_move(state, move),
                depth - 1,
                alpha,
                beta,
                maximizing_color,
                model,
                next_color,
            )
            if score > best_score:
                best_score = score
                best_move = move
            # Alpha-beta pruning skips branches that cannot improve the result.
            alpha = max(alpha, best_score)
            if beta <= alpha:
                break
        return best_score, best_move

    # Opponent tries to lower the maximizing side's score.
    best_score = float("inf")
    best_move = None
    for move in legal_moves:
        score, _ = minimax_nn(
            apply_simulated_move(state, move),
            depth - 1,
            alpha,
            beta,
            maximizing_color,
            model,
            next_color,
        )
        if score < best_score:
            best_score = score
            best_move = move
        # Beta cutoff mirrors the maximizing branch's alpha cutoff.
        beta = min(beta, best_score)
        if beta <= alpha:
            break
    return best_score, best_move


def choose_nn_search_move(
    state,
    color: str,
    model: TinyChessNet | None = None,
    depth: int = 2,
) -> tuple[Coord, Coord, str | None] | None:
    """Choose a move with a shallow neural evaluator search."""
    # Depth is clamped to at least 1 so the function always examines legal moves.
    model = model or get_default_model()
    search_depth = max(1, depth)
    legal_moves = all_legal_moves(state, color)
    if not legal_moves:
        return None

    scored_moves: list[tuple[float, tuple[Coord, Coord, str | None]]] = []
    for move in legal_moves:
        # Score each root move separately so near-equal root choices can vary naturally.
        simulated_state = apply_simulated_move(state, move)
        score, _reply = minimax_nn(
            state=simulated_state,
            depth=search_depth - 1,
            alpha=float("-inf"),
            beta=float("inf"),
            maximizing_color=color,
            model=model,
            current_color=other_color(color),
        )
        scored_moves.append((score, move))

    return _choose_near_best_move(scored_moves)


def _captured_piece_value(state, origin: Coord, target: Coord) -> int:
    """Return the material value gained by moving to the target square."""
    # Normal captures are visible on the target square.
    moving_piece = piece_at(state.board, origin)
    captured_piece = piece_at(state.board, target)
    # En-passant captures land on an empty target square, so inspect the pawn behind it.
    if captured_piece is None and moving_piece is not None and moving_piece.kind == "pawn" and origin[1] != target[1]:
        capture_square = (origin[0], target[1])
        captured_piece = piece_at(state.board, capture_square)
    if captured_piece is None:
        return 0
    return PIECE_VALUES.get(captured_piece.kind, 0)


def _attacked_material(board, color: str) -> int:
    """Estimate how much of one side's material is currently under attack."""
    enemy_color = other_color(color)
    score = 0
    # Sum the value of friendly pieces currently attacked by the opponent.
    for row in range(8):
        for col in range(8):
            piece = board[row][col]
            if piece is None or piece.color != color:
                continue
            square = (row, col)
            # Local import avoids a top-level cycle with game.rules.
            from game.rules import is_square_attacked

            if is_square_attacked(board, square, enemy_color):
                score += PIECE_VALUES.get(piece.kind, 0)
    return score


def _score_move_for_personality(state, color: str, move, personality: str) -> int:
    """Score one legal move according to the chosen AI personality."""
    origin, target, promotion_choice = move
    # Score against the resulting position so checks, mate, and safety are visible.
    simulated_state = deepcopy(state)
    success, _ = make_move(simulated_state, origin, target, promotion_choice=promotion_choice)
    if not success:
        return -10_000

    # Shared tactical inputs used by both handcrafted personalities.
    capture_value = _captured_piece_value(state, origin, target)
    moving_piece = piece_at(state.board, origin)
    promotion_bonus = 8 if promotion_choice == "queen" else 0

    if simulated_state.winner == color:
        return 100_000

    # Checking the opponent is useful for aggressive and defensive play.
    enemy_color = other_color(color)
    check_bonus = 30 if is_in_check(simulated_state.board, enemy_color) else 0

    if personality == "aggressive":
        # Aggressive play values captures, promotions, and checks.
        return (capture_value * 25) + (promotion_bonus * 3) + check_bonus

    if personality == "defensive":
        # Defensive play still captures, but heavily penalizes exposed material.
        moved_piece_risk = 0
        # Local import avoids a top-level cycle with game.rules.
        from game.rules import is_square_attacked

        if moving_piece is not None and is_square_attacked(simulated_state.board, target, enemy_color):
            moved_piece_risk = PIECE_VALUES.get(moving_piece.kind, 0)
        attacked_material_penalty = _attacked_material(simulated_state.board, color)
        return (capture_value * 8) + promotion_bonus + check_bonus - (attacked_material_penalty * 6) - (moved_piece_risk * 10)

    return 0


def choose_ai_move(state, color: str, personality: str = "random") -> tuple[Coord, Coord, str | None] | None:
    """Pick one legal move for the computer player."""
    # Normalize saved/user input before dispatching to a strategy.
    personality = normalize_ai_personality(personality)
    if personality == "random":
        return choose_random_move(state, color)
    if personality == "neural":
        return choose_nn_move(state, color)
    if personality == "neural_search":
        return choose_nn_search_move(state, color, depth=2)

    legal_moves = all_legal_moves(state, color)
    if not legal_moves:
        return None

    # Handcrafted personalities score all legal moves and randomly choose among ties.
    best_score: int | None = None
    best_moves: list[tuple[Coord, Coord, str | None]] = []
    for move in legal_moves:
        score = _score_move_for_personality(state, color, move, personality)
        if best_score is None or score > best_score:
            best_score = score
            best_moves = [move]
        elif score == best_score:
            best_moves.append(move)

    return random.choice(best_moves)


def choose_ai_move_for_difficulty(
    state,
    color: str,
    difficulty: str = "easy",
) -> tuple[Coord, Coord, str | None] | None:
    """Pick one legal move using the configured AI difficulty."""
    return choose_ai_move(state, color, ai_personality_for_difficulty(difficulty))
