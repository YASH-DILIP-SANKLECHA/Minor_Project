"""
Minor Project One - Redundancy Result Models
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class SimilarityPair:
    """Stores the similarity calculated for one pair."""

    information_unit_id_a: str
    information_unit_id_b: str
    text_a: str
    text_b: str
    similarity_score: float

    def __post_init__(self) -> None:
        """Validate the pair and its similarity score."""
        if not self.information_unit_id_a.strip():
            raise ValueError(
                "information_unit_id_a cannot be empty."
            )

        if not self.information_unit_id_b.strip():
            raise ValueError(
                "information_unit_id_b cannot be empty."
            )

        if self.information_unit_id_a == self.information_unit_id_b:
            raise ValueError(
                "A similarity pair cannot contain the same unit twice."
            )

        self.similarity_score = self._validate_score(
            self.similarity_score,
            "similarity_score",
        )

    @staticmethod
    def _validate_score(
        value: float,
        field_name: str,
    ) -> float:
        """Validate a score in the range 0 to 1."""
        try:
            score = float(value)
        except (TypeError, ValueError) as exc:
            raise TypeError(
                f"{field_name} must be numeric."
            ) from exc

        if not 0.0 <= score <= 1.0:
            raise ValueError(
                f"{field_name} must be between 0.0 and 1.0."
            )

        return score

    def to_dict(self) -> Dict[str, Any]:
        """Convert the similarity pair to a dictionary."""
        return {
            "information_unit_id_a": self.information_unit_id_a,
            "information_unit_id_b": self.information_unit_id_b,
            "text_a": self.text_a,
            "text_b": self.text_b,
            "similarity_score": self.similarity_score,
        }


@dataclass
class RedundancyPair:
    """Stores a pair classified as a similarity/redundancy candidate."""

    information_unit_id_a: str
    information_unit_id_b: str
    similarity_score: float
    redundancy_score: float
    text_a: str = ""
    text_b: str = ""

    def __post_init__(self) -> None:
        """Validate identifiers, text and numeric scores."""
        if not self.information_unit_id_a.strip():
            raise ValueError(
                "information_unit_id_a cannot be empty."
            )

        if not self.information_unit_id_b.strip():
            raise ValueError(
                "information_unit_id_b cannot be empty."
            )

        if self.information_unit_id_a == self.information_unit_id_b:
            raise ValueError(
                "A redundancy pair cannot contain the same unit twice."
            )

        self.similarity_score = self._validate_score(
            self.similarity_score,
            "similarity_score",
        )

        self.redundancy_score = self._validate_score(
            self.redundancy_score,
            "redundancy_score",
        )

    @staticmethod
    def _validate_score(
        value: float,
        field_name: str,
    ) -> float:
        """Validate a score in the range 0 to 1."""
        try:
            score = float(value)
        except (TypeError, ValueError) as exc:
            raise TypeError(
                f"{field_name} must be numeric."
            ) from exc

        if not 0.0 <= score <= 1.0:
            raise ValueError(
                f"{field_name} must be between 0.0 and 1.0."
            )

        return score

    def to_dict(self) -> Dict[str, Any]:
        """Convert the redundancy candidate to a dictionary."""
        return {
            "information_unit_id_a": self.information_unit_id_a,
            "information_unit_id_b": self.information_unit_id_b,
            "similarity_score": self.similarity_score,
            "redundancy_score": self.redundancy_score,
            "text_a": self.text_a,
            "text_b": self.text_b,
        }


@dataclass
class RedundancyGroup:
    """Stores information units belonging to one similarity group."""

    group_id: str
    information_unit_ids: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate the group and remove duplicate IDs."""
        if not self.group_id.strip():
            raise ValueError("group_id cannot be empty.")

        self.information_unit_ids = list(
            dict.fromkeys(self.information_unit_ids)
        )

    @property
    def size(self) -> int:
        """Return the number of information units in this group."""
        return len(self.information_unit_ids)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the redundancy group to a dictionary."""
        return {
            "group_id": self.group_id,
            "information_unit_ids": self.information_unit_ids,
            "size": self.size,
        }


@dataclass
class RedundancyAnalysisResult:
    """
    Stores the complete Phase 3 analysis.

    all_similarities:
        Every pair that was compared.

    similar_pairs:
        Every pair classified as similar using the configured threshold.

    groups:
        Connected groups of similar information units.
    """

    all_similarities: List[SimilarityPair] = field(
        default_factory=list
    )
    similar_pairs: List[RedundancyPair] = field(
        default_factory=list
    )
    groups: List[RedundancyGroup] = field(
        default_factory=list
    )

    similarity_threshold: float = 0.65
    redundancy_threshold: float = 0.65

    def __post_init__(self) -> None:
        """Validate configured thresholds."""
        if not 0.0 <= self.similarity_threshold <= 1.0:
            raise ValueError(
                "similarity_threshold must be between 0.0 and 1.0."
            )

        if not 0.0 <= self.redundancy_threshold <= 1.0:
            raise ValueError(
                "redundancy_threshold must be between 0.0 and 1.0."
            )

    @property
    def total_comparisons(self) -> int:
        """Return the total number of unique pairs compared."""
        return len(self.all_similarities)

    @property
    def similar_pair_count(self) -> int:
        """Return the number of automatically identified similar pairs."""
        return len(self.similar_pairs)

    @property
    def group_count(self) -> int:
        """Return the number of detected similarity groups."""
        return len(self.groups)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the complete analysis result to a dictionary."""
        return {
            "all_similarities": [
                pair.to_dict()
                for pair in self.all_similarities
            ],
            "similar_pairs": [
                pair.to_dict()
                for pair in self.similar_pairs
            ],
            "groups": [
                group.to_dict()
                for group in self.groups
            ],
            "similarity_threshold": self.similarity_threshold,
            "redundancy_threshold": self.redundancy_threshold,
            "total_comparisons": self.total_comparisons,
            "similar_pair_count": self.similar_pair_count,
            "group_count": self.group_count,
        }