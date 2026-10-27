"""
Minor Project One - Optimization Result.

Stores the result of Phase 8 optimization, including:
- retained information units
- removed information units
- change records
- output statistics
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChangeRecord:
    """
    Store one reversible dataset modification.

    A change record records exactly what was removed and why.
    """

    information_unit_id: str
    document_id: str
    original_text: str
    reason: str
    decision: str
    confidence: float
    paired_information_unit_id: str

    def __post_init__(self) -> None:
        """Validate the change record."""
        if not self.information_unit_id.strip():
            raise ValueError(
                "information_unit_id cannot be empty."
            )

        if not self.document_id.strip():
            raise ValueError(
                "document_id cannot be empty."
            )

        if not self.original_text.strip():
            raise ValueError(
                "original_text cannot be empty."
            )

        if not self.reason.strip():
            raise ValueError(
                "reason cannot be empty."
            )

        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError(
                "confidence must be between 0.0 and 1.0."
            )

    def to_dict(self) -> dict[str, Any]:
        """Convert the change record into a serializable dictionary."""
        return {
            "information_unit_id": self.information_unit_id,
            "document_id": self.document_id,
            "original_text": self.original_text,
            "reason": self.reason,
            "decision": self.decision,
            "confidence": self.confidence,
            "paired_information_unit_id": (
                self.paired_information_unit_id
            ),
        }


@dataclass
class OptimizationResult:
    """
    Store the complete Phase 8 optimization result.
    """

    retained_unit_ids: list[str] = field(default_factory=list)
    removed_unit_ids: list[str] = field(default_factory=list)
    change_records: list[ChangeRecord] = field(
        default_factory=list
    )

    original_unit_count: int = 0
    final_unit_count: int = 0

    def __post_init__(self) -> None:
        """Validate and normalize optimization statistics."""
        if self.original_unit_count < 0:
            raise ValueError(
                "original_unit_count cannot be negative."
            )

        if self.final_unit_count < 0:
            raise ValueError(
                "final_unit_count cannot be negative."
            )

        if self.final_unit_count > self.original_unit_count:
            raise ValueError(
                "final_unit_count cannot exceed original_unit_count."
            )

    @property
    def removed_count(self) -> int:
        """Return the number of removed information units."""
        return len(self.removed_unit_ids)

    @property
    def reduction_percentage(self) -> float:
        """Return dataset information-unit reduction percentage."""
        if self.original_unit_count == 0:
            return 0.0

        return (
            self.removed_count
            / self.original_unit_count
            * 100.0
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert the optimization result into a serializable dictionary."""
        return {
            "retained_unit_ids": self.retained_unit_ids,
            "removed_unit_ids": self.removed_unit_ids,
            "change_records": [
                record.to_dict()
                for record in self.change_records
            ],
            "original_unit_count": self.original_unit_count,
            "final_unit_count": self.final_unit_count,
            "removed_count": self.removed_count,
            "reduction_percentage": self.reduction_percentage,
        }