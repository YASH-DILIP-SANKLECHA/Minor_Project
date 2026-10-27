"""Run Iteration 3 as a standalone duplicate-and-conflict detection demo."""

from __future__ import annotations

import argparse
from pathlib import Path

from core.contradiction_engine.contradiction_engine import ContradictionEngine
from core.decision_engine.decision_engine import DecisionEngine
from core.embedding_engine.embedding_engine import EmbeddingEngine
from core.information_extractor.information_extractor import InformationExtractor
from core.optimizer.optimizer import Optimizer
from core.reconstruction.reconstruction_engine import ReconstructionEngine
from core.redundancy_engine.redundancy_engine import RedundancyEngine
from core.rarity_engine.rarity_engine import RarityEngine
from core.utility_engine.utility_engine import UtilityEngine
from services.pipeline_service import PipelineService


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Refine duplicates while retaining possible factual conflicts."
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output") / "refined_before_verification.txt",
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
    extractions = InformationExtractor().extract_many(units)
    extraction_by_id = {item.information_unit_id: item for item in extractions}
    utility = UtilityEngine().calculate_many(extractions)
    rarity = RarityEngine().calculate_many(extractions)
    metadata = {
        unit.information_unit_id: {
            "utility_score": utility[unit.information_unit_id],
            "rarity_score": rarity[unit.information_unit_id],
        }
        for unit in units
    }
    conflicts = ContradictionEngine().analyze_pairs(
        similarity.all_similarities,
        extraction_by_id,
    )
    decisions = DecisionEngine().decide_all(
        similarity.similar_pairs,
        metadata,
        conflicts,
    )
    optimization = Optimizer().optimize(units, decisions)
    refined_text = ReconstructionEngine().reconstruct(
        units,
        optimization.retained_unit_ids,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(refined_text + ("\n" if refined_text else ""), encoding="utf-8")
    print(f"Original statements: {len(units)}")
    print(f"Safe duplicate removals: {len(optimization.removed_unit_ids)}")
    print(f"Possible conflicts retained: {len(conflicts)}")
    print(f"Saved: {args.output.resolve()}")


if __name__ == "__main__":
    main()
