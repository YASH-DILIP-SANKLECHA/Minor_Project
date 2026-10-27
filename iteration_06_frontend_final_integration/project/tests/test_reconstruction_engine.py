"""
Minor Project One - Reconstruction Engine Tests.
"""

from core.reconstruction.reconstruction_engine import (
    ReconstructionEngine,
)
from models.information_unit import InformationUnit


def make_unit(
    unit_id: str,
    document_id: str,
    text: str,
    index: int,
) -> InformationUnit:
    """
    Create an InformationUnit for reconstruction testing.
    """

    # Construct the information unit with its original position.
    return InformationUnit(
        information_unit_id=unit_id,
        document_id=document_id,
        text=text,
        unit_index=index,
    )


def test_reconstruct_retained_units() -> None:
    """
    Verify that only retained information units appear in output.
    """

    units = [
        make_unit(
            "unit_001",
            "doc_001",
            "First sentence.",
            1,
        ),
        make_unit(
            "unit_002",
            "doc_001",
            "Second sentence.",
            2,
        ),
        make_unit(
            "unit_003",
            "doc_001",
            "Third sentence.",
            3,
        ),
    ]

    result = ReconstructionEngine().reconstruct(
        units,
        [
            "unit_001",
            "unit_003",
        ],
    )

    assert "First sentence." in result
    assert "Second sentence." not in result
    assert "Third sentence." in result
    assert "First sentence.\nThird sentence." in result


def test_reconstruct_preserves_sentence_order() -> None:
    """
    Verify that retained sentences stay in their original order.
    """

    units = [
        make_unit(
            "unit_001",
            "doc_001",
            "First.",
            1,
        ),
        make_unit(
            "unit_002",
            "doc_001",
            "Second.",
            2,
        ),
        make_unit(
            "unit_003",
            "doc_001",
            "Third.",
            3,
        ),
    ]

    result = ReconstructionEngine().reconstruct_from_units(
        units
    )

    first_position = result.index("First.")
    second_position = result.index("Second.")
    third_position = result.index("Third.")

    assert (
        first_position
        < second_position
        < third_position
    )


def test_multiple_documents_are_reconstructed_separately() -> None:
    """
    Verify that different documents remain separated.
    """

    units = [
        make_unit(
            "unit_001",
            "doc_001",
            "Document one.",
            1,
        ),
        make_unit(
            "unit_002",
            "doc_002",
            "Document two.",
            1,
        ),
    ]

    result = ReconstructionEngine().reconstruct_from_units(
        units
    )

    assert "\n\n" in result
    assert "Document one." in result
    assert "Document two." in result
