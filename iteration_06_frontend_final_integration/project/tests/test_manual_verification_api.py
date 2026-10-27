"""Tests for persisted, user-driven contradiction decisions."""

import json

import app as web_app
from services.pipeline_service import PipelineService


def test_submitted_windows_newlines_do_not_create_blank_dataset_lines() -> None:
    text = "First statement.\r\nSecond statement.\r\n"

    assert web_app._normalize_submitted_dataset_text(text) == (
        "First statement.\nSecond statement."
    )


def test_manual_choice_rebuilds_refined_dataset_and_report(tmp_path, monkeypatch) -> None:
    raw_path = tmp_path / "dataset.txt"
    refined_path = tmp_path / "optimized_dataset.txt"
    log_path = tmp_path / "changes.json"
    raw_text = "The capital of Japan is Tokyo.\nThe capital of Japan is Osaka.\n"
    raw_path.write_text(raw_text, encoding="utf-8")
    units = PipelineService().process_file(raw_path).information_units
    first_id, second_id = [unit.information_unit_id for unit in units]
    refined_path.write_text(raw_text, encoding="utf-8")
    log_path.write_text(
        json.dumps(
            {
                "retained_unit_ids": [first_id, second_id],
                "removed_unit_ids": [],
                "change_records": [],
                "original_unit_count": 2,
                "final_unit_count": 2,
                "final_report": {
                    "original_dataset_lines": 2,
                    "semantic_duplicates_removed": 0,
                    "contradictions_resolved_automatically": 0,
                },
                "phase9_verification": {
                    "manual_verification_required": [
                        {
                            "case_number": 1,
                            "information_unit_id_a": first_id,
                            "information_unit_id_b": second_id,
                            "text_a": units[0].text,
                            "text_b": units[1].text,
                            "review_status": "PENDING",
                        }
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(web_app, "RAW_DATASET", raw_path)
    monkeypatch.setattr(web_app, "REFINED_DATASET", refined_path)
    monkeypatch.setattr(web_app, "CHANGE_LOG", log_path)

    response = web_app.apply_manual_verification(
        1,
        web_app.ManualReviewDecisionRequest(decision="KEEP_FIRST"),
    )
    saved_log = json.loads(log_path.read_text(encoding="utf-8"))

    assert response["pending_count"] == 0
    assert refined_path.read_text(encoding="utf-8").strip() == units[0].text
    assert saved_log["retained_unit_ids"] == [first_id]
    assert second_id in saved_log["removed_unit_ids"]
    assert saved_log["final_report"]["manual_intervention_required"] == 0
    assert saved_log["final_report"]["manual_verifications_completed"] == 1


def test_manual_choices_are_batched_until_the_last_pending_pair(tmp_path, monkeypatch) -> None:
    raw_path = tmp_path / "dataset.txt"
    refined_path = tmp_path / "optimized_dataset.txt"
    log_path = tmp_path / "changes.json"
    raw_text = (
        "My dog is named Bruno.\nMy dog is named Brownie.\n"
        "My cat is named Luna.\nMy cat is named Miso.\n"
    )
    raw_path.write_text(raw_text, encoding="utf-8")
    units = PipelineService().process_file(raw_path).information_units
    refined_path.write_text(raw_text, encoding="utf-8")
    pairs = [(units[0], units[1]), (units[2], units[3])]
    log_path.write_text(
        json.dumps(
            {
                "retained_unit_ids": [unit.information_unit_id for unit in units],
                "removed_unit_ids": [],
                "change_records": [],
                "original_unit_count": 4,
                "final_report": {"original_dataset_lines": 4},
                "phase9_verification": {
                    "manual_verification_required": [
                        {
                            "case_number": number,
                            "information_unit_id_a": first.information_unit_id,
                            "information_unit_id_b": second.information_unit_id,
                            "text_a": first.text,
                            "text_b": second.text,
                            "review_status": "PENDING",
                        }
                        for number, (first, second) in enumerate(pairs, start=1)
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(web_app, "RAW_DATASET", raw_path)
    monkeypatch.setattr(web_app, "REFINED_DATASET", refined_path)
    monkeypatch.setattr(web_app, "CHANGE_LOG", log_path)

    first_response = web_app.apply_manual_verification(
        1, web_app.ManualReviewDecisionRequest(decision="KEEP_FIRST")
    )

    assert first_response["finalized"] is False
    assert first_response["refined_line_count"] == 3
    assert refined_path.read_text(encoding="utf-8") == raw_text
    after_first = json.loads(log_path.read_text(encoding="utf-8"))
    assert after_first["manual_verification_finalized"] is False
    assert after_first["final_report"]["refined_dataset_lines"] == 3
    assert after_first["final_report"]["reductions_made"] == 1

    second_response = web_app.apply_manual_verification(
        2, web_app.ManualReviewDecisionRequest(decision="KEEP_SECOND")
    )

    assert second_response["finalized"] is True
    assert refined_path.read_text(encoding="utf-8").strip() == (
        f"{units[0].text}\n{units[3].text}"
    )
