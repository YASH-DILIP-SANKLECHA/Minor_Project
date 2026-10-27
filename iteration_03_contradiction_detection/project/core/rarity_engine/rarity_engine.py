"""
Minor Project One - Rarity Engine.

Phase 5 calculates how rare each information unit is inside
the current dataset.

Rare information receives protection because rare does not mean
incorrect or unimportant.
"""

from __future__ import annotations

from collections import Counter

from core.information_extractor.extraction_result import (
    ExtractionResult,
)


class RarityEngine:
    """
    Calculate a preliminary rarity-protection score.
    """

    def calculate_score(
        self,
        frequency: int,
        total_units: int,
    ) -> float:
        """
        Convert occurrence frequency into a rarity score.

        A score of 1.0 represents maximum rarity protection in
        this preliminary Phase 5 implementation.
        """

        # The dataset must contain at least one information unit.
        if total_units <= 0:
            raise ValueError(
                "total_units must be greater than zero."
            )

        # Existing information must have a positive frequency.
        if frequency <= 0:
            raise ValueError(
                "frequency must be greater than zero."
            )

        # A single occurrence is maximally rare.
        if frequency == 1:
            return 1.0

        # Convert frequency into a fraction of the dataset.
        occurrence_rate = frequency / total_units

        # Higher occurrence means lower rarity.
        rarity = 1.0 - occurrence_rate

        # Keep the result within the 0-to-1 range.
        return max(
            0.0,
            min(1.0, rarity),
        )

    def calculate_many(
        self,
        extractions: list[ExtractionResult],
    ) -> dict[str, float]:
        """
        Calculate rarity scores for all information units.
        """

        # Count exact textual occurrences.
        frequencies = Counter(
            extraction.text.strip().lower()
            for extraction in extractions
        )

        # Store the total number of information units.
        total_units = len(extractions)

        # Store the score for each information-unit ID.
        results: dict[str, float] = {}

        # Calculate a rarity score for every unit.
        for extraction in extractions:

            # Retrieve this unit's occurrence frequency.
            frequency = frequencies[
                extraction.text.strip().lower()
            ]

            # Calculate and store its rarity score.
            results[
                extraction.information_unit_id
            ] = self.calculate_score(
                frequency,
                total_units,
            )

        return results