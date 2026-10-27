"""
INFORA - Phase 1 Pipeline Service

Current pipeline:

TXT Dataset
    ↓
Document Parser
    ↓
Documents
    ↓
Sentence Segmenter
    ↓
Information Units

No AI/ML decisions are performed here yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from core.parser.document_parser import DocumentParser
from core.segmenter.sentence_segmenter import SentenceSegmenter
from models.document import Document
from models.information_unit import InformationUnit


@dataclass
class PipelineResult:
    """Contains the output of the Phase 1 dataset pipeline."""

    documents: List[Document]
    information_units: List[InformationUnit]

    @property
    def document_count(self) -> int:
        """Return number of parsed documents."""
        return len(self.documents)

    @property
    def information_unit_count(self) -> int:
        """Return number of information units."""
        return len(self.information_units)


class PipelineService:
    """
    Coordinates the initial INFORA dataset processing pipeline.
    """

    def __init__(
        self,
        parser: DocumentParser | None = None,
        segmenter: SentenceSegmenter | None = None,
    ) -> None:
        self.parser = parser or DocumentParser()
        self.segmenter = segmenter or SentenceSegmenter()

    def process_file(self, file_path: str | Path) -> PipelineResult:
        """
        Process a TXT dataset file.

        Args:
            file_path: Path to the TXT dataset.

        Returns:
            PipelineResult containing documents and information units.
        """
        documents = self.parser.parse_file(file_path)

        information_units = self.segmenter.segment_documents(
            documents
        )

        return PipelineResult(
            documents=documents,
            information_units=information_units,
        )

    def process_text(self, text: str) -> PipelineResult:
        """
        Process raw dataset text.

        Args:
            text: Dataset text.

        Returns:
            PipelineResult containing documents and information units.
        """
        documents = self.parser.parse_text(text)

        information_units = self.segmenter.segment_documents(
            documents
        )

        return PipelineResult(
            documents=documents,
            information_units=information_units,
        )