"""
INFORA - Semantic Embedding Engine

Uses Sentence Transformers to convert textual information units
into semantic embedding vectors.

Current model:
    all-MiniLM-L6-v2

This module only generates embeddings and calculates semantic similarity.
It does NOT make redundancy or deletion decisions.
"""

from __future__ import annotations

from typing import Iterable, List

import numpy as np
from sentence_transformers import SentenceTransformer

from models.information_unit import InformationUnit
from core.embedding_engine.embedding_result import EmbeddingResult


class EmbeddingEngine:
    """
    Generates semantic embeddings using a local Sentence Transformer model.
    """

    DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
    ) -> None:
        if not isinstance(model_name, str) or not model_name.strip():
            raise ValueError("model_name must be a non-empty string.")

        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def encode_texts(
        self,
        texts: Iterable[str],
        batch_size: int = 32,
    ) -> EmbeddingResult:
        """
        Convert a collection of texts into normalized embedding vectors.

        Args:
            texts: Collection of text strings.
            batch_size: Number of texts processed at once.

        Returns:
            EmbeddingResult containing the original texts and embeddings.
        """
        text_list = list(texts)

        if not text_list:
            return EmbeddingResult(
                texts=[],
                embeddings=[],
                model_name=self.model_name,
            )

        if any(
            not isinstance(text, str) or not text.strip()
            for text in text_list
        ):
            raise ValueError(
                "Every text must be a non-empty string."
            )

        if not isinstance(batch_size, int) or batch_size < 1:
            raise ValueError(
                "batch_size must be a positive integer."
            )

        embeddings = self.model.encode(
            text_list,
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        return EmbeddingResult(
            texts=text_list,
            embeddings=[
                embedding.astype(np.float32).tolist()
                for embedding in embeddings
            ],
            model_name=self.model_name,
        )

    def encode_information_units(
        self,
        information_units: List[InformationUnit],
        batch_size: int = 32,
    ) -> List[InformationUnit]:
        """
        Generate embeddings for InformationUnit objects.

        The generated embedding is stored directly inside each
        InformationUnit object.

        Args:
            information_units: Information units to encode.
            batch_size: Number processed at once.

        Returns:
            The same information units with embeddings attached.
        """
        if not isinstance(information_units, list):
            raise TypeError(
                "information_units must be a list."
            )

        if not information_units:
            return []

        texts = [unit.text for unit in information_units]

        result = self.encode_texts(
            texts=texts,
            batch_size=batch_size,
        )

        for unit, embedding in zip(
            information_units,
            result.embeddings,
            strict=True,
        ):
            unit.embedding = embedding

        return information_units

    @staticmethod
    def cosine_similarity(
        embedding_a: List[float],
        embedding_b: List[float],
    ) -> float:
        """
        Calculate cosine similarity between two embedding vectors.

        Since embeddings are normalized during encoding, the calculation
        is equivalent to their dot product.

        Returns:
            Similarity in approximately the range [-1, 1].
        """
        if not embedding_a or not embedding_b:
            raise ValueError(
                "Embeddings cannot be empty."
            )

        vector_a = np.asarray(
            embedding_a,
            dtype=np.float32,
        )

        vector_b = np.asarray(
            embedding_b,
            dtype=np.float32,
        )

        if vector_a.shape != vector_b.shape:
            raise ValueError(
                "Embedding vectors must have the same dimensions."
            )

        norm_a = np.linalg.norm(vector_a)
        norm_b = np.linalg.norm(vector_b)

        if norm_a == 0 or norm_b == 0:
            raise ValueError(
                "Embedding vector norm cannot be zero."
            )

        similarity = float(
            np.dot(vector_a, vector_b)
            / (norm_a * norm_b)
        )

        return similarity