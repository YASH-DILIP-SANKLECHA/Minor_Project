"""
Minor Project One - Information Extraction Result.

This module defines the data structure used to store information
extracted from an InformationUnit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExtractionResult:
    """
    Store structured information extracted from one information unit.

    The original sentence is preserved unchanged in `text`.
    """

    information_unit_id: str
    text: str
    entities: list[dict[str, Any]] = field(default_factory=list)
    values: list[str] = field(default_factory=list)
    dates: list[str] = field(default_factory=list)
    numbers: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """
        Validate the extraction result after it is created.
        """
        if not self.information_unit_id.strip():
            raise ValueError(
                "information_unit_id cannot be empty."
            )

        if not self.text.strip():
            raise ValueError(
                "text cannot be empty."
            )

    @property
    def entity_count(self) -> int:
        """
        Return the number of extracted named entities.
        """
        return len(self.entities)

    @property
    def value_count(self) -> int:
        """
        Return the number of extracted value expressions.
        """
        return len(self.values)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the extraction result into a dictionary.

        This makes the result easy to store later in PostgreSQL
        or return through FastAPI.
        """
        return {
            "information_unit_id": self.information_unit_id,
            "text": self.text,
            "entities": self.entities,
            "values": self.values,
            "dates": self.dates,
            "numbers": self.numbers,
            "entity_count": self.entity_count,
            "value_count": self.value_count,
        }