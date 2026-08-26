"""
Minor Project One - Contradiction Engine Tests.

These tests use controlled InformationUnit data only to verify
the contradiction algorithm.

The project's real dataset remains:
    datasets/raw/dataset.txt
"""

from core.contradiction_engine.contradiction_engine import (
    ContradictionEngine,
)
from core.information_extractor.extraction_result import (
    ExtractionResult,
)
from core.redundancy_engine.redundancy_result import (
    RedundancyPair,
)


def make_pair(
    score: float = 0.95,
) -> RedundancyPair:
    """
    Create a test redundancy pair with a configurable
    semantic-similarity score.
    """

    return RedundancyPair(
        information_unit_id_a="unit_001",
        information_unit_id_b="unit_002",
        similarity_score=score,
        redundancy_score=score,
        text_a="The temperature is 80 degrees.",
        text_b="The temperature is 70 degrees.",
    )


def make_extractions() -> tuple[
    ExtractionResult,
    ExtractionResult,
]:
    """
    Create two extraction results containing conflicting values.
    """

    extraction_a = ExtractionResult(
        information_unit_id="unit_001",
        text="The temperature is 80 degrees.",
        values=["80"],
        numbers=["80"],
    )

    extraction_b = ExtractionResult(
        information_unit_id="unit_002",
        text="The temperature is 70 degrees.",
        values=["70"],
        numbers=["70"],
    )

    return extraction_a, extraction_b


def test_conflicting_values_are_detected() -> None:
    """
    Verify that semantically similar statements with different
    factual values are detected as contradictions.
    """

    # Create the contradiction engine.
    engine = ContradictionEngine()

    # Create the two similar statements.
    pair = make_pair()

    # Create their extracted factual values.
    extraction_a, extraction_b = make_extractions()

    # Analyze the pair.
    result = engine.analyze_pair(
        pair,
        extraction_a,
        extraction_b,
    )

    # A contradiction should be detected.
    assert result is not None
    assert result.contradiction_score >= 0.80
    assert result.value_a == ["80"]
    assert result.value_b == ["70"]


def test_same_value_is_not_contradiction() -> None:
    """
    Verify that identical factual values are not classified
    as contradictions.
    """

    # Create the contradiction engine.
    engine = ContradictionEngine()

    # Create a highly similar pair.
    pair = RedundancyPair(
        information_unit_id_a="unit_001",
        information_unit_id_b="unit_002",
        similarity_score=0.95,
        redundancy_score=0.95,
        text_a="The temperature is 80 degrees.",
        text_b="The temperature is also 80 degrees.",
    )

    # Both statements contain the same value.
    extraction_a = ExtractionResult(
        information_unit_id="unit_001",
        text="The temperature is 80 degrees.",
        values=["80"],
    )

    extraction_b = ExtractionResult(
        information_unit_id="unit_002",
        text="The temperature is also 80 degrees.",
        values=["80"],
    )

    # Analyze the pair.
    result = engine.analyze_pair(
        pair,
        extraction_a,
        extraction_b,
    )

    # The statements agree, so no contradiction should be returned.
    assert result is None


def test_unrelated_pair_is_not_analyzed_as_contradiction() -> None:
    """
    Verify that low semantic similarity prevents contradiction detection.
    """

    # Use a similarity score below the configured minimum.
    engine = ContradictionEngine(
        minimum_similarity=0.80,
    )

    pair = make_pair(
        score=0.40
    )

    extraction_a, extraction_b = make_extractions()

    # Analyze the unrelated pair.
    result = engine.analyze_pair(
        pair,
        extraction_a,
        extraction_b,
    )

    # It should not become a contradiction.
    assert result is None


def test_multiple_pairs_are_analyzed() -> None:
    """
    Verify that multiple redundancy pairs can be analyzed
    automatically.
    """

    # Create the engine.
    engine = ContradictionEngine()

    # Create two similar-pair objects.
    pairs = [
        make_pair(0.95),
        RedundancyPair(
            information_unit_id_a="unit_003",
            information_unit_id_b="unit_004",
            similarity_score=0.92,
            redundancy_score=0.92,
            text_a="The population is 80 million.",
            text_b="The population is 70 million.",
        ),
    ]

    # Create extraction results for every ID.
    extractions = {
        "unit_001": ExtractionResult(
            information_unit_id="unit_001",
            text="The temperature is 80 degrees.",
            values=["80"],
        ),
        "unit_002": ExtractionResult(
            information_unit_id="unit_002",
            text="The temperature is 70 degrees.",
            values=["70"],
        ),
        "unit_003": ExtractionResult(
            information_unit_id="unit_003",
            text="The population is 80 million.",
            values=["80 million"],
        ),
        "unit_004": ExtractionResult(
            information_unit_id="unit_004",
            text="The population is 70 million.",
            values=["70 million"],
        ),
    }

    # Analyze all pairs.
    results = engine.analyze_pairs(
        pairs,
        extractions,
    )

    # Both contradictory pairs should be detected.
    assert len(results) == 2