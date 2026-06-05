"""Smoke tests for the clinician-facing validation pack."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

from scribeval.calibration import RatingPair, compute_agreement

ROOT = Path(__file__).resolve().parents[1]
VALIDATION_PACK = ROOT / "validation_pack"
CORPUS = VALIDATION_PACK / "corpus"
EVIDENCE = VALIDATION_PACK / "evidence"


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


def test_bootstrap_corpus_has_traceable_case_packets() -> None:
    manifest = json.loads((CORPUS / "corpus_manifest.json").read_text())

    assert manifest["benchmark_unit"] == "whole transcript -> final note quality score"
    assert manifest["target_case_count"] == 20
    assert manifest["current_case_count"] == 12
    assert len(manifest["case_files"]) == 12

    specialties: set[str] = set()
    prompt_strategies: set[str] = set()
    note_sources: set[str] = set()
    failure_modes: set[str] = set()
    for rel_path in manifest["case_files"]:
        case = json.loads((CORPUS / rel_path).read_text())
        specialties.add(case["specialty"])
        failure_modes.update(case["safety_failure_modes"])
        assert case["transcript"]
        assert 2 <= len(case["candidate_notes"]) <= 5
        assert len({note["submission_id"] for note in case["candidate_notes"]}) == len(
            case["candidate_notes"]
        )
        for note in case["candidate_notes"]:
            note_sources.add(note["note_source"])
            prompt_strategies.add(note["prompt_strategy"])
            failure_modes.update(note["seeded_failure_modes"])
            assert note["note"]

    assert specialties == {
        "aged_care",
        "chronic_disease",
        "general_practice",
        "mental_health",
        "paediatrics",
        "palliative_care",
        "telehealth",
        "urgent_care",
    }
    assert {"nurse_cdss", "model_candidate"} <= note_sources
    assert {"standard", "structured_soap", "safety_first", "cdss_informed"} <= prompt_strategies
    assert "clinically_significant_omission" in failure_modes
    assert "unsupported_hallucination" in failure_modes
    assert "suicide_risk_documentation_gap" in failure_modes
    assert "renal_medication_interaction" in failure_modes
    assert "ectopic_pregnancy_escalation_gap" in failure_modes
    assert "asthma_action_plan_gap" in failure_modes
    assert "results_followup_ownership_gap" in failure_modes


def test_evidence_pairs_reference_corpus_and_are_computable() -> None:
    corpus_manifest = json.loads((CORPUS / "corpus_manifest.json").read_text())
    case_submissions: set[tuple[str, str]] = set()
    for rel_path in corpus_manifest["case_files"]:
        case = json.loads((CORPUS / rel_path).read_text())
        for note in case["candidate_notes"]:
            case_submissions.add((case["case_id"], note["submission_id"]))

    raw_pairs = json.loads((EVIDENCE / "calibration_pairs_v0.json").read_text())
    assert raw_pairs
    assert {
        (pair["case_id"], pair["submission_id"]) for pair in raw_pairs
    } <= case_submissions

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
        "medication_terminology",
        "medicolegal",
        "omission",
        "pdqi9",
        "qnote",
    }
    assert min(agreement.n_pairs for agreement in agreements) >= 3


def test_validation_pack_audit_script_passes() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/validation_pack_audit.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Validation pack audit passed." in result.stdout


def test_reviewer_import_reproduces_evidence_pairs(tmp_path: Path) -> None:
    output = tmp_path / "pairs.json"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/import_validation_ratings.py",
            "--worksheet",
            "validation_pack/evidence/synthetic_reviewer_worksheet_v0.csv",
            "--judge-scores",
            "validation_pack/evidence/synthetic_scribeval_scores_v0.json",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Wrote 70 calibration pairs" in result.stdout
    assert json.loads(output.read_text()) == json.loads(
        (EVIDENCE / "calibration_pairs_v0.json").read_text()
    )


def test_frontend_exposes_validation_pilot_summary() -> None:
    demo_data = json.loads((ROOT / "frontend" / "demo-data.json").read_text())
    pilot = demo_data["validation_pilot"]

    assert pilot["case_count"] == 20
    assert pilot["corpus_case_packets"] == 12
    assert pilot["submissions_per_case"] == 5
    assert pilot["evidence_pairs"] == 70
    assert len(pilot["agreement"]) == 7
    assert pilot["summary"]["median_weighted_kappa"] >= 0.70
