"""
Minor Project One - Information Extractor.

Phase 4 extracts structured factual information from each
InformationUnit.

The original dataset text is never modified.

No LLM is used in this phase.
"""

from __future__ import annotations

import re

import spacy

from core.information_extractor.extraction_result import (
    ExtractionResult,
)
from models.information_unit import InformationUnit


class InformationExtractor:
    """
    Extract structured factual signals from InformationUnit objects.
    """

    # Match values such as:
    # 1.46
    # 1.46 billion
    # 500 million
    NUMBER_PATTERN = re.compile(
        r"\b\d+(?:\.\d+)?(?:\s?(?:thousand|million|billion|trillion))?\b",
        re.IGNORECASE,
    )

    # Dataset statements frequently spell small factual quantities instead of
    # writing digits (for example, "seven days" versus "twelve days").
    # Treat those quantities as values too, so they take the same
    # contradiction route as "7" versus "12".  The source text remains
    # untouched; this is extraction metadata only.
    NUMBER_WORD_PATTERN = re.compile(
        r"\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|"
        r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|"
        r"eighteen|nineteen|twenty)\b",
        re.IGNORECASE,
    )

    # Match four-digit years such as 2025.
    DATE_PATTERN = re.compile(
        r"\b(?:19|20)\d{2}\b"
    )

    def __init__(self) -> None:
        """
        Initialize the lightweight spaCy processing pipeline.

        A blank English pipeline is used here so the project does not
        need an additional large spaCy model download.
        """

        # Create the basic English NLP pipeline.
        self.nlp = spacy.blank("en")

        # Add sentence-boundary handling if it is not already present.
        if "sentencizer" not in self.nlp.pipe_names:
            self.nlp.add_pipe("sentencizer")

    def extract(
        self,
        information_unit: InformationUnit,
    ) -> ExtractionResult:
        """
        Extract structured information from one InformationUnit.

        The following signals are currently extracted:
        - named entities when available
        - numeric/value expressions
        - years
        - numeric components
        """

        # Make sure the caller supplied the expected model type.
        if not isinstance(
            information_unit,
            InformationUnit,
        ):
            raise TypeError(
                "information_unit must be an InformationUnit."
            )

        # Process the original sentence with spaCy.
        doc = self.nlp(information_unit.text)

        # Extract named entities if the configured NLP pipeline provides them.
        # The current blank spaCy pipeline may return an empty list.
        entities = [
            {
                "text": entity.text,
                "label": entity.label_,
            }
            for entity in doc.ents
        ]

        # Extract complete numeric/value expressions.
        values = self._extract_values(
            information_unit.text
        )

        # Extract four-digit year expressions.
        dates = self._extract_dates(
            information_unit.text
        )

        # Extract the numeric components separately.
        numbers = self._extract_numbers(
            information_unit.text
        )

        # Return the structured result without changing the original text.
        return ExtractionResult(
            information_unit_id=(
                information_unit.information_unit_id
            ),
            text=information_unit.text,
            entities=entities,
            values=values,
            dates=dates,
            numbers=numbers,
        )

    def extract_many(
        self,
        information_units: list[InformationUnit],
    ) -> list[ExtractionResult]:
        """
        Extract structured information from every InformationUnit.
        """

        # Verify that the input collection is a list.
        if not isinstance(information_units, list):
            raise TypeError(
                "information_units must be a list."
            )

        # Process each information unit independently.
        return [
            self.extract(unit)
            for unit in information_units
        ]

    @classmethod
    def _extract_values(
        cls,
        text: str,
    ) -> list[str]:
        """
        Extract complete numeric/value expressions from a sentence.
        """

        # Find all configured numeric/value expressions.
        matches = cls.NUMBER_PATTERN.findall(text)
        matches.extend(cls.NUMBER_WORD_PATTERN.findall(text))

        # Remove duplicates while preserving order.
        return list(dict.fromkeys(matches))

    @classmethod
    def _extract_dates(
        cls,
        text: str,
    ) -> list[str]:
        """
        Extract four-digit year expressions from a sentence.
        """

        # Find year-like values.
        matches = cls.DATE_PATTERN.findall(text)

        # Remove duplicate years while preserving order.
        return list(dict.fromkeys(matches))

    @classmethod
    def _extract_numbers(
        cls,
        text: str,
    ) -> list[str]:
        """
        Extract numeric components such as 1.46 or 500.
        """

        # Match integer and decimal numeric components.
        matches = re.findall(
            r"\b\d+(?:\.\d+)?\b",
            text,
        )

        # Remove duplicate numeric components.
        return list(dict.fromkeys(matches))
