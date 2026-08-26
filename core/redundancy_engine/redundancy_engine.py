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

The real application service explicitly uses:
    cross_document_only=True

Therefore the project's actual dataset behavior remains:
only cross-document repetition is shown as redundancy.
"""

from __future__ import annotations

from typing import Dict, List

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

    # Keep the working Phase 3 threshold.
    DEFAULT_SIMILARITY_THRESHOLD = 0.80

    # Keep the working Phase 3 redundancy threshold.
    DEFAULT_REDUNDANCY_THRESHOLD = 0.80

    def __init__(
        self,
        embedding_engine: EmbeddingEngine | None = None,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        redundancy_threshold: float = DEFAULT_REDUNDANCY_THRESHOLD,
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

        The real project service explicitly passes True so that the
        actual dataset reports cross-document redundancy only.
        """

        # Validate all information units first.
        self._validate_information_units(information_units)

        # Calculate every pair before any filtering.
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
        )

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