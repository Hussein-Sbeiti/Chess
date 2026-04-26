"""Small pure-Python neural evaluator used by the chess AI."""
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
# Matrices are stored as row-major nested Python lists.
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
        # Layer sizes are stored so saved models can validate compatible input.
        self.input_size = input_size
        self.hidden1 = hidden1
        self.hidden2 = hidden2
        # Deterministic initialization makes tests and fresh fallback models repeatable.
        rng = random.Random(seed)
        # Weight/bias naming follows the three-layer feedforward layout.
        self.W1 = self._random_matrix(rng, input_size, hidden1)
        self.b1 = [0.0 for _ in range(hidden1)]
        self.W2 = self._random_matrix(rng, hidden1, hidden2)
        self.b2 = [0.0 for _ in range(hidden2)]
        self.W3 = self._random_matrix(rng, hidden2, 1)
        self.b3 = [0.0]

    @staticmethod
    def _random_matrix(rng: random.Random, rows: int, cols: int) -> Matrix:
        """Create a deterministic random matrix for model initialization."""
        return [[rng.gauss(0.0, 0.05) for _ in range(cols)] for _ in range(rows)]

    @staticmethod
    def _matvec(vector: Vector, weights: Matrix, bias: Vector) -> Vector:
        """Multiply a matrix by a vector using plain Python lists."""
        return [
            bias[col] + sum(vector[row] * weights[row][col] for row in range(len(vector)))
            for col in range(len(bias))
        ]

    @staticmethod
    def _relu(vector: Vector) -> Vector:
        """Apply the ReLU activation function element by element."""
        return [max(0.0, value) for value in vector]

    @staticmethod
    def _relu_derivative(vector: Vector) -> Vector:
        """Return the derivative mask for ReLU activations."""
        return [1.0 if value > 0.0 else 0.0 for value in vector]

    def _forward_details(self, features: Vector) -> dict[str, Vector]:
        """Return intermediate layer values needed for prediction and training."""
        # Training math assumes the feature vector matches the model input layer.
        if len(features) != self.input_size:
            raise ValueError(f"Expected {self.input_size} features, got {len(features)}.")

        # Forward pass: input -> ReLU hidden layer -> ReLU hidden layer -> tanh output.
        z1 = self._matvec(features, self.W1, self.b1)
        a1 = self._relu(z1)
        z2 = self._matvec(a1, self.W2, self.b2)
        a2 = self._relu(z2)
        z3 = self._matvec(a2, self.W3, self.b3)
        # tanh keeps the chess score bounded between black-winning and white-winning.
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
        # Clamp labels into the same range as the tanh output.
        target = max(-1.0, min(1.0, float(target)))
        cache = self._forward_details(features)
        y = cache["y"][0]
        # Squared-error derivative through tanh output.
        error = y - target
        dz3 = 2.0 * error * (1.0 - (y * y))

        # Preserve old downstream weights for backprop before mutating them.
        old_W3 = [row[:] for row in self.W3]
        old_W2 = [row[:] for row in self.W2]

        # Update output layer weights and bias.
        for row, a2_value in enumerate(cache["a2"]):
            self.W3[row][0] -= lr * a2_value * dz3
        self.b3[0] -= lr * dz3

        dz2: Vector = []
        relu2 = self._relu_derivative(cache["z2"])
        # Backpropagate output gradient into the second hidden layer.
        for index in range(self.hidden2):
            dz2.append(dz3 * old_W3[index][0] * relu2[index])

        # Update second hidden layer weights and biases.
        for row, a1_value in enumerate(cache["a1"]):
            for col, dz2_value in enumerate(dz2):
                self.W2[row][col] -= lr * a1_value * dz2_value
        for col, dz2_value in enumerate(dz2):
            self.b2[col] -= lr * dz2_value

        relu1 = self._relu_derivative(cache["z1"])
        dz1: Vector = []
        # Backpropagate through the first hidden layer.
        for index in range(self.hidden1):
            downstream = sum(dz2[col] * old_W2[index][col] for col in range(self.hidden2))
            dz1.append(downstream * relu1[index])

        # Update input-to-hidden weights and first-layer biases.
        for row, feature_value in enumerate(cache["x"]):
            for col, dz1_value in enumerate(dz1):
                self.W1[row][col] -= lr * feature_value * dz1_value
        for col, dz1_value in enumerate(dz1):
            self.b1[col] -= lr * dz1_value

        return error * error

    def to_data(self) -> dict[str, object]:
        """Return JSON-safe model weights."""
        # JSON stores architecture and raw numeric weights together.
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
        # Create parent directories so first-time training can write models/.
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(self.to_data()), encoding="utf-8")

    def load(self, path: str | Path) -> None:
        """Load model weights from JSON into this instance."""
        # Replace this instance in-place so existing references keep working.
        loaded = self.from_file(path)
        self.__dict__.update(loaded.__dict__)

    @classmethod
    def from_data(cls, data: dict[str, object]) -> "TinyChessNet":
        """Create a model from JSON-safe weights."""
        # Build the architecture first, then replace initialized weights with saved values.
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
        # Parse JSON before validating that the root object is a dictionary.
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Model file is invalid.")
        return cls.from_data(data)
