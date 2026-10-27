"""
Minor Project One - Automatic Redundancy Analysis Service.

Implemented phases:

    Phase 1 -> Parsing + segmentation
    Phase 2 -> Semantic embeddings
    Phase 3 -> Similarity/redundancy detection
    Phase 4 -> Information extraction
    Phase 5 -> Utility + rarity
    Phase 6 -> Contradiction detection
    Phase 7 -> KEEP / REMOVE / REVIEW
    Phase 8 -> Intelligent optimization + reconstruction

The original dataset:

    datasets/raw/dataset.txt

is never overwritten by Phase 8.

Phase 8 produces:
    datasets/optimized/optimized_dataset.txt
    datasets/optimized/changes.json
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from collections.abc import Callable

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
from core.optimizer.optimizer import Optimizer
from core.optimizer.optimization_result import (
    OptimizationResult,
)
from core.rarity_engine.rarity_engine import RarityEngine
from core.redundancy_engine.redundancy_engine import RedundancyEngine
from core.redundancy_engine.redundancy_result import (
    RedundancyAnalysisResult,
)
from core.reconstruction.reconstruction_engine import (
    ReconstructionEngine,
)
from core.utility_engine.utility_engine import UtilityEngine
from core.llm.manual_verification_result import ManualVerificationResult
from core.llm.verification_engine import VerificationEngine
from core.llm.verification_result import VerificationResult
from models.information_unit import InformationUnit
from services.pipeline_service import PipelineService


class RedundancyAnalysisService:
    """
    Coordinate the complete Phase 1-8 analysis pipeline.
    """

    # Ollama verifies candidates sequentially.  This capacity covers a large
    # validation batch (including 200 public conflicts) without silently
    # changing public facts into manual-review items.  Above the capacity,
    # candidates are still preserved for manual review rather than lost.
    MAX_PHASE9_VERIFICATIONS = 250
    MAX_PRINTED_ITEMS = 50

    def __init__(
        self,
        pipeline_service: PipelineService | None = None,
        embedding_engine: EmbeddingEngine | None = None,
        redundancy_engine: RedundancyEngine | None = None,
        contradiction_engine: ContradictionEngine | None = None,
        decision_engine: DecisionEngine | None = None,
        progress_callback: Callable[[str, int], None] | None = None,
    ) -> None:
        """
        Initialize all analysis components.
        """

        # The web application supplies this callback so the visible status is
        # tied to the real work, rather than to a timer in the browser.
        self.progress_callback = progress_callback

        # Reuse the existing Phase 1 dataset pipeline.
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
                # These are candidate thresholds. Qwen or the user makes the
                # final conflict decision, so a strict 0.80 filter must not
                # discard valid paraphrases and factual conflicts first.
                similarity_threshold=0.65,
                redundancy_threshold=0.65,
            )
        )

        # Initialize Phase 4 extraction.
        self.information_extractor = InformationExtractor()

        # Initialize Phase 5 utility analysis.
        self.utility_engine = UtilityEngine()

        # Initialize Phase 5 rarity analysis.
        self.rarity_engine = RarityEngine()

        # Initialize Phase 6 contradiction detection.
        self.contradiction_engine = (
            contradiction_engine
            # MiniLM often gives factually conflicting paraphrases a score
            # below 0.80 because the crucial value is different. This remains
            # only a candidate threshold; no statement is removed here.
            or ContradictionEngine(contradiction_threshold=0.40)
        )

        # Initialize Phase 7 decision making.
        self.decision_engine = (
            decision_engine
            or DecisionEngine()
        )

        # Initialize Phase 8 optimization.
        self.optimizer = Optimizer()

        # Initialize Phase 8 dataset reconstruction.
        self.reconstruction_engine = (
            ReconstructionEngine()
        )

        # Initialize Phase 9 local-AI verification.
        self.verification_engine = VerificationEngine()

        # Store latest contradiction results.
        self.last_contradictions: list[
            ContradictionResult
        ] = []

        # Store latest decision results.
        self.last_decisions: list[
            DecisionResult
        ] = []

        # Store latest optimization results.
        self.last_optimization: OptimizationResult | None = None

        # Store the latest information units so Phase 8 can reconstruct
        # the refined dataset after analysis.
        self.last_information_units: list[
            InformationUnit
        ] = []

        # Track physical input/output line counts separately from sentence
        # counts so the final report reflects the user's actual files.
        self.last_original_source_line_count = 0
        self.last_refined_output_line_count = 0

        # Store latest Phase 9 Qwen verification results.
        self.last_phase9_results: list[VerificationResult] = []

        # Store candidates separately from results so the audit log records
        # both generated and successfully verified Phase 9 cases.
        self.last_phase9_candidates = []

        # Store latest Phase 9 manual-verification flags.
        self.last_manual_verifications: list[
            ManualVerificationResult
        ] = []

    def _notify_progress(self, message: str, progress: int) -> None:
        """Publish a real pipeline milestone when the caller requested it."""
        if self.progress_callback is not None:
            self.progress_callback(message, progress)

    @staticmethod
    def _count_nonblank_lines(text: str) -> int:
        """Count statements without CRLF-created blank-line artifacts."""
        return sum(1 for line in text.splitlines() if line.strip())

    def analyze_file(
        self,
        file_path: str | Path,
    ) -> RedundancyAnalysisResult:
        """
        Run the complete Phase 1-8 pipeline on the actual dataset file.

        The raw dataset itself is never modified.
        """

        self.last_original_source_line_count = self._count_nonblank_lines(
            Path(file_path).read_text(encoding="utf-8")
        )

        self._notify_progress("Reading and separating statements.", 12)

        # Phase 1:
        # Parse the dataset and create information units.
        pipeline_result = self.pipeline_service.process_file(
            file_path
        )

        self._notify_progress("Creating local semantic embeddings.", 22)

        # Phase 2:
        # Generate semantic embeddings.
        information_units = (
            self.embedding_engine.encode_information_units(
                pipeline_result.information_units
            )
        )

        self._notify_progress("Preparing statement details for review.", 40)

        # Phase 4:
        # Extract structured information.
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

        # Build an efficient extraction lookup.
        extraction_by_id = {
            extraction.information_unit_id: extraction
            for extraction in extractions
        }

        # Store Phase 4/5 metadata without changing source text.
        for information_unit in information_units:

            # Identify the current unit.
            unit_id = information_unit.information_unit_id

            # Retrieve its extracted information.
            extraction = extraction_by_id[unit_id]

            # Store extraction metadata.
            information_unit.metadata[
                "extraction"
            ] = extraction.to_dict()

            # Store utility metadata.
            information_unit.metadata[
                "utility_score"
            ] = utility_scores[unit_id]

            # Store rarity metadata.
            information_unit.metadata[
                "rarity_score"
            ] = rarity_scores[unit_id]

            # Also populate the explicit model fields so Phase 8 can
            # use them directly without depending only on metadata.
            information_unit.utility_score = (
                utility_scores[unit_id]
            )

            information_unit.rarity_score = (
                rarity_scores[unit_id]
            )

        self._notify_progress("Finding related and duplicate statements.", 55)

        # Phase 3:
        # Include same-document and cross-document similarity candidates.
        result = self.redundancy_engine.analyze(
            information_units,
            cross_document_only=False,
        )

        self._notify_progress("Checking related statements for conflicts.", 68)

        # Phase 6:
        # Detect contradictions among every sufficiently similar comparison.
        self.last_contradictions = (
            self.contradiction_engine.analyze_pairs(
                result.all_similarities,
                extraction_by_id,
            )
        )

        # Create metadata needed by Phase 7.
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

        self._notify_progress("Choosing retained statements.", 74)

        # Phase 7:
        # Generate KEEP / REMOVE / REVIEW recommendations.
        self.last_decisions = (
            self.decision_engine.decide_all(
                pairs=result.similar_pairs,
                metadata_by_id=metadata_by_id,
                contradictions=self.last_contradictions,
            )
        )

        # Save the current information units for Phase 8.
        self.last_information_units = list(
            information_units
        )

        # Phase 8:
        # Convert REMOVE decisions into actual removal candidates.
        self.last_optimization = (
            self.optimizer.optimize(
                information_units=information_units,
                decisions=self.last_decisions,
            )
        )

        self._notify_progress("Applying duplicate-removal decisions.", 80)

        # Phase 9: verify contradiction candidates with local Qwen3:4B.
        self._run_phase9(
            information_units=information_units,
            extractions=extraction_by_id,
            result=result,
        )

        # The returned result remains the same Phase 3-compatible object.
        return result

    def analyze_text(
        self,
        text: str,
    ) -> RedundancyAnalysisResult:
        """
        Run Phases 1-8 on in-memory text.

        This method remains available for existing tests and future
        backend/API usage.
        """

        self.last_original_source_line_count = self._count_nonblank_lines(text)

        self._notify_progress("Reading and separating statements.", 12)

        # Phase 1:
        # Parse and segment the supplied text.
        pipeline_result = self.pipeline_service.process_text(
            text
        )

        self._notify_progress("Creating local semantic embeddings.", 22)

        # Phase 2:
        # Generate embeddings.
        information_units = (
            self.embedding_engine.encode_information_units(
                pipeline_result.information_units
            )
        )

        self._notify_progress("Preparing statement details for review.", 40)

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

        # Store Phase 4/5 information.
        for information_unit in information_units:

            # Retrieve the current unit ID.
            unit_id = information_unit.information_unit_id

            # Retrieve extracted information.
            extraction = extraction_by_id[unit_id]

            # Store structured extraction metadata.
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

            # Populate explicit model fields as well.
            information_unit.utility_score = (
                utility_scores[unit_id]
            )

            information_unit.rarity_score = (
                rarity_scores[unit_id]
            )

        self._notify_progress("Finding related and duplicate statements.", 55)

        # Preserve the existing test-oriented Phase 3 behavior.
        result = self.redundancy_engine.analyze(
            information_units,
            cross_document_only=False,
        )

        self._notify_progress("Checking related statements for conflicts.", 68)

        # Phase 6:
        # Detect contradictions among every sufficiently similar comparison.
        self.last_contradictions = (
            self.contradiction_engine.analyze_pairs(
                result.all_similarities,
                extraction_by_id,
            )
        )

        # Build metadata for Phase 7.
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

        self._notify_progress("Choosing retained statements.", 74)

        # Phase 7:
        # Create KEEP / REMOVE / REVIEW recommendations.
        self.last_decisions = (
            self.decision_engine.decide_all(
                pairs=result.similar_pairs,
                metadata_by_id=metadata_by_id,
                contradictions=self.last_contradictions,
            )
        )

        self._notify_progress("Applying duplicate-removal decisions.", 80)

        # Phase 8:
        # Apply only REMOVE recommendations.
        self.last_optimization = (
            self.optimizer.optimize(
                information_units=information_units,
                decisions=self.last_decisions,
            )
        )

        # Preserve the analyzed units before Phase 9 applies its final
        # contradiction resolution to the Phase 8 retention set.
        self.last_information_units = list(
            information_units
        )

        # Phase 9: verify contradiction candidates with local Qwen3:4B.
        self._run_phase9(
            information_units=information_units,
            extractions=extraction_by_id,
            result=result,
        )

        return result

    def _run_phase9(
        self,
        information_units: list[InformationUnit],
        extractions: dict[str, object],
        result: RedundancyAnalysisResult,
    ) -> None:
        """Run Phase 9 without changing the Phase 1-8 detection engines."""

        self.last_phase9_candidates = []
        self.last_phase9_results = []
        self.last_manual_verifications = []

        candidates = self.verification_engine.prepare_candidates(
            information_units=information_units,
            similarities=result.all_similarities,
            extractions=extractions,  # type: ignore[arg-type]
            phase6_contradictions=self.last_contradictions,
        )
        self.last_phase9_candidates = list(candidates)

        if not candidates:
            self._notify_progress("No conflicts require local AI verification.", 84)
            return

        personal_candidates = [
            (case_number, candidate)
            for case_number, candidate in enumerate(candidates, start=1)
            if self.verification_engine.requires_manual_scope(candidate)
        ]
        automatic_candidates = [
            (case_number, candidate)
            for case_number, candidate in enumerate(candidates, start=1)
            if not self.verification_engine.requires_manual_scope(candidate)
        ]
        verification_candidates = automatic_candidates[:self.MAX_PHASE9_VERIFICATIONS]
        total = len(verification_candidates)
        self._notify_progress(
            f"Verifying {total} possible conflicts with local AI (0/{total}).",
            82,
        )

        # Verify one candidate at a time so the web UI reflects the actual
        # local-AI work. This also keeps the service compatible with the
        # existing verification-engine API and its tests.
        self.last_phase9_results = []
        for completed, (case_number, candidate) in enumerate(verification_candidates, start=1):
            # ``verify([candidate])`` numbers a one-item batch as case 1.
            # Replace that local number with the global review-case number so
            # each manual choice can be addressed unambiguously in the UI.
            verification = self.verification_engine.verify([candidate])[0]
            self.last_phase9_results.append(
                replace(verification, case_number=case_number)
            )
            progress = 82 + int((completed / total) * 6)
            self._notify_progress(
                f"Verifying {total} possible conflicts with local AI ({completed}/{total}).",
                progress,
            )
        # The manual screen is reserved for explicitly personal/private
        # information. A cautious local-model response about geography,
        # science, or another general claim must not be mislabeled as a user
        # decision. Such a result remains retained for safety, but is not
        # added to the personal manual-review queue.
        personal_model_results = [
            verification
            for verification in self.last_phase9_results
            if (
                verification.decision == "MANUAL_REVIEW"
                and self.verification_engine.requires_manual_scope(
                    verification
                )
            )
        ]
        self.last_manual_verifications = self.verification_engine.create_manual_flags(
            personal_model_results
        )
        self.last_manual_verifications.extend(
            ManualVerificationResult(
                case_number=case_number,
                information_unit_id_a=candidate.information_unit_id_a,
                information_unit_id_b=candidate.information_unit_id_b,
                text_a=candidate.text_a,
                text_b=candidate.text_b,
                message=(
                    "Manual verification required: this is personal or "
                    "user-specific information that the local model cannot "
                    "verify from general knowledge."
                ),
            )
            for case_number, candidate in personal_candidates
        )
        # A bounded local-AI queue must not make extra candidates disappear.
        # They remain retained and are represented by ``deferred_count`` in
        # the change log. They are not personal manual-review tasks.
        self._apply_phase9_results(self.last_phase9_results)

    def _apply_phase9_results(
        self,
        results: list[VerificationResult],
    ) -> None:
        """Apply only Qwen's contradiction decisions to Phase 8 retention."""
        if self.last_optimization is None:
            raise RuntimeError("Phase 8 optimization must exist before Phase 9.")

        retained = set(self.last_optimization.retained_unit_ids)
        removed = set(self.last_optimization.removed_unit_ids)
        all_unit_ids = {
            unit.information_unit_id
            for unit in self.last_information_units
        }

        for result in results:
            first = result.information_unit_id_a
            second = result.information_unit_id_b
            if first not in all_unit_ids or second not in all_unit_ids:
                raise ValueError("Phase 9 referenced an unknown information unit.")

            if result.decision == "KEEP_FIRST":
                retained.add(first)
                retained.discard(second)
                removed.add(second)
                removed.discard(first)
            elif result.decision == "KEEP_SECOND":
                retained.add(second)
                retained.discard(first)
                removed.add(first)
                removed.discard(second)
            elif result.decision == "MANUAL_REVIEW":
                # Preserve both sides until the user manually edits the data later.
                retained.add(first)
                retained.add(second)
                removed.discard(first)
                removed.discard(second)

        self.last_optimization.retained_unit_ids = [
            unit.information_unit_id
            for unit in self.last_information_units
            if unit.information_unit_id in retained
        ]
        self.last_optimization.removed_unit_ids = [
            unit.information_unit_id
            for unit in self.last_information_units
            if unit.information_unit_id in removed
            and unit.information_unit_id not in retained
        ]
        # Keep the audit log consistent with Phase 9 reversals. For example,
        # MANUAL_REVIEW reinstates both units and must remove stale Phase 8
        # removal records for either one.
        self.last_optimization.change_records = [
            record
            for record in self.last_optimization.change_records
            if record.information_unit_id
            in self.last_optimization.removed_unit_ids
        ]
        self.last_optimization.final_unit_count = len(
            self.last_optimization.retained_unit_ids
        )

    def get_phase9_results(
        self,
    ) -> list[VerificationResult]:
        """Return the latest Phase 9 Qwen decisions."""
        return list(self.last_phase9_results)

    def get_manual_verifications(
        self,
    ) -> list[ManualVerificationResult]:
        """Return the latest contradictions requiring manual editing."""
        return list(self.last_manual_verifications)

    def get_contradictions(
        self,
    ) -> list[ContradictionResult]:
        """
        Return contradiction results from the latest analysis.
        """

        # Return a copy to avoid accidental mutation.
        return list(
            self.last_contradictions
        )

    def get_decisions(
        self,
    ) -> list[DecisionResult]:
        """
        Return Phase 7 decision results from the latest analysis.
        """

        # Return a copy to protect internal state.
        return list(
            self.last_decisions
        )

    def get_optimization(
        self,
    ) -> OptimizationResult | None:
        """
        Return the latest Phase 8 optimization result.
        """

        # Return the current optimization result.
        return self.last_optimization

    def build_optimized_dataset(
        self,
        output_directory: str | Path = (
            "datasets/optimized"
        ),
    ) -> Path:
        """
        Reconstruct the refined dataset and save it to disk.

        Output:
            optimized_dataset.txt
            changes.json

        The raw dataset is never overwritten.
        """

        # Ensure an analysis has been performed first.
        if self.last_optimization is None:
            raise RuntimeError(
                "Run analyze_file() or analyze_text() before "
                "building an optimized dataset."
            )

        # Ensure information units are available for reconstruction.
        if not self.last_information_units:
            raise RuntimeError(
                "No information units are available for reconstruction."
            )

        # Create the output directory if necessary.
        output_path = Path(
            output_directory
        )

        output_path.mkdir(
            parents=True,
            exist_ok=True,
        )

        # Reconstruct the dataset using only retained units.
        optimized_text = (
            self.reconstruction_engine.reconstruct(
                information_units=self.last_information_units,
                retained_unit_ids=(
                    self.last_optimization.retained_unit_ids
                ),
            )
        )
        self.last_refined_output_line_count = sum(
            1
            for line in optimized_text.splitlines()
            if line.strip()
        )

        # Define the optimized dataset file.
        optimized_dataset_path = (
            output_path
            / "optimized_dataset.txt"
        )

        # Write the refined dataset.
        optimized_dataset_path.write_text(
            optimized_text,
            encoding="utf-8",
        )

        # Define the audit/change-log path.
        changes_path = (
            output_path
            / "changes.json"
        )

        # Serialize the complete optimization result plus Phase 9 status.
        change_log = self.last_optimization.to_dict()
        change_log["final_report"] = self.get_final_report()
        change_log["phase9_verification"] = {
            "candidate_count": len(self.last_phase9_candidates),
            "verified_count": len(self.last_phase9_results),
            "deferred_count": max(
                0,
                len(self.last_phase9_candidates)
                - len(self.last_phase9_results),
            ),
            "results": [
                result.to_dict()
                for result in self.last_phase9_results
            ],
            "manual_verification_required": [
                {
                    **result.to_dict(),
                    # Persisted UI state is separate from the domain-model
                    # status above, which remains MANUAL_VERIFICATION_REQUIRED.
                    "review_status": "PENDING",
                }
                for result in self.last_manual_verifications
            ],
        }
        changes_path.write_text(
            json.dumps(
                change_log,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        # Return the path of the optimized dataset.
        return optimized_dataset_path

    def get_final_report(self) -> dict[str, int | float]:
        """Return the final user-facing counts for the latest analysis."""
        if self.last_optimization is None:
            raise RuntimeError("Run an analysis before requesting the final report.")

        original_lines = getattr(
            self,
            "last_original_source_line_count",
            self.last_optimization.original_unit_count,
        )
        refined_lines = getattr(
            self,
            "last_refined_output_line_count",
            self.last_optimization.final_unit_count,
        )
        automatically_resolved = sum(
            result.decision in {"KEEP_FIRST", "KEEP_SECOND"}
            for result in self.last_phase9_results
        )

        return {
            "original_dataset_lines": original_lines,
            "refined_dataset_lines": refined_lines,
            "original_information_units": self.last_optimization.original_unit_count,
            "refined_information_units": self.last_optimization.final_unit_count,
            "reductions_made": self.last_optimization.removed_count,
            "semantic_duplicates_removed": len(
                self.last_optimization.change_records
            ),
            "reduction_percentage": self.last_optimization.reduction_percentage,
            "contradiction_candidates": len(
                getattr(self, "last_contradictions", [])
            ),
            "contradictions_resolved_automatically": automatically_resolved,
            "contradictions_resolved_manually": 0,
            "manual_intervention_required": len(self.last_manual_verifications),
            "manual_verifications_completed": 0,
        }

    @staticmethod
    def print_result(
        result: RedundancyAnalysisResult,
        contradictions: list[ContradictionResult] | None = None,
        decisions: list[DecisionResult] | None = None,
        optimization: OptimizationResult | None = None,
    ) -> None:
        """
        Print the analysis, decisions, and Phase 8 optimization summary.
        """

        # Print the total number of comparisons performed.
        print(
            f"Total comparisons performed: "
            f"{result.total_comparisons}"
        )

        # Print the number of final similar pairs.
        print(
            f"Final similar pairs detected: "
            f"{result.similar_pair_count}"
        )

        # Print the current similarity threshold.
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

        # Preserve the existing similar-pair output.
        if not result.similar_pairs:
            print(
                "No cross-document similar pairs detected."
            )
        else:
            # Sort by strongest similarity first.
            sorted_pairs = sorted(
                result.similar_pairs,
                key=lambda pair: pair.similarity_score,
                reverse=True,
            )

            # Print every detected pair.
            for index, pair in enumerate(
                sorted_pairs[:RedundancyAnalysisService.MAX_PRINTED_ITEMS],
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

            if len(sorted_pairs) > RedundancyAnalysisService.MAX_PRINTED_ITEMS:
                print(
                    f"\n... {len(sorted_pairs) - RedundancyAnalysisService.MAX_PRINTED_ITEMS} "
                    "additional similar pairs omitted from console output."
                )

        print(
            "\n"
            + "=" * 70
            + "\nCONTRADICTION CANDIDATES\n"
            + "=" * 70
        )

        # Print contradiction candidates.
        if not contradictions:
            print(
                "No contradiction candidates detected."
            )
        else:
            for index, contradiction in enumerate(
                contradictions[:RedundancyAnalysisService.MAX_PRINTED_ITEMS],
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

            if len(contradictions) > RedundancyAnalysisService.MAX_PRINTED_ITEMS:
                print(
                    f"\n... {len(contradictions) - RedundancyAnalysisService.MAX_PRINTED_ITEMS} "
                    "additional contradiction candidates omitted from console output."
                )

        print(
            "\n"
            + "=" * 70
            + "\nDECISIONS\n"
            + "=" * 70
        )

        # Print Phase 7 decision counts.
        if not decisions:
            print(
                "No decision candidates detected."
            )
        else:
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

            print(f"KEEP: {keep_count}")
            print(f"REMOVE: {remove_count}")
            print(f"REVIEW: {review_count}")

            # Print each decision.
            for index, decision in enumerate(
                decisions[:RedundancyAnalysisService.MAX_PRINTED_ITEMS],
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

            if len(decisions) > RedundancyAnalysisService.MAX_PRINTED_ITEMS:
                print(
                    f"\n... {len(decisions) - RedundancyAnalysisService.MAX_PRINTED_ITEMS} "
                    "additional decisions omitted from console output."
                )

        print(
            "\n"
            + "=" * 70
            + "\nOPTIMIZATION\n"
            + "=" * 70
        )

        # Print Phase 8 optimization information.
        if optimization is None:
            print(
                "No optimization result available."
            )
            return

        print(
            f"Original information units: "
            f"{optimization.original_unit_count}"
        )

        print(
            f"Final information units: "
            f"{optimization.final_unit_count}"
        )

        print(
            f"Removed information units: "
            f"{optimization.removed_count}"
        )

        print(
            f"Reduction: "
            f"{optimization.reduction_percentage:.2f}%"
        )


def main() -> None:
    """
    Run the complete Phase 1-9 pipeline.

    A different raw dataset can be supplied for testing without modifying
    the project's existing default dataset.
    """

    import argparse

    parser = argparse.ArgumentParser(
        description="Run the complete Phase 1-9 redundancy-analysis pipeline."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("datasets/raw/dataset.txt"),
        help="Path to the raw dataset to analyze.",
    )
    args = parser.parse_args()
    dataset_path = args.input

    service = RedundancyAnalysisService()
    result = service.analyze_file(dataset_path)
    contradictions = service.get_contradictions()
    decisions = service.get_decisions()
    optimization = service.get_optimization()
    phase9_results = service.get_phase9_results()
    manual_verifications = service.get_manual_verifications()

    service.print_result(
        result,
        contradictions,
        decisions,
        optimization,
    )

    print(
        "\n"
        + "=" * 70
        + "\nPHASE 9 VERIFICATION\n"
        + "=" * 70
    )

    if not phase9_results:
        print("No Phase 9 contradiction candidates were identified.")
    else:
        for index, verification in enumerate(phase9_results, start=1):
            print(f"\n[{index}]")
            print(verification.text_a)
            print("<->")
            print(verification.text_b)
            print(f"Qwen decision: {verification.decision}")
            print(f"Reason: {verification.reason}")

        if manual_verifications:
            print("\nMANUAL VERIFICATION REQUIRED")
            for flag in manual_verifications:
                print(f"\n{flag.message}")
                print(f"Statement 1: {flag.text_a}")
                print(f"Statement 2: {flag.text_b}")

    optimized_dataset_path = service.build_optimized_dataset()
    final_report = service.get_final_report()

    print(
        "\n"
        + "=" * 70
        + "\nFINAL REPORT\n"
        + "=" * 70
    )
    print(f"Original dataset lines: {final_report['original_dataset_lines']}")
    print(f"Refined dataset lines: {final_report['refined_dataset_lines']}")
    print(f"Reductions made: {final_report['reductions_made']}")
    print(
        "Semantic duplicates removed: "
        f"{final_report['semantic_duplicates_removed']}"
    )
    print(f"Reduction: {final_report['reduction_percentage']:.2f}%")
    print(f"Contradiction candidates: {final_report['contradiction_candidates']}")
    print(
        "Contradictions resolved automatically: "
        f"{final_report['contradictions_resolved_automatically']}"
    )
    print(
        "Manual intervention required: "
        f"{final_report['manual_intervention_required']}"
    )

    print("\nOptimized dataset:")
    print(optimized_dataset_path)
    print("Change log:")
    print(optimized_dataset_path.parent / "changes.json")


if __name__ == "__main__":
    # Start the complete project pipeline.
    main()
