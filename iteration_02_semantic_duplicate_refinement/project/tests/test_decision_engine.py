"""
Minor Project One - Decision Engine Tests.

These tests verify Phase 7 decisions independently.

The real project dataset is not changed by these tests.
"""

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
        text_a="Delhi is the capital of India.",
        text_b="The capital of India is Delhi.",
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


def test_high_protection_selects_the_representative_but_still_removes_duplicate() -> None:
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

    # High utility determines which duplicate Phase 8 retains; it must not
    # prevent duplicate removal altogether.
    assert result.decision == "REMOVE"


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


def test_shared_sentence_template_is_not_enough_to_remove_content() -> None:
    """Unrelated statements must survive a high embedding similarity."""
    pair = RedundancyPair(
        information_unit_id_a="unit_001",
        information_unit_id_b="unit_002",
        similarity_score=0.95,
        redundancy_score=0.95,
        text_a="At dawn, the gentle harbor waited near the distant garden.",
        text_b="At dawn, the blue library wandered near the quiet valley.",
    )

    result = DecisionEngine().decide_pair(
        pair=pair,
        utility_score_a=0.1,
        utility_score_b=0.1,
        rarity_score_a=0.1,
        rarity_score_b=0.1,
    )

    assert result.decision == "REVIEW"


def test_shared_value_does_not_make_different_subjects_duplicates() -> None:
    """A shared value must not erase claims about different entities."""
    pair = RedundancyPair(
        information_unit_id_a="unit_001",
        information_unit_id_b="unit_002",
        similarity_score=0.95,
        redundancy_score=0.95,
        text_a="The capital of Nigeria is Atlantis.",
        text_b="The capital of Niger is Atlantis.",
    )

    result = DecisionEngine().decide_pair(
        pair=pair,
        utility_score_a=0.1,
        utility_score_b=0.1,
        rarity_score_a=0.1,
        rarity_score_b=0.1,
    )

    assert result.decision == "REVIEW"


def test_reordered_template_words_are_not_silently_removed() -> None:
    """High overlap without the same asserted event stays retained."""
    pair = RedundancyPair(
        information_unit_id_a="unit_001",
        information_unit_id_b="unit_002",
        similarity_score=0.93,
        redundancy_score=0.93,
        text_a="At dawn, the gentle valley gathered near the distant harbor glowed.",
        text_b="At dawn, the gentle valley rested near the distant harbor glowed.",
    )

    result = DecisionEngine().decide_pair(
        pair=pair,
        utility_score_a=0.1,
        utility_score_b=0.1,
        rarity_score_a=0.1,
        rarity_score_b=0.1,
    )

    assert result.decision == "REVIEW"


def test_possessive_reordered_fact_is_removed_as_a_duplicate() -> None:
    """Equivalent possessive/reordered wording must retain only one line."""
    pair = RedundancyPair(
        information_unit_id_a="unit_001",
        information_unit_id_b="unit_002",
        similarity_score=0.72,
        redundancy_score=0.72,
        text_a="India's capital is Delhi.",
        text_b="Delhi is the capital of India.",
    )

    result = DecisionEngine().decide_pair(
        pair=pair,
        utility_score_a=0.1,
        utility_score_b=0.1,
        rarity_score_a=0.1,
        rarity_score_b=0.1,
    )

    assert result.decision == "REMOVE"


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
            text_a="Paris is the capital of France.",
            text_b="The capital of France is Paris.",
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
    assert results[1].decision == "REMOVE"
