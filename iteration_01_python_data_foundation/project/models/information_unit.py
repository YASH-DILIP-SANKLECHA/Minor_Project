"""
INFORA - Information Unit Model
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class InformationUnit:
    """
    Represents the smallest currently processed textual unit.

    In Phase 1 this is a sentence.
    Later this model can be extended with:
    - embeddings
    - entities
    - properties
    - values
    - dates
    - source information
    - redundancy scores
    - utility scores
    - rarity scores
    - contradiction information
    """

    information_unit_id: str
    document_id: str
    text: str
    unit_index: int

    metadata: Dict[str, Any] = field(default_factory=dict)

    embedding: Optional[list[float]] = None
    redundancy_score: Optional[float] = None
    utility_score: Optional[float] = None
    rarity_score: Optional[float] = None

    def __post_init__(self) -> None:
        if not self.information_unit_id.strip():
            raise ValueError("information_unit_id cannot be empty.")

        if not self.document_id.strip():
            raise ValueError("document_id cannot be empty.")

        if not isinstance(self.text, str):
            raise TypeError("text must be a string.")

        if not self.text.strip():
            raise ValueError("text cannot be empty.")

        if not isinstance(self.unit_index, int):
            raise TypeError("unit_index must be an integer.")

        if self.unit_index < 1:
            raise ValueError("unit_index must be greater than or equal to 1.")

        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dictionary.")

    def to_dict(self) -> Dict[str, Any]:
        """Convert the information unit into a serializable dictionary."""
        return {
            "information_unit_id": self.information_unit_id,
            "document_id": self.document_id,
            "text": self.text,
            "unit_index": self.unit_index,
            "metadata": self.metadata,
            "embedding": self.embedding,
            "redundancy_score": self.redundancy_score,
            "utility_score": self.utility_score,
            "rarity_score": self.rarity_score,
        }
        