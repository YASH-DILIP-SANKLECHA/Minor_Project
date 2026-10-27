from core.llm.verification_engine import VerificationEngine
from core.llm.verification_result import VerificationCandidate


def _candidate(first: str, second: str) -> VerificationCandidate:
    return VerificationCandidate("one", "two", first, second)


def test_personal_claims_are_routed_to_manual_review() -> None:
    assert VerificationEngine.requires_manual_scope(
        _candidate("My dog is named Bruno.", "My dog is named Brownie.")
    )


def test_public_claims_remain_eligible_for_local_verification() -> None:
    assert not VerificationEngine.requires_manual_scope(
        _candidate("Mars is the Red Planet.", "Mars is the Blue Planet.")
    )


def test_geography_is_not_routed_to_manual_review() -> None:
    assert not VerificationEngine.requires_manual_scope(
        _candidate(
            "The Sahara Desert is in Africa.",
            "The Sahara Desert is in Antarctica.",
        )
    )


def test_private_attribute_is_routed_to_manual_review() -> None:
    assert VerificationEngine.requires_manual_scope(
        _candidate(
            "The Wi-Fi password is Cedar-91.",
            "The Wi-Fi password is Maple-62.",
        )
    )
