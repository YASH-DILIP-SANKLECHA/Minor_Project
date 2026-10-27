"""
Minor Project One - Redundancy Engine.

Phase 3:
- Compare every unique pair of information units.
- Calculate semantic similarity using embeddings.
- Detect similar pairs automatically.
- Build similarity groups.

Phase 4/5 compatibility:
- The engine can receive utility and rarity information later.
- The new scoring engine is available without changing the
  existing Phase 3 similarity-detection behavior.

Important:
The default `cross_document_only` value is False so the engine's
unit tests can analyze arbitrary InformationUnit collections.

The application service uses:
    cross_document_only=False

Therefore same-document contradictions can remain in the candidate flow.
"""

from __future__ import annotations

import re
from typing import Dict, List

import numpy as np

from core.embedding_engine.embedding_engine import EmbeddingEngine
from core.redundancy_engine.redundancy_result import (
    RedundancyAnalysisResult,
    RedundancyGroup,
    RedundancyPair,
    SimilarityPair,
)
from core.scoring.scoring_engine import ScoringEngine
from models.information_unit import InformationUnit


class RedundancyEngine:
    """
    Automatically calculate semantic similarity and identify
    potentially redundant information.
    """

    # MiniLM semantic paraphrase/contradiction pairs often score below 0.80.
    # Keep this as a candidate threshold, not a final truth decision.
    DEFAULT_SIMILARITY_THRESHOLD = 0.65

    # Keep the same threshold for Phase 3 redundancy candidates.
    DEFAULT_REDUNDANCY_THRESHOLD = 0.65

    # Small inputs retain every calculated pair for complete diagnostics.
    # Large inputs store only threshold-qualified candidates to avoid keeping
    # millions of Python objects in memory.
    MAX_MATERIALIZED_COMPARISONS = 100_000
    LARGE_INPUT_BATCH_SIZE = 256
    # These bounds are deliberately high enough for 5k-10k-line datasets,
    # while still avoiding creation of every O(n^2) Python pair object.
    MAX_CANDIDATES_PER_UNIT = 12
    MAX_CANDIDATE_PAIRS = 12_000
    MAX_FACTUAL_ANCHOR_PAIRS = 20_000
    FACTUAL_CUE_PATTERN = re.compile(
        r"\b(?:is|are|was|were|has|have|contains|contain|located|"
        r"capital|freezes|boils|produces|produce|called|highest|largest|"
        r"smallest|formula|symbol|planet|star|named|name|password|"
        r"favourite|favorite|stored|starts|contact|classroom|supervisor|"
        r"presentation|locker|code)\b",
        re.IGNORECASE,
    )
    FACTUAL_ANCHOR_STOP_WORDS = frozenset({
        "about", "after", "also", "and", "are", "been", "both",
        "called", "chemical", "contains", "from", "have", "into",
        "is", "its", "located", "major", "most", "near", "not",
        "atomic", "number", "capital", "largest", "smallest", "highest", "nearest", "natural",
        "planet", "moon", "solar", "system", "sample", "record",
        "entry", "item", "line", "our", "user",
        "of", "on", "or", "the", "this", "that", "through", "was",
        "with",
    })

    def __init__(
        self,
        embedding_engine: EmbeddingEngine | None = None,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        redundancy_threshold: float = DEFAULT_REDUNDANCY_THRESHOLD,
        max_materialized_comparisons: int = MAX_MATERIALIZED_COMPARISONS,
        max_candidates_per_unit: int = MAX_CANDIDATES_PER_UNIT,
        max_candidate_pairs: int = MAX_CANDIDATE_PAIRS,
    ) -> None:
        """
        Initialize the redundancy engine.

        Args:
            embedding_engine:
                Optional reference to the embedding engine.

            similarity_threshold:
                Minimum similarity required for a pair to become
                a similarity candidate.

            redundancy_threshold:
                Minimum redundancy score required for a pair.
        """

        # Store the existing embedding-engine reference.
        self.embedding_engine = embedding_engine

        # Validate and store the semantic similarity threshold.
        self.similarity_threshold = self._validate_threshold(
            similarity_threshold,
            "similarity_threshold",
        )

        # Validate and store the redundancy threshold.
        self.redundancy_threshold = self._validate_threshold(
            redundancy_threshold,
            "redundancy_threshold",
        )

        self.max_materialized_comparisons = self._validate_positive_int(
            max_materialized_comparisons,
            "max_materialized_comparisons",
        )
        self.max_candidates_per_unit = self._validate_positive_int(
            max_candidates_per_unit,
            "max_candidates_per_unit",
        )
        self.max_candidate_pairs = self._validate_positive_int(
            max_candidate_pairs,
            "max_candidate_pairs",
        )

        # Initialize Phase 5 combined scoring support.
        # It does not replace the working Phase 3 logic.
        self.scoring_engine = ScoringEngine()

    @staticmethod
    def _validate_threshold(
        value: float,
        field_name: str,
    ) -> float:
        """
        Validate that a threshold is between 0.0 and 1.0.
        """

        # Convert the supplied value to float.
        try:
            threshold = float(value)
        except (TypeError, ValueError) as exc:
            raise TypeError(
                f"{field_name} must be numeric."
            ) from exc

        # Reject invalid threshold values.
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(
                f"{field_name} must be between 0.0 and 1.0."
            )

        return threshold

    @staticmethod
    def _validate_positive_int(value: int, field_name: str) -> int:
        if not isinstance(value, int) or value < 1:
            raise ValueError(f"{field_name} must be a positive integer.")
        return value

    def calculate_all_similarities(
        self,
        information_units: List[InformationUnit],
    ) -> List[SimilarityPair]:
        """
        Compare every unique pair of information units.

        No threshold is applied in this method.

        For N units:
            N * (N - 1) / 2

        unique comparisons are performed.
        """

        # Validate the incoming information units.
        self._validate_information_units(information_units)

        # Store every calculated pair.
        all_results: List[SimilarityPair] = []

        # Select the first unit in the pair.
        for index, unit_a in enumerate(information_units):

            # Compare it with every later unit.
            # This prevents comparing A-B and B-A twice.
            for unit_b in information_units[index + 1:]:

                # Calculate semantic similarity from embeddings.
                similarity = self._calculate_similarity(
                    unit_a,
                    unit_b,
                )

                # Store the complete pairwise result.
                all_results.append(
                    SimilarityPair(
                        information_unit_id_a=unit_a.information_unit_id,
                        information_unit_id_b=unit_b.information_unit_id,
                        text_a=unit_a.text,
                        text_b=unit_b.text,
                        similarity_score=similarity,
                    )
                )

        return all_results

    def analyze(
        self,
        information_units: List[InformationUnit],
        cross_document_only: bool = False,
    ) -> RedundancyAnalysisResult:
        """
        Identify similar information pairs.

        Processing:
            1. Compare every possible pair.
            2. Apply the existing similarity threshold.
            3. Optionally restrict final candidates to different documents.
            4. Build redundancy groups.

        The default is False for compatibility with direct engine tests.

        The application service passes False so same-document
        contradictions can remain in the candidate flow.
        """

        # Validate all information units first.
        self._validate_information_units(information_units)

        comparison_count = len(information_units) * (len(information_units) - 1) // 2
        candidate_pairs_limited = (
            comparison_count > self.max_materialized_comparisons
        )

        if candidate_pairs_limited:
            # Use vectorized blocks and retain only strong candidates. This
            # avoids materializing O(n^2) SimilarityPair Python objects.
            all_similarities = self._calculate_large_input_candidates(
                information_units
            )
        else:
            # Small inputs retain every pair for complete diagnostics.
            all_similarities = self.calculate_all_similarities(
                information_units
            )

        # Store pairs that qualify as similar.
        similar_pairs: List[RedundancyPair] = []

        # Examine every calculated pair.
        for pair in all_similarities:

            # Preserve the working Phase 3 threshold.
            if pair.similarity_score < self.similarity_threshold:
                continue

            # Locate the original information units.
            unit_a = self._find_information_unit(
                information_units,
                pair.information_unit_id_a,
            )

            unit_b = self._find_information_unit(
                information_units,
                pair.information_unit_id_b,
            )

            # When requested, keep only cross-document candidates.
            if (
                cross_document_only
                and unit_a.document_id == unit_b.document_id
            ):
                continue

            # Preserve the Phase 3 redundancy-score formula.
            redundancy_score = self._calculate_redundancy_score(
                pair.similarity_score
            )

            # Preserve the existing redundancy threshold.
            if redundancy_score < self.redundancy_threshold:
                continue

            # Store the final candidate.
            similar_pairs.append(
                RedundancyPair(
                    information_unit_id_a=pair.information_unit_id_a,
                    information_unit_id_b=pair.information_unit_id_b,
                    similarity_score=pair.similarity_score,
                    redundancy_score=redundancy_score,
                    text_a=pair.text_a,
                    text_b=pair.text_b,
                )
            )

        # Build groups from the detected candidates.
        groups = self._build_groups(
            information_units,
            similar_pairs,
        )

        # Return all pairwise results plus the final candidate list.
        return RedundancyAnalysisResult(
            all_similarities=all_similarities,
            similar_pairs=similar_pairs,
            groups=groups,
            similarity_threshold=self.similarity_threshold,
            redundancy_threshold=self.redundancy_threshold,
            comparison_count=comparison_count,
            candidate_pairs_limited=candidate_pairs_limited,
        )

    def _calculate_large_input_candidates(
        self,
        information_units: List[InformationUnit],
    ) -> List[SimilarityPair]:
        """Return bounded high-similarity candidates for a large dataset."""
        embeddings = []
        for unit in information_units:
            if unit.embedding is None:
                raise ValueError(
                    f"Missing embedding for {unit.information_unit_id}."
                )
            embeddings.append(unit.embedding)

        matrix = np.asarray(embeddings, dtype=np.float32)
        if matrix.ndim != 2:
            raise ValueError("Embedding vectors must have the same dimensions.")

        norms = np.linalg.norm(matrix, axis=1)
        if np.any(norms == 0):
            raise ValueError("Embedding vector norm cannot be zero.")
        matrix = matrix / norms[:, None]

        candidates: List[SimilarityPair] = []
        unit_count = len(information_units)

        for start in range(0, unit_count, self.LARGE_INPUT_BATCH_SIZE):
            stop = min(start + self.LARGE_INPUT_BATCH_SIZE, unit_count)
            scores = matrix[start:stop] @ matrix.T

            for local_index, score_row in enumerate(scores):
                first_index = start + local_index
                second_indexes = np.flatnonzero(
                    score_row[first_index + 1:] >= self.similarity_threshold
                ) + first_index + 1

                if len(second_indexes) > self.max_candidates_per_unit:
                    selected = np.argpartition(
                        score_row[second_indexes],
                        -self.max_candidates_per_unit,
                    )[-self.max_candidates_per_unit:]
                    second_indexes = second_indexes[selected]

                for second_index in second_indexes:
                    unit_a = information_units[first_index]
                    unit_b = information_units[int(second_index)]
                    candidates.append(
                        SimilarityPair(
                            information_unit_id_a=unit_a.information_unit_id,
                            information_unit_id_b=unit_b.information_unit_id,
                            text_a=unit_a.text,
                            text_b=unit_b.text,
                            # A float32 matrix product can exceed 1.0 by a
                            # tiny rounding amount for identical embeddings.
                            # Cosine similarity is mathematically bounded, so
                            # clamp only that numerical overshoot.
                            similarity_score=max(
                                0.0,
                                min(1.0, float(score_row[second_index])),
                            ),
                        )
                    )

        # A contradiction can differ in exactly the important value and score
        # below the general redundancy threshold. Factual statements sharing
        # a subject anchor are cheap to compare separately and remain eligible
        # for Phase 6 without admitting unrelated poetic prose.
        seen_pairs = {
            (pair.information_unit_id_a, pair.information_unit_id_b)
            for pair in candidates
        }
        for first_index, second_index in self._factual_anchor_indexes(
            information_units
        ):
            unit_a = information_units[first_index]
            unit_b = information_units[second_index]
            pair_key = (
                unit_a.information_unit_id,
                unit_b.information_unit_id,
            )
            if pair_key in seen_pairs:
                continue

            similarity = float(matrix[first_index] @ matrix[second_index])
            candidates.append(
                SimilarityPair(
                    information_unit_id_a=unit_a.information_unit_id,
                    information_unit_id_b=unit_b.information_unit_id,
                    text_a=unit_a.text,
                    text_b=unit_b.text,
                    similarity_score=max(0.0, min(1.0, similarity)),
                )
            )
            seen_pairs.add(pair_key)

        # Keep one representative per non-identical textual pair so thousands
        # of repeated factual lines cannot consume the bounded candidate queue
        # and hide genuine conflicts. Exact-repeat pairs are retained after
        # those unique pairs because Phase 3 still needs them for duplicate
        # removal; Phase 6 independently rejects them as contradictions.
        unique_candidates: List[SimilarityPair] = []
        exact_duplicate_candidates: List[SimilarityPair] = []
        seen_text_pairs: set[tuple[str, str]] = set()
        for pair in candidates:
            first_text = self._normalized_candidate_text(pair.text_a)
            second_text = self._normalized_candidate_text(pair.text_b)
            if first_text == second_text:
                exact_duplicate_candidates.append(pair)
                continue
            text_pair = tuple(sorted((first_text, second_text)))
            if text_pair in seen_text_pairs:
                continue
            seen_text_pairs.add(text_pair)
            unique_candidates.append(pair)

        # Factual-looking pairs are ranked before poetic or incomplete prose
        # so they remain available when the large-input candidate cap applies.
        unique_candidates.sort(
            key=lambda pair: (
                self._is_fact_like_pair(pair.text_a, pair.text_b),
                pair.similarity_score,
            ),
            reverse=True,
        )
        exact_duplicate_candidates.sort(
            key=lambda pair: pair.similarity_score,
            reverse=True,
        )
        return (
            unique_candidates[:self.max_candidate_pairs]
            + exact_duplicate_candidates[
                : max(0, self.max_candidate_pairs - len(unique_candidates))
            ]
        )

    @staticmethod
    def _normalized_candidate_text(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip().lower()

    @classmethod
    def _is_fact_like_pair(cls, text_a: str, text_b: str) -> bool:
        return bool(
            cls.FACTUAL_CUE_PATTERN.search(text_a)
            and cls.FACTUAL_CUE_PATTERN.search(text_b)
        )

    @classmethod
    def _factual_anchor_indexes(
        cls,
        information_units: List[InformationUnit],
    ) -> List[tuple[int, int]]:
        """Find bounded pairs of distinct factual statements sharing a term.

        Exact repeated lines are removed deterministically by Phase 8, so
        they must not consume this bounded candidate budget.  Keeping one
        representative for each normalized text ensures a 6,000-line input
        with 138 distinct statements can still reach all of its distinct
        contradiction candidates.
        """
        by_subject: Dict[str, List[int]] = {}
        by_anchor: Dict[str, List[int]] = {}
        seen_texts: set[str] = set()
        for index, unit in enumerate(information_units):
            if not cls.FACTUAL_CUE_PATTERN.search(unit.text):
                continue
            normalized_text = cls._normalized_candidate_text(unit.text)
            if normalized_text in seen_texts:
                continue
            seen_texts.add(normalized_text)
            subject_key = cls._claim_subject_key(unit.text)
            if subject_key:
                by_subject.setdefault(subject_key, []).append(index)
            anchors = {
                word.lower()
                for word in re.findall(r"[A-Za-z]{3,}", unit.text)
                if word.lower() not in cls.FACTUAL_ANCHOR_STOP_WORDS
            }
            for anchor in anchors:
                by_anchor.setdefault(anchor, []).append(index)

        pairs: List[tuple[int, int]] = []
        seen: set[tuple[int, int]] = set()
        # Pair exact claim subjects first.  This prevents a broad word such
        # as "sum", "capital", or "number" from exhausting the bounded
        # factual-candidate budget before later, genuinely competing claims
        # are reached in a large dataset.
        for indexes in list(by_subject.values()) + list(by_anchor.values()):
            for offset, first_index in enumerate(indexes):
                for second_index in indexes[offset + 1:]:
                    pair = (first_index, second_index)
                    if pair in seen:
                        continue
                    seen.add(pair)
                    pairs.append(pair)
                    if len(pairs) >= cls.MAX_FACTUAL_ANCHOR_PAIRS:
                        return pairs
        return pairs

    @staticmethod
    def _claim_subject_key(text: str) -> str:
        """Extract a generic claim subject used only for candidate indexing."""
        normalized = re.sub(r"[^a-z0-9\s]", " ", text.casefold())
        normalized = re.sub(r"\s+", " ", normalized).strip()
        match = re.search(
            r"\b(?:is|are|was|were|has|have|contains|contain|"
            r"freezes|boils|starts|produces|produce)\b",
            normalized,
        )
        if match is None:
            return ""
        subject = normalized[:match.start()].strip()
        return re.sub(r"^(?:the|a|an|my|our)\s+", "", subject)

    def find_similar_pairs(
        self,
        information_units: List[InformationUnit],
        cross_document_only: bool = False,
    ) -> List[RedundancyPair]:
        """
        Return the automatically detected similar pairs.
        """

        # Reuse the complete analysis logic.
        return self.analyze(
            information_units,
            cross_document_only=cross_document_only,
        ).similar_pairs

    def calculate_final_candidate_score(
        self,
        similarity_score: float,
        utility_score_a: float,
        utility_score_b: float,
        rarity_score_a: float,
        rarity_score_b: float,
    ) -> float:
        """
        Calculate the Phase 5 combined redundancy score.

        This method provides the new utility/rarity-aware score
        without replacing the existing Phase 3 candidate detection.
        """

        # Delegate the combined score calculation to ScoringEngine.
        return self.scoring_engine.calculate_score(
            similarity_score=similarity_score,
            utility_score_a=utility_score_a,
            utility_score_b=utility_score_b,
            rarity_score_a=rarity_score_a,
            rarity_score_b=rarity_score_b,
        )

    @staticmethod
    def _calculate_similarity(
        unit_a: InformationUnit,
        unit_b: InformationUnit,
    ) -> float:
        """
        Calculate cosine similarity from the two stored embeddings.

        No keyword matching is performed.
        """

        # Ensure the first information unit has an embedding.
        if unit_a.embedding is None:
            raise ValueError(
                f"Missing embedding for {unit_a.information_unit_id}."
            )

        # Ensure the second information unit has an embedding.
        if unit_b.embedding is None:
            raise ValueError(
                f"Missing embedding for {unit_b.information_unit_id}."
            )

        # Reuse the established Phase 2 cosine-similarity calculation.
        raw_similarity = EmbeddingEngine.cosine_similarity(
            unit_a.embedding,
            unit_b.embedding,
        )

        # Protect against tiny floating-point overshoots such as
        # 1.0000000002 that can occur during numerical computation.
        similarity = max(
            0.0,
            min(1.0, raw_similarity),
        )

        return similarity

    @staticmethod
    def _calculate_redundancy_score(
        similarity_score: float,
    ) -> float:
        """
        Calculate the current Phase 3 redundancy score.

        Formula:
            redundancy_score = similarity_score
        """

        # Keep the score in the valid 0-to-1 range.
        return max(
            0.0,
            min(1.0, float(similarity_score)),
        )

    @staticmethod
    def _find_information_unit(
        information_units: List[InformationUnit],
        information_unit_id: str,
    ) -> InformationUnit:
        """
        Find an InformationUnit using its unique identifier.
        """

        # Search the existing in-memory information-unit list.
        for unit in information_units:

            # Return the matching unit.
            if unit.information_unit_id == information_unit_id:
                return unit

        # Raise an error if the internal IDs are inconsistent.
        raise ValueError(
            f"Information unit not found: {information_unit_id}"
        )

    def _build_groups(
        self,
        information_units: List[InformationUnit],
        pairs: List[RedundancyPair],
    ) -> List[RedundancyGroup]:
        """
        Build connected groups from detected similar pairs.

        Example:
            A <-> B
            B <-> C

        becomes:
            {A, B, C}
        """

        # No pairs means no groups.
        if not pairs:
            return []

        # Start with every unit in its own group.
        parent: Dict[str, str] = {
            unit.information_unit_id: unit.information_unit_id
            for unit in information_units
        }

        def find(item: str) -> str:
            """
            Find the root of a connected group.
            """

            # Follow parent links until reaching the root.
            while parent[item] != item:

                # Compress the path for faster future lookups.
                parent[item] = parent[parent[item]]

                # Move upward in the group.
                item = parent[item]

            return item

        def union(first: str, second: str) -> None:
            """
            Merge the groups containing two related units.
            """

            # Find the root of each unit.
            root_first = find(first)
            root_second = find(second)

            # Merge different groups.
            if root_first != root_second:
                parent[root_second] = root_first

        # Join all detected candidate pairs.
        for pair in pairs:
            union(
                pair.information_unit_id_a,
                pair.information_unit_id_b,
            )

        # Collect members by root.
        grouped: Dict[str, List[str]] = {}

        for pair in pairs:

            # Find the current root.
            root = find(pair.information_unit_id_a)

            # Create the group list when needed.
            grouped.setdefault(root, [])

            # Add the first member.
            if pair.information_unit_id_a not in grouped[root]:
                grouped[root].append(
                    pair.information_unit_id_a
                )

            # Add the second member.
            if pair.information_unit_id_b not in grouped[root]:
                grouped[root].append(
                    pair.information_unit_id_b
                )

        groups: List[RedundancyGroup] = []

        # Convert each collected group into a result object.
        for group_index, unit_ids in enumerate(
            grouped.values(),
            start=1,
        ):

            # Remove duplicate IDs.
            unique_ids = list(dict.fromkeys(unit_ids))

            # Ignore invalid single-member groups.
            if len(unique_ids) < 2:
                continue

            # Create the structured redundancy group.
            groups.append(
                RedundancyGroup(
                    group_id=f"redundancy_group_{group_index:04d}",
                    information_unit_ids=unique_ids,
                )
            )

        return groups

    @staticmethod
    def _validate_information_units(
        information_units: List[InformationUnit],
    ) -> None:
        """
        Validate that the supplied collection contains only
        InformationUnit objects.
        """

        # The top-level object must be a list.
        if not isinstance(information_units, list):
            raise TypeError(
                "information_units must be a list."
            )

        # Validate every member.
        for unit in information_units:
            if not isinstance(unit, InformationUnit):
                raise TypeError(
                    "Every item must be an InformationUnit."
                )
