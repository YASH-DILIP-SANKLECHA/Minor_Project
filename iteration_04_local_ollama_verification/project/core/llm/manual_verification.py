"""Phase 9 manual-verification flag creation."""

from __future__ import annotations

from core.llm.manual_verification_result import ManualVerificationResult
from core.llm.verification_result import VerificationResult


class ManualVerification:
    """Create manual-verification flags without interactive input."""

    def create_flag(
        self,
        result: VerificationResult,
    ) -> ManualVerificationResult:
        """Create a flag only for a MANUAL_REVIEW result."""

        if result.decision != "MANUAL_REVIEW":
            raise ValueError(
                "A manual-verification flag requires "
                "a MANUAL_REVIEW decision."
            )

        return ManualVerificationResult(
            case_number=result.case_number,
            information_unit_id_a=result.information_unit_id_a,
            information_unit_id_b=result.information_unit_id_b,
            text_a=result.text_a,
            text_b=result.text_b,
        )