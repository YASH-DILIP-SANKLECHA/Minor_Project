"""
Minor Project One - Scoring Engine.

Phase 5 combines:
- semantic similarity
- utility protection
- rarity protection

The result is a preliminary redundancy score.

This module does NOT perform KEEP/REMOVE/REVIEW decisions.
"""

from __future__ import annotations


class ScoringEngine:
    """
    Calculate a combined preliminary redundancy score.
    """

    # Semantic similarity is intentionally the dominant signal.
    SIMILARITY_WEIGHT = 0.60

    # Utility protects information that may be valuable.
    UTILITY_WEIGHT = 0.25

    # Rarity protects information that appears infrequently.
    RARITY_WEIGHT = 0.15

    def calculate_score(
        self,
        similarity_score: float,
        utility_score_a: float,
        utility_score_b: float,
        rarity_score_a: float,
        rarity_score_b: float,
    ) -> float:
        """
        Calculate a combined redundancy score for two information units.

        Higher semantic similarity increases redundancy.

        Higher utility and rarity reduce the score because valuable
        or rare information should be protected.
        """

        # Validate the semantic similarity.
        similarity_score = self._validate_score(
            similarity_score,
            "similarity_score",
        )

        # Validate utility of the first information unit.
        utility_score_a = self._validate_score(
            utility_score_a,
            "utility_score_a",
        )

        # Validate utility of the second information unit.
        utility_score_b = self._validate_score(
            utility_score_b,
            "utility_score_b",
        )

        # Validate rarity of the first information unit.
        rarity_score_a = self._validate_score(
            rarity_score_a,
            "rarity_score_a",
        )

        # Validate rarity of the second information unit.
        rarity_score_b = self._validate_score(
            rarity_score_b,
            "rarity_score_b",
        )

        # Use the stronger utility protection of the two units.
        utility_protection = max(
            utility_score_a,
            utility_score_b,
        )

        # Use the stronger rarity protection of the two units.
        rarity_protection = max(
            rarity_score_a,
            rarity_score_b,
        )

        # Combine similarity with protection signals.
        score = (
            self.SIMILARITY_WEIGHT * similarity_score
            + self.UTILITY_WEIGHT * (1.0 - utility_protection)
            + self.RARITY_WEIGHT * (1.0 - rarity_protection)
        )

        # Keep the final score inside the valid range.
        return max(
            0.0,
            min(1.0, score),
        )

    @staticmethod
    def _validate_score(
        value: float,
        name: str,
    ) -> float:
        """
        Validate that an input score is between 0 and 1.
        """

        # Convert the supplied value to a float.
        score = float(value)

        # Reject values outside the valid score range.
        if not 0.0 <= score <= 1.0:
            raise ValueError(
                f"{name} must be between 0.0 and 1.0."
            )

        return score