"""
Minor Project One - Scoring Engine Tests.
"""

from core.scoring.scoring_engine import ScoringEngine


def test_high_similarity_increases_redundancy() -> None:
    """
    Verify that strong semantic similarity produces a strong
    redundancy score when protection signals are low.
    """
    engine = ScoringEngine()

    score = engine.calculate_score(
        similarity_score=0.95,
        utility_score_a=0.2,
        utility_score_b=0.2,
        rarity_score_a=0.2,
        rarity_score_b=0.2,
    )

    assert score > 0.70
    assert score <= 1.0


def test_high_utility_reduces_redundancy() -> None:
    """
    Verify that high utility protects information from being
    treated as simple redundancy.
    """
    engine = ScoringEngine()

    low_utility_score = engine.calculate_score(
        similarity_score=0.90,
        utility_score_a=0.1,
        utility_score_b=0.1,
        rarity_score_a=0.2,
        rarity_score_b=0.2,
    )

    high_utility_score = engine.calculate_score(
        similarity_score=0.90,
        utility_score_a=0.9,
        utility_score_b=0.9,
        rarity_score_a=0.2,
        rarity_score_b=0.2,
    )

    assert high_utility_score < low_utility_score


def test_high_rarity_reduces_redundancy() -> None:
    """
    Verify that rare information receives stronger protection.
    """
    engine = ScoringEngine()

    common_score = engine.calculate_score(
        similarity_score=0.90,
        utility_score_a=0.5,
        utility_score_b=0.5,
        rarity_score_a=0.1,
        rarity_score_b=0.1,
    )

    rare_score = engine.calculate_score(
        similarity_score=0.90,
        utility_score_a=0.5,
        utility_score_b=0.5,
        rarity_score_a=0.9,
        rarity_score_b=0.9,
    )

    assert rare_score < common_score