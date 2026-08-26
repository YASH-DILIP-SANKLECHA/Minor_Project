"""
Minor Project One - Information Extractor Tests.
"""

from core.information_extractor.information_extractor import (
    InformationExtractor,
)
from models.information_unit import InformationUnit


def test_extract_numeric_value() -> None:
    """
    Verify that a numeric factual value is extracted correctly.
    """
    extractor = InformationExtractor()

    unit = InformationUnit(
        information_unit_id="unit_001",
        document_id="doc_001",
        text="India has a population of 1.46 billion people.",
        unit_index=1,
    )

    result = extractor.extract(unit)

    assert "1.46 billion" in result.values
    assert "1.46" in result.numbers


def test_extract_year() -> None:
    """
    Verify that a four-digit year is extracted correctly.
    """
    extractor = InformationExtractor()

    unit = InformationUnit(
        information_unit_id="unit_001",
        document_id="doc_001",
        text="Population increased during 2025.",
        unit_index=1,
    )

    result = extractor.extract(unit)

    assert "2025" in result.dates


def test_original_text_is_preserved() -> None:
    """
    Verify that information extraction never modifies the source text.
    """
    extractor = InformationExtractor()

    original_text = (
        "India has a population of 1.46 billion people."
    )

    unit = InformationUnit(
        information_unit_id="unit_001",
        document_id="doc_001",
        text=original_text,
        unit_index=1,
    )

    result = extractor.extract(unit)

    assert result.text == original_text


def test_extract_many() -> None:
    """
    Verify extraction across multiple information units.
    """
    extractor = InformationExtractor()

    units = [
        InformationUnit(
            information_unit_id="unit_001",
            document_id="doc_001",
            text="India has 1.46 billion people.",
            unit_index=1,
        ),
        InformationUnit(
            information_unit_id="unit_002",
            document_id="doc_002",
            text="The population changed in 2025.",
            unit_index=1,
        ),
    ]

    results = extractor.extract_many(units)

    assert len(results) == 2