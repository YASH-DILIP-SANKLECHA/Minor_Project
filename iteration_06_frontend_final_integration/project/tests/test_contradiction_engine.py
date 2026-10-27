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


def test_different_serial_numbers_are_not_a_factual_contradiction() -> None:
    """Dataset row labels must not be treated as competing factual values."""
    engine = ContradictionEngine()
    pair = RedundancyPair(
        information_unit_id_a="unit_001",
        information_unit_id_b="unit_002",
        similarity_score=0.98,
        redundancy_score=0.98,
        text_a="Sample 0093: the saffron sandstone travels beyond the harbor.",
        text_b="Sample 3789: the saffron sandstone travels beyond the harbor.",
    )
    first = ExtractionResult("unit_001", pair.text_a, values=["0093"])
    second = ExtractionResult("unit_002", pair.text_b, values=["3789"])

    assert engine.analyze_pair(pair, first, second) is None


def test_identical_fact_is_a_duplicate_not_a_contradiction() -> None:
    engine = ContradictionEngine()
    pair = RedundancyPair(
        information_unit_id_a="unit_001",
        information_unit_id_b="unit_002",
        similarity_score=1.0,
        redundancy_score=1.0,
        text_a="React is a JavaScript library for user interfaces.",
        text_b="React is a JavaScript library for user interfaces.",
    )
    extraction = ExtractionResult("unit_001", pair.text_a)
    repeated = ExtractionResult("unit_002", pair.text_b)

    assert engine.analyze_pair(pair, extraction, repeated) is None


def test_shared_possessive_word_does_not_make_private_claims_related() -> None:
    engine = ContradictionEngine()
    pair = RedundancyPair(
        information_unit_id_a="unit_001",
        information_unit_id_b="unit_002",
        similarity_score=0.91,
        redundancy_score=0.91,
        text_a="Our classroom is room 204.",
        text_b="Our delivery gate code is 8843.",
    )
    first = ExtractionResult("unit_001", pair.text_a, values=["204"])
    second = ExtractionResult("unit_002", pair.text_b, values=["8843"])

    assert engine.analyze_pair(pair, first, second) is None


def test_personal_named_claims_reach_manual_candidate_stage() -> None:
    engine = ContradictionEngine()
    pair = RedundancyPair(
        information_unit_id_a="unit_001",
        information_unit_id_b="unit_002",
        similarity_score=0.86,
        redundancy_score=0.86,
        text_a="My dog is named Bruno.",
        text_b="My dog is named Brownie.",
    )
    first = ExtractionResult("unit_001", pair.text_a)
    second = ExtractionResult("unit_002", pair.text_b)

    assert engine.analyze_pair(pair, first, second) is not None


def test_spelled_quantity_conflict_reaches_local_ai_verification() -> None:
    """Public written-number conflicts are automatic-Qwen candidates."""
    engine = ContradictionEngine()
    pair = RedundancyPair(
        information_unit_id_a="unit_001",
        information_unit_id_b="unit_002",
        # A changed factual value can lower embedding similarity.  It must
        # still reach Qwen once the generic factual structure agrees.
        similarity_score=0.45,
        redundancy_score=0.45,
        text_a="There are seven weeks in a day.",
        text_b="There are twelve weeks in a day.",
    )
    first = ExtractionResult("unit_001", pair.text_a, values=["seven"])
    second = ExtractionResult("unit_002", pair.text_b, values=["twelve"])

    assert engine.analyze_pair(pair, first, second) is not None


def test_different_ranked_descriptions_of_one_subject_are_compared() -> None:
    """Highest/deepest claims share a rank slot and can conflict."""
    engine = ContradictionEngine()
    pair = RedundancyPair(
        information_unit_id_a="unit_001",
        information_unit_id_b="unit_002",
        similarity_score=0.70,
        redundancy_score=0.70,
        text_a="Mount Everest is the highest mountain above sea level.",
        text_b="Mount Everest is the deepest ocean trench.",
    )
    first = ExtractionResult("unit_001", pair.text_a)
    second = ExtractionResult("unit_002", pair.text_b)

    assert engine.analyze_pair(pair, first, second) is not None


def test_single_letter_personal_storage_values_reach_manual_stage() -> None:
    """Garage A and garage B are different values, not interchangeable articles."""
    engine = ContradictionEngine()
    pair = RedundancyPair(
        information_unit_id_a="unit_001",
        information_unit_id_b="unit_002",
        similarity_score=0.91,
        redundancy_score=0.91,
        text_a="My bicycle is stored in garage A.",
        text_b="My bicycle is stored in garage B.",
    )
    first = ExtractionResult("unit_001", pair.text_a)
    second = ExtractionResult("unit_002", pair.text_b)

    assert engine.analyze_pair(pair, first, second) is not None


def test_related_supporting_facts_are_not_sent_for_contradiction_review() -> None:
    """Different properties of one subject are not competing claims."""
    engine = ContradictionEngine()
    pair = RedundancyPair(
        information_unit_id_a="unit_001",
        information_unit_id_b="unit_002",
        similarity_score=0.88,
        redundancy_score=0.88,
        text_a="Gold has the chemical symbol Au.",
        text_b="Gold is a chemical element.",
    )
    first = ExtractionResult("unit_001", pair.text_a, values=["Au"])
    second = ExtractionResult("unit_002", pair.text_b)

    assert engine.analyze_pair(pair, first, second) is None


def test_general_statement_contained_in_detailed_fact_is_not_conflict() -> None:
    """A more detailed version of the same fact is supporting context."""
    engine = ContradictionEngine()
    pair = RedundancyPair(
        information_unit_id_a="unit_001",
        information_unit_id_b="unit_002",
        similarity_score=0.88,
        redundancy_score=0.88,
        text_a="The Nile is a major river in Africa.",
        text_b="The Nile is a river.",
    )
    first = ExtractionResult("unit_001", pair.text_a)
    second = ExtractionResult("unit_002", pair.text_b)

    assert engine.analyze_pair(pair, first, second) is None


def test_directional_modifier_in_assigned_value_is_a_conflict() -> None:
    """A place/name modifier is a competing value, not extra detail."""
    engine = ContradictionEngine()
    pair = RedundancyPair(
        information_unit_id_a="unit_001",
        information_unit_id_b="unit_002",
        similarity_score=0.92,
        redundancy_score=0.92,
        text_a="The capital of Exampleland is Example City.",
        text_b="The capital of Exampleland is North Example City.",
    )
    first = ExtractionResult("unit_001", pair.text_a)
    second = ExtractionResult("unit_002", pair.text_b)

    assert engine.analyze_pair(pair, first, second) is not None


def test_new_name_modifier_in_assigned_value_is_a_conflict() -> None:
    """The containment guard must not hide New X versus X values."""
    engine = ContradictionEngine()
    pair = RedundancyPair(
        information_unit_id_a="unit_001",
        information_unit_id_b="unit_002",
        similarity_score=0.92,
        redundancy_score=0.92,
        text_a="The administrative centre of Exampleland is York.",
        text_b="The administrative centre of Exampleland is New York.",
    )
    first = ExtractionResult("unit_001", pair.text_a)
    second = ExtractionResult("unit_002", pair.text_b)

    assert engine.analyze_pair(pair, first, second) is not None


def test_named_value_suffix_is_not_treated_as_descriptive_entailment() -> None:
    """Lake View versus View must remain a candidate without a name list."""
    engine = ContradictionEngine()
    pair = RedundancyPair(
        information_unit_id_a="unit_001",
        information_unit_id_b="unit_002",
        similarity_score=0.92,
        redundancy_score=0.92,
        text_a="The headquarters of Example Institute is View.",
        text_b="The headquarters of Example Institute is Lake View.",
    )
    first = ExtractionResult("unit_001", pair.text_a)
    second = ExtractionResult("unit_002", pair.text_b)

    assert engine.analyze_pair(pair, first, second) is not None


def test_lowercase_descriptive_entailment_remains_protected() -> None:
    """Ordinary descriptions are still not routed as contradictions."""
    engine = ContradictionEngine()
    pair = RedundancyPair(
        information_unit_id_a="unit_001",
        information_unit_id_b="unit_002",
        similarity_score=0.92,
        redundancy_score=0.92,
        text_a="Silver is a metal.",
        text_b="Silver is a precious metal.",
    )
    first = ExtractionResult("unit_001", pair.text_a)
    second = ExtractionResult("unit_002", pair.text_b)

    assert engine.analyze_pair(pair, first, second) is None


def test_negated_claim_is_not_treated_as_descriptive_detail() -> None:
    """Adding a negation reverses a claim rather than elaborating it."""
    engine = ContradictionEngine()
    pair = RedundancyPair(
        information_unit_id_a="unit_001",
        information_unit_id_b="unit_002",
        similarity_score=0.94,
        redundancy_score=0.94,
        text_a="The surface is conductive.",
        text_b="The surface is not conductive.",
    )
    first = ExtractionResult("unit_001", pair.text_a)
    second = ExtractionResult("unit_002", pair.text_b)

    assert engine.analyze_pair(pair, first, second) is not None


def test_explicitly_different_time_scopes_are_not_a_contradiction() -> None:
    """Historical snapshots with distinct stated dates can both be valid."""
    engine = ContradictionEngine()
    pair = RedundancyPair(
        information_unit_id_a="unit_001",
        information_unit_id_b="unit_002",
        similarity_score=0.94,
        redundancy_score=0.94,
        text_a="Example Corporation is led by Ana as of 2020.",
        text_b="Example Corporation is led by Ben as of 2025.",
    )
    first = ExtractionResult("unit_001", pair.text_a, values=["2020"])
    second = ExtractionResult("unit_002", pair.text_b, values=["2025"])

    assert engine.analyze_pair(pair, first, second) is None


def test_different_factual_dates_still_reach_verification() -> None:
    """A changed date value is not confused with an explicit time scope."""
    engine = ContradictionEngine()
    pair = RedundancyPair(
        information_unit_id_a="unit_001",
        information_unit_id_b="unit_002",
        similarity_score=0.94,
        redundancy_score=0.94,
        text_a="Example Museum was founded in 1984.",
        text_b="Example Museum was founded in 1986.",
    )
    first = ExtractionResult("unit_001", pair.text_a, values=["1984"])
    second = ExtractionResult("unit_002", pair.text_b, values=["1986"])

    assert engine.analyze_pair(pair, first, second) is not None


def test_different_numeric_properties_of_one_subject_are_not_conflicts() -> None:
    """One subject can have independent numeric properties."""
    engine = ContradictionEngine()
    pair = RedundancyPair(
        information_unit_id_a="unit_001",
        information_unit_id_b="unit_002",
        similarity_score=0.92,
        redundancy_score=0.92,
        text_a="Exampleland has 28 provinces.",
        text_b="Exampleland has 8 districts.",
    )
    first = ExtractionResult("unit_001", pair.text_a, values=["28"])
    second = ExtractionResult("unit_002", pair.text_b, values=["8"])

    assert engine.analyze_pair(pair, first, second) is None


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
