"""Phase 9 verification data models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ALLOWED_DECISIONS = frozenset(
    {"KEEP_FIRST", "KEEP_SECOND", "MANUAL_REVIEW"}
)


@dataclass(frozen=True)
class VerificationCandidate:
    """One contradiction that is eligible for Qwen verification."""

    information_unit_id_a: str
    information_unit_id_b: str
    text_a: str
    text_b: str
    context: str = ""

    def __post_init__(self) -> None:
        if not self.information_unit_id_a.strip():
            raise ValueError("information_unit_id_a cannot be empty.")
        if not self.information_unit_id_b.strip():
            raise ValueError("information_unit_id_b cannot be empty.")
        if self.information_unit_id_a == self.information_unit_id_b:
            raise ValueError("A contradiction cannot contain the same unit twice.")
        if not self.text_a.strip() or not self.text_b.strip():
            raise ValueError("Both statements must contain text.")

    @property
    def pair_key(self) -> tuple[str, str]:
        return tuple(sorted((self.information_unit_id_a, self.information_unit_id_b)))

    @property
    def reason(self) -> str:
        """Compatibility alias for older callers that used ``reason``."""
        return self.context

    def to_dict(self) -> dict[str, Any]:
        return {
            "information_unit_id_a": self.information_unit_id_a,
            "information_unit_id_b": self.information_unit_id_b,
            "text_a": self.text_a,
            "text_b": self.text_b,
            "context": self.context,
        }


@dataclass(frozen=True)
class VerificationResult:
    """Store one Qwen decision for one contradiction candidate."""

    case_number: int
    information_unit_id_a: str
    information_unit_id_b: str
    text_a: str
    text_b: str
    decision: str
    raw_response: str = ""
    reason: str = ""

    ALLOWED_DECISIONS = ALLOWED_DECISIONS

    def __post_init__(self) -> None:
        if self.case_number < 1:
            raise ValueError("case_number must be greater than zero.")
        if not self.information_unit_id_a.strip():
            raise ValueError("information_unit_id_a cannot be empty.")
        if not self.information_unit_id_b.strip():
            raise ValueError("information_unit_id_b cannot be empty.")
        if self.information_unit_id_a == self.information_unit_id_b:
            raise ValueError("A verification pair cannot contain the same unit twice.")
        if not self.text_a.strip() or not self.text_b.strip():
            raise ValueError("Both statements must contain text.")
        if self.decision not in ALLOWED_DECISIONS:
            raise ValueError(
                "decision must be KEEP_FIRST, KEEP_SECOND, or MANUAL_REVIEW."
            )

    @property
    def requires_manual_verification(self) -> bool:
        return self.decision == "MANUAL_REVIEW"

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_number": self.case_number,
            "information_unit_id_a": self.information_unit_id_a,
            "information_unit_id_b": self.information_unit_id_b,
            "text_a": self.text_a,
            "text_b": self.text_b,
            "decision": self.decision,
            "reason": self.reason,
        }
