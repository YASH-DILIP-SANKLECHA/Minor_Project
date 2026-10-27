"""
Minor Project One - Reconstruction Engine.

Rebuilds a readable dataset from retained InformationUnits.

The original raw dataset is never modified.

Documents are reconstructed in their original document order,
and information units are reconstructed in their original unit order.
"""

from __future__ import annotations

from collections import defaultdict

from models.information_unit import InformationUnit


class ReconstructionEngine:
    """
    Reconstruct an optimized dataset from retained information units.
    """

    def reconstruct(
        self,
        information_units: list[InformationUnit],
        retained_unit_ids: list[str],
    ) -> str:
        """
        Build the refined dataset text.

        Only information units listed in retained_unit_ids are included.

        Document order is determined from the first appearance of each
        document in the original information-unit sequence.
        """

        # Convert the retained IDs into a set for fast lookup.
        retained_set = set(
            retained_unit_ids
        )

        # Group retained units by document.
        documents: dict[str, list[InformationUnit]] = (
            defaultdict(list)
        )

        # Preserve the original sequence while assigning units to documents.
        for unit in information_units:

            # Skip information selected for removal.
            if unit.information_unit_id not in retained_set:
                continue

            # Append the retained unit to its original document group.
            documents[unit.document_id].append(unit)

        # Store output document sections in their original document order.
        output_sections: list[str] = []

        # Track which document IDs have already been emitted.
        emitted_documents: set[str] = set()

        # Iterate through the original information-unit ordering.
        for unit in information_units:

            # Read this unit's document ID.
            document_id = unit.document_id

            # Skip documents already reconstructed.
            if document_id in emitted_documents:
                continue

            # Mark the document as processed.
            emitted_documents.add(document_id)

            # Retrieve the retained units of this document.
            document_units = documents.get(
                document_id,
                [],
            )

            # Ignore documents from which every unit was removed.
            if not document_units:
                continue

            # Sort by original sentence position.
            document_units.sort(
                key=lambda current_unit: current_unit.unit_index
            )

            # Keep one retained information unit per output line. Joining
            # sentences with spaces collapses a large refined dataset into
            # one unreadable physical line.
            document_text = "\n".join(
                current_unit.text.strip()
                for current_unit in document_units
                if current_unit.text.strip()
            )

            # Preserve document boundaries without inserting synthetic text
            # that was not present in the user's dataset.
            output_sections.append(document_text)

        # Separate reconstructed documents using blank lines.
        return "\n\n".join(
            output_sections
        ).strip()

    def reconstruct_from_units(
        self,
        information_units: list[InformationUnit],
    ) -> str:
        """
        Reconstruct a dataset without removing any information.

        This is useful for testing the reconstruction engine independently.
        """

        # Retain every existing information-unit ID.
        retained_ids = [
            unit.information_unit_id
            for unit in information_units
        ]

        # Reuse the normal reconstruction logic.
        return self.reconstruct(
            information_units,
            retained_ids,
        )
