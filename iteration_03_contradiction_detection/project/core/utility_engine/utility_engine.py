"""
Minor Project One - Utility Engine.

Phase 5 estimates whether information may have useful value
even when similar information exists elsewhere.

This engine does not delete or modify dataset content.
"""

from __future__ import annotations

from collections import Counter

from core.information_extractor.extraction_result import (
    ExtractionResult,
)


class UtilityEngine:
    """
    Calculate a preliminary utility-protection score.
    """

    def calculate_score(
        self,
        extraction: ExtractionResult,
        frequency: int,
    ) -> float:
        """
        Calculate a utility score between 0 and 1.

        Higher utility means the information should receive
        stronger protection against later removal.
        """

        # Begin with a neutral utility level.
        score = 0.50

        # Specific numeric/value-bearing information receives
        # additional protection.
        if extraction.values:
            score += 0.20

        # Temporal information may provide additional context.
        if extraction.dates:
            score += 0.10

        # Named entities increase contextual specificity when available.
        if extraction.entities:
            score += 0.10

        # Rare information receives an additional protection signal.
        if frequency <= 2:
            score += 0.10

        # Prevent the score from exceeding the valid maximum.
        return min(1.0, score)

    def calculate_many(
        self,
        extractions: list[ExtractionResult],
    ) -> dict[str, float]:
        """
        Calculate utility scores for all extracted information units.
        """

        # Count exact textual occurrences in a case-insensitive manner.
        frequencies = Counter(
            extraction.text.strip().lower()
            for extraction in extractions
        )

        # Store the calculated score for each information-unit ID.
        results: dict[str, float] = {}

        # Process every extracted information unit.
        for extraction in extractions:

            # Retrieve this information unit's frequency.
            frequency = frequencies[
                extraction.text.strip().lower()
            ]

            # Calculate and save its utility score.
            results[
                extraction.information_unit_id
            ] = self.calculate_score(
                extraction,
                frequency,
            )

        return results