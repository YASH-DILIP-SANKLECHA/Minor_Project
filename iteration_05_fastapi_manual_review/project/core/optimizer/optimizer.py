"""
Minor Project One - Phase 8 Optimizer.

The optimizer consumes Phase 7 decisions.

Rules:
    KEEP   -> never remove
    REVIEW -> never automatically remove
    REMOVE -> eligible for removal

When a REMOVE decision exists between two information units,
the optimizer removes only one side.

The information unit with stronger utility/rarity protection
is retained.

This module does not write files.
"""

from __future__ import annotations

import re
from typing import Dict, List

from core.decision_engine.decision_result import DecisionResult
from core.optimizer.optimization_result import (
    ChangeRecord,
    OptimizationResult,
)
from models.information_unit import InformationUnit


class Optimizer:
    """
    Convert Phase 7 REMOVE recommendations into actual
    information-unit removal selections.
    """

    def optimize(
        self,
        information_units: List[InformationUnit],
        decisions: List[DecisionResult],
    ) -> OptimizationResult:
        """
        Determine which information units can safely be removed.

        Only Phase 7 REMOVE decisions are acted upon.

        KEEP and REVIEW decisions always preserve both units.

        When a pair is marked REMOVE, the unit with weaker combined
        protection is selected for removal.
        """

        # Validate all supplied information units.
        self._validate_information_units(
            information_units
        )

        # Create a lookup for fast ID-based access.
        units_by_id: Dict[str, InformationUnit] = {
            unit.information_unit_id: unit
            for unit in information_units
        }

        # Track units that are explicitly selected for removal.
        removed_ids: set[str] = set()

        # Store reversible change records.
        change_records: list[ChangeRecord] = []

        # Remove exact repeats deterministically before using semantic
        # decisions.  Similarity candidate caps intentionally keep the
        # expensive comparison graph bounded for large datasets, so relying
        # on that graph alone can leave thousands of identical lines behind.
        # The first occurrence is retained; every later occurrence is an
        # exact duplicate regardless of how many times it appears.
        first_unit_by_text: Dict[str, InformationUnit] = {}
        for unit in information_units:
            normalized_text = self._normalized_text(unit.text)
            first_unit = first_unit_by_text.get(normalized_text)

            if first_unit is None:
                first_unit_by_text[normalized_text] = unit
                continue

            removed_ids.add(unit.information_unit_id)
            change_records.append(
                ChangeRecord(
                    information_unit_id=unit.information_unit_id,
                    document_id=unit.document_id,
                    original_text=unit.text,
                    reason=(
                        "Removed as an exact duplicate of an earlier "
                        "statement."
                    ),
                    decision="REMOVE",
                    confidence=1.0,
                    paired_information_unit_id=(
                        first_unit.information_unit_id
                    ),
                )
            )

        # Examine every Phase 7 decision.
        for decision in decisions:

            # Only REMOVE recommendations are allowed to affect
            # the refined dataset.
            if decision.decision != "REMOVE":
                continue

            # Retrieve both information units.
            unit_a = units_by_id.get(
                decision.information_unit_id_a
            )

            unit_b = units_by_id.get(
                decision.information_unit_id_b
            )

            # If either unit cannot be found, do not remove anything.
            if unit_a is None or unit_b is None:
                continue

            # Select the weaker-protected side of the redundant pair.
            unit_to_remove, unit_to_keep = (
                self._select_removal_target(
                    unit_a,
                    unit_b,
                )
            )

            # Never remove the same unit twice.
            if unit_to_remove.information_unit_id in removed_ids:
                continue

            # Record the selected removal.
            removed_ids.add(
                unit_to_remove.information_unit_id
            )

            # Create a reversible audit record.
            change_records.append(
                ChangeRecord(
                    information_unit_id=(
                        unit_to_remove.information_unit_id
                    ),
                    document_id=unit_to_remove.document_id,
                    original_text=unit_to_remove.text,
                    reason=decision.reason,
                    decision=decision.decision,
                    confidence=decision.confidence,
                    paired_information_unit_id=(
                        unit_to_keep.information_unit_id
                    ),
                )
            )

        # Keep every unit that was not selected for removal.
        retained_ids = [
            unit.information_unit_id
            for unit in information_units
            if unit.information_unit_id not in removed_ids
        ]
        ordered_removed_ids = [
            unit.information_unit_id
            for unit in information_units
            if unit.information_unit_id in removed_ids
        ]

        # Calculate the resulting information-unit count.
        final_count = len(retained_ids)

        # Return the complete optimization result.
        return OptimizationResult(
            retained_unit_ids=retained_ids,
            removed_unit_ids=ordered_removed_ids,
            change_records=change_records,
            original_unit_count=len(information_units),
            final_unit_count=final_count,
        )

    @staticmethod
    def _select_removal_target(
        unit_a: InformationUnit,
        unit_b: InformationUnit,
    ) -> tuple[InformationUnit, InformationUnit]:
        """
        Select which side of a REMOVE pair should be removed.

        Higher utility and rarity receive stronger protection.

        If protection is equal, the second unit is selected for removal
        so the result remains deterministic.
        """

        # Read utility scores from metadata first because Phase 5
        # stores those values there.
        utility_a = Optimizer._get_score(
            unit_a,
            "utility_score",
        )

        utility_b = Optimizer._get_score(
            unit_b,
            "utility_score",
        )

        # Read rarity protection scores.
        rarity_a = Optimizer._get_score(
            unit_a,
            "rarity_score",
        )

        rarity_b = Optimizer._get_score(
            unit_b,
            "rarity_score",
        )

        # Calculate total protection for each side.
        protection_a = (
            utility_a
            + rarity_a
        )

        protection_b = (
            utility_b
            + rarity_b
        )

        # Keep the stronger-protected information.
        if protection_a >= protection_b:
            return unit_b, unit_a

        return unit_a, unit_b

    @staticmethod
    def _get_score(
        unit: InformationUnit,
        score_name: str,
    ) -> float:
        """
        Retrieve a utility or rarity score from InformationUnit metadata.

        The function checks the explicit model field first and then
        falls back to metadata for compatibility with Phase 5.
        """

        # Read the direct model attribute.
        direct_value = getattr(
            unit,
            score_name,
            None,
        )

        if direct_value is not None:
            return max(
                0.0,
                min(1.0, float(direct_value)),
            )

        # Read the value stored by the Phase 5 service.
        metadata_value = unit.metadata.get(
            score_name,
            0.0,
        )

        return max(
            0.0,
            min(1.0, float(metadata_value)),
        )

    @staticmethod
    def _normalized_text(text: str) -> str:
        """Normalize harmless formatting when identifying exact repeats."""
        return re.sub(r"\s+", " ", text).strip().casefold()

    @staticmethod
    def _validate_information_units(
        information_units: List[InformationUnit],
    ) -> None:
        """
        Verify that all supplied objects are InformationUnit instances.
        """

        # Require a list.
        if not isinstance(information_units, list):
            raise TypeError(
                "information_units must be a list."
            )

        # Validate every item.
        for unit in information_units:
            if not isinstance(
                unit,
                InformationUnit,
            ):
                raise TypeError(
                    "Every item must be an InformationUnit."
                )
