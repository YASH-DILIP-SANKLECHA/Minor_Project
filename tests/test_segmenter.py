"""
INFORA - Sentence Segmenter Tests
"""

import pytest

from core.segmenter.sentence_segmenter import SentenceSegmenter
from models.document import Document


def test_segment_single_document() -> None:
    segmenter = SentenceSegmenter()

    document = Document(
        document_id="doc_000001",
        content=(
            "India has a population of 1.46 billion. "
            "Delhi is the capital of India. "
            "The population is changing over time."
        ),
    )

    units = segmenter.segment_document(document)

    assert len(units) == 3

    assert units[0].information_unit_id == (
        "doc_000001_unit_0001"
    )

    assert units[1].information_unit_id == (
        "doc_000001_unit_0002"
    )

    assert units[2].information_unit_id == (
        "doc_000001_unit_0003"
    )

    assert units[0].document_id == "doc_000001"
    assert units[0].unit_index == 1

    assert units[0].text == (
        "India has a population of 1.46 billion."
    )


def test_segment_multiple_documents() -> None:
    segmenter = SentenceSegmenter()

    documents = [
        Document(
            document_id="doc_000001",
            content="India is a country. Delhi is its capital.",
        ),
        Document(
            document_id="doc_000002",
            content="Bengaluru is a technology hub.",
        ),
    ]

    units = segmenter.segment_documents(documents)

    assert len(units) == 3

    assert units[0].document_id == "doc_000001"
    assert units[1].document_id == "doc_000001"
    assert units[2].document_id == "doc_000002"


def test_empty_document_returns_no_units() -> None:
    segmenter = SentenceSegmenter()

    document = Document(
        document_id="doc_000001",
        content="   ",
    )

    units = segmenter.segment_document(document)

    assert units == []


def test_invalid_document_type_raises_error() -> None:
    segmenter = SentenceSegmenter()

    with pytest.raises(TypeError):
        segmenter.segment_document(
            "This is not a Document object."
        )