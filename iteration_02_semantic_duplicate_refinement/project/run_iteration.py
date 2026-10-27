"""Run Iteration 2 as a standalone local duplicate-refinement demonstration."""

from __future__ import annotations

import argparse
from pathlib import Path

from core.decision_engine.decision_engine import DecisionEngine
from core.embedding_engine.embedding_engine import EmbeddingEngine
from core.optimizer.optimizer import Optimizer
from core.reconstruction.reconstruction_engine import ReconstructionEngine
from core.redundancy_engine.redundancy_engine import RedundancyEngine
from services.pipeline_service import PipelineService


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Identify and remove safe duplicate statements locally."
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output") / "optimized_dataset.txt",
    )
    args = parser.parse_args()
    if not args.input.is_file():
        parser.error(f"Input file does not exist: {args.input}")

    units = PipelineService().process_file(args.input).information_units
    embeddings = EmbeddingEngine()
    units = embeddings.encode_information_units(units)
    similarity = RedundancyEngine(embedding_engine=embeddings).analyze(
        units,
        cross_document_only=False,
    )
    metadata = {
        unit.information_unit_id: {"utility_score": 0.0, "rarity_score": 0.0}
        for unit in units
    }
    decisions = DecisionEngine().decide_all(similarity.similar_pairs, metadata, [])
    optimization = Optimizer().optimize(units, decisions)
    refined_text = ReconstructionEngine().reconstruct(
        units,
        optimization.retained_unit_ids,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(refined_text + ("\n" if refined_text else ""), encoding="utf-8")
    print(f"Original statements: {len(units)}")
    print(f"Duplicate candidates: {len(similarity.similar_pairs)}")
    print(f"Refined statements: {optimization.final_unit_count}")
    print(f"Saved: {args.output.resolve()}")


if __name__ == "__main__":
    main()
