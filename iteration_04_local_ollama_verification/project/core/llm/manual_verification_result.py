"""
Phase 9 manual-verification-required result model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ManualVerificationResult:
    """Represent one contradiction that needs user correction."""

    case_number: int
    information_unit_id_a: str
    information_unit_id_b: str
    text_a: str
    text_b: str

    status: str = "MANUAL_VERIFICATION_REQUIRED"

    message: str = (
        "Manual verification required: this contradiction could not be "
        "reliably resolved automatically from the model's learned knowledge. "
        "Please review and correct the conflicting information manually."
    )

    EXPECTED_STATUS = "MANUAL_VERIFICATION_REQUIRED"

    def __post_init__(self) -> None:
        if not isinstance(self.case_number, int):
            raise TypeError("case_number must be an integer.")

        if self.case_number < 1:
            raise ValueError(
                "case_number must be greater than zero."
            )

        if not isinstance(self.information_unit_id_a, str):
            raise TypeError(
                "information_unit_id_a must be a string."
            )

        if not isinstance(self.information_unit_id_b, str):
            raise TypeError(
                "information_unit_id_b must be a string."
            )

        if not isinstance(self.text_a, str):
            raise TypeError("text_a must be a string.")

        if not isinstance(self.text_b, str):
            raise TypeError("text_b must be a string.")

        if not self.information_unit_id_a.strip():
            raise ValueError(
                "information_unit_id_a cannot be empty."
            )

        if not self.information_unit_id_b.strip():
            raise ValueError(
                "information_unit_id_b cannot be empty."
            )

        if self.information_unit_id_a == self.information_unit_id_b:
            raise ValueError(
                "A manual verification pair cannot contain "
                "the same unit twice."
            )

        if not self.text_a.strip() or not self.text_b.strip():
            raise ValueError(
                "Both statements must contain text."
            )

        if self.status != self.EXPECTED_STATUS:
            raise ValueError(
                f"status must be {self.EXPECTED_STATUS}."
            )

        if not self.message.strip():
            raise ValueError(
                "message cannot be empty."
            )

    def to_dict(self) -> dict[str, Any]:
        """Convert the result to a JSON-compatible dictionary."""

        return {
            "case_number": self.case_number,
            "information_unit_id_a": self.information_unit_id_a,
            "information_unit_id_b": self.information_unit_id_b,
            "text_a": self.text_a,
            "text_b": self.text_b,
            "status": self.status,
            "message": self.message,
        }