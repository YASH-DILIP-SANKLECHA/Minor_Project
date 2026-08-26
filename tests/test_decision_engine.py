"""
Minor Project One - Decision Engine Tests.

These tests verify Phase 7 decisions independently.

The real project dataset is not changed by these tests.
"""

from core.contradiction_engine.contradiction_result import (
    ContradictionResult,
)
from core.decision_engine.decision_engine import DecisionEngine
from core.redundancy_engine.redundancy_result import (
    RedundancyPair,
)


def make_pair(
    similarity: float = 0.95,
) -> RedundancyPair:
    """
    Create a reusable redundancy pair for testing.
    """

    return RedundancyPair(
        information_unit_id_a="unit_001",
        information_unit_id_b="unit_002",
        similarity_score=similarity,
        redundancy_score=similarity,
        text_a="Statement A.",
        text_b="Statement B.",
    )


def test_contradiction_goes_to_review() -> None:
    """
    Verify that contradictory information is never automatically removed.
    """

    # Create the decision engine.
    engine = DecisionEngine()

    # Create a contradictory result.
    result = engine.decide_pair(
        pair=make_pair(0.95),
        utility_score_a=0.1,
        utility_score_b=0.1,
        rarity_score_a=0.1,
        rarity_score_b=0.1,
        contradiction_detected=True,
    )

    # Contradictions must go to human review.
    assert result.decision == "REVIEW"
    assert result.contradiction_detected is True


def test_high_protection_results_in_keep() -> None:
    """
    Verify that highly useful or rare information is protected.
    """

    # Create the decision engine.
    engine = DecisionEngine()

    # Give the pair strong utility protection.
    result = engine.decide_pair(
        pair=make_pair(0.95),
        utility_score_a=0.90,
        utility_score_b=0.20,
        rarity_score_a=0.20,
        rarity_score_b=0.20,
    )

    # The pair should be retained.
    assert result.decision == "KEEP"


def test_strong_redundancy_with_low_protection_can_remove() -> None:
    """
    Verify that strong redundancy with low protection can
    produce a REMOVE recommendation.
    """

    # Create the decision engine.
    engine = DecisionEngine()

    # Use extremely low utility and rarity.
    result = engine.decide_pair(
        pair=make_pair(0.95),
        utility_score_a=0.10,
        utility_score_b=0.10,
        rarity_score_a=0.10,
        rarity_score_b=0.10,
    )

    # Strongly redundant low-value information can be removed later.
    assert result.decision == "REMOVE"


def test_moderate_case_goes_to_review() -> None:
    """
    Verify that uncertain cases are sent for review.
    """

    # Create a pair whose evidence is not strong enough for removal.
    pair = make_pair(0.83)
    pair.redundancy_score = 0.83

    engine = DecisionEngine(
        remove_threshold=0.90,
    )

    result = engine.decide_pair(
        pair=pair,
        utility_score_a=0.40,
        utility_score_b=0.40,
        rarity_score_a=0.40,
        rarity_score_b=0.40,
    )

    # The conservative engine should request review.
    assert result.decision == "REVIEW"


def test_all_pairs_can_be_decided() -> None:
    """
    Verify that multiple redundancy pairs are processed automatically.
    """

    # Create the decision engine.
    engine = DecisionEngine()

    # Create two candidate pairs.
    pairs = [
        make_pair(0.95),
        RedundancyPair(
            information_unit_id_a="unit_003",
            information_unit_id_b="unit_004",
            similarity_score=0.90,
            redundancy_score=0.90,
            text_a="Statement C.",
            text_b="Statement D.",
        ),
    ]

    # Provide utility/rarity metadata for all four units.
    metadata = {
        "unit_001": {
            "utility_score": 0.10,
            "rarity_score": 0.10,
        },
        "unit_002": {
            "utility_score": 0.10,
            "rarity_score": 0.10,
        },
        "unit_003": {
            "utility_score": 0.80,
            "rarity_score": 0.80,
        },
        "unit_004": {
            "utility_score": 0.80,
            "rarity_score": 0.80,
        },
    }

    # No contradictions are present.
    contradictions: list[ContradictionResult] = []

    # Make decisions for every pair.
    results = engine.decide_all(
        pairs=pairs,
        metadata_by_id=metadata,
        contradictions=contradictions,
    )

    # Every pair must receive exactly one decision.
    assert len(results) == 2
    assert results[0].decision == "REMOVE"
    assert results[1].decision == "KEEP"