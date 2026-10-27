"""
Minor Project One - Contradiction Engine.

Phase 6 receives the semantically similar pairs produced by Phase 3.

Phase 6 does NOT attempt to make a final semantic contradiction decision.
Its job is to identify strong contradiction candidates for Phase 9.

A candidate is created when:
    - the pair is sufficiently semantically similar, and
    - the two statements contain different extracted values OR
      no reliable extracted values are available.

This allows Phase 9/Qwen to handle semantic contradictions instead of
silently dropping them in Phase 6.
"""

from __future__ import annotations

import re

from core.contradiction_engine.contradiction_result import (
    ContradictionResult,
)
from core.information_extractor.extraction_result import (
    ExtractionResult,
)
from core.redundancy_engine.redundancy_result import (
    RedundancyPair,
    SimilarityPair,
)


class ContradictionEngine:
    """
    Identify contradiction candidates among Phase 3 similar pairs.

    Phase 6 is deliberately conservative about declaring a contradiction,
    but it must not discard a highly similar pair merely because the
    information extractor did not find explicit values.
    """

    # Phase 6 has its own broader candidate threshold. It must not depend on
    # the stricter Phase 3 redundancy-output threshold.
    # Factual pairs sharing a subject anchor may differ substantially in their
    # value wording, so they use a lower Phase 6 candidate threshold.
    DEFAULT_MINIMUM_SIMILARITY = 0.40
    # Candidate-only threshold. The local verifier or manual review decides
    # whether a candidate is truly contradictory.
    # This is a candidate threshold, not a truth decision.  A factual pair
    # with the same subject and claim slot can differ exactly where it
    # matters (for example, seven versus twelve), which can lower MiniLM's
    # cosine score.  Phase 9/Qwen makes the final public-fact decision.
    DEFAULT_CONTRADICTION_THRESHOLD = 0.40
    FACTUAL_CUE_PATTERN = re.compile(
        r"\b(?:is|are|was|were|has|have|contains|contain|located|"
        r"capital|freezes|boils|produces|produce|called|highest|largest|"
        r"smallest|formula|symbol|planet|star|named|name|password|"
        r"favourite|favorite|stored|starts|contact|classroom|supervisor|"
        r"presentation|locker|code|became|become)\b",
        re.IGNORECASE,
    )
    FACTUAL_ANCHOR_STOP_WORDS = frozenset({
        "about", "after", "also", "and", "are", "been", "both",
        "called", "chemical", "contains", "from", "have", "into",
        "is", "its", "located", "major", "most", "near", "not",
        # Category words describe a fact type, not its subject. Treating
        # them as anchors makes unrelated claims such as Moon/Jupiter appear
        # contradictory merely because both contain "planet" or "moon".
        "atomic", "number", "capital", "largest", "smallest", "highest", "nearest", "natural",
        "planet", "moon", "solar", "system", "sample", "record",
        "entry", "item", "line", "our", "user",
        "of", "on", "or", "the", "this", "that", "through", "was",
        "with",
    })
    # A directional or place-name modifier changes an assigned value.  For
    # example, ``Monaco`` and ``North Monaco`` are not a general statement
    # plus a more detailed statement when they occur as the value of the
    # same claim.  This list is intentionally domain-neutral: it covers
    # common value modifiers without naming countries, cities, datasets, or
    # individual facts.
    VALUE_MODIFIER_WORDS = frozenset({
        "central", "east", "eastern", "greater", "lower", "new",
        "north", "northern", "old", "south", "southern", "upper",
        "west", "western",
    })
    NEGATION_WORDS = frozenset({"no", "not", "never", "without"})
    _TEMPORAL_CONTEXT_PATTERN = re.compile(
        r"\b(?:as\s+of|during)\s+((?:19|20)\d{2})\b",
        re.IGNORECASE,
    )

    def __init__(
        self,
        minimum_similarity: float = DEFAULT_MINIMUM_SIMILARITY,
        contradiction_threshold: float = DEFAULT_CONTRADICTION_THRESHOLD,
    ) -> None:
        self.minimum_similarity = self._validate_score(
            minimum_similarity,
            "minimum_similarity",
        )

        self.contradiction_threshold = self._validate_score(
            contradiction_threshold,
            "contradiction_threshold",
        )

    def analyze_pair(
        self,
        pair: RedundancyPair | SimilarityPair,
        extraction_a: ExtractionResult,
        extraction_b: ExtractionResult,
    ) -> ContradictionResult | None:
        """
        Convert a sufficiently similar pair into a Phase 6
        contradiction candidate.

        Explicit conflicting values strengthen the candidate.

        When explicit values are unavailable, the pair is still
        forwarded because semantic contradiction cannot safely be
        ruled out by the deterministic extractor.
        """

        similarity = self._validate_score(
            pair.similarity_score,
            "similarity_score",
        )

        if similarity < self.minimum_similarity:
            return None

        # Exact repeated statements are redundancy candidates, not factual
        # conflicts. This must happen before numeric extraction because a
        # repeated year, room number, or serial can otherwise enter Phase 9.
        if self._normalized_text(pair.text_a) == self._normalized_text(pair.text_b):
            return None

        values_a = self._normalized_values(
            extraction_a.values
        )

        values_b = self._normalized_values(
            extraction_b.values
        )

        values_conflict = self._values_conflict(
            values_a,
            values_b,
        )

        values_missing = not values_a or not values_b

        if not values_conflict and not values_missing:
            return None

        if self._differs_only_by_row_label(pair.text_a, pair.text_b):
            return None

        # Different serial numbers, list indexes, or other incidental values
        # do not make two sentences contradictory. A factual conflict needs a
        # shared meaningful subject before its values can be compared.
        if not self._shares_factual_anchor(pair.text_a, pair.text_b):
            return None

        # A shared noun alone is not enough.  For example, "Gold has the
        # chemical symbol Au" and "Gold is a chemical element" are related
        # facts, but they cannot contradict one another.  Only forward pairs
        # that make the same kind of claim about the same subject; this keeps
        # Phase 9 from asking Qwen to choose between supporting facts.
        if not self._claims_can_conflict(pair.text_a, pair.text_b):
            return None

        # Similar poetic, fictional, or incomplete prose has no reliable
        # factual claim for Phase 9 to resolve. Explicit value conflicts are
        # still preserved, but value-missing pairs need factual language.
        if values_missing and (
            not self._is_fact_like_pair(pair.text_a, pair.text_b)
            or not self._shares_factual_anchor(pair.text_a, pair.text_b)
        ):
            return None

        contradiction_score = self._calculate_contradiction_score(
            similarity_score=similarity,
            values_conflict=values_conflict,
        )

        if contradiction_score < self.contradiction_threshold:
            return None

        if values_conflict:
            reason = (
                "Semantically similar statements contain "
                "different extracted factual values and require "
                "contradiction verification."
            )
        else:
            reason = (
                "Semantically similar statements require semantic "
                "contradiction verification because explicit "
                "comparable factual values were not available."
            )

        return ContradictionResult(
            information_unit_id_a=pair.information_unit_id_a,
            information_unit_id_b=pair.information_unit_id_b,
            text_a=pair.text_a,
            text_b=pair.text_b,
            similarity_score=similarity,
            value_a=list(extraction_a.values),
            value_b=list(extraction_b.values),
            contradiction_score=contradiction_score,
            reason=reason,
        )

    def analyze_pairs(
        self,
        pairs: list[RedundancyPair | SimilarityPair],
        extractions: dict[str, ExtractionResult],
    ) -> list[ContradictionResult]:
        """
        Analyze all Phase 3 similar pairs.

        Processing is linear in the number of candidate pairs and
        uses dictionary lookups for extraction results.
        """

        contradictions: list[ContradictionResult] = []

        for pair in pairs:
            extraction_a = extractions.get(
                pair.information_unit_id_a
            )
            extraction_b = extractions.get(
                pair.information_unit_id_b
            )

            if extraction_a is None or extraction_b is None:
                continue

            contradiction = self.analyze_pair(
                pair=pair,
                extraction_a=extraction_a,
                extraction_b=extraction_b,
            )

            if contradiction is not None:
                contradictions.append(contradiction)

        return contradictions

    @staticmethod
    def _normalized_values(
        values: list[str],
    ) -> list[str]:
        """Normalize extracted values without changing their meaning."""

        normalized: list[str] = []

        for value in values:
            if not isinstance(value, str):
                continue

            cleaned = re.sub(
                r"\s+",
                " ",
                value.strip().lower(),
            )

            if cleaned:
                normalized.append(cleaned)

        return list(dict.fromkeys(normalized))

    @staticmethod
    def _normalized_text(text: str) -> str:
        """Normalize display-only formatting for exact-duplicate detection."""
        return re.sub(r"\s+", " ", text).strip().lower()

    @staticmethod
    def _values_conflict(
        values_a: list[str],
        values_b: list[str],
    ) -> bool:
        """
        Detect whether two non-empty value collections disagree.

        If there is no common value, the values are considered
        potentially conflicting and Phase 9 gets the final say.
        """

        if not values_a or not values_b:
            return False

        return not bool(set(values_a) & set(values_b))

    @staticmethod
    def _differs_only_by_row_label(text_a: str, text_b: str) -> bool:
        """Ignore identifiers such as ``Sample 0093:`` at a line's start."""
        prefix = re.compile(
            r"^\s*(?:sample|record|entry|item|line)\s+\d+\s*[:#\-]\s*",
            re.IGNORECASE,
        )
        remainder_a = prefix.sub("", text_a, count=1)
        remainder_b = prefix.sub("", text_b, count=1)
        return (
            remainder_a != text_a
            and remainder_b != text_b
            and re.sub(r"\s+", " ", remainder_a).strip().lower()
            == re.sub(r"\s+", " ", remainder_b).strip().lower()
        )

    @classmethod
    def _is_fact_like_pair(cls, text_a: str, text_b: str) -> bool:
        """Require factual language before sending value-missing text to Qwen."""
        return bool(
            cls.FACTUAL_CUE_PATTERN.search(text_a)
            and cls.FACTUAL_CUE_PATTERN.search(text_b)
        )

    @classmethod
    def _shares_factual_anchor(cls, text_a: str, text_b: str) -> bool:
        """Require a shared meaningful subject term for value-missing text."""
        anchors_a = {
            word.lower()
            for word in re.findall(r"[A-Za-z]{3,}", text_a)
            if word.lower() not in cls.FACTUAL_ANCHOR_STOP_WORDS
        }
        anchors_b = {
            word.lower()
            for word in re.findall(r"[A-Za-z]{3,}", text_b)
            if word.lower() not in cls.FACTUAL_ANCHOR_STOP_WORDS
        }
        return bool(anchors_a & anchors_b)

    @classmethod
    def _claims_can_conflict(cls, text_a: str, text_b: str) -> bool:
        """Return whether two statements assert comparable claim slots.

        This is deliberately structural rather than fact-specific: it
        compares the grammatical subject and relation (``has``, ``is in``,
        ``is named``, ``freezes at`` and so on).  It also rejects a short
        general statement that is contained by a longer supporting statement,
        because that is an entailment, not a contradiction.
        """
        # Claims explicitly scoped to different times can both be true.  This
        # guard intentionally recognises only unambiguous time qualifiers
        # such as "as of 2020" and "during 2020"; a factual date value such
        # as "was founded in 2020" remains eligible for comparison.
        if cls._has_distinct_temporal_context(text_a, text_b):
            return False

        signature_a = cls._claim_signature(text_a)
        signature_b = cls._claim_signature(text_b)

        if signature_a is None or signature_b is None:
            return False

        subject_a, relation_a, object_a = signature_a
        subject_b, relation_b, object_b = signature_b

        if subject_a != subject_b or relation_a != relation_b:
            return False

        # A title-cased token in the changed value signals a named value
        # (for example, ``Lake View`` versus ``View``).  Named values are
        # assignments, not descriptive detail, so they must be presented to
        # the verifier instead of being hidden by lexical containment.
        if cls._has_named_value_difference(text_a, text_b):
            return True

        return not cls._object_entails(object_a, object_b)

    @classmethod
    def _has_distinct_temporal_context(cls, text_a: str, text_b: str) -> bool:
        """Return true when two statements use different explicit time scopes."""
        match_a = cls._TEMPORAL_CONTEXT_PATTERN.search(text_a)
        match_b = cls._TEMPORAL_CONTEXT_PATTERN.search(text_b)
        return bool(
            match_a is not None
            and match_b is not None
            and match_a.group(1) != match_b.group(1)
        )

    @staticmethod
    def _has_named_value_difference(text_a: str, text_b: str) -> bool:
        """Detect a title-cased token that differs in two claim values.

        SentenceTransformer supplies the semantic candidate; this helper
        prevents the deterministic entailment guard from treating a proper
        name as merely a more detailed version of itself.  It does not use
        lists of countries, people, cities, or dataset terms.
        """
        value_pattern = re.compile(
            r"\b(?:is|are|was|were|has|have|contains|contain|"
            r"freezes|boils|starts|produces|produce|became|become)\b\s*(.*)",
            re.IGNORECASE,
        )

        def value_words(text: str) -> dict[str, bool]:
            match = value_pattern.search(text)
            if match is None:
                return {}
            value_text = match.group(1).strip()

            # A sentence such as "The Nile is a major river in Africa"
            # gives contextual location detail to the description "river".
            # When comparing it with "The Nile is a river", that trailing
            # context must not be mistaken for an assigned named value.
            # The rule is deliberately limited to article-led descriptions;
            # direct values such as "is North Monaco" or "is Lake View"
            # are preserved intact.
            if re.match(r"^(?:a|an|the)\s+", value_text, re.IGNORECASE):
                value_text = re.split(
                    r"\b(?:in|on|at|from|near)\s+",
                    value_text,
                    maxsplit=1,
                    flags=re.IGNORECASE,
                )[0]
            return {
                token.casefold(): token[0].isupper()
                for token in re.findall(r"[A-Za-z][A-Za-z'-]*", value_text)
            }

        words_a = value_words(text_a)
        words_b = value_words(text_b)
        for token in words_a.keys() ^ words_b.keys():
            if words_a.get(token, False) or words_b.get(token, False):
                return True
        return False

    @staticmethod
    def _claim_signature(text: str) -> tuple[str, str, str] | None:
        """Extract a small, generic subject/relation/object claim signature."""
        normalized = re.sub(r"[^a-z0-9\s]", " ", text.casefold())
        normalized = re.sub(r"\s+", " ", normalized).strip()
        if not normalized:
            return None

        verb_match = re.search(
            r"\b(is|are|was|were|has|have|contains|contain|"
            r"freezes|boils|starts|produces|produce|became|become)\b",
            normalized,
        )
        if verb_match is None:
            return None

        subject = normalized[:verb_match.start()].strip()
        verb = verb_match.group(1)
        object_text = normalized[verb_match.end():].strip()
        subject = re.sub(r"^(?:the|a|an|my|our)\s+", "", subject)
        if not subject or not object_text:
            return None

        object_without_article = re.sub(
            r"^(?:the|a|an|also|often)\s+", "", object_text
        )

        if verb in {"is", "are", "was", "were"}:
            if object_without_article.startswith("named "):
                relation = "named"
                object_text = object_without_article[6:].strip()
            elif object_without_article.startswith("called "):
                relation = "called"
                object_text = object_without_article[7:].strip()
            elif object_without_article.startswith("located in "):
                relation = "is:in"
                object_text = object_without_article[11:].strip()
            elif object_without_article.startswith(("in ", "on ", "at ", "from ")):
                preposition, _, remainder = object_without_article.partition(" ")
                relation = f"is:{preposition}"
                object_text = remainder.strip()
            elif re.match(
                r"(?:largest|smallest|highest|lowest|deepest|shallowest|"
                r"longest|shortest|tallest|first|second|third|fourth|"
                r"fifth|nearest|farthest)\b",
                object_without_article,
            ):
                relation = "is:rank"
                object_text = object_without_article
            else:
                relation = "is:description"
                object_text = object_without_article
        elif verb in {"has", "have", "contains", "contain"}:
            # Keep a named property such as "chemical symbol" separate from
            # a generic possession such as "has four chambers".
            property_text = re.sub(r"^(?:the|a|an)\s+", "", object_text)
            if re.match(
                r"(?:\d+|zero|one|two|three|four|five|six|seven|eight|"
                r"nine|ten)\b",
                property_text,
            ):
                # A leading quantity is the value; the words that follow it
                # name the property.  For example, “India has 28 states”
                # and “India has 8 union territories” share a subject but
                # assert different properties, so they cannot contradict.
                quantity_match = re.match(
                    r"(?:\d+|zero|one|two|three|four|five|six|seven|"
                    r"eight|nine|ten)\b\s*(.*)",
                    property_text,
                )
                property_words = re.findall(
                    r"[a-z]+",
                    quantity_match.group(1) if quantity_match else "",
                )[:2]
                relation = verb + (
                    ":" + " ".join(property_words)
                    if property_words else ""
                )
            else:
                property_words = re.findall(r"[a-z]+", property_text)[:2]
                relation = verb + (
                    ":" + " ".join(property_words)
                    if property_words else ""
                )
        else:
            relation = verb

        object_text = re.sub(r"\s+", " ", object_text).strip()
        return subject, relation, object_text

    @staticmethod
    def _object_entails(object_a: str, object_b: str) -> bool:
        """Detect a general statement wholly contained in a detailed claim."""
        # Strip articles only when they introduce an object.  Removing every
        # ``a`` would make values such as "garage A" and "garage B" look
        # identical, incorrectly hiding a personal conflict from review.
        cleaned_a = re.sub(r"^(?:a|an|the)\s+", "", object_a.strip())
        cleaned_b = re.sub(r"^(?:a|an|the)\s+", "", object_b.strip())
        tokens_a = {
            token for token in re.findall(r"[a-z0-9]+", cleaned_a)
            if token not in {"is", "are", "of", "and"}
        }
        tokens_b = {
            token for token in re.findall(r"[a-z0-9]+", cleaned_b)
            if token not in {"is", "are", "of", "and"}
        }
        if not tokens_a or not tokens_b or tokens_a == tokens_b:
            return False

        # Negation changes the truth value.  It is never merely added detail:
        # "is flat" and "is not flat" must remain available to the verifier.
        if bool(tokens_a & ContradictionEngine.NEGATION_WORDS) != bool(
            tokens_b & ContradictionEngine.NEGATION_WORDS
        ):
            return False

        # Token containment normally captures harmless descriptive detail:
        # ``a river`` versus ``a major river in Africa``.  It must not hide
        # a conflicting assigned value merely because that value contains a
        # directional or naming modifier: ``Monaco`` versus ``North Monaco``
        # or ``York`` versus ``New York``.  The rule is generic and applies
        # to any subject/property, not to a particular country or sample.
        differing_tokens = tokens_a ^ tokens_b
        if differing_tokens & ContradictionEngine.VALUE_MODIFIER_WORDS:
            return False

        return tokens_a < tokens_b or tokens_b < tokens_a

    @staticmethod
    def _calculate_contradiction_score(
        similarity_score: float,
        values_conflict: bool,
    ) -> float:
        """
        Calculate the Phase 6 candidate strength.

        Semantic similarity is the primary signal.

        Explicit value conflict does not invent a new probability;
        it only confirms that the deterministic extractor found
        conflicting values.

        Therefore the score remains grounded in the actual semantic
        similarity produced by Phase 3.
        """

        del values_conflict

        return max(
            0.0,
            min(
                1.0,
                float(similarity_score),
            ),
        )

    @staticmethod
    def _validate_score(
        value: float,
        name: str,
    ) -> float:
        """Validate a score in the inclusive [0, 1] range."""

        try:
            score = float(value)
        except (TypeError, ValueError) as exc:
            raise TypeError(
                f"{name} must be numeric."
            ) from exc

        if not 0.0 <= score <= 1.0:
            raise ValueError(
                f"{name} must be between 0.0 and 1.0."
            )

        return score
