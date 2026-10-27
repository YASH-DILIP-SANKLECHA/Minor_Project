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
2. High-confidence non-contradictory paraphrases are reduced to one unit.
3. Utility and rarity select which equivalent unit to retain; they do not
   prevent semantic duplicate removal.
4. Uncertain cases go to REVIEW.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from core.decision_engine.decision_result import DecisionResult
from core.redundancy_engine.redundancy_result import RedundancyPair


class DecisionEngine:
    """
    Make conservative KEEP/REMOVE/REVIEW recommendations.
    """

    # MiniLM supplies the semantic candidate score.  The strict content
    # equivalence check below guards deletion, so an equivalent paraphrase
    # should not be retained merely because its cosine score is below 0.80.
    DEFAULT_REMOVE_THRESHOLD = 0.65
    DEFAULT_KEEP_PROTECTION_THRESHOLD = 0.70
    # Embeddings identify candidates, but a high cosine score alone cannot
    # prove that two templated statements mean the same thing.  These common
    # structural words are ignored when confirming semantic duplicate
    # candidates with their meaningful lexical content.
    DUPLICATE_STOP_WORDS = frozenset({
        "a", "an", "and", "are", "as", "at", "be", "by", "for",
        "from", "in", "is", "it", "near", "of", "on", "or", "the",
        "this", "that", "to", "was", "were", "with",
    })

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

        High-confidence semantic redundancy
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
        # Utility and rarity choose the representative in Phase 8, but exact
        # or high-confidence semantic duplicates must still be reduced.
        if (
            pair.redundancy_score >= self.remove_threshold
            and self._has_duplicate_content(pair.text_a, pair.text_b)
        ):
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
                    "The information is a high-confidence semantic duplicate. "
                    "Phase 8 will retain the stronger utility/rarity representative."
                ),
            )

        # Rule 3:
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

    @classmethod
    def _has_duplicate_content(cls, text_a: str, text_b: str) -> bool:
        """Confirm that a semantic candidate shares its meaningful content.

        This blocks false removals where many unrelated statements share a
        grammatical template.  Exact repeats are always accepted.  For
        differently worded statements, two or more meaningful terms must
        overlap and cover most of the shorter statement's content.
        """
        normalized_a = cls._normalize_for_content_check(text_a)
        normalized_b = cls._normalize_for_content_check(text_b)
        if normalized_a == normalized_b:
            return True

        numeric_values_a = set(re.findall(r"\b\d+(?:\.\d+)?\b", normalized_a))
        numeric_values_b = set(re.findall(r"\b\d+(?:\.\d+)?\b", normalized_b))
        if numeric_values_a != numeric_values_b:
            return False

        tokens_a = {
            token
            for token in re.findall(r"[a-z0-9]+", normalized_a)
            if token not in cls.DUPLICATE_STOP_WORDS
        }
        tokens_b = {
            token
            for token in re.findall(r"[a-z0-9]+", normalized_b)
            if token not in cls.DUPLICATE_STOP_WORDS
        }
        if not tokens_a or not tokens_b:
            return False

        shared_count = len(tokens_a & tokens_b)
        union_count = len(tokens_a | tokens_b)
        same_content_terms = tokens_a == tokens_b
        return (
            shared_count >= 2
            # Coverage of only the shorter sentence can make two different
            # claims look identical when they share a template and one value
            # (for example, two unrelated "capital ... Atlantis" claims).
            # Jaccard overlap requires the meaningful content of *both*
            # statements to agree.
            and shared_count / union_count >= 0.60
            # Bag-of-words overlap loses sentence structure.  Without this
            # guard, unrelated templated statements can share several nouns
            # and verbs while asserting different events.  A close ordered
            # sequence is required before automatic deletion; broader cases
            # remain available for review instead of being silently lost.
            and (
                # Reordered wording of the same content ("Delhi is the
                # capital of India" / "The capital of India is Delhi") is
                # safe to reduce.
                same_content_terms
                # Otherwise, require near-identical ordered content.  This
                # prevents one altered subject/action in a template from
                # deleting a different statement.
                or SequenceMatcher(
                    None,
                    cls._content_sequence(normalized_a),
                    cls._content_sequence(normalized_b),
                ).ratio() >= 0.98
            )
        )

    @classmethod
    def _content_sequence(cls, text: str) -> str:
        """Return ordered meaningful tokens for conservative comparison."""
        return " ".join(
            token
            for token in re.findall(r"[a-z0-9]+", text)
            if token not in cls.DUPLICATE_STOP_WORDS
        )

    @staticmethod
    def _normalize_for_content_check(text: str) -> str:
        """Normalize punctuation and possessives before comparing content.

        This makes ordinary reordered paraphrases such as ``India's capital
        is Delhi`` and ``Delhi is the capital of India`` comparable without
        relaxing the meaningful-term safeguards that reject look-alike
        templates with different facts.
        """
        normalized = text.casefold()
        normalized = re.sub(r"\b([a-z0-9]+)'s\b", r"\1", normalized)
        return re.sub(r"\s+", " ", normalized).strip()

    def decide_all(
        self,
        pairs: list[RedundancyPair],
        metadata_by_id: dict[str, dict[str, float]],
        contradictions: list[object],
    ) -> list[DecisionResult]:
        """
        Make decisions for all detected redundancy pairs.

        Args:
            pairs:
                Similar pairs produced by Phase 3.

            metadata_by_id:
                Utility and rarity scores indexed by information-unit ID.

            contradictions:
                Reserved for later increments. Iteration 2 has no
                contradiction-detection component, so this is passed as an
                empty list by its standalone runner.

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
