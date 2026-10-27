"""Run Iteration 1 as a standalone dataset parsing demonstration."""

from __future__ import annotations

import argparse
from pathlib import Path

from services.pipeline_service import PipelineService


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse a TXT dataset into sentence-level information units."
    )
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args()

    if not args.input.is_file():
        parser.error(f"Input file does not exist: {args.input}")

    result = PipelineService().process_file(args.input)
    print(f"Documents parsed: {result.document_count}")
    print(f"Statements identified: {result.information_unit_count}")
    for unit in result.information_units[:5]:
        print(f"- {unit.text}")


if __name__ == "__main__":
    main()
