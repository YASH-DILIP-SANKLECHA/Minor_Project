"""
INFORA - Document Model
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class Document:
    """
    Represents one document/article in the dataset.
    """

    document_id: str
    content: str
    source_type: str = "txt"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.document_id.strip():
            raise ValueError("document_id cannot be empty.")

        if not isinstance(self.content, str):
            raise TypeError("content must be a string.")

        if not isinstance(self.source_type, str):
            raise TypeError("source_type must be a string.")

        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dictionary.")

    @property
    def character_count(self) -> int:
        """Return the number of characters in the document."""
        return len(self.content)

    @property
    def word_count(self) -> int:
        """Return the approximate number of whitespace-separated words."""
        return len(self.content.split())

    def to_dict(self) -> Dict[str, Any]:
        """Convert the document into a serializable dictionary."""
        return {
            "document_id": self.document_id,
            "content": self.content,
            "source_type": self.source_type,
            "metadata": self.metadata,
            "character_count": self.character_count,
            "word_count": self.word_count,
        }