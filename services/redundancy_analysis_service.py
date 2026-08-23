"""
Minor Project One - Automatic Redundancy Analysis Service

This service analyzes ONLY the user's actual dataset file.

It does not contain:
- sample text
- hardcoded keywords
- Delhi-specific logic
- population-specific logic
- Bengaluru-specific logic

The dataset file is the only source of information.
"""

from __future__ import annotations

from pathlib import Path

from core.embedding_engine.embedding_engine import EmbeddingEngine
from core.redundancy_engine.redundancy_engine import RedundancyEngine
from core.redundancy_engine.redundancy_result import (
    RedundancyAnalysisResult,
)
from services.pipeline_service import PipelineService


class RedundancyAnalysisService:
    """
    Runs the complete automatic redundancy analysis pipeline.

    Flow:

        User's dataset.txt
             ↓
        Document parsing
             ↓
        Sentence segmentation
             ↓
        Information units
             ↓
        Sentence embeddings
             ↓
        ALL pairwise comparisons
             ↓
        Cross-document similarity filtering
             ↓
        Final similar pairs
    """

    def __init__(
        self,
        pipeline_service: PipelineService | None = None,
        embedding_engine: EmbeddingEngine | None = None,
        redundancy_engine: RedundancyEngine | None = None,
    ) -> None:
        """
        Initialize the automatic analysis service.
        """

        # Use the existing Phase 1 pipeline.
        self.pipeline_service = (
            pipeline_service
            or PipelineService()
        )

        # Use the existing Phase 2 embedding engine.
        self.embedding_engine = (
            embedding_engine
            or EmbeddingEngine()
        )

        # Use the Phase 3 redundancy engine with the same embedding engine.
        self.redundancy_engine = (
            redundancy_engine
            or RedundancyEngine(
                embedding_engine=self.embedding_engine,
                similarity_threshold=0.80,
                redundancy_threshold=0.80,
            )
        )

    def analyze_file(
        self,
        file_path: str | Path,
    ) -> RedundancyAnalysisResult:
        """
        Analyze the supplied dataset file automatically.

        The caller supplies only the file path.
        The contents are read and analyzed automatically.
        """

        # Parse the actual dataset file into documents and information units.
        pipeline_result = self.pipeline_service.process_file(
            file_path
        )

        # Convert every information unit into a semantic embedding.
        information_units = (
            self.embedding_engine.encode_information_units(
                pipeline_result.information_units
            )
        )

        # Run the redundancy engine.
        # Every pair is compared internally, but final candidates
        # are restricted to high-similarity pairs across different documents.
        return self.redundancy_engine.analyze(
            information_units,
            cross_document_only=True,
        )

    @staticmethod
    def print_result(
        result: RedundancyAnalysisResult,
    ) -> None:
        """
        Print ONLY the final automatically detected similar pairs.

        The complete pairwise similarity matrix remains available
        internally through result.all_similarities, but it is not dumped
        to the terminal.

        This keeps the terminal output focused on the project's actual
        redundancy candidates.
        """

        # Show how many total pairwise comparisons were performed internally.
        print(
            f"Total comparisons performed: "
            f"{result.total_comparisons}"
        )

        # Show how many final cross-document similar pairs were detected.
        print(
            f"Final similar pairs detected: "
            f"{result.similar_pair_count}"
        )

        # Show the current experimental semantic threshold.
        print(
            f"Similarity threshold: "
            f"{result.similarity_threshold:.2f}"
        )

        # Show the number of similarity groups.
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

        # If no pair satisfies the current criteria, report that clearly.
        if not result.similar_pairs:
            print("No cross-document similar pairs detected.")
            return

        # Sort the final pairs from highest similarity to lowest.
        sorted_pairs = sorted(
            result.similar_pairs,
            key=lambda pair: pair.similarity_score,
            reverse=True,
        )

        # Print ONLY the final similar pairs.
        for index, pair in enumerate(
            sorted_pairs,
            start=1,
        ):

            # Display the pair number.
            print(f"\n[{index}]")

            # Display the first sentence.
            print(pair.text_a)

            # Display the relationship marker.
            print("<->")

            # Display the second sentence.
            print(pair.text_b)

            # Display the semantic similarity score.
            print(
                f"Similarity: "
                f"{pair.similarity_score:.4f}"
            )

            # Display the current Phase 3 redundancy score.
            print(
                f"Redundancy Score: "
                f"{pair.redundancy_score:.4f}"
            )


def main() -> None:
    """
    Analyze the project's actual dataset.txt.

    No text is embedded in this file.
    """

    # Point directly to the real project dataset.
    dataset_path = Path(
        "datasets/raw/dataset.txt"
    )

    # Create the automatic service.
    service = RedundancyAnalysisService()

    # Analyze only the supplied dataset file.
    result = service.analyze_file(
        dataset_path
    )

    # Print only the final similar-pair results.
    service.print_result(result)


if __name__ == "__main__":
    # Start the analysis when the module is executed directly.
    main()