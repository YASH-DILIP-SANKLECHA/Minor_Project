"""
Minor Project One - Automatic Redundancy Analysis Service.

The only real project dataset is:

    datasets/raw/dataset.txt

Implemented phases:

    Phase 1 -> Parsing + segmentation
    Phase 2 -> Semantic embeddings
    Phase 3 -> Similarity/redundancy detection
    Phase 4 -> Information extraction
    Phase 5 -> Utility + rarity
    Phase 6 -> Contradiction detection
    Phase 7 -> KEEP / REMOVE / REVIEW

Important:
Phases 1-6 are preserved.
Phase 7 only consumes their results and does not modify the dataset.
Actual removal belongs to Phase 8.
"""

from __future__ import annotations

from pathlib import Path

from core.contradiction_engine.contradiction_engine import (
    ContradictionEngine,
)
from core.contradiction_engine.contradiction_result import (
    ContradictionResult,
)
from core.decision_engine.decision_engine import DecisionEngine
from core.decision_engine.decision_result import DecisionResult
from core.embedding_engine.embedding_engine import EmbeddingEngine
from core.information_extractor.information_extractor import (
    InformationExtractor,
)
from core.rarity_engine.rarity_engine import RarityEngine
from core.redundancy_engine.redundancy_engine import RedundancyEngine
from core.redundancy_engine.redundancy_result import (
    RedundancyAnalysisResult,
)
from core.utility_engine.utility_engine import UtilityEngine
from services.pipeline_service import PipelineService


class RedundancyAnalysisService:
    """
    Coordinate the complete Phase 1-7 analysis pipeline.
    """

    def __init__(
        self,
        pipeline_service: PipelineService | None = None,
        embedding_engine: EmbeddingEngine | None = None,
        redundancy_engine: RedundancyEngine | None = None,
        contradiction_engine: ContradictionEngine | None = None,
        decision_engine: DecisionEngine | None = None,
    ) -> None:
        """
        Initialize all project analysis components.
        """

        # Reuse the existing Phase 1 parser and segmenter.
        self.pipeline_service = (
            pipeline_service
            or PipelineService()
        )

        # Reuse the existing Phase 2 embedding engine.
        self.embedding_engine = (
            embedding_engine
            or EmbeddingEngine()
        )

        # Reuse the existing Phase 3 redundancy engine.
        self.redundancy_engine = (
            redundancy_engine
            or RedundancyEngine(
                embedding_engine=self.embedding_engine,
                similarity_threshold=0.80,
                redundancy_threshold=0.80,
            )
        )

        # Initialize the Phase 4 information extractor.
        self.information_extractor = InformationExtractor()

        # Initialize the Phase 5 utility engine.
        self.utility_engine = UtilityEngine()

        # Initialize the Phase 5 rarity engine.
        self.rarity_engine = RarityEngine()

        # Initialize the Phase 6 contradiction engine.
        self.contradiction_engine = (
            contradiction_engine
            or ContradictionEngine()
        )

        # Initialize the Phase 7 decision engine.
        self.decision_engine = (
            decision_engine
            or DecisionEngine()
        )

        # Store contradiction results from the latest analysis.
        self.last_contradictions: list[
            ContradictionResult
        ] = []

        # Store decision results from the latest analysis.
        self.last_decisions: list[
            DecisionResult
        ] = []

    def analyze_file(
        self,
        file_path: str | Path,
    ) -> RedundancyAnalysisResult:
        """
        Run the complete Phase 1-7 pipeline on the supplied dataset file.

        The file path is the only dataset-specific input.
        """

        # Phase 1:
        # Parse the actual dataset and create information units.
        pipeline_result = self.pipeline_service.process_file(
            file_path
        )

        # Phase 2:
        # Generate semantic embeddings.
        information_units = (
            self.embedding_engine.encode_information_units(
                pipeline_result.information_units
            )
        )

        # Phase 4:
        # Extract structured information from every unit.
        extractions = self.information_extractor.extract_many(
            information_units
        )

        # Phase 5:
        # Calculate utility scores.
        utility_scores = self.utility_engine.calculate_many(
            extractions
        )

        # Phase 5:
        # Calculate rarity scores.
        rarity_scores = self.rarity_engine.calculate_many(
            extractions
        )

        # Create an efficient lookup by information-unit ID.
        extraction_by_id = {
            extraction.information_unit_id: extraction
            for extraction in extractions
        }

        # Attach Phase 4/5 metadata to the existing InformationUnit objects.
        for information_unit in information_units:

            # Identify the current information unit.
            unit_id = information_unit.information_unit_id

            # Retrieve its extraction result.
            extraction = extraction_by_id[unit_id]

            # Store structured extracted information.
            information_unit.metadata[
                "extraction"
            ] = extraction.to_dict()

            # Store utility protection.
            information_unit.metadata[
                "utility_score"
            ] = utility_scores[unit_id]

            # Store rarity protection.
            information_unit.metadata[
                "rarity_score"
            ] = rarity_scores[unit_id]

        # Phase 3:
        # Preserve the existing cross-document similarity behavior.
        result = self.redundancy_engine.analyze(
            information_units,
            cross_document_only=True,
        )

        # Phase 6:
        # Analyze only the similar pairs identified by Phase 3.
        self.last_contradictions = (
            self.contradiction_engine.analyze_pairs(
                result.similar_pairs,
                extraction_by_id,
            )
        )

        # Build the utility/rarity metadata required by Phase 7.
        metadata_by_id = {
            information_unit.information_unit_id: {
                "utility_score": information_unit.metadata.get(
                    "utility_score",
                    0.0,
                ),
                "rarity_score": information_unit.metadata.get(
                    "rarity_score",
                    0.0,
                ),
            }
            for information_unit in information_units
        }

        # Phase 7:
        # Make KEEP/REMOVE/REVIEW recommendations.
        self.last_decisions = (
            self.decision_engine.decide_all(
                pairs=result.similar_pairs,
                metadata_by_id=metadata_by_id,
                contradictions=self.last_contradictions,
            )
        )

        # Return the same RedundancyAnalysisResult used by previous phases.
        return result

    def analyze_text(
        self,
        text: str,
    ) -> RedundancyAnalysisResult:
        """
        Run Phases 1-7 on in-memory text.

        This method is retained for the existing automated tests
        and future API usage.
        """

        # Phase 1:
        # Parse and segment the supplied text.
        pipeline_result = self.pipeline_service.process_text(
            text
        )

        # Phase 2:
        # Generate embeddings.
        information_units = (
            self.embedding_engine.encode_information_units(
                pipeline_result.information_units
            )
        )

        # Phase 4:
        # Extract structured information.
        extractions = self.information_extractor.extract_many(
            information_units
        )

        # Phase 5:
        # Calculate utility.
        utility_scores = self.utility_engine.calculate_many(
            extractions
        )

        # Phase 5:
        # Calculate rarity.
        rarity_scores = self.rarity_engine.calculate_many(
            extractions
        )

        # Build the extraction lookup.
        extraction_by_id = {
            extraction.information_unit_id: extraction
            for extraction in extractions
        }

        # Attach Phase 4/5 metadata to each information unit.
        for information_unit in information_units:

            # Retrieve the current unit ID.
            unit_id = information_unit.information_unit_id

            # Retrieve its extraction.
            extraction = extraction_by_id[unit_id]

            # Store extraction metadata.
            information_unit.metadata[
                "extraction"
            ] = extraction.to_dict()

            # Store utility.
            information_unit.metadata[
                "utility_score"
            ] = utility_scores[unit_id]

            # Store rarity.
            information_unit.metadata[
                "rarity_score"
            ] = rarity_scores[unit_id]

        # Preserve the test-oriented behavior of the service.
        result = self.redundancy_engine.analyze(
            information_units,
            cross_document_only=False,
        )

        # Phase 6:
        # Detect contradictions among similar pairs.
        self.last_contradictions = (
            self.contradiction_engine.analyze_pairs(
                result.similar_pairs,
                extraction_by_id,
            )
        )

        # Prepare metadata for Phase 7.
        metadata_by_id = {
            information_unit.information_unit_id: {
                "utility_score": information_unit.metadata.get(
                    "utility_score",
                    0.0,
                ),
                "rarity_score": information_unit.metadata.get(
                    "rarity_score",
                    0.0,
                ),
            }
            for information_unit in information_units
        }

        # Phase 7:
        # Make decisions for all similar pairs.
        self.last_decisions = (
            self.decision_engine.decide_all(
                pairs=result.similar_pairs,
                metadata_by_id=metadata_by_id,
                contradictions=self.last_contradictions,
            )
        )

        return result

    def get_contradictions(
        self,
    ) -> list[ContradictionResult]:
        """
        Return contradiction results from the latest analysis.
        """

        # Return a copy to protect internal state.
        return list(self.last_contradictions)

    def get_decisions(
        self,
    ) -> list[DecisionResult]:
        """
        Return Phase 7 decisions from the latest analysis.
        """

        # Return a copy to protect internal state.
        return list(self.last_decisions)

    @staticmethod
    def print_result(
        result: RedundancyAnalysisResult,
        contradictions: list[ContradictionResult] | None = None,
        decisions: list[DecisionResult] | None = None,
    ) -> None:
        """
        Print the existing similarity/contradiction results and
        the new Phase 7 decisions.
        """

        # Print the number of pairwise comparisons.
        print(
            f"Total comparisons performed: "
            f"{result.total_comparisons}"
        )

        # Print the number of final similar pairs.
        print(
            f"Final similar pairs detected: "
            f"{result.similar_pair_count}"
        )

        # Print the existing Phase 3 threshold.
        print(
            f"Similarity threshold: "
            f"{result.similarity_threshold:.2f}"
        )

        # Print the number of similarity groups.
        print(
            f"Similarity groups: "
            f"{result.group_count}"
        )

        print(
            "\n"
            + "=" * 70
            + "\nFINAL SIMILAR PAIRS\n"
            + "=" * 70
        )

        # Preserve the existing final similar-pair output.
        if not result.similar_pairs:
            print(
                "No cross-document similar pairs detected."
            )
        else:
            # Sort candidates by strongest similarity first.
            sorted_pairs = sorted(
                result.similar_pairs,
                key=lambda pair: pair.similarity_score,
                reverse=True,
            )

            # Print every final similar pair.
            for index, pair in enumerate(
                sorted_pairs,
                start=1,
            ):
                print(f"\n[{index}]")
                print(pair.text_a)
                print("<->")
                print(pair.text_b)
                print(
                    f"Similarity: "
                    f"{pair.similarity_score:.4f}"
                )
                print(
                    f"Redundancy Score: "
                    f"{pair.redundancy_score:.4f}"
                )

        print(
            "\n"
            + "=" * 70
            + "\nCONTRADICTION CANDIDATES\n"
            + "=" * 70
        )

        # Print contradiction results produced by Phase 6.
        if not contradictions:
            print(
                "No contradiction candidates detected."
            )
        else:
            # Print each contradiction candidate.
            for index, contradiction in enumerate(
                contradictions,
                start=1,
            ):
                print(f"\n[{index}]")
                print(contradiction.text_a)
                print("<->")
                print(contradiction.text_b)
                print(
                    f"Similarity: "
                    f"{contradiction.similarity_score:.4f}"
                )
                print(
                    f"Contradiction Score: "
                    f"{contradiction.contradiction_score:.4f}"
                )
                print(
                    f"Value A: "
                    f"{', '.join(contradiction.value_a)}"
                )
                print(
                    f"Value B: "
                    f"{', '.join(contradiction.value_b)}"
                )
                print(
                    f"Reason: "
                    f"{contradiction.reason}"
                )

        print(
            "\n"
            + "=" * 70
            + "\nDECISIONS\n"
            + "=" * 70
        )

        # Report when there are no decisions.
        if not decisions:
            print(
                "No decision candidates detected."
            )
            return

        # Count each decision category for the summary.
        keep_count = sum(
            decision.decision == "KEEP"
            for decision in decisions
        )

        remove_count = sum(
            decision.decision == "REMOVE"
            for decision in decisions
        )

        review_count = sum(
            decision.decision == "REVIEW"
            for decision in decisions
        )

        # Print the summary counts.
        print(
            f"KEEP: {keep_count}"
        )
        print(
            f"REMOVE: {remove_count}"
        )
        print(
            f"REVIEW: {review_count}"
        )

        # Print each decision with its supporting reason.
        for index, decision in enumerate(
            decisions,
            start=1,
        ):
            print(f"\n[{index}]")
            print(decision.text_a)
            print("<->")
            print(decision.text_b)
            print(
                f"Decision: "
                f"{decision.decision}"
            )
            print(
                f"Confidence: "
                f"{decision.confidence:.4f}"
            )
            print(
                f"Reason: "
                f"{decision.reason}"
            )


def main() -> None:
    """
    Run the complete Phase 1-7 analysis on the real dataset.
    """

    # Use the project's only actual dataset file.
    dataset_path = Path(
        "datasets/raw/dataset.txt"
    )

    # Create the complete analysis service.
    service = RedundancyAnalysisService()

    # Run the actual project dataset through Phases 1-7.
    result = service.analyze_file(
        dataset_path
    )

    # Retrieve contradiction results.
    contradictions = service.get_contradictions()

    # Retrieve Phase 7 decisions.
    decisions = service.get_decisions()

    # Display all currently implemented results.
    service.print_result(
        result,
        contradictions,
        decisions,
    )


if __name__ == "__main__":
    # Start the analysis when this module is executed directly.
    main()