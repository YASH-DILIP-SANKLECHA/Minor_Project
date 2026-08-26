"""
Minor Project One - Decision Engine.

Phase 7 converts the outputs of Phases 3-6 into:

    KEEP
    REMOVE
    REVIEW

Important:
This module does NOT delete anything.

It only recommends what should happen later in Phase 8.

Decision principles:
1. Contradictions are never automatically removed.
2. Rare information receives protection.
3. Useful information receives protection.
4. Strong semantic redundancy with low protection can become
   a REMOVE recommendation.
5. Uncertain cases go to REVIEW.
"""

from __future__ import annotations

from core.contradiction_engine.contradiction_result import (
    ContradictionResult,
)
from core.decision_engine.decision_result import DecisionResult
from core.redundancy_engine.redundancy_result import RedundancyPair


class DecisionEngine:
    """
    Make conservative KEEP/REMOVE/REVIEW recommendations.
    """

    DEFAULT_REMOVE_THRESHOLD = 0.85
    DEFAULT_KEEP_PROTECTION_THRESHOLD = 0.70

    def __init__(
        self,
        remove_threshold: float = DEFAULT_REMOVE_THRESHOLD,
        keep_protection_threshold: float = (
            DEFAULT_KEEP_PROTECTION_THRESHOLD
        ),
    ) -> None:
        """
        Initialize the decision engine.

        Args:
            remove_threshold:
                Minimum redundancy score required before a pair
                can become a REMOVE recommendation.

            keep_protection_threshold:
                Utility/rarity protection level above which
                information is protected from automatic removal.
        """

        # Validate the removal threshold.
        self.remove_threshold = self._validate_score(
            remove_threshold,
            "remove_threshold",
        )

        # Validate the protection threshold.
        self.keep_protection_threshold = self._validate_score(
            keep_protection_threshold,
            "keep_protection_threshold",
        )

    def decide_pair(
        self,
        pair: RedundancyPair,
        utility_score_a: float,
        utility_score_b: float,
        rarity_score_a: float,
        rarity_score_b: float,
        contradiction_detected: bool = False,
    ) -> DecisionResult:
        """
        Make a KEEP/REMOVE/REVIEW recommendation for one pair.

        The decision is conservative:

        CONTRADICTION
            -> REVIEW

        Strong utility/rarity protection
            -> KEEP

        Very strong redundancy with low protection
            -> REMOVE

        Everything else
            -> REVIEW

        Actual deletion does not occur here.
        """

        # Validate the incoming protection scores.
        utility_score_a = self._validate_score(
            utility_score_a,
            "utility_score_a",
        )

        utility_score_b = self._validate_score(
            utility_score_b,
            "utility_score_b",
        )

        rarity_score_a = self._validate_score(
            rarity_score_a,
            "rarity_score_a",
        )

        rarity_score_b = self._validate_score(
            rarity_score_b,
            "rarity_score_b",
        )

        # Calculate the strongest protection signal among the pair.
        utility_protection = max(
            utility_score_a,
            utility_score_b,
        )

        rarity_protection = max(
            rarity_score_a,
            rarity_score_b,
        )

        # Use the stronger of utility and rarity protection.
        protection = max(
            utility_protection,
            rarity_protection,
        )

        # Rule 1:
        # Contradictory information must never be silently removed.
        if contradiction_detected:
            return DecisionResult(
                information_unit_id_a=pair.information_unit_id_a,
                information_unit_id_b=pair.information_unit_id_b,
                text_a=pair.text_a,
                text_b=pair.text_b,
                similarity_score=pair.similarity_score,
                utility_score_a=utility_score_a,
                utility_score_b=utility_score_b,
                rarity_score_a=rarity_score_a,
                rarity_score_b=rarity_score_b,
                contradiction_detected=True,
                decision="REVIEW",
                confidence=pair.similarity_score,
                reason=(
                    "The information is highly similar but contains "
                    "conflicting factual values. Human review is required."
                ),
            )

        # Rule 2:
        # Strong utility or rarity protection means the information
        # should be retained.
        if protection >= self.keep_protection_threshold:
            confidence = max(
                utility_protection,
                rarity_protection,
            )

            return DecisionResult(
                information_unit_id_a=pair.information_unit_id_a,
                information_unit_id_b=pair.information_unit_id_b,
                text_a=pair.text_a,
                text_b=pair.text_b,
                similarity_score=pair.similarity_score,
                utility_score_a=utility_score_a,
                utility_score_b=utility_score_b,
                rarity_score_a=rarity_score_a,
                rarity_score_b=rarity_score_b,
                contradiction_detected=False,
                decision="KEEP",
                confidence=confidence,
                reason=(
                    "The repeated information has sufficient utility "
                    "or rarity protection and should be preserved."
                ),
            )

        # Rule 3:
        # Very strong semantic redundancy with low protection can
        # become a REMOVE recommendation.
        if pair.redundancy_score >= self.remove_threshold:
            confidence = pair.redundancy_score

            return DecisionResult(
                information_unit_id_a=pair.information_unit_id_a,
                information_unit_id_b=pair.information_unit_id_b,
                text_a=pair.text_a,
                text_b=pair.text_b,
                similarity_score=pair.similarity_score,
                utility_score_a=utility_score_a,
                utility_score_b=utility_score_b,
                rarity_score_a=rarity_score_a,
                rarity_score_b=rarity_score_b,
                contradiction_detected=False,
                decision="REMOVE",
                confidence=confidence,
                reason=(
                    "The information is strongly redundant and has "
                    "insufficient utility/rarity protection."
                ),
            )

        # Rule 4:
        # Everything uncertain goes to review rather than being
        # aggressively removed.
        return DecisionResult(
            information_unit_id_a=pair.information_unit_id_a,
            information_unit_id_b=pair.information_unit_id_b,
            text_a=pair.text_a,
            text_b=pair.text_b,
            similarity_score=pair.similarity_score,
            utility_score_a=utility_score_a,
            utility_score_b=utility_score_b,
            rarity_score_a=rarity_score_a,
            rarity_score_b=rarity_score_b,
            contradiction_detected=False,
            decision="REVIEW",
            confidence=pair.redundancy_score,
            reason=(
                "The pair is similar but the available evidence "
                "is insufficient for automatic removal."
            ),
        )

    def decide_all(
        self,
        pairs: list[RedundancyPair],
        metadata_by_id: dict[str, dict[str, float]],
        contradictions: list[ContradictionResult],
    ) -> list[DecisionResult]:
        """
        Make decisions for all detected redundancy pairs.

        Args:
            pairs:
                Similar pairs produced by Phase 3.

            metadata_by_id:
                Utility and rarity scores indexed by information-unit ID.

            contradictions:
                Contradiction results produced by Phase 6.

        Returns:
            One DecisionResult for every input redundancy pair.
        """

        # Create a fast lookup set for contradiction pairs.
        contradiction_pairs = {
            (
                contradiction.information_unit_id_a,
                contradiction.information_unit_id_b,
            )
            for contradiction in contradictions
        }

        # Also recognize reversed pair ordering.
        reversed_contradiction_pairs = {
            (
                second,
                first,
            )
            for first, second in contradiction_pairs
        }

        # Store all decisions.
        decisions: list[DecisionResult] = []

        # Process every Phase 3 similar pair.
        for pair in pairs:

            # Retrieve metadata for both information units.
            metadata_a = metadata_by_id.get(
                pair.information_unit_id_a,
                {},
            )

            metadata_b = metadata_by_id.get(
                pair.information_unit_id_b,
                {},
            )

            # Read utility scores while safely defaulting to zero.
            utility_a = float(
                metadata_a.get(
                    "utility_score",
                    0.0,
                )
            )

            utility_b = float(
                metadata_b.get(
                    "utility_score",
                    0.0,
                )
            )

            # Read rarity scores while safely defaulting to zero.
            rarity_a = float(
                metadata_a.get(
                    "rarity_score",
                    0.0,
                )
            )

            rarity_b = float(
                metadata_b.get(
                    "rarity_score",
                    0.0,
                )
            )

            # Determine whether this pair has been flagged as contradictory.
            contradiction_detected = (
                (
                    pair.information_unit_id_a,
                    pair.information_unit_id_b,
                )
                in contradiction_pairs
                or (
                    pair.information_unit_id_a,
                    pair.information_unit_id_b,
                )
                in reversed_contradiction_pairs
            )

            # Make the final Phase 7 recommendation.
            decision = self.decide_pair(
                pair=pair,
                utility_score_a=utility_a,
                utility_score_b=utility_b,
                rarity_score_a=rarity_a,
                rarity_score_b=rarity_b,
                contradiction_detected=contradiction_detected,
            )

            # Store the decision.
            decisions.append(decision)

        return decisions

    @staticmethod
    def _validate_score(
        value: float,
        name: str,
    ) -> float:
        """
        Validate a numerical score between 0 and 1.
        """

        # Convert the supplied value to a float.
        score = float(value)

        # Reject values outside the valid range.
        if not 0.0 <= score <= 1.0:
            raise ValueError(
                f"{name} must be between 0.0 and 1.0."
            )

        return score