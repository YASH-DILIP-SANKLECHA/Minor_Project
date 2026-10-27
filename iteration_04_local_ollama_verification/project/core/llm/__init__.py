"""Phase 9 local-AI contradiction verification."""

from core.llm.manual_verification import ManualVerification
from core.llm.manual_verification_result import ManualVerificationResult
from core.llm.ollama_client import OllamaClient
from core.llm.verification_engine import VerificationEngine
from core.llm.verification_result import (
    VerificationCandidate,
    VerificationResult,
)

__all__ = [
    "ManualVerification",
    "ManualVerificationResult",
    "OllamaClient",
    "VerificationCandidate",
    "VerificationEngine",
    "VerificationResult",
]