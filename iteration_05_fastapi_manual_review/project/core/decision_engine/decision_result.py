"""
Minor Project One - Decision Result.

Stores the final Phase 7 decision for one information pair.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class DecisionResult:
    """
    Store one Phase 7 decision.

    The decision engine can recommend:
        KEEP
        REMOVE
        REVIEW

    REMOVE is only a recommendation at this stage.
    Actual dataset modification belongs to Phase 8.
    """

    information_unit_id_a: str
    information_unit_id_b: str

    text_a: str
    text_b: str

    similarity_score: float
    utility_score_a: float
    utility_score_b: float
    rarity_score_a: float
    rarity_score_b: float

    contradiction_detected: bool

    decision: str
    confidence: float
    reason: str

    def __post_init__(self) -> None:
        """
        Validate the decision result.
        """

        # Both information-unit IDs must exist.
        if not self.information_unit_id_a.strip():
            raise ValueError(
                "information_unit_id_a cannot be empty."
            )

        if not self.information_unit_id_b.strip():
            raise ValueError(
                "information_unit_id_b cannot be empty."
            )

        # A unit cannot be compared with itself.
        if (
            self.information_unit_id_a
            == self.information_unit_id_b
        ):
            raise ValueError(
                "A decision pair cannot contain the same unit twice."
            )

        # Both source sentences must be present.
        if not self.text_a.strip():
            raise ValueError(
                "text_a cannot be empty."
            )

        if not self.text_b.strip():
            raise ValueError(
                "text_b cannot be empty."
            )

        # Validate every numerical score.
        self.similarity_score = self._validate_score(
            self.similarity_score,
            "similarity_score",
        )

        self.utility_score_a = self._validate_score(
            self.utility_score_a,
            "utility_score_a",
        )

        self.utility_score_b = self._validate_score(
            self.utility_score_b,
            "utility_score_b",
        )

        self.rarity_score_a = self._validate_score(
            self.rarity_score_a,
            "rarity_score_a",
        )

        self.rarity_score_b = self._validate_score(
            self.rarity_score_b,
            "rarity_score_b",
        )

        self.confidence = self._validate_score(
            self.confidence,
            "confidence",
        )

        # Only the three supported decision values are allowed.
        allowed_decisions = {
            "KEEP",
            "REMOVE",
            "REVIEW",
        }

        if self.decision not in allowed_decisions:
            raise ValueError(
                "decision must be KEEP, REMOVE, or REVIEW."
            )

        # Ensure contradiction_detected is actually boolean.
        if not isinstance(
            self.contradiction_detected,
            bool,
        ):
            raise TypeError(
                "contradiction_detected must be a boolean."
            )

        # A reason is required for auditability.
        if not self.reason.strip():
            raise ValueError(
                "reason cannot be empty."
            )

    @staticmethod
    def _validate_score(
        value: float,
        name: str,
    ) -> float:
        """
        Validate a score so it remains between 0 and 1.
        """

        # Convert the value into a float.
        score = float(value)

        # Reject invalid score ranges.
        if not 0.0 <= score <= 1.0:
            raise ValueError(
                f"{name} must be between 0.0 and 1.0."
            )

        return score

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the decision into a serializable dictionary.

        This will later support database storage, reports,
        APIs, auditing, and change logs.
        """

        return {
            "information_unit_id_a": self.information_unit_id_a,
            "information_unit_id_b": self.information_unit_id_b,
            "text_a": self.text_a,
            "text_b": self.text_b,
            "similarity_score": self.similarity_score,
            "utility_score_a": self.utility_score_a,
            "utility_score_b": self.utility_score_b,
            "rarity_score_a": self.rarity_score_a,
            "rarity_score_b": self.rarity_score_b,
            "contradiction_detected": self.contradiction_detected,
            "decision": self.decision,
            "confidence": self.confidence,
            "reason": self.reason,
        }