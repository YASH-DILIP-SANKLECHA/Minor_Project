"""Phase 9 local Qwen contradiction verification engine."""

from __future__ import annotations

import json
import re
from typing import Any, Iterable

from core.contradiction_engine.contradiction_result import ContradictionResult
from core.llm.ollama_client import OllamaClient
from core.llm.verification_result import (
    ALLOWED_DECISIONS,
    VerificationCandidate,
    VerificationResult,
)


class VerificationEngine:
    """Verify only contradiction candidates with local Qwen3:4B."""

    ALLOWED_DECISIONS = ALLOWED_DECISIONS

    _CASE_DECISION_PATTERN = re.compile(
        r"(?:CASE\s*)?(\d+)\s*[:.\-]\s*"
        r"(KEEP_FIRST|KEEP_SECOND|MANUAL_REVIEW)\b",
        re.IGNORECASE,
    )

    _DECISION_PATTERN = re.compile(
        r"\b(KEEP_FIRST|KEEP_SECOND|MANUAL_REVIEW)\b",
        re.IGNORECASE,
    )

    # These are scope signals, not dataset-specific facts. They prevent a
    # local model from confidently inventing an answer for a user's own dog,
    # address, account, family member, health detail, or similar private fact.
    _PERSONAL_SCOPE_PATTERN = re.compile(
        r"\b(?:my|our|i\s+am|i'm|we\s+are|user(?:'s|\s+)?)\b",
        re.IGNORECASE,
    )
    _PRIVATE_ATTRIBUTE_PATTERN = re.compile(
        r"\b(?:password|passcode|pin|emergency\s+contact|home\s+address|"
        r"phone\s+number|email\s+address|bank\s+account|medical\s+record)\b",
        re.IGNORECASE,
    )

    def __init__(
        self,
        client: OllamaClient | Any | None = None,
        ollama_client: OllamaClient | Any | None = None,
    ) -> None:
        if client is not None and ollama_client is not None:
            raise ValueError("Provide either client or ollama_client, not both.")

        self.client = (
            client
            if client is not None
            else ollama_client
            if ollama_client is not None
            else OllamaClient()
        )
        self.ollama_client = self.client

    def prepare_candidates(
        self,
        phase6_contradictions: Iterable[ContradictionResult] | None = None,
        **_: Any,
    ) -> list[VerificationCandidate]:
        """Convert genuine Phase 6 contradictions into unique candidates."""
        candidates: list[VerificationCandidate] = []
        seen: set[tuple[str, str]] = set()
        seen_text_pairs: set[tuple[str, str]] = set()

        for contradiction in phase6_contradictions or []:
            if not isinstance(contradiction, ContradictionResult):
                raise TypeError("Phase 9 accepts only ContradictionResult objects.")

            candidate = VerificationCandidate(
                information_unit_id_a=contradiction.information_unit_id_a,
                information_unit_id_b=contradiction.information_unit_id_b,
                text_a=contradiction.text_a,
                text_b=contradiction.text_b,
                context=contradiction.reason,
            )

            if candidate.pair_key in seen:
                continue

            # The same fact can be repeated thousands of times in an input.
            # It must yield one verification case, not one case per repeated
            # statement ID pair. Text-level deduplication preserves distinct
            # contradictions while preventing inflated manual-review counts.
            text_pair_key = tuple(sorted((
                self._normalized_statement(candidate.text_a),
                self._normalized_statement(candidate.text_b),
            )))
            if text_pair_key[0] == text_pair_key[1] or text_pair_key in seen_text_pairs:
                continue

            seen.add(candidate.pair_key)
            seen_text_pairs.add(text_pair_key)
            candidates.append(candidate)

        return candidates

    @staticmethod
    def _normalized_statement(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip().lower()

    @classmethod
    def requires_manual_scope(
        cls,
        candidate: VerificationCandidate | VerificationResult,
    ) -> bool:
        """Return true only for explicitly personal or private claims.

        General geography, science, history, and technology claims do not
        become user manual-review items merely because local Ollama is
        cautious.  Those stay in the automatic verification route.
        """
        return bool(
            cls._PERSONAL_SCOPE_PATTERN.search(candidate.text_a)
            or cls._PERSONAL_SCOPE_PATTERN.search(candidate.text_b)
            or cls._PRIVATE_ATTRIBUTE_PATTERN.search(candidate.text_a)
            or cls._PRIVATE_ATTRIBUTE_PATTERN.search(candidate.text_b)
        )

    def verify(
        self,
        candidates: list[VerificationCandidate],
    ) -> list[VerificationResult]:
        """Verify each contradiction independently, preserving input order."""
        results: list[VerificationResult] = []

        for case_number, candidate in enumerate(candidates, start=1):
            results.append(self._verify_single(candidate, case_number))

        return results

    def verify_all(
        self,
        contradictions: list[ContradictionResult] | list[VerificationCandidate],
    ) -> list[VerificationResult]:
        """Backward-compatible verification entry point."""
        if not contradictions:
            return []

        if all(isinstance(item, VerificationCandidate) for item in contradictions):
            return self.verify(list(contradictions))

        if all(isinstance(item, ContradictionResult) for item in contradictions):
            return self.verify(self.prepare_candidates(phase6_contradictions=contradictions))

        raise TypeError(
            "verify_all accepts only ContradictionResult or VerificationCandidate objects."
        )

    def _verify_single(
        self,
        candidate: VerificationCandidate,
        case_number: int,
    ) -> VerificationResult:
        prompt = self._build_single_prompt(candidate)
        raw_response = self.client.generate(prompt)

        try:
            decision, reason = self._parse_single_response(raw_response)
            self._validate_real_automatic_decision(decision, reason)
        except RuntimeError:
            # Fake clients remain strict so unit tests still catch malformed
            # responses. Real Ollama gets one constrained retry.
            if not isinstance(self.client, OllamaClient):
                raise

            raw_response = self.client.generate(
                self._build_retry_prompt(candidate)
            )

            try:
                decision, reason = self._parse_single_response(raw_response)
                self._validate_real_automatic_decision(decision, reason)
            except RuntimeError:
                # Never invent KEEP_FIRST/KEEP_SECOND from non-conforming
                # prose. Preserve both statements through Phase 8 instead.
                decision = "MANUAL_REVIEW"
                reason = (
                    "Ollama did not return a valid Phase 9 decision after "
                    "a structured retry; manual verification is required."
                )

        # A public factual pair is already excluded from the personal-review
        # path by the service.  Qwen can occasionally choose MANUAL_REVIEW
        # simply because its first response is overly cautious.  Give it one
        # explicit binary retry before preserving the pair for a human.
        if (
            isinstance(self.client, OllamaClient)
            and decision == "MANUAL_REVIEW"
            and not self.requires_manual_scope(candidate)
        ):
            retry_response = self.client.generate(
                self._build_public_fact_retry_prompt(candidate)
            )
            try:
                retry_decision, retry_reason = self._parse_single_response(
                    retry_response
                )
                if retry_decision in {"KEEP_FIRST", "KEEP_SECOND"}:
                    decision = retry_decision
                    reason = retry_reason
                    raw_response = retry_response
            except RuntimeError:
                # Preserve both statements when even the constrained retry
                # is invalid; correctness is safer than an invented choice.
                pass

        return VerificationResult(
            case_number=case_number,
            information_unit_id_a=candidate.information_unit_id_a,
            information_unit_id_b=candidate.information_unit_id_b,
            text_a=candidate.text_a,
            text_b=candidate.text_b,
            decision=decision,
            raw_response=raw_response,
            reason=reason,
        )

    def _validate_real_automatic_decision(
        self,
        decision: str,
        reason: str,
    ) -> None:
        """Reject unsupported automatic removals from the real model."""
        if (
            isinstance(self.client, OllamaClient)
            and decision in {"KEEP_FIRST", "KEEP_SECOND"}
            and not reason.strip()
        ):
            raise RuntimeError(
                "Ollama returned an automatic Phase 9 decision without a reason."
            )

    @staticmethod
    def _build_single_prompt(candidate: VerificationCandidate) -> str:
        """Build a compact, instruction-resistant contradiction prompt."""
        context = candidate.context.strip() or (
            "The contradiction detector identified these two statements as conflicting."
        )

        return "\n".join(
            [
                "You are a contradiction verification component.",
                "Decide which of the two statements is correct using only your learned knowledge.",
                "Do not use web search, external evidence, retrieval, APIs, or assumptions.",
                "For established general facts: choose the factually correct statement.",
                "Use MANUAL_REVIEW only for explicitly personal, private, or user-specific claims.",
                "For every non-personal claim, choose the best-supported statement from learned general knowledge.",
                "Return a JSON object only. No explanation outside the JSON.",
                'Required JSON format: {"decision":"KEEP_FIRST"|"KEEP_SECOND"|"MANUAL_REVIEW","reason":"brief reason"}',
                "",
                "STATEMENT 1",
                candidate.text_a,
                "",
                "STATEMENT 2",
                candidate.text_b,
                "",
                "DETECTOR CONTEXT",
                context,
            ]
        )

    @staticmethod
    def _build_retry_prompt(candidate: VerificationCandidate) -> str:
        """Build an even smaller corrective prompt for the real Ollama client."""
        return "\n".join(
            [
                "Return ONLY JSON. Do not explain.",
                'JSON schema: {"decision":"KEEP_FIRST|KEEP_SECOND|MANUAL_REVIEW","reason":"brief reason"}',
                "For non-personal claims, select the best-supported statement from learned general knowledge.",
                "Use MANUAL_REVIEW only for explicitly personal, private, or user-specific claims.",
                "Statement 1:",
                candidate.text_a,
                "Statement 2:",
                candidate.text_b,
            ]
        )

    @staticmethod
    def _build_public_fact_retry_prompt(candidate: VerificationCandidate) -> str:
        """Request a binary decision for a non-personal factual conflict."""
        return "\n".join(
            [
                "Choose the factually correct statement using learned general knowledge.",
                "This is not personal information.",
                "Return ONLY JSON with KEEP_FIRST or KEEP_SECOND; do not use MANUAL_REVIEW.",
                'JSON schema: {"decision":"KEEP_FIRST|KEEP_SECOND","reason":"brief reason"}',
                "Statement 1:",
                candidate.text_a,
                "Statement 2:",
                candidate.text_b,
            ]
        )

    @classmethod
    def _parse_single_response(cls, response: str) -> tuple[str, str]:
        """Parse one Qwen decision without guessing."""
        text = (response or "").strip()
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL).strip()
        if not text:
            raise RuntimeError("Ollama returned an empty Phase 9 decision.")

        # Preferred path: structured JSON returned by Ollama.
        json_objects = cls._extract_json_objects(text)
        if json_objects:
            decisions: list[str] = []
            reasons: list[str] = []
            for obj in json_objects:
                decision = obj.get("decision")
                if not isinstance(decision, str):
                    raise RuntimeError("Ollama JSON response has no valid decision field.")
                normalized = decision.strip().upper()
                if normalized not in cls.ALLOWED_DECISIONS:
                    raise RuntimeError(f"Unsupported Phase 9 decision: {decision}")
                decisions.append(normalized)
                reason = obj.get("reason", "")
                reasons.append(reason.strip() if isinstance(reason, str) else "")

            unique = list(dict.fromkeys(decisions))
            if len(unique) != 1:
                raise RuntimeError("Ollama returned multiple Phase 9 decisions for one case.")
            return unique[0], reasons[0] if reasons else ""

        # Backward-compatible plain-token handling for tests and simple responses.
        case_matches = [
            match.group(2).upper()
            for match in cls._CASE_DECISION_PATTERN.finditer(text)
        ]
        if case_matches:
            unique = list(dict.fromkeys(case_matches))
            if len(unique) != 1:
                raise RuntimeError("Ollama returned multiple Phase 9 decisions for one case.")
            return unique[0], ""

        matches = [match.group(1).upper() for match in cls._DECISION_PATTERN.finditer(text)]
        unique = list(dict.fromkeys(matches))
        if len(unique) != 1:
            raise RuntimeError(
                "Ollama returned an ambiguous Phase 9 decision: "
                f"{response!r}"
            )
        return unique[0], ""

    @staticmethod
    def _extract_json_objects(text: str) -> list[dict[str, Any]]:
        """Extract JSON objects from a response without accepting arbitrary text as a decision."""
        objects: list[dict[str, Any]] = []

        decoder = json.JSONDecoder()
        index = 0
        while index < len(text):
            start = text.find("{", index)
            if start < 0:
                break
            try:
                value, end = decoder.raw_decode(text[start:])
            except json.JSONDecodeError:
                index = start + 1
                continue

            if isinstance(value, dict):
                objects.append(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        objects.append(item)
            index = start + end

        return objects

    @classmethod
    def _parse_response(cls, response: str, case_count: int) -> dict[int, str]:
        """Parse the legacy multi-case response format."""
        parsed: dict[int, str] = {}
        for match in cls._CASE_DECISION_PATTERN.finditer(response or ""):
            case_number = int(match.group(1))
            decision = match.group(2).upper()
            if not 1 <= case_number <= case_count:
                continue
            previous = parsed.get(case_number)
            if previous is not None and previous != decision:
                raise RuntimeError(
                    f"Ollama returned conflicting decisions for case {case_number}."
                )
            parsed[case_number] = decision
        return parsed

    def create_manual_flags(
        self,
        verifications: list[VerificationResult],
    ) -> list[Any]:
        """Create flags only for MANUAL_REVIEW cases; no interactive choices."""
        from core.llm.manual_verification import ManualVerification

        manual = ManualVerification()
        return [
            manual.create_flag(result)
            for result in verifications
            if result.decision == "MANUAL_REVIEW"
        ]
