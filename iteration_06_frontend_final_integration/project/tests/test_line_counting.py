"""Regression tests for physical browser line-ending normalization."""

from services.redundancy_analysis_service import RedundancyAnalysisService


def test_analyze_text_counts_only_nonblank_source_lines() -> None:
    """CRLF artifacts must not inflate the user-facing input line count."""
    text = "First statement.\r\n\r\nSecond statement.\r\n"
    assert RedundancyAnalysisService._count_nonblank_lines(text) == 2
