"""Smoke tests for the clinician-facing validation pack."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from scribeval.calibration import RatingPair, compute_agreement

ROOT = Path(__file__).resolve().parents[1]
VALIDATION_PACK = ROOT / "validation_pack"


def test_validation_manifest_defines_twenty_blinded_cases() -> None:
    manifest = json.loads((VALIDATION_PACK / "case_manifest.json").read_text())

    assert manifest["benchmark_unit"] == "whole transcript -> final note quality score"
    assert manifest["case_count"] == 20
    assert len(manifest["cases"]) == 20
    assert len(manifest["submission_slots"]) == 5
    assert manifest["review_rules"]["blind_review"] is True
    assert manifest["review_rules"]["max_scored_submissions_per_case"] == 5

    case_ids = [case["case_id"] for case in manifest["cases"]]
    assert len(case_ids) == len(set(case_ids))
    assert {slot["blind_label"] for slot in manifest["submission_slots"]} == {
        "Submission A",
        "Submission B",
        "Submission C",
        "Submission D",
        "Submission E",
    }


def test_reviewer_worksheet_covers_every_case_submission_pair() -> None:
    manifest = json.loads((VALIDATION_PACK / "case_manifest.json").read_text())
    case_ids = {case["case_id"] for case in manifest["cases"]}
    blind_labels = {slot["blind_label"] for slot in manifest["submission_slots"]}

    with (VALIDATION_PACK / "reviewer_worksheet.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == len(case_ids) * len(blind_labels)
    assert {row["case_id"] for row in rows} == case_ids
    assert {row["blinded_submission"] for row in rows} == blind_labels
    assert "reviewer_comments" in rows[0]


def test_example_calibration_pairs_are_computable() -> None:
    raw_pairs = json.loads(
        (VALIDATION_PACK / "results" / "example_calibration_pairs.json").read_text()
    )
    pairs = [
        RatingPair(
            dimension=item["dimension"],
            judge_score=float(item["judge_score"]),
            human_score=float(item["human_score"]),
            judge_severity=item["judge_severity"],
            human_severity=item["human_severity"],
        )
        for item in raw_pairs
    ]

    agreements = compute_agreement(pairs)
    assert {agreement.dimension for agreement in agreements} == {
        "ahpra",
        "hallucination",
        "medicolegal",
        "omission",
        "pdqi9",
        "qnote",
    }
    assert all(agreement.n_pairs == 8 for agreement in agreements)
    assert min(agreement.kappa for agreement in agreements) >= 0.70


def test_frontend_exposes_validation_pilot_summary() -> None:
    demo_data = json.loads((ROOT / "frontend" / "demo-data.json").read_text())
    pilot = demo_data["validation_pilot"]

    assert pilot["case_count"] == 20
    assert pilot["submissions_per_case"] == 5
    assert len(pilot["agreement"]) == 6
    assert pilot["summary"]["median_weighted_kappa"] >= 0.70
