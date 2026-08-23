"""
Minor Project One - Redundancy Analysis Service Tests
"""

from services.redundancy_analysis_service import (
    RedundancyAnalysisService,
)


def test_complete_automatic_pipeline() -> None:
    """
    Verify the full automatic flow:

    text
    → documents
    → sentences
    → embeddings
    → all pair comparisons
    → similar pairs
    """
    service = RedundancyAnalysisService()

    text = """
    Article 1
    India has a population of 1.46 billion.
    Approximately 1.46 billion people live in India.
    Delhi is the capital of India.
    The capital city of India is Delhi.

    Article 2
    Bengaluru is a major technology hub.
    """

    result = service.analyze_text(text)

    assert result.total_comparisons == 10
    assert result.similar_pair_count >= 2


def test_no_keywords_are_required() -> None:
    """
    Verify that the service needs only the dataset text and
    performs semantic comparison automatically.
    """
    service = RedundancyAnalysisService()

    text = """
    Article 1
    The capital city is Delhi.

    Article 2
    Delhi is India's capital city.
    """

    result = service.analyze_text(text)

    assert result.total_comparisons == 1
    assert result.similar_pair_count >= 1


def test_all_pairs_are_compared_even_when_not_similar() -> None:
    """
    Verify that unrelated information is still compared rather
    than being skipped before similarity calculation.
    """
    service = RedundancyAnalysisService()

    text = """
    Article 1
    Delhi is the capital of India.

    Article 2
    Bengaluru is a technology hub.

    Article 3
    The Pacific Ocean is the largest ocean.
    """

    result = service.analyze_text(text)

    assert result.total_comparisons == 3


def test_multiple_similarity_groups_can_be_found() -> None:
    """
    Verify that separate semantic groups can be identified
    in one dataset.
    """
    service = RedundancyAnalysisService()

    text = """
    Article 1
    India has a population of 1.46 billion.
    India's population is about 1.46 billion.

    Article 2
    Delhi is the capital of India.
    The capital city of India is Delhi.

    Article 3
    Bengaluru is a major technology hub.
    """

    result = service.analyze_text(text)

    assert result.total_comparisons == 10
    assert result.similar_pair_count >= 2