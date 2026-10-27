"""
INFORA - Embedding Engine Tests
"""

import pytest

from core.embedding_engine.embedding_engine import EmbeddingEngine
from models.information_unit import InformationUnit


@pytest.fixture(scope="module")
def embedding_engine() -> EmbeddingEngine:
    """
    Create one shared embedding engine for the test module.

    The first execution downloads the Sentence Transformer model.
    """
    return EmbeddingEngine()


def test_encode_texts(
    embedding_engine: EmbeddingEngine,
) -> None:
    texts = [
        "India has a population of 1.46 billion.",
        "Approximately 1.46 billion people live in India.",
    ]

    result = embedding_engine.encode_texts(texts)

    assert result.count == 2
    assert result.dimension > 0
    assert len(result.embeddings) == 2
    assert len(result.embeddings[0]) == result.dimension
    assert len(result.embeddings[1]) == result.dimension
    assert result.model_name == "all-MiniLM-L6-v2"


def test_semantically_similar_sentences_have_high_similarity(
    embedding_engine: EmbeddingEngine,
) -> None:
    result = embedding_engine.encode_texts(
        [
            "India has a population of 1.46 billion.",
            "Approximately 1.46 billion people live in India.",
        ]
    )

    similarity = embedding_engine.cosine_similarity(
        result.embeddings[0],
        result.embeddings[1],
    )

    assert similarity > 0.70


def test_different_sentences_have_lower_similarity(
    embedding_engine: EmbeddingEngine,
) -> None:
    result = embedding_engine.encode_texts(
        [
            "India has a population of 1.46 billion.",
            "The Pacific Ocean is the largest ocean on Earth.",
        ]
    )

    similarity = embedding_engine.cosine_similarity(
        result.embeddings[0],
        result.embeddings[1],
    )

    assert similarity < 0.70


def test_information_units_receive_embeddings(
    embedding_engine: EmbeddingEngine,
) -> None:
    units = [
        InformationUnit(
            information_unit_id="doc_000001_unit_0001",
            document_id="doc_000001",
            text="India has a population of 1.46 billion.",
            unit_index=1,
        ),
        InformationUnit(
            information_unit_id="doc_000001_unit_0002",
            document_id="doc_000001",
            text="Delhi is the capital of India.",
            unit_index=2,
        ),
    ]

    result = embedding_engine.encode_information_units(units)

    assert len(result) == 2

    for unit in result:
        assert unit.embedding is not None
        assert len(unit.embedding) > 0


def test_empty_texts_return_empty_result(
    embedding_engine: EmbeddingEngine,
) -> None:
    result = embedding_engine.encode_texts([])

    assert result.count == 0
    assert result.dimension == 0
    assert result.embeddings == []