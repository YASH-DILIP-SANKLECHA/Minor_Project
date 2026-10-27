"""Phase 9 local Qwen contradiction verification tests."""

from __future__ import annotations

import json

import pytest

from core.contradiction_engine.contradiction_result import ContradictionResult
from core.llm.manual_verification import ManualVerification
from core.llm.manual_verification_result import ManualVerificationResult
from core.llm.verification_engine import VerificationEngine
from core.llm.verification_result import VerificationCandidate, VerificationResult
from core.optimizer.optimization_result import OptimizationResult
from models.information_unit import InformationUnit
from services.redundancy_analysis_service import RedundancyAnalysisService


def _contradiction(case_number: int) -> ContradictionResult:
    return ContradictionResult(
        information_unit_id_a=f"unit-{case_number}-a",
        information_unit_id_b=f"unit-{case_number}-b",
        text_a=f"Statement A for case {case_number}.",
        text_b=f"Statement B for case {case_number}.",
        similarity_score=0.95,
        value_a=["value-a"],
        value_b=["value-b"],
        contradiction_score=0.95,
        reason="conflicting factual values",
    )


def _candidate(case_number: int) -> VerificationCandidate:
    contradiction = _contradiction(case_number)
    return VerificationCandidate(
        information_unit_id_a=contradiction.information_unit_id_a,
        information_unit_id_b=contradiction.information_unit_id_b,
        text_a=contradiction.text_a,
        text_b=contradiction.text_b,
        context=contradiction.reason,
    )


class FakeOllamaClient:
    def __init__(self, responses: list[str] | str) -> None:
        self.responses = [responses] if isinstance(responses, str) else list(responses)
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if not self.responses:
            raise AssertionError("No fake Ollama response remains.")
        return self.responses.pop(0)


def test_prepare_candidates_accepts_only_phase6_contradictions() -> None:
    engine = VerificationEngine(client=FakeOllamaClient("KEEP_FIRST"))
    candidates = engine.prepare_candidates(
        phase6_contradictions=[_contradiction(1)]
    )

    assert len(candidates) == 1
    assert isinstance(candidates[0], VerificationCandidate)
    assert candidates[0].text_a == "Statement A for case 1."
    assert candidates[0].text_b == "Statement B for case 1."


def test_verify_processes_small_requests_and_preserves_order() -> None:
    client = FakeOllamaClient(
        ["KEEP_FIRST", "KEEP_SECOND", "MANUAL_REVIEW"]
    )
    engine = VerificationEngine(client=client)

    results = engine.verify(
        [_candidate(1), _candidate(2), _candidate(3)]
    )

    assert [item.case_number for item in results] == [1, 2, 3]
    assert [item.decision for item in results] == [
        "KEEP_FIRST",
        "KEEP_SECOND",
        "MANUAL_REVIEW",
    ]
    assert len(client.prompts) == 3
    assert "Statement A for case 1." in client.prompts[0]
    assert "Statement B for case 2." in client.prompts[1]
    assert "Statement A for case 3." in client.prompts[2]


def test_qwen_decision_is_not_hardcoded() -> None:
    client = FakeOllamaClient("KEEP_SECOND")
    engine = VerificationEngine(client=client)

    result = engine.verify([_candidate(1)])[0]

    assert result.decision == "KEEP_SECOND"


def test_ambiguous_qwen_response_is_rejected() -> None:
    client = FakeOllamaClient("KEEP_FIRST and KEEP_SECOND")
    engine = VerificationEngine(client=client)

    with pytest.raises(RuntimeError, match="ambiguous"):
        engine.verify([_candidate(1)])


def test_invalid_qwen_response_is_rejected_instead_of_guessing() -> None:
    client = FakeOllamaClient("I cannot determine the answer.")
    engine = VerificationEngine(client=client)

    with pytest.raises(RuntimeError):
        engine.verify([_candidate(1)])


def test_manual_verification_creates_only_a_flag() -> None:
    verification = VerificationResult(
        case_number=1,
        information_unit_id_a="a",
        information_unit_id_b="b",
        text_a="Statement 1",
        text_b="Statement 2",
        decision="MANUAL_REVIEW",
    )

    result = ManualVerification().create_flag(verification)

    assert isinstance(result, ManualVerificationResult)
    assert result.status == "MANUAL_VERIFICATION_REQUIRED"
    assert "manual" in result.message.lower()
    assert not hasattr(result, "action")
    assert not hasattr(result, "choice")


def test_manual_verification_rejects_ai_resolved_case() -> None:
    verification = VerificationResult(
        case_number=1,
        information_unit_id_a="a",
        information_unit_id_b="b",
        text_a="Statement 1",
        text_b="Statement 2",
        decision="KEEP_FIRST",
    )

    with pytest.raises(ValueError):
        ManualVerification().create_flag(verification)


def test_service_ai_decisions_override_phase8_for_contradiction_pairs() -> None:
    service = RedundancyAnalysisService.__new__(RedundancyAnalysisService)
    service.last_information_units = [
        InformationUnit("a", "doc1", "Statement A", 1),
        InformationUnit("b", "doc2", "Statement B", 1),
        InformationUnit("c", "doc3", "Statement C", 1),
    ]
    service.last_optimization = OptimizationResult(
        retained_unit_ids=["a", "b", "c"],
        removed_unit_ids=[],
        original_unit_count=3,
        final_unit_count=3,
    )

    service._apply_phase9_results([
        VerificationResult(1, "a", "b", "Statement A", "Statement B", "KEEP_FIRST"),
        VerificationResult(2, "b", "c", "Statement B", "Statement C", "KEEP_SECOND"),
    ])

    assert service.last_optimization.retained_unit_ids == ["a", "c"]
    assert service.last_optimization.removed_unit_ids == ["b"]
    assert service.last_optimization.final_unit_count == 2


def test_service_manual_review_preserves_both_sides_and_change_log(tmp_path) -> None:
    service = RedundancyAnalysisService.__new__(RedundancyAnalysisService)
    service.last_information_units = [
        InformationUnit("a", "doc1", "Private statement A", 1),
        InformationUnit("b", "doc2", "Private statement B", 1),
    ]
    service.last_optimization = OptimizationResult(
        retained_unit_ids=["a"],
        removed_unit_ids=["b"],
        original_unit_count=2,
        final_unit_count=1,
    )
    service.last_phase9_candidates = [_candidate(1)]
    service.last_phase9_results = [
        VerificationResult(
            1,
            "a",
            "b",
            "Private statement A",
            "Private statement B",
            "MANUAL_REVIEW",
        )
    ]
    service.last_manual_verifications = [
        ManualVerificationResult(
            1,
            "a",
            "b",
            "Private statement A",
            "Private statement B",
        )
    ]

    service._apply_phase9_results(service.last_phase9_results)

    class FakeReconstructor:
        def reconstruct(self, information_units, retained_unit_ids):
            return "Private statement A\nPrivate statement B\n"

    service.reconstruction_engine = FakeReconstructor()

    output = service.build_optimized_dataset(tmp_path)
    log = json.loads((tmp_path / "changes.json").read_text(encoding="utf-8"))

    assert output.exists()
    assert log["phase9_verification"]["candidate_count"] == 1
    assert len(log["phase9_verification"]["manual_verification_required"]) == 1
    assert (
        log["phase9_verification"]["manual_verification_required"][0]["status"]
        == "MANUAL_VERIFICATION_REQUIRED"
    )
