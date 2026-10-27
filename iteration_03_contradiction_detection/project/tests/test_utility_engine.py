"""
Minor Project One - Utility Engine Tests.
"""

from core.information_extractor.extraction_result import (
    ExtractionResult,
)
from core.utility_engine.utility_engine import UtilityEngine


def test_specific_numeric_information_gets_protection() -> None:
    """
    Verify that factual numeric information receives utility protection.
    """
    engine = UtilityEngine()

    extraction = ExtractionResult(
        information_unit_id="unit_001",
        text="Population is 1.46 billion.",
        values=["1.46 billion"],
        numbers=["1.46"],
    )

    score = engine.calculate_score(
        extraction,
        frequency=1,
    )

    assert score > 0.5
    assert score <= 1.0


def test_rare_information_gets_protection() -> None:
    """
    Verify that a rarely occurring information unit receives protection.
    """
    engine = UtilityEngine()

    extraction = ExtractionResult(
        information_unit_id="unit_001",
        text="A rare fact.",
    )

    score = engine.calculate_score(
        extraction,
        frequency=1,
    )

    assert score >= 0.6


def test_calculate_many() -> None:
    """
    Verify utility scoring for multiple information units.
    """
    engine = UtilityEngine()

    extractions = [
        ExtractionResult(
            information_unit_id="unit_001",
            text="Population is 1.46 billion.",
            values=["1.46 billion"],
        ),
        ExtractionResult(
            information_unit_id="unit_002",
            text="Delhi is the capital.",
        ),
    ]

    scores = engine.calculate_many(extractions)

    assert len(scores) == 2
    assert "unit_001" in scores
    assert "unit_002" in scores