"""
INFORA - Embedding Result Model
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class EmbeddingResult:
    """
    Stores embedding-generation results.
    """

    texts: List[str]
    embeddings: List[List[float]]
    model_name: str

    def __post_init__(self) -> None:
        if not isinstance(self.texts, list):
            raise TypeError("texts must be a list.")

        if not isinstance(self.embeddings, list):
            raise TypeError("embeddings must be a list.")

        if len(self.texts) != len(self.embeddings):
            raise ValueError(
                "texts and embeddings must have the same length."
            )

        if not isinstance(self.model_name, str):
            raise TypeError(
                "model_name must be a string."
            )

    @property
    def count(self) -> int:
        """Return the number of embedded texts."""
        return len(self.texts)

    @property
    def dimension(self) -> int:
        """Return the dimensionality of the embeddings."""
        if not self.embeddings:
            return 0

        return len(self.embeddings[0])

    def to_dict(self) -> Dict[str, Any]:
        """Convert the result into a serializable dictionary."""
        return {
            "texts": self.texts,
            "embeddings": self.embeddings,
            "model_name": self.model_name,
            "count": self.count,
            "dimension": self.dimension,
        }