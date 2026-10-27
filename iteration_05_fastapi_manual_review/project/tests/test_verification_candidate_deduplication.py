from core.contradiction_engine.contradiction_result import ContradictionResult
from core.llm.verification_engine import VerificationEngine


def _conflict(first_id: str, second_id: str) -> ContradictionResult:
    return ContradictionResult(
        information_unit_id_a=first_id,
        information_unit_id_b=second_id,
        text_a="The capital of Japan is Tokyo.",
        text_b="The capital of Japan is Osaka.",
        similarity_score=0.9,
        contradiction_score=0.9,
        value_a=["Tokyo"],
        value_b=["Osaka"],
        reason="Conflicting factual values.",
    )


def test_repeated_textual_conflicts_create_one_verification_case() -> None:
    candidates = VerificationEngine().prepare_candidates(
        phase6_contradictions=[
            _conflict("a1", "b1"),
            _conflict("a2", "b2"),
            _conflict("a3", "b3"),
        ]
    )

    assert len(candidates) == 1
