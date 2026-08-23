"""
INFORA - Document Parser

Reads a TXT dataset and converts it into structured Document objects.

Supported input:
1. Articles separated by headings such as:
   Article 1
   Article 2

2. Articles separated by blank lines.

The parser preserves the original article content.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List

from models.document import Document


class DocumentParser:
    """Parses a TXT dataset into Document objects."""

    ARTICLE_HEADING_PATTERN = re.compile(
        r"^\s*(?:article|document)\s+(\d+)\s*:?\s*$",
        re.IGNORECASE,
    )

    def parse_file(self, file_path: str | Path) -> List[Document]:
        """
        Read and parse a TXT dataset.

        Args:
            file_path: Path to the input TXT dataset.

        Returns:
            List of parsed Document objects.

        Raises:
            FileNotFoundError: If the dataset does not exist.
            ValueError: If the dataset is empty.
            UnicodeDecodeError: If the file cannot be decoded as UTF-8.
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Dataset file not found: {path}")

        if not path.is_file():
            raise ValueError(f"Dataset path is not a file: {path}")

        text = path.read_text(encoding="utf-8")

        if not text.strip():
            raise ValueError("Dataset file is empty.")

        return self.parse_text(text)

    def parse_text(self, text: str) -> List[Document]:
        """
        Parse raw dataset text into Document objects.

        The parser first tries to recognize explicit Article/Document
        headings. If none are present, blank-line-separated blocks are
        treated as individual documents.

        Args:
            text: Raw dataset text.

        Returns:
            List of Document objects.
        """
        if not isinstance(text, str):
            raise TypeError("text must be a string.")

        cleaned_text = text.replace("\r\n", "\n").replace("\r", "\n").strip()

        if not cleaned_text:
            raise ValueError("Dataset text is empty.")

        if self._contains_article_headings(cleaned_text):
            blocks = self._parse_heading_based_dataset(cleaned_text)
        else:
            blocks = self._parse_blank_line_dataset(cleaned_text)

        documents: List[Document] = []

        for index, content in enumerate(blocks, start=1):
            normalized_content = self._normalize_content(content)

            if not normalized_content:
                continue

            documents.append(
                Document(
                    document_id=f"doc_{index:06d}",
                    content=normalized_content,
                    source_type="txt",
                )
            )

        if not documents:
            raise ValueError("No valid documents were found in the dataset.")

        return documents

    def _contains_article_headings(self, text: str) -> bool:
        """Return True when explicit article/document headings exist."""
        return any(
            self.ARTICLE_HEADING_PATTERN.match(line)
            for line in text.splitlines()
        )

    def _parse_heading_based_dataset(self, text: str) -> List[str]:
        """Parse datasets containing Article/Document headings."""
        blocks: List[str] = []
        current_lines: List[str] = []

        for line in text.splitlines():
            if self.ARTICLE_HEADING_PATTERN.match(line):
                if current_lines:
                    blocks.append("\n".join(current_lines).strip())
                    current_lines = []
                continue

            current_lines.append(line)

        if current_lines:
            blocks.append("\n".join(current_lines).strip())

        return blocks

    def _parse_blank_line_dataset(self, text: str) -> List[str]:
        """Parse datasets where documents are separated by blank lines."""
        raw_blocks = re.split(r"\n\s*\n+", text)

        return [
            block.strip()
            for block in raw_blocks
            if block.strip()
        ]

    def _normalize_content(self, content: str) -> str:
        """
        Normalize unnecessary whitespace without changing the actual text
        content.
        """
        lines = [line.strip() for line in content.splitlines()]
        lines = [line for line in lines if line]

        return " ".join(lines)