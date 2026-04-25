from __future__ import annotations

# game/nn_model.py
# Chess Project - tiny dependency-free neural evaluator

"""
A small feedforward network for scoring chess positions.

The evaluator intentionally avoids third-party dependencies so the desktop app
and tests keep running in a fresh Python install. It can still be trained with
simple supervised examples and persisted as JSON weights.
"""

import json
import math
import random
from pathlib import Path

from game.encoding import ENCODED_STATE_SIZE


Vector = list[float]
Matrix = list[list[float]]


class TinyChessNet:
    """A tiny 70 -> 64 -> 32 -> 1 tanh evaluator."""

    def __init__(
        self,
        input_size: int = ENCODED_STATE_SIZE,
        hidden1: int = 64,
        hidden2: int = 32,
        seed: int = 42,
    ) -> None:
        self.input_size = input_size
        self.hidden1 = hidden1
        self.hidden2 = hidden2
        rng = random.Random(seed)
        self.W1 = self._random_matrix(rng, input_size, hidden1)
        self.b1 = [0.0 for _ in range(hidden1)]
        self.W2 = self._random_matrix(rng, hidden1, hidden2)
        self.b2 = [0.0 for _ in range(hidden2)]
        self.W3 = self._random_matrix(rng, hidden2, 1)
        self.b3 = [0.0]

    @staticmethod
    def _random_matrix(rng: random.Random, rows: int, cols: int) -> Matrix:
        return [[rng.gauss(0.0, 0.05) for _ in range(cols)] for _ in range(rows)]

    @staticmethod
    def _matvec(vector: Vector, weights: Matrix, bias: Vector) -> Vector:
        return [
            bias[col] + sum(vector[row] * weights[row][col] for row in range(len(vector)))
            for col in range(len(bias))
        ]

    @staticmethod
    def _relu(vector: Vector) -> Vector:
        return [max(0.0, value) for value in vector]

    @staticmethod
    def _relu_derivative(vector: Vector) -> Vector:
        return [1.0 if value > 0.0 else 0.0 for value in vector]

    def _forward_details(self, features: Vector) -> dict[str, Vector]:
        if len(features) != self.input_size:
            raise ValueError(f"Expected {self.input_size} features, got {len(features)}.")

        z1 = self._matvec(features, self.W1, self.b1)
        a1 = self._relu(z1)
        z2 = self._matvec(a1, self.W2, self.b2)
        a2 = self._relu(z2)
        z3 = self._matvec(a2, self.W3, self.b3)
        y = [math.tanh(z3[0])]
        return {"x": features, "z1": z1, "a1": a1, "z2": z2, "a2": a2, "z3": z3, "y": y}

    def forward(self, features: Vector) -> float:
        """Return a white-positive score in [-1, 1]."""
        return self._forward_details(features)["y"][0]

    def predict(self, features: Vector) -> float:
        """Return a white-positive score in [-1, 1]."""
        return self.forward(features)

    def train_step(self, features: Vector, target: float, lr: float = 0.001) -> float:
        """Run one gradient-descent step and return squared error loss."""
        target = max(-1.0, min(1.0, float(target)))
        cache = self._forward_details(features)
        y = cache["y"][0]
        error = y - target
        dz3 = 2.0 * error * (1.0 - (y * y))

        old_W3 = [row[:] for row in self.W3]
        old_W2 = [row[:] for row in self.W2]

        for row, a2_value in enumerate(cache["a2"]):
            self.W3[row][0] -= lr * a2_value * dz3
        self.b3[0] -= lr * dz3

        dz2: Vector = []
        relu2 = self._relu_derivative(cache["z2"])
        for index in range(self.hidden2):
            dz2.append(dz3 * old_W3[index][0] * relu2[index])

        for row, a1_value in enumerate(cache["a1"]):
            for col, dz2_value in enumerate(dz2):
                self.W2[row][col] -= lr * a1_value * dz2_value
        for col, dz2_value in enumerate(dz2):
            self.b2[col] -= lr * dz2_value

        relu1 = self._relu_derivative(cache["z1"])
        dz1: Vector = []
        for index in range(self.hidden1):
            downstream = sum(dz2[col] * old_W2[index][col] for col in range(self.hidden2))
            dz1.append(downstream * relu1[index])

        for row, feature_value in enumerate(cache["x"]):
            for col, dz1_value in enumerate(dz1):
                self.W1[row][col] -= lr * feature_value * dz1_value
        for col, dz1_value in enumerate(dz1):
            self.b1[col] -= lr * dz1_value

        return error * error

    def to_data(self) -> dict[str, object]:
        """Return JSON-safe model weights."""
        return {
            "input_size": self.input_size,
            "hidden1": self.hidden1,
            "hidden2": self.hidden2,
            "W1": self.W1,
            "b1": self.b1,
            "W2": self.W2,
            "b2": self.b2,
            "W3": self.W3,
            "b3": self.b3,
        }

    def save(self, path: str | Path) -> None:
        """Save model weights as JSON."""
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(self.to_data()), encoding="utf-8")

    def load(self, path: str | Path) -> None:
        """Load model weights from JSON into this instance."""
        loaded = self.from_file(path)
        self.__dict__.update(loaded.__dict__)

    @classmethod
    def from_data(cls, data: dict[str, object]) -> "TinyChessNet":
        """Create a model from JSON-safe weights."""
        model = cls(
            input_size=int(data["input_size"]),
            hidden1=int(data["hidden1"]),
            hidden2=int(data["hidden2"]),
        )
        model.W1 = data["W1"]  # type: ignore[assignment]
        model.b1 = data["b1"]  # type: ignore[assignment]
        model.W2 = data["W2"]  # type: ignore[assignment]
        model.b2 = data["b2"]  # type: ignore[assignment]
        model.W3 = data["W3"]  # type: ignore[assignment]
        model.b3 = data["b3"]  # type: ignore[assignment]
        return model

    @classmethod
    def from_file(cls, path: str | Path) -> "TinyChessNet":
        """Load a model from a JSON weight file."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Model file is invalid.")
        return cls.from_data(data)
