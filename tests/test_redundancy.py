"""
Minor Project One - Redundancy Engine Tests
"""

import pytest

from core.redundancy_engine.redundancy_engine import RedundancyEngine
from models.information_unit import InformationUnit


def make_unit(
    unit_id: str,
    text: str,
    embedding: list[float],
    unit_index: int,
) -> InformationUnit:
    """Create a reusable InformationUnit for testing."""
    return InformationUnit(
        information_unit_id=unit_id,
        document_id="doc_000001",
        text=text,
        unit_index=unit_index,
        embedding=embedding,
    )


def test_every_pair_is_compared() -> None:
    """Verify that every unique pair is automatically compared."""
    engine = RedundancyEngine()

    units = [
        make_unit("unit_001", "Sentence A.", [1.0, 0.0, 0.0], 1),
        make_unit("unit_002", "Sentence B.", [0.0, 1.0, 0.0], 2),
        make_unit("unit_003", "Sentence C.", [0.0, 0.0, 1.0], 3),
        make_unit("unit_004", "Sentence D.", [0.7, 0.7, 0.0], 4),
    ]

    results = engine.calculate_all_similarities(units)

    assert len(results) == 6


def test_similar_pairs_are_detected_without_keywords() -> None:
    """Verify that similar embeddings produce automatic candidates."""
    engine = RedundancyEngine(
        similarity_threshold=0.65,
        redundancy_threshold=0.65,
    )

    units = [
        make_unit(
            "unit_001",
            "The capital city is Delhi.",
            [1.0, 0.0],
            1,
        ),
        make_unit(
            "unit_002",
            "Delhi is the capital of India.",
            [0.98, 0.10],
            2,
        ),
    ]

    result = engine.analyze(units)

    assert result.total_comparisons == 1
    assert result.similar_pair_count == 1
    assert result.similar_pairs[0].similarity_score >= 0.65


def test_unrelated_pair_can_be_compared_without_being_classified() -> None:
    """Verify that unrelated information is still compared."""
    engine = RedundancyEngine(
        similarity_threshold=0.65,
        redundancy_threshold=0.65,
    )

    units = [
        make_unit(
            "unit_001",
            "Delhi is the capital of India.",
            [1.0, 0.0],
            1,
        ),
        make_unit(
            "unit_002",
            "Bengaluru is a technology hub.",
            [0.0, 1.0],
            2,
        ),
    ]

    result = engine.analyze(units)

    assert result.total_comparisons == 1
    assert result.similar_pair_count == 0


def test_multiple_similar_pairs_are_returned() -> None:
    """Verify that multiple similar pairs are all returned."""
    engine = RedundancyEngine(
        similarity_threshold=0.65,
        redundancy_threshold=0.65,
    )

    units = [
        make_unit(
            "unit_001",
            "India has a population of 1.46 billion.",
            [1.0, 0.0, 0.0],
            1,
        ),
        make_unit(
            "unit_002",
            "Approximately 1.46 billion people live in India.",
            [0.97, 0.10, 0.0],
            2,
        ),
        make_unit(
            "unit_003",
            "India's population is about 1.46 billion.",
            [0.96, 0.12, 0.0],
            3,
        ),
        make_unit(
            "unit_004",
            "Delhi is the capital of India.",
            [0.0, 1.0, 0.0],
            4,
        ),
        make_unit(
            "unit_005",
            "The capital city of India is Delhi.",
            [0.0, 0.97, 0.10],
            5,
        ),
    ]

    result = engine.analyze(units)

    assert result.total_comparisons == 10
    assert result.similar_pair_count >= 4


def test_similarity_scores_are_between_zero_and_one() -> None:
    """Verify that every calculated similarity lies in the valid range."""
    engine = RedundancyEngine()

    units = [
        make_unit("unit_001", "A.", [1.0, 0.0], 1),
        make_unit("unit_002", "B.", [0.0, 1.0], 2),
        make_unit("unit_003", "C.", [0.8, 0.6], 3),
    ]

    results = engine.calculate_all_similarities(units)

    assert len(results) == 3

    for pair in results:
        assert 0.0 <= pair.similarity_score <= 1.0


def test_single_unit_produces_zero_comparisons() -> None:
    """Verify that one information unit cannot produce a pair."""
    engine = RedundancyEngine()

    units = [
        make_unit(
            "unit_001",
            "Only sentence.",
            [1.0, 0.0],
            1,
        )
    ]

    result = engine.analyze(units)

    assert result.total_comparisons == 0
    assert result.similar_pair_count == 0


def test_missing_embedding_raises_error() -> None:
    """Verify that missing embeddings are rejected."""
    engine = RedundancyEngine()

    units = [
        InformationUnit(
            information_unit_id="unit_001",
            document_id="doc_000001",
            text="Missing embedding.",
            unit_index=1,
            embedding=None,
        ),
        make_unit(
            "unit_002",
            "Valid embedding.",
            [1.0, 0.0],
            2,
        ),
    ]

    with pytest.raises(ValueError, match="Missing embedding"):
        engine.analyze(units)


def test_invalid_threshold_raises_error() -> None:
    """Verify that invalid thresholds are rejected."""
    with pytest.raises(
        ValueError,
        match="between 0.0 and 1.0",
    ):
        RedundancyEngine(similarity_threshold=1.5)


def test_redundancy_groups_are_created() -> None:
    """Verify that connected similar pairs become a group."""
    engine = RedundancyEngine(
        similarity_threshold=0.65,
        redundancy_threshold=0.65,
    )

    units = [
        make_unit("unit_001", "A.", [1.0, 0.0], 1),
        make_unit("unit_002", "B.", [0.98, 0.10], 2),
        make_unit("unit_003", "C.", [0.97, 0.12], 3),
    ]

    result = engine.analyze(units)

    assert result.group_count == 1
    assert result.groups[0].size == 3


def test_result_can_be_serialized() -> None:
    """Verify that the complete analysis is serializable."""
    engine = RedundancyEngine()

    units = [
        make_unit("unit_001", "A.", [1.0, 0.0], 1),
        make_unit("unit_002", "B.", [0.98, 0.10], 2),
    ]

    data = engine.analyze(units).to_dict()

    assert "all_similarities" in data
    assert "similar_pairs" in data
    assert "groups" in data
    assert "total_comparisons" in data
    assert "similar_pair_count" in data