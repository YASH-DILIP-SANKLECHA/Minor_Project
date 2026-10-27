"""
Minor Project One - Optimizer Tests.

These tests verify Phase 8 removal selection without changing
the project's real dataset.
"""

from core.decision_engine.decision_result import DecisionResult
from core.optimizer.optimizer import Optimizer
from models.information_unit import InformationUnit


def make_unit(
    unit_id: str,
    text: str,
    utility: float,
    rarity: float,
) -> InformationUnit:
    """
    Create a test InformationUnit with Phase 5 metadata.
    """

    # Construct the information unit.
    return InformationUnit(
        information_unit_id=unit_id,
        document_id="doc_001",
        text=text,
        unit_index=1,
        metadata={
            "utility_score": utility,
            "rarity_score": rarity,
        },
        utility_score=utility,
        rarity_score=rarity,
    )


def make_decision(
    decision: str,
    confidence: float = 0.95,
) -> DecisionResult:
    """
    Create a test Phase 7 decision.
    """

    return DecisionResult(
        information_unit_id_a="unit_001",
        information_unit_id_b="unit_002",
        text_a="Statement A.",
        text_b="Statement B.",
        similarity_score=0.95,
        utility_score_a=0.2,
        utility_score_b=0.2,
        rarity_score_a=0.2,
        rarity_score_b=0.2,
        contradiction_detected=False,
        decision=decision,
        confidence=confidence,
        reason="Test decision.",
    )


def test_remove_decision_removes_weaker_unit() -> None:
    """
    Verify that a REMOVE decision removes the less-protected unit.
    """

    # Create one strongly protected and one weakly protected unit.
    units = [
        make_unit(
            "unit_001",
            "Protected statement.",
            utility=0.9,
            rarity=0.9,
        ),
        make_unit(
            "unit_002",
            "Weak statement.",
            utility=0.1,
            rarity=0.1,
        ),
    ]

    # Create a REMOVE decision for the pair.
    decisions = [
        make_decision("REMOVE")
    ]

    # Run the optimizer.
    result = Optimizer().optimize(
        units,
        decisions,
    )

    # The weaker unit should be removed.
    assert result.removed_unit_ids == ["unit_002"]

    # The stronger unit should remain.
    assert result.retained_unit_ids == ["unit_001"]

    # Exactly one change should be recorded.
    assert result.removed_count == 1


def test_keep_decision_does_not_remove() -> None:
    """
    Verify that KEEP never modifies the retained set.
    """

    units = [
        make_unit(
            "unit_001",
            "Statement A.",
            utility=0.5,
            rarity=0.5,
        ),
        make_unit(
            "unit_002",
            "Statement B.",
            utility=0.5,
            rarity=0.5,
        ),
    ]

    decisions = [
        make_decision("KEEP")
    ]

    result = Optimizer().optimize(
        units,
        decisions,
    )

    assert result.removed_count == 0
    assert result.final_unit_count == 2


def test_review_decision_does_not_remove() -> None:
    """
    Verify that REVIEW never causes automatic removal.
    """

    units = [
        make_unit(
            "unit_001",
            "Statement A.",
            utility=0.1,
            rarity=0.1,
        ),
        make_unit(
            "unit_002",
            "Statement B.",
            utility=0.1,
            rarity=0.1,
        ),
    ]

    decisions = [
        make_decision("REVIEW")
    ]

    result = Optimizer().optimize(
        units,
        decisions,
    )

    assert result.removed_count == 0
    assert result.final_unit_count == 2


def test_reduction_percentage() -> None:
    """
    Verify reduction percentage calculation.
    """

    units = [
        make_unit(
            "unit_001",
            "Statement A.",
            utility=0.9,
            rarity=0.9,
        ),
        make_unit(
            "unit_002",
            "Statement B.",
            utility=0.1,
            rarity=0.1,
        ),
    ]

    decisions = [
        make_decision("REMOVE")
    ]

    result = Optimizer().optimize(
        units,
        decisions,
    )

    assert result.reduction_percentage == 50.0


def test_all_exact_duplicates_are_removed_without_similarity_pairs() -> None:
    """Exact repeats must not depend on a bounded similarity graph."""
    units = [
        make_unit("unit_001", "The capital is Delhi.", 0.5, 0.5),
        make_unit("unit_002", "The capital is Delhi.", 0.5, 0.5),
        make_unit("unit_003", "The capital is Delhi.", 0.5, 0.5),
        make_unit("unit_004", "Another fact.", 0.5, 0.5),
    ]

    result = Optimizer().optimize(units, [])

    assert result.retained_unit_ids == ["unit_001", "unit_004"]
    assert result.removed_unit_ids == ["unit_002", "unit_003"]
    assert all(record.confidence == 1.0 for record in result.change_records)
