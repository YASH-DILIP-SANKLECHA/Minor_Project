"""
Minor Project One - Redundancy Engine

Phase 3:
Automatically compares information units using semantic embeddings
and identifies potentially redundant information across documents.

Important design:
1. Every possible pair is compared internally.
2. No keywords or hardcoded words are used.
3. Final redundancy candidates can be restricted to different
   documents because redundancy across separate articles is the
   primary target of this project.
4. No information is deleted in this module.
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
from models.information_unit import InformationUnit


class RedundancyEngine:
    """
    Automatically calculates semantic similarity between information units
    and identifies cross-document similarity candidates.
    """

    # Conservative initial threshold for Phase 3.
    # This is a configurable experimental value, not the final research
    # threshold for the complete INFORA system.
    DEFAULT_SIMILARITY_THRESHOLD = 0.80

    # In Phase 3 the redundancy score is currently equal to semantic
    # similarity. Later phases will add additional signals.
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
                Minimum semantic similarity required for a pair
                to be considered a candidate.

            redundancy_threshold:
                Minimum redundancy score required for a candidate.
        """

        # Keep the embedding engine reference for future extensions.
        self.embedding_engine = embedding_engine

        # Validate the semantic similarity threshold.
        self.similarity_threshold = self._validate_threshold(
            similarity_threshold,
            "similarity_threshold",
        )

        # Validate the redundancy score threshold.
        self.redundancy_threshold = self._validate_threshold(
            redundancy_threshold,
            "redundancy_threshold",
        )

    @staticmethod
    def _validate_threshold(
        value: float,
        field_name: str,
    ) -> float:
        """
        Validate a threshold value.

        A valid threshold must be between 0.0 and 1.0.
        """

        # Convert numeric input to float.
        try:
            threshold = float(value)
        except (TypeError, ValueError) as exc:
            raise TypeError(
                f"{field_name} must be numeric."
            ) from exc

        # Reject values outside the valid similarity range.
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
        Calculate similarity for EVERY unique pair.

        For N information units:

            N * (N - 1) / 2

        comparisons are performed.

        No similarity threshold is applied here.
        This means the engine first calculates the complete
        similarity landscape of the dataset.
        """

        # Validate that every input is a proper InformationUnit.
        self._validate_information_units(information_units)

        # Store every pairwise similarity result.
        all_results: List[SimilarityPair] = []

        # Select the first information unit.
        for index, unit_a in enumerate(information_units):

            # Compare it with every later information unit.
            # This avoids calculating both A-B and B-A.
            for unit_b in information_units[index + 1:]:

                # Calculate semantic similarity using only embeddings.
                similarity = self._calculate_similarity(
                    unit_a,
                    unit_b,
                )

                # Store the result without filtering.
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
        cross_document_only: bool = True,
    ) -> RedundancyAnalysisResult:
        """
        Perform automatic redundancy analysis.

        Processing order:

            1. Compare every possible pair.
            2. Apply the similarity threshold.
            3. Optionally require the two units to belong to
               different documents.
            4. Create redundancy candidates.
            5. Build similarity groups.

        Args:
            information_units:
                Information units extracted from the dataset.

            cross_document_only:
                If True, only similarities between different documents
                are treated as redundancy candidates.

        Returns:
            Complete redundancy analysis result.
        """

        # Validate the information units before analysis.
        self._validate_information_units(information_units)

        # ALWAYS calculate every pair first.
        all_similarities = self.calculate_all_similarities(
            information_units
        )

        # This list contains only final redundancy candidates.
        similar_pairs: List[RedundancyPair] = []

        # Examine each calculated similarity.
        for pair in all_similarities:

            # Ignore low semantic similarity for candidate classification.
            # The comparison itself was still performed and preserved.
            if pair.similarity_score < self.similarity_threshold:
                continue

            # Locate the original information units so that we can
            # determine whether the two units belong to different documents.
            unit_a = self._find_information_unit(
                information_units,
                pair.information_unit_id_a,
            )

            unit_b = self._find_information_unit(
                information_units,
                pair.information_unit_id_b,
            )

            # For dataset redundancy, repeated information across
            # different documents is the primary target.
            if (
                cross_document_only
                and unit_a.document_id == unit_b.document_id
            ):
                continue

            # Phase 3 currently uses semantic similarity as the
            # redundancy score.
            redundancy_score = self._calculate_redundancy_score(
                pair.similarity_score
            )

            # Apply the redundancy threshold after calculating the score.
            if redundancy_score < self.redundancy_threshold:
                continue

            # Store the automatically detected candidate.
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

        # Create groups from the final cross-document candidates.
        groups = self._build_groups(
            information_units,
            similar_pairs,
        )

        # Return both:
        # - every pair that was compared
        # - only the final candidate pairs
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
        cross_document_only: bool = True,
    ) -> List[RedundancyPair]:
        """
        Return only the final automatically detected similar pairs.

        All pairwise comparisons still happen internally.
        """

        # Run the complete analysis and return only final candidates.
        return self.analyze(
            information_units,
            cross_document_only=cross_document_only,
        ).similar_pairs

    @staticmethod
    def _calculate_similarity(
        unit_a: InformationUnit,
        unit_b: InformationUnit,
    ) -> float:
        """
        Calculate cosine similarity between two semantic embeddings.

        No keyword matching or text search is used here.
        """

        # Ensure the first unit has an embedding.
        if unit_a.embedding is None:
            raise ValueError(
                f"Missing embedding for {unit_a.information_unit_id}."
            )

        # Ensure the second unit has an embedding.
        if unit_b.embedding is None:
            raise ValueError(
                f"Missing embedding for {unit_b.information_unit_id}."
            )

        # Use the Phase 2 cosine similarity implementation.
        return EmbeddingEngine.cosine_similarity(
            unit_a.embedding,
            unit_b.embedding,
        )

    @staticmethod
    def _calculate_redundancy_score(
        similarity_score: float,
    ) -> float:
        """
        Calculate the current Phase 3 redundancy score.

        Current formula:

            redundancy_score = similarity_score

        This will later be expanded with:
            - frequency
            - utility
            - rarity
            - context
            - source
            - temporal information
            - contradiction
            - information overlap
        """

        # Keep the result in the valid 0-to-1 range.
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
        Find an InformationUnit by its unique identifier.

        This is used to check document membership after
        similarity calculation.
        """

        # Search the already parsed information units.
        for unit in information_units:
            if unit.information_unit_id == information_unit_id:
                return unit

        # The ID should always exist if the analysis is internally consistent.
        raise ValueError(
            f"Information unit not found: {information_unit_id}"
        )

    def _build_groups(
        self,
        information_units: List[InformationUnit],
        pairs: List[RedundancyPair],
    ) -> List[RedundancyGroup]:
        """
        Build connected groups of automatically detected similar units.

        Example:

            Article 1 A <-> Article 2 B
            Article 2 B <-> Article 3 C

        becomes one similarity group.
        """

        # No candidates means no groups.
        if not pairs:
            return []

        # Initially every information unit belongs to itself.
        parent: Dict[str, str] = {
            unit.information_unit_id: unit.information_unit_id
            for unit in information_units
        }

        def find(item: str) -> str:
            """
            Find the root of a connected similarity group.
            """

            # Follow parent links until the root is reached.
            while parent[item] != item:

                # Compress the path for faster future lookups.
                parent[item] = parent[parent[item]]

                # Move to the parent node.
                item = parent[item]

            return item

        def union(first: str, second: str) -> None:
            """
            Merge two similarity groups into one.
            """

            # Find the roots of the two units.
            root_first = find(first)
            root_second = find(second)

            # Merge only when the roots are different.
            if root_first != root_second:
                parent[root_second] = root_first

        # Connect every detected similar pair.
        for pair in pairs:
            union(
                pair.information_unit_id_a,
                pair.information_unit_id_b,
            )

        # Collect group members.
        grouped: Dict[str, List[str]] = {}

        for pair in pairs:

            # Find the root of the current pair.
            root = find(pair.information_unit_id_a)

            # Create the list for this group if necessary.
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

        # Convert each group to a structured result.
        for group_index, unit_ids in enumerate(
            grouped.values(),
            start=1,
        ):

            # Remove accidental duplicate IDs.
            unique_ids = list(dict.fromkeys(unit_ids))

            # Ignore invalid groups containing fewer than two units.
            if len(unique_ids) < 2:
                continue

            # Create the final RedundancyGroup.
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
        Verify that the input contains only InformationUnit objects.
        """

        # The input must be a list.
        if not isinstance(information_units, list):
            raise TypeError(
                "information_units must be a list."
            )

        # Every member must be an InformationUnit.
        for unit in information_units:
            if not isinstance(unit, InformationUnit):
                raise TypeError(
                    "Every item must be an InformationUnit."
                )