"""
Minor Project One - Contradiction Engine.

Phase 6 detects possible contradictions among information pairs
that Phase 3 has already identified as semantically similar.

Current deterministic Phase 6 logic:

    Similar information
          +
    Conflicting extracted values
          =
    Contradiction candidate

No LLM is used yet.

Ollama will be introduced later for difficult semantic cases.
"""

from __future__ import annotations

import re

from core.contradiction_engine.contradiction_result import (
    ContradictionResult,
)
from core.information_extractor.extraction_result import (
    ExtractionResult,
)
from core.redundancy_engine.redundancy_result import (
    RedundancyPair,
)


class ContradictionEngine:
    """
    Detect contradictions among already-detected similar pairs.
    """

    # Only highly similar statements should reach contradiction analysis.
    # This keeps unrelated sentences out of contradiction processing.
    DEFAULT_MINIMUM_SIMILARITY = 0.80

    # A high similarity plus conflicting factual values is treated
    # as a strong contradiction candidate.
    DEFAULT_CONTRADICTION_THRESHOLD = 0.80

    def __init__(
        self,
        minimum_similarity: float = DEFAULT_MINIMUM_SIMILARITY,
        contradiction_threshold: float = DEFAULT_CONTRADICTION_THRESHOLD,
    ) -> None:
        """
        Initialize the contradiction engine.

        Args:
            minimum_similarity:
                Minimum semantic similarity required for analysis.

            contradiction_threshold:
                Minimum contradiction score required for final reporting.
        """

        # Validate and store the minimum similarity.
        self.minimum_similarity = self._validate_score(
            minimum_similarity,
            "minimum_similarity",
        )

        # Validate and store the contradiction threshold.
        self.contradiction_threshold = self._validate_score(
            contradiction_threshold,
            "contradiction_threshold",
        )

    def analyze_pair(
        self,
        pair: RedundancyPair,
        extraction_a: ExtractionResult,
        extraction_b: ExtractionResult,
    ) -> ContradictionResult | None:
        """
        Analyze one semantically similar pair for contradiction.

        The current implementation focuses on factual numeric/value
        conflicts.

        Example:

            Population = 1.46 billion
            Population = 1.10 billion

        becomes a contradiction candidate.

        Returns:
            ContradictionResult when a contradiction is detected.
            None when no contradiction is identified.
        """

        # Ignore pairs that are not sufficiently similar.
        if pair.similarity_score < self.minimum_similarity:
            return None

        # Extract comparable factual values.
        values_a = self._normalized_values(
            extraction_a.values
        )

        values_b = self._normalized_values(
            extraction_b.values
        )

        # If neither statement has a factual value, the current
        # deterministic engine cannot confidently establish a contradiction.
        if not values_a or not values_b:
            return None

        # Determine whether the two statements contain conflicting values.
        if not self._values_conflict(
            values_a,
            values_b,
        ):
            return None

        # Calculate how strongly the pair indicates contradiction.
        contradiction_score = self._calculate_contradiction_score(
            pair.similarity_score
        )

        # Do not report weak contradiction candidates.
        if contradiction_score < self.contradiction_threshold:
            return None

        # Build a human-readable explanation for the result.
        reason = (
            "Semantically similar statements contain "
            "different factual values."
        )

        # Return the contradiction result.
        return ContradictionResult(
            information_unit_id_a=pair.information_unit_id_a,
            information_unit_id_b=pair.information_unit_id_b,
            text_a=pair.text_a,
            text_b=pair.text_b,
            similarity_score=pair.similarity_score,
            value_a=extraction_a.values,
            value_b=extraction_b.values,
            contradiction_score=contradiction_score,
            reason=reason,
        )

    def analyze_pairs(
        self,
        pairs: list[RedundancyPair],
        extractions: dict[str, ExtractionResult],
    ) -> list[ContradictionResult]:
        """
        Analyze all Phase 3 similar pairs automatically.

        Args:
            pairs:
                Similar pairs already detected by Phase 3.

            extractions:
                Extraction results indexed by InformationUnit ID.

        Returns:
            All contradiction candidates detected by Phase 6.
        """

        # Store the contradiction results.
        contradictions: list[ContradictionResult] = []

        # Process every similar pair independently.
        for pair in pairs:

            # Retrieve extraction data for both statements.
            extraction_a = extractions.get(
                pair.information_unit_id_a
            )

            extraction_b = extractions.get(
                pair.information_unit_id_b
            )

            # Skip the pair if extraction information is unavailable.
            if extraction_a is None or extraction_b is None:
                continue

            # Analyze the pair.
            contradiction = self.analyze_pair(
                pair,
                extraction_a,
                extraction_b,
            )

            # Keep only detected contradictions.
            if contradiction is not None:
                contradictions.append(
                    contradiction
                )

        return contradictions

    @staticmethod
    def _normalized_values(
        values: list[str],
    ) -> list[str]:
        """
        Normalize extracted values for comparison.

        Textual formatting differences such as capitalization and
        repeated whitespace are normalized without changing meaning.
        """

        # Normalize every extracted value.
        normalized = []

        for value in values:

            # Convert to lowercase and normalize whitespace.
            cleaned = re.sub(
                r"\s+",
                " ",
                value.strip().lower(),
            )

            # Keep non-empty values.
            if cleaned:
                normalized.append(cleaned)

        # Remove duplicates while preserving order.
        return list(dict.fromkeys(normalized))

    @staticmethod
    def _values_conflict(
        values_a: list[str],
        values_b: list[str],
    ) -> bool:
        """
        Determine whether two value collections conflict.

        The current Phase 6 implementation treats differing factual
        numeric values as a contradiction candidate when the statements
        are already semantically similar.
        """

        # If the two value sets have an intersection, the values
        # are not contradictory based on the available evidence.
        if set(values_a) & set(values_b):
            return False

        # Different non-empty factual values indicate a possible conflict.
        return bool(values_a and values_b)

    @staticmethod
    def _calculate_contradiction_score(
        similarity_score: float,
    ) -> float:
        """
        Calculate the current contradiction score.

        Current Phase 6 formula:

            contradiction_score = similarity_score

        The score is high because contradiction analysis starts only
        after strong semantic similarity has already been established.
        """

        # Keep the score in the valid range.
        return max(
            0.0,
            min(1.0, float(similarity_score)),
        )

    @staticmethod
    def _validate_score(
        value: float,
        name: str,
    ) -> float:
        """
        Validate a score between 0 and 1.
        """

        # Convert the input to float.
        score = float(value)

        # Reject invalid scores.
        if not 0.0 <= score <= 1.0:
            raise ValueError(
                f"{name} must be between 0.0 and 1.0."
            )

        return score