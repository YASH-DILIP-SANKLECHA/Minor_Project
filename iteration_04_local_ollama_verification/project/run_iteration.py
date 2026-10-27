"""Run Iteration 4 as a standalone local-Ollama refinement demonstration."""

from __future__ import annotations

import argparse
from pathlib import Path

from services.redundancy_analysis_service import RedundancyAnalysisService


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Refine a dataset and verify public conflicts with local Ollama."
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path("output"))
    args = parser.parse_args()
    if not args.input.is_file():
        parser.error(f"Input file does not exist: {args.input}")

    service = RedundancyAnalysisService()
    service.analyze_file(args.input)
    refined_file = service.build_optimized_dataset(args.output)
    print(f"Original statements: {service.last_original_source_line_count}")
    print(f"Local-AI conflict decisions: {len(service.last_phase9_results)}")
    print(f"Manual cases retained: {len(service.last_manual_verifications)}")
    print(f"Saved: {refined_file.resolve()}")


if __name__ == "__main__":
    main()
