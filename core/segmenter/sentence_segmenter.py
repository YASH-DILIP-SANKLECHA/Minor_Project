"""
INFORA - Sentence Segmenter

Converts document text into sentence-level units.

Uses spaCy's lightweight sentencizer so that no external language model
download is required for Phase 1.
"""

from __future__ import annotations

from typing import List

import spacy

from models.document import Document
from models.information_unit import InformationUnit


class SentenceSegmenter:
    """Splits documents into structured sentence-level information units."""

    def __init__(self) -> None:
        self.nlp = spacy.blank("en")

        if "sentencizer" not in self.nlp.pipe_names:
            self.nlp.add_pipe("sentencizer")

    def segment_document(self, document: Document) -> List[InformationUnit]:
        """
        Segment one document into sentence-level information units.

        Args:
            document: Document object to process.

        Returns:
            List of InformationUnit objects.
        """
        if not isinstance(document, Document):
            raise TypeError("document must be a Document instance.")

        if not document.content.strip():
            return []

        doc = self.nlp(document.content)

        information_units: List[InformationUnit] = []

        for index, sentence in enumerate(doc.sents, start=1):
            sentence_text = sentence.text.strip()

            if not sentence_text:
                continue

            information_units.append(
                InformationUnit(
                    information_unit_id=(
                        f"{document.document_id}_unit_{index:04d}"
                    ),
                    document_id=document.document_id,
                    text=sentence_text,
                    unit_index=index,
                )
            )

        return information_units

    def segment_documents(
        self,
        documents: List[Document],
    ) -> List[InformationUnit]:
        """
        Segment multiple documents.

        Args:
            documents: List of Document objects.

        Returns:
            Flattened list of InformationUnit objects.
        """
        if not isinstance(documents, list):
            raise TypeError("documents must be a list.")

        information_units: List[InformationUnit] = []

        for document in documents:
            information_units.extend(
                self.segment_document(document)
            )

        return information_units