"""Local web interface for comparing raw and refined dataset answers."""

from __future__ import annotations

import json
import re
import threading
from difflib import SequenceMatcher
from pathlib import Path
from typing import Literal
from urllib import error, request

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from core.reconstruction.reconstruction_engine import ReconstructionEngine
from services.pipeline_service import PipelineService


BASE_DIR = Path(__file__).resolve().parent
RAW_DATASET = BASE_DIR / "datasets" / "raw" / "dataset.txt"
REFINED_DATASET = BASE_DIR / "datasets" / "optimized" / "optimized_dataset.txt"
CHANGE_LOG = BASE_DIR / "datasets" / "optimized" / "changes.json"
STATIC_DIR = BASE_DIR / "web" / "static"

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
OLLAMA_MODEL = "qwen3:4b"
MAX_CONTEXT_CHARACTERS = 12_000
MAX_MATCHING_LINES = 40
MAX_DATASET_CHARACTERS = 5_000_000

LOCATION_QUESTION_WORDS = frozenset({
    "where", "location", "located", "place", "places", "based", "flow", "flows",
})
LOCATION_PATTERN = re.compile(
    r"^(?:the\s+)?(?P<subject>.+?)\s+"
    r"(?:is|are|was|were)\s+.+?\b(?:in|at|on)\s+(?P<place>[A-Z][^.!?]*)[.!?]?$",
    re.IGNORECASE,
)

app = FastAPI(title="INFORA Dataset Refinement Lab")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
_refinement_lock = threading.Lock()
_manual_review_lock = threading.Lock()
_refinement_status: dict[str, str | int | None] = {
    "state": "idle",
    "message": "Ready for a raw dataset.",
    "progress": 0,
    "error": None,
}


def _update_refinement_status(message: str, progress: int) -> None:
    """Receive actual processing milestones from the refinement service."""
    _refinement_status.update(
        state="running",
        message=message,
        progress=max(0, min(99, int(progress))),
        error=None,
    )


def _normalize_submitted_dataset_text(dataset_text: str) -> str:
    """Normalize browser line endings without changing statement content."""
    return dataset_text.replace("\r\n", "\n").replace("\r", "\n").strip()


class QuestionRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1_000)


class RefinementRequest(BaseModel):
    dataset_text: str = Field(min_length=3, max_length=MAX_DATASET_CHARACTERS)


class ManualReviewDecisionRequest(BaseModel):
    """One explicit user choice for a pending contradiction pair."""

    decision: Literal["KEEP_FIRST", "KEEP_SECOND"]


class DatasetAnswer(BaseModel):
    dataset: Literal["raw", "refined"]
    answer: str
    context_line_count: int


class ComparisonResponse(BaseModel):
    question: str
    raw: DatasetAnswer
    refined: DatasetAnswer


def _read_dataset(path: Path, label: str) -> str:
    if not path.exists():
        raise HTTPException(
            status_code=409,
            detail=(
                f"The {label} dataset is unavailable. Run the refinement "
                "pipeline first so optimized_dataset.txt is created."
            ),
        )
    return path.read_text(encoding="utf-8")


def _keywords(text: str) -> set[str]:
    ignored = {
        "a", "an", "and", "are", "as", "at", "be", "by", "for",
        "from", "how", "in", "is", "it", "of", "on", "or", "the",
        "to", "was", "what", "when", "where", "which", "who", "why",
        "with",
    }
    return {
        word.lower()
        for word in re.findall(r"[A-Za-z0-9]+", text)
        if len(word) > 1 and word.lower() not in ignored
    }


def _token_matches(word: str, candidates: set[str]) -> bool:
    """Match a query term exactly or tolerate a small spelling mistake."""
    if word in candidates:
        return True
    if len(word) < 3:
        return False
    return any(
        len(candidate) >= 3
        and SequenceMatcher(a=word, b=candidate).ratio() >= 0.80
        for candidate in candidates
    )


def _location_answer(question: str, context_lines: list[str]) -> str | None:
    """Answer location-style questions directly from matching dataset facts.

    This avoids treating "where is the Nile?", "Nile River location", and
    small spelling slips such as "nil river" as unrelated questions. It also
    prevents the language model from adding a route or other geography that
    the supplied dataset never stated.
    """
    raw_question_words = {
        word.lower()
        for word in re.findall(r"[A-Za-z0-9]+", question)
    }
    question_words = _keywords(question)
    if not raw_question_words & LOCATION_QUESTION_WORDS:
        return None

    matches: list[tuple[str, str]] = []
    for line in context_lines:
        match = LOCATION_PATTERN.match(line.strip())
        if match is None:
            continue
        subject = re.sub(r"^the\s+", "", match.group("subject").strip(), flags=re.IGNORECASE)
        subject_words = _keywords(subject)
        if not subject_words:
            continue
        # A location query needs one meaningful subject-word match. Exact
        # matching is preferred; fuzzy matching covers minor human typos.
        if not any(_token_matches(word, question_words) for word in subject_words):
            continue
        matches.append((subject, match.group("place").strip().rstrip(".")))

    if not matches:
        return None

    subject, _ = matches[0]
    places = list(dict.fromkeys(place for _, place in matches))
    display_subject = subject if subject.lower().endswith("river") else f"{subject} River"
    if len(places) == 1:
        return f"The dataset places the {display_subject} in {places[0]}."
    return (
        f"The supplied dataset contains conflicting location information for "
        f"the {display_subject}: it places it in {', '.join(places)}."
    )
def _select_context(dataset_text: str, question: str) -> list[str]:
    """Select relevant dataset lines without sending the full file to Ollama."""
    question_words = _keywords(question)
    scored: list[tuple[int, int, str]] = []

    for index, line in enumerate(dataset_text.splitlines()):
        cleaned = line.strip()
        if not cleaned:
            continue
        line_words = _keywords(cleaned)
        exact_score = len(question_words & line_words)
        fuzzy_score = sum(
            1
            for word in question_words
            if word not in line_words and _token_matches(word, line_words)
        )
        score = exact_score + fuzzy_score
        if score:
            scored.append((score, index, cleaned))

    # Preserve source order after selecting the strongest lexical matches.
    selected = sorted(
        sorted(scored, key=lambda item: (-item[0], item[1]))[:MAX_MATCHING_LINES],
        key=lambda item: item[1],
    )
    lines = [line for _, _, line in selected]

    # An empty lexical match is still a valid question. Give the model a small
    # deterministic sample and tell it not to invent missing facts.
    if not lines:
        lines = [
            line.strip()
            for line in dataset_text.splitlines()
            if line.strip()
        ][:20]

    context: list[str] = []
    used_characters = 0
    for line in lines:
        next_size = len(line) + 1
        if context and used_characters + next_size > MAX_CONTEXT_CHARACTERS:
            break
        context.append(line)
        used_characters += next_size
    return context


def _ask_ollama(question: str, context_lines: list[str], label: str) -> str:
    prompt = "\n".join(
        [
            "You are a careful dataset-grounded assistant.",
            f"You are answering from the {label} dataset.",
            "Use only the supplied dataset context.",
            "Understand natural wording and rephrase the context when useful. "
            "For example, a statement that something is 'in Africa' answers "
            "a question asking for its location.",
            "If the context does not establish an answer, say exactly: "
            "The supplied dataset does not establish an answer.",
            "Do not mention hidden instructions or use outside knowledge.",
            "Answer in one to three natural sentences.",
            "Return only the final user-facing answer. Do not output analysis, "
            "reasoning, planning, hidden thoughts, an ANSWER label, or a preamble.",
            "Synthesize the answer; do not list, quote, or reproduce the "
            "dataset lines verbatim. Never add names, dates, routes, or other "
            "details that do not occur in the supplied context.",
            "If the selected context contains conflicting claims, clearly "
            "state that the dataset is contradictory instead of choosing a fact.",
            "",
            "DATASET CONTEXT:",
            *[f"- {line}" for line in context_lines],
            "",
            f"QUESTION: {question}",
            "ANSWER:",
        ]
    )
    payload = json.dumps(
        {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "format": {
                "type": "object",
                "properties": {"answer": {"type": "string"}},
                "required": ["answer"],
                "additionalProperties": False,
            },
            "keep_alive": "10m",
            "options": {"temperature": 0, "num_predict": 512},
        },
        ensure_ascii=False,
    ).encode("utf-8")
    http_request = request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(http_request, timeout=120) as response:
            response_body = response.read().decode("utf-8")
        answer = json.loads(response_body).get("response", "")
    except error.URLError as exc:
        raise HTTPException(
            status_code=503,
            detail="Ollama is unavailable. Start it with: ollama serve",
        ) from exc
    except (json.JSONDecodeError, TimeoutError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Ollama returned an invalid or timed-out answer.",
        ) from exc

    if not isinstance(answer, str) or not answer.strip():
        raise HTTPException(status_code=502, detail="Ollama returned no usable answer.")
    return _final_answer_only(answer)


def _final_answer_only(answer: str) -> str:
    """Remove Qwen thinking text even when an Ollama version ignores think=False."""
    cleaned = answer.replace("<\\/think>", "</think>").replace("\\</think>", "</think>")
    cleaned = re.sub(r"<think\b[^>]*>.*?</think\s*>", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    # Some Qwen/Ollama combinations emit the content but omit the opening tag.
    if re.search(r"</think\s*>", cleaned, flags=re.IGNORECASE):
        cleaned = re.split(r"</think\s*>", cleaned, maxsplit=1, flags=re.IGNORECASE)[1]
    # The response is requested as {"answer": "..."}. Extract it even if a
    # model prepends non-visible reasoning before the JSON object.
    decoder = json.JSONDecoder()
    for index, character in enumerate(cleaned):
        if character != "{":
            continue
        try:
            structured, _ = decoder.raw_decode(cleaned[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(structured, dict) and isinstance(structured.get("answer"), str):
            cleaned = structured["answer"]
            break
    cleaned = re.sub(r"^\s*(?:answer|final answer)\s*:\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip()
    if not cleaned:
        raise HTTPException(status_code=502, detail="Ollama returned thoughts but no final answer.")
    return cleaned


def _line_count(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip())


def _load_change_log() -> dict[str, object]:
    """Load the persisted refinement state required for manual review."""
    if not CHANGE_LOG.exists() or not REFINED_DATASET.exists():
        raise HTTPException(
            status_code=409,
            detail="Refine a dataset before starting manual verification.",
        )
    try:
        payload = json.loads(CHANGE_LOG.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=500,
            detail="The saved refinement report is not valid JSON.",
        ) from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=500, detail="The saved refinement report is invalid.")
    return payload


def _manual_entries(change_log: dict[str, object]) -> list[dict[str, object]]:
    phase9 = change_log.get("phase9_verification", {})
    if not isinstance(phase9, dict):
        return []
    entries = phase9.get("manual_verification_required", [])
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def _pending_manual_entries(change_log: dict[str, object]) -> list[dict[str, object]]:
    retained = set(change_log.get("retained_unit_ids", []))
    return [
        entry
        for entry in _manual_entries(change_log)
        if entry.get("review_status", "PENDING") == "PENDING"
        and entry.get("information_unit_id_a") in retained
        and entry.get("information_unit_id_b") in retained
    ]


def _refresh_manual_report(change_log: dict[str, object], refined_text: str) -> None:
    """Keep displayed totals synchronized with a completed user choice."""
    report = change_log.setdefault("final_report", {})
    if not isinstance(report, dict):
        report = {}
        change_log["final_report"] = report
    retained = change_log.get("retained_unit_ids", [])
    removed = change_log.get("removed_unit_ids", [])
    original_units = int(change_log.get("original_unit_count", 0))
    pending = _pending_manual_entries(change_log)
    completed = sum(
        entry.get("review_status") == "RESOLVED"
        for entry in _manual_entries(change_log)
    )
    report["refined_dataset_lines"] = _line_count(refined_text)
    report["refined_information_units"] = len(retained) if isinstance(retained, list) else 0
    report["reductions_made"] = len(removed) if isinstance(removed, list) else 0
    report["reduction_percentage"] = (
        (len(removed) / original_units * 100.0) if original_units else 0.0
    )
    report["manual_intervention_required"] = len(pending)
    report["manual_verifications_completed"] = completed
    report["contradictions_resolved_manually"] = completed
    change_log["final_unit_count"] = report["refined_information_units"]
    change_log["removed_count"] = report["reductions_made"]
    change_log["reduction_percentage"] = report["reduction_percentage"]


def _refresh_manual_progress(change_log: dict[str, object]) -> None:
    """Update projected totals without rebuilding the dataset file yet."""
    report = change_log.setdefault("final_report", {})
    if not isinstance(report, dict):
        report = {}
        change_log["final_report"] = report
    retained = change_log.get("retained_unit_ids", [])
    removed = change_log.get("removed_unit_ids", [])
    original_units = int(change_log.get("original_unit_count", 0))
    completed = sum(
        entry.get("review_status") == "RESOLVED"
        for entry in _manual_entries(change_log)
    )
    retained_count = len(retained) if isinstance(retained, list) else 0
    removed_count = len(removed) if isinstance(removed, list) else 0
    report["refined_dataset_lines"] = retained_count
    report["refined_information_units"] = retained_count
    report["reductions_made"] = removed_count
    report["reduction_percentage"] = (
        (removed_count / original_units * 100.0) if original_units else 0.0
    )
    report["manual_intervention_required"] = len(_pending_manual_entries(change_log))
    report["manual_verifications_completed"] = completed
    report["contradictions_resolved_manually"] = completed
    change_log["final_unit_count"] = retained_count
    change_log["removed_count"] = removed_count
    change_log["reduction_percentage"] = report["reduction_percentage"]


def _reconstruct_after_manual_choice(change_log: dict[str, object]) -> str:
    """Rebuild the file by stable information-unit IDs, never text matching."""
    units = PipelineService().process_file(RAW_DATASET).information_units
    retained_ids = change_log.get("retained_unit_ids", [])
    if not isinstance(retained_ids, list):
        raise HTTPException(status_code=500, detail="The saved retained-statement list is invalid.")
    available_ids = {unit.information_unit_id for unit in units}
    if not set(retained_ids).issubset(available_ids):
        raise HTTPException(
            status_code=409,
            detail="This report belongs to different raw data. Run refinement again before manual verification.",
        )
    return ReconstructionEngine().reconstruct(units, retained_ids)


def _run_refinement(dataset_text: str) -> None:
    """Save submitted text and run the existing pipeline off the request thread."""
    try:
        _refinement_status.update(
            state="running",
            message="Preparing your dataset for refinement.",
            progress=10,
            error=None,
        )
        RAW_DATASET.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = RAW_DATASET.with_suffix(".tmp")
        # Browser text areas on Windows commonly submit CRLF.  Normalizing
        # before writing prevents Python's text-mode newline translation from
        # producing CRCRLF and apparent blank lines between every statement.
        normalized_dataset_text = _normalize_submitted_dataset_text(dataset_text)
        temporary_path.write_text(
            normalized_dataset_text + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(RAW_DATASET)

        # Import only in the worker: opening the web UI does not load the
        # embedding model until the user explicitly starts refinement.
        from services.redundancy_analysis_service import RedundancyAnalysisService

        service = RedundancyAnalysisService(
            progress_callback=_update_refinement_status,
        )
        service.analyze_file(RAW_DATASET)
        _refinement_status.update(
            message="Writing the refined dataset and final report.",
            progress=92,
        )
        service.build_optimized_dataset()
        _refinement_status.update(
            state="complete",
            message="Your refined dataset and results are ready.",
            progress=100,
            error=None,
        )
    except Exception as exc:  # Report errors to the UI rather than losing a worker traceback.
        _refinement_status.update(
            state="failed",
            message="Refinement failed.",
            progress=0,
            error=str(exc),
        )
    finally:
        _refinement_lock.release()


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/status")
def status() -> dict[str, object]:
    # A first-time refinement has no refined file until the job completes.
    raw_text = RAW_DATASET.read_text(encoding="utf-8") if RAW_DATASET.exists() else ""
    refined_text = REFINED_DATASET.read_text(encoding="utf-8") if REFINED_DATASET.exists() else ""
    report: dict[str, object] = {}
    if CHANGE_LOG.exists():
        change_log = json.loads(CHANGE_LOG.read_text(encoding="utf-8"))
        report = change_log.get("final_report", {})
        if isinstance(change_log, dict) and not change_log.get(
            "manual_verification_finalized", True
        ):
            # The file is rebuilt after the last choice, but the dashboard
            # must show the current projected result after every choice.
            change_log_copy = dict(change_log)
            _refresh_manual_progress(change_log_copy)
            report = change_log_copy.get("final_report", report)
    refinement = dict(_refinement_status)
    # The server starts in ``idle`` after a restart, but an already saved
    # refined file is still ready to view, download, compare, and review.
    if (
        refinement.get("state") == "idle"
        and REFINED_DATASET.exists()
        and CHANGE_LOG.exists()
    ):
        refinement.update(
            state="complete",
            message="Your saved refined dataset and results are ready.",
            progress=100,
            error=None,
        )
    return {
        "model": OLLAMA_MODEL,
        "raw_line_count": _line_count(raw_text),
        "refined_line_count": _line_count(refined_text),
        "final_report": report,
        "refinement": refinement,
    }


@app.get("/api/manual-verification")
def get_manual_verification() -> dict[str, object]:
    """Return only contradiction pairs that still need a user decision."""
    change_log = _load_change_log()
    entries = _pending_manual_entries(change_log)
    resolved_count = sum(
        entry.get("review_status") == "RESOLVED"
        for entry in _manual_entries(change_log)
    )
    return {
        "pending_count": len(entries),
        "resolved_count": resolved_count,
        "pairs": entries,
    }


@app.post("/api/manual-verification/{case_number}")
def apply_manual_verification(
    case_number: int,
    payload: ManualReviewDecisionRequest,
) -> dict[str, object]:
    """Apply one user decision to the file and saved refinement report."""
    if _refinement_lock.locked():
        raise HTTPException(
            status_code=409,
            detail="Wait for the active refinement to finish before reviewing statements.",
        )
    if not _manual_review_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Another manual decision is being saved.")

    try:
        change_log = _load_change_log()
        entry = next(
            (
                item
                for item in _pending_manual_entries(change_log)
                if item.get("case_number") == case_number
            ),
            None,
        )
        if entry is None:
            raise HTTPException(status_code=404, detail="This pending review pair was not found.")

        first_id = entry.get("information_unit_id_a")
        second_id = entry.get("information_unit_id_b")
        if not isinstance(first_id, str) or not isinstance(second_id, str):
            raise HTTPException(status_code=500, detail="The selected review pair is invalid.")
        kept_id, removed_id = (
            (first_id, second_id)
            if payload.decision == "KEEP_FIRST"
            else (second_id, first_id)
        )

        retained_ids = change_log.get("retained_unit_ids", [])
        removed_ids = change_log.get("removed_unit_ids", [])
        if not isinstance(retained_ids, list) or not isinstance(removed_ids, list):
            raise HTTPException(status_code=500, detail="The saved optimization state is invalid.")
        if kept_id not in retained_ids or removed_id not in retained_ids:
            raise HTTPException(status_code=409, detail="This pair is no longer available for review.")

        change_log["retained_unit_ids"] = [
            unit_id for unit_id in retained_ids if unit_id != removed_id
        ]
        change_log["removed_unit_ids"] = list(dict.fromkeys([*removed_ids, removed_id]))
        entry["review_status"] = "RESOLVED"
        entry["manual_decision"] = payload.decision
        entry["kept_information_unit_id"] = kept_id
        entry["removed_information_unit_id"] = removed_id

        # A choice may make another pending pair impossible because one side
        # was removed. Mark it superseded instead of showing a broken review.
        for other in _manual_entries(change_log):
            if (
                other is not entry
                and other.get("review_status", "PENDING") == "PENDING"
                and removed_id in {
                    other.get("information_unit_id_a"),
                    other.get("information_unit_id_b"),
                }
            ):
                other["review_status"] = "SUPERSEDED"

        source_units = PipelineService().process_file(RAW_DATASET).information_units
        source_by_id = {unit.information_unit_id: unit for unit in source_units}
        removed_unit = source_by_id.get(removed_id)
        if removed_unit is None:
            raise HTTPException(
                status_code=409,
                detail="This report belongs to different raw data. Run refinement again before manual verification.",
            )
        records = change_log.setdefault("change_records", [])
        if isinstance(records, list):
            records.append(
                {
                    "information_unit_id": removed_id,
                    "document_id": removed_unit.document_id,
                    "original_text": removed_unit.text,
                    "reason": "Removed after the user's manual contradiction decision.",
                    "decision": payload.decision,
                    "confidence": 1.0,
                    "paired_information_unit_id": kept_id,
                }
            )

        pending_count = len(_pending_manual_entries(change_log))
        finalized = pending_count == 0
        if finalized:
            # Rebuild once, after the complete review batch is finished. This
            # avoids rewriting a very large dataset after every click.
            refined_text = _reconstruct_after_manual_choice(change_log)
            REFINED_DATASET.write_text(refined_text, encoding="utf-8")
            _refresh_manual_report(change_log, refined_text)
        else:
            # The automatic-Qwen refined file remains downloadable while
            # choices are collected. Its final manual edits are applied only
            # when the last pending pair has a selection.
            _refresh_manual_progress(change_log)
            refined_text = _read_dataset(REFINED_DATASET, "refined")
        change_log["manual_verification_finalized"] = finalized
        CHANGE_LOG.write_text(
            json.dumps(change_log, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return {
            "message": (
                "All manual selections were applied and the final refined "
                "dataset is ready."
                if finalized
                else "Your selection was saved. The final dataset will be "
                "rebuilt after all pending pairs are reviewed."
            ),
            "pending_count": pending_count,
            "finalized": finalized,
            "refined_line_count": int(
                (change_log.get("final_report", {}) or {}).get(
                    "refined_dataset_lines",
                    _line_count(refined_text),
                )
            ),
        }
    finally:
        _manual_review_lock.release()


@app.get("/api/datasets/refined", response_class=PlainTextResponse)
def view_refined_dataset() -> PlainTextResponse:
    """Open the current refined dataset in a browser-safe plain-text view."""
    return PlainTextResponse(
        _read_dataset(REFINED_DATASET, "refined"),
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": "inline; filename=optimized_dataset.txt",
            "Cache-Control": "no-store",
        },
    )


@app.get("/api/datasets/refined/download", response_class=PlainTextResponse)
def download_refined_dataset() -> PlainTextResponse:
    """Download the current refined dataset as a text file."""
    return PlainTextResponse(
        _read_dataset(REFINED_DATASET, "refined"),
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=refined_dataset.txt",
            "Cache-Control": "no-store",
        },
    )


@app.get("/api/datasets/raw", response_class=PlainTextResponse)
def view_raw_dataset() -> PlainTextResponse:
    """Return the exact raw dataset saved for the completed refinement."""
    return PlainTextResponse(
        _read_dataset(RAW_DATASET, "raw"),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": "inline; filename=raw_dataset.txt"},
    )


@app.post("/api/refine", status_code=202)
def start_refinement(payload: RefinementRequest) -> dict[str, str]:
    """Start refinement for pasted user data without blocking the web UI."""
    if not payload.dataset_text.strip():
        raise HTTPException(status_code=422, detail="Paste a non-empty dataset first.")
    if not _refinement_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail="A dataset refinement job is already running.",
        )

    _refinement_status.update(
        state="queued",
        message="Dataset accepted. Starting refinement…",
        progress=0,
        error=None,
    )
    threading.Thread(
        target=_run_refinement,
        args=(payload.dataset_text,),
        daemon=True,
        name="infora-refinement",
    ).start()
    return {"message": "Refinement started."}


@app.post("/api/compare", response_model=ComparisonResponse)
def compare_answers(payload: QuestionRequest) -> ComparisonResponse:
    raw_text = _read_dataset(RAW_DATASET, "raw")
    refined_text = _read_dataset(REFINED_DATASET, "refined")
    raw_context = _select_context(raw_text, payload.question)
    refined_context = _select_context(refined_text, payload.question)
    raw_answer = _location_answer(payload.question, raw_context)
    refined_answer = _location_answer(payload.question, refined_context)

    return ComparisonResponse(
        question=payload.question,
        raw=DatasetAnswer(
            dataset="raw",
            answer=raw_answer or _ask_ollama(payload.question, raw_context, "raw"),
            context_line_count=len(raw_context),
        ),
        refined=DatasetAnswer(
            dataset="refined",
            answer=refined_answer or _ask_ollama(
                payload.question, refined_context, "refined"
            ),
            context_line_count=len(refined_context),
        ),
    )
