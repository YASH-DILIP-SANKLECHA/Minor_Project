"""
Minor Project One - Contradiction Result.

Stores the result of comparing two semantically similar
information units for possible contradiction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ContradictionResult:
    """
    Store one detected contradiction candidate.

    A contradiction candidate means that two statements are
    semantically related but appear to contain conflicting
    factual values.
    """

    information_unit_id_a: str
    information_unit_id_b: str
    text_a: str
    text_b: str

    similarity_score: float

    value_a: list[str] = field(default_factory=list)
    value_b: list[str] = field(default_factory=list)

    contradiction_score: float = 0.0
    reason: str = ""

    def __post_init__(self) -> None:
        """
        Validate the contradiction result.
        """

        # Ensure both information-unit IDs are present.
        if not self.information_unit_id_a.strip():
            raise ValueError(
                "information_unit_id_a cannot be empty."
            )

        if not self.information_unit_id_b.strip():
            raise ValueError(
                "information_unit_id_b cannot be empty."
            )

        # The same information unit cannot contradict itself.
        if (
            self.information_unit_id_a
            == self.information_unit_id_b
        ):
            raise ValueError(
                "A contradiction cannot contain the same "
                "information unit twice."
            )

        # Ensure both statements exist.
        if not self.text_a.strip():
            raise ValueError(
                "text_a cannot be empty."
            )

        if not self.text_b.strip():
            raise ValueError(
                "text_b cannot be empty."
            )

        # Similarity and contradiction scores must be valid.
        self.similarity_score = self._validate_score(
            self.similarity_score,
            "similarity_score",
        )

        self.contradiction_score = self._validate_score(
            self.contradiction_score,
            "contradiction_score",
        )

    @staticmethod
    def _validate_score(
        value: float,
        name: str,
    ) -> float:
        """
        Validate that a score lies between 0 and 1.
        """

        # Convert the supplied value into a float.
        score = float(value)

        # Reject invalid scores.
        if not 0.0 <= score <= 1.0:
            raise ValueError(
                f"{name} must be between 0.0 and 1.0."
            )

        return score

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the contradiction result into a dictionary.

        This will later make it easy to store the result in PostgreSQL
        and expose it through FastAPI.
        """

        return {
            "information_unit_id_a": self.information_unit_id_a,
            "information_unit_id_b": self.information_unit_id_b,
            "text_a": self.text_a,
            "text_b": self.text_b,
            "similarity_score": self.similarity_score,
            "value_a": self.value_a,
            "value_b": self.value_b,
            "contradiction_score": self.contradiction_score,
            "reason": self.reason,
        }