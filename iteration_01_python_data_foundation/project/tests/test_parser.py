"""
INFORA - Parser Tests
"""

from pathlib import Path

import pytest

from core.parser.document_parser import DocumentParser


def test_parse_heading_based_dataset() -> None:
    parser = DocumentParser()

    text = """
    Article 1
    India has a population of 1.46 billion.
    Delhi is the capital of India.

    Article 2
    Bengaluru is known as a technology hub.
    """

    documents = parser.parse_text(text)

    assert len(documents) == 2

    assert documents[0].document_id == "doc_000001"
    assert documents[1].document_id == "doc_000002"

    assert "India has a population" in documents[0].content
    assert "Bengaluru" in documents[1].content


def test_parse_blank_line_dataset() -> None:
    parser = DocumentParser()

    text = """
    India has a population of 1.46 billion.

    Delhi is the capital of India.

    Bengaluru is a technology hub.
    """

    documents = parser.parse_text(text)

    assert len(documents) == 3

    assert documents[0].content == (
        "India has a population of 1.46 billion."
    )

    assert documents[1].content == (
        "Delhi is the capital of India."
    )

    assert documents[2].content == (
        "Bengaluru is a technology hub."
    )


def test_parse_file(tmp_path: Path) -> None:
    parser = DocumentParser()

    dataset_file = tmp_path / "dataset.txt"

    dataset_file.write_text(
        """
        Article 1
        India has a population of 1.46 billion.

        Article 2
        Delhi is the capital of India.
        """,
        encoding="utf-8",
    )

    documents = parser.parse_file(dataset_file)

    assert len(documents) == 2
    assert documents[0].source_type == "txt"


def test_empty_text_raises_error() -> None:
    parser = DocumentParser()

    with pytest.raises(ValueError, match="Dataset text is empty"):
        parser.parse_text("   ")


def test_missing_file_raises_error(tmp_path: Path) -> None:
    parser = DocumentParser()

    missing_file = tmp_path / "does_not_exist.txt"

    with pytest.raises(FileNotFoundError):
        parser.parse_file(missing_file)