"""Smoke tests for the clinician-facing validation pack."""

from __future__ import annotations

import csv
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from scribeval.calibration import RatingPair, compute_agreement
from tests.conftest import MockJudge

ROOT = Path(__file__).resolve().parents[1]
VALIDATION_PACK = ROOT / "validation_pack"
CORPUS = VALIDATION_PACK / "corpus"
EVIDENCE = VALIDATION_PACK / "evidence"
REVIEWER_PACKETS = VALIDATION_PACK / "reviewer_packets"

FORBIDDEN_REVIEWER_PACKET_TOKENS = {
    "cdss_checklist",
    "cdss_informed",
    "model_candidate",
    "note_source",
    "nurse_cdss",
    "prompt_strategy",
    "safety_first",
    "seeded_failure_modes",
    "structured_soap",
    "submission_id",
}
REQUIRED_REVIEWER_REGISTRY_FIELDS = {
    "conflict_of_interest",
    "country",
    "profession",
    "registration_status",
    "review_role",
    "reviewer_id",
    "specialty",
    "training_completed",
    "years_post_registration",
}
REQUIRED_CLINICIAN_REVIEW_DIMENSIONS = (
    "omission",
    "hallucination",
    "medicolegal",
    "ahpra",
    "pdqi9",
    "qnote",
)


def load_script_module(name: str):
    spec = importlib.util.spec_from_file_location(
        name,
        ROOT / "scripts" / f"{name}.py",
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def reviewer_worksheet_fields() -> list[str]:
    with (VALIDATION_PACK / "reviewer_worksheet.csv").open(newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or [])


def write_qualified_reviewer_registry(path: Path) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "reviewer_id",
                "profession",
                "country",
                "registration_status",
                "years_post_registration",
                "specialty",
                "review_role",
                "conflict_of_interest",
                "training_completed",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "reviewer_id": "reviewer_clinician_001",
                "profession": "general_practitioner",
                "country": "AU",
                "registration_status": "current",
                "years_post_registration": "8",
                "specialty": "general_practice",
                "review_role": "primary_reviewer",
                "conflict_of_interest": "none",
                "training_completed": "yes",
            }
        )
        writer.writerow(
            {
                "reviewer_id": "reviewer_clinician_002",
                "profession": "general_practitioner",
                "country": "AU",
                "registration_status": "current",
                "years_post_registration": "12",
                "specialty": "general_practice",
                "review_role": "secondary_reviewer",
                "conflict_of_interest": "none",
                "training_completed": "yes",
            }
        )


def write_complete_review_worksheet_and_judge_scores(
    worksheet: Path,
    judge_scores: Path,
) -> None:
    corpus_manifest = json.loads((CORPUS / "corpus_manifest.json").read_text())
    judge_score_rows: list[dict[str, object]] = []
    with worksheet.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=reviewer_worksheet_fields())
        writer.writeheader()
        for rel_path in corpus_manifest["case_files"]:
            case = json.loads((CORPUS / rel_path).read_text())
            for note in case["candidate_notes"]:
                for dimension in REQUIRED_CLINICIAN_REVIEW_DIMENSIONS:
                    judge_score_rows.append(
                        {
                            "case_id": case["case_id"],
                            "submission_id": note["submission_id"],
                            "dimension": dimension,
                            "judge_score": 0.9,
                            "judge_severity": "low",
                        }
                    )
                for reviewer_id in ("reviewer_clinician_001", "reviewer_clinician_002"):
                    row = {
                        "case_id": case["case_id"],
                        "blinded_submission": note["blind_label"],
                        "reviewer_id": reviewer_id,
                        "reviewer_comments": "Complete readiness fixture.",
                    }
                    for dimension in REQUIRED_CLINICIAN_REVIEW_DIMENSIONS:
                        row[f"{dimension}_score"] = "0.90"
                        row[f"{dimension}_severity"] = "low"
                    writer.writerow(row)
    judge_scores.write_text(json.dumps(judge_score_rows, indent=2) + "\n")


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


def test_clinician_review_protocol_defines_reviewer_provenance() -> None:
    protocol = json.loads((VALIDATION_PACK / "clinician_review_protocol.json").read_text())

    assert protocol["benchmark_unit"] == "whole transcript -> final note quality score"
    assert "export_validation_judge_scores.py" in protocol["judge_score_export_command"]
    assert "<scribeval_scores.json>" in protocol["judge_score_export_command"]
    assert "summarize_reviewer_reliability.py" in protocol["reviewer_reliability_command"]
    requirements = protocol["minimum_independent_review_requirements"]
    assert requirements["reviewers_per_case"] == 2
    assert requirements["reviewers_per_case_submission"] == 2
    assert requirements["eligible_registration_status"] == "current"
    assert requirements["required_training_completed"] is True
    assert requirements["minimum_years_post_registration"] >= 1
    assert tuple(requirements["required_dimensions"]) == REQUIRED_CLINICIAN_REVIEW_DIMENSIONS

    with (VALIDATION_PACK / "reviewer_registry_template.csv").open(newline="") as handle:
        fieldnames = set(csv.DictReader(handle).fieldnames or [])
    assert fieldnames >= REQUIRED_REVIEWER_REGISTRY_FIELDS
    assert {"name", "email", "phone", "provider_number", "registration_number"}.isdisjoint(
        fieldnames
    )


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
    assert manifest["current_case_count"] == 20
    assert len(manifest["case_files"]) == 20

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
    assert "diabetes_safety_net_gap" in failure_modes
    assert "withdrawal_risk_gap" in failure_modes
    assert "contraception_contraindication_gap" in failure_modes
    assert "delirium_escalation_gap" in failure_modes


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


def test_stratified_evidence_summary_covers_corpus_metadata() -> None:
    corpus_manifest = json.loads((CORPUS / "corpus_manifest.json").read_text())
    summary = json.loads((EVIDENCE / "stratified_summary_v0.json").read_text())

    specialties: set[str] = set()
    note_sources: set[str] = set()
    prompt_strategies: set[str] = set()
    failure_modes: set[str] = set()
    for rel_path in corpus_manifest["case_files"]:
        case = json.loads((CORPUS / rel_path).read_text())
        specialties.add(case["specialty"])
        failure_modes.update(case["safety_failure_modes"])
        for note in case["candidate_notes"]:
            note_sources.add(note["note_source"])
            prompt_strategies.add(note["prompt_strategy"])
            failure_modes.update(note["seeded_failure_modes"])

    assert summary["benchmark_unit"] == "whole transcript -> final note quality score"
    assert summary["coverage"]["case_count"] == 20
    assert summary["coverage"]["submission_count"] == 100
    assert summary["coverage"]["pair_count"] == 118
    assert set(summary["coverage"]["dimensions"]) == {
        "ahpra",
        "hallucination",
        "medication_terminology",
        "medicolegal",
        "omission",
        "pdqi9",
        "qnote",
    }
    assert {row["value"] for row in summary["strata"]["specialty"]} == specialties
    assert {row["value"] for row in summary["strata"]["note_source"]} == note_sources
    assert {row["value"] for row in summary["strata"]["prompt_strategy"]} == prompt_strategies
    assert {row["value"] for row in summary["strata"]["failure_mode"]} == failure_modes
    assert all(row["pair_count"] > 0 for rows in summary["strata"].values() for row in rows)


def test_reviewer_packets_cover_corpus_without_metadata_leakage() -> None:
    corpus_manifest = json.loads((CORPUS / "corpus_manifest.json").read_text())
    packet_manifest = json.loads(
        (REVIEWER_PACKETS / "reviewer_packet_manifest.json").read_text()
    )

    assert packet_manifest["case_count"] == 20
    assert len(packet_manifest["packet_files"]) == len(corpus_manifest["case_files"])

    packet_files = {Path(path).stem: path for path in packet_manifest["packet_files"]}
    for rel_path in corpus_manifest["case_files"]:
        case = json.loads((CORPUS / rel_path).read_text())
        packet_path = REVIEWER_PACKETS / packet_files[case["case_id"]]
        packet_text = packet_path.read_text()
        lower_packet_text = packet_text.lower()

        assert case["title"] in packet_text
        assert "## Transcript" in packet_text
        assert "## Blinded Candidate Notes" in packet_text
        for token in FORBIDDEN_REVIEWER_PACKET_TOKENS:
            assert token not in lower_packet_text
        for submission in case["candidate_notes"]:
            assert f"### {submission['blind_label']}" in packet_text
            assert submission["note"] in packet_text


def test_validation_pack_audit_script_passes() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/validation_pack_audit.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Validation pack audit passed." in result.stdout
    assert "Reviewer packets: 20" in result.stdout


def test_reviewer_packet_builder_reproduces_committed_packets(tmp_path: Path) -> None:
    output_dir = tmp_path / "reviewer_packets"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_reviewer_packets.py",
            "--output-dir",
            str(output_dir),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Wrote 20 reviewer packets" in result.stdout
    expected_files = sorted(
        path.relative_to(REVIEWER_PACKETS) for path in REVIEWER_PACKETS.rglob("*")
    )
    generated_files = sorted(path.relative_to(output_dir) for path in output_dir.rglob("*"))
    assert generated_files == expected_files
    for rel_path in expected_files:
        expected_path = REVIEWER_PACKETS / rel_path
        generated_path = output_dir / rel_path
        if expected_path.is_file():
            assert generated_path.read_text() == expected_path.read_text()


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

    assert "Wrote 118 calibration pairs" in result.stdout
    assert json.loads(output.read_text()) == json.loads(
        (EVIDENCE / "calibration_pairs_v0.json").read_text()
    )


def test_reviewer_import_accepts_qualified_reviewer_registry(tmp_path: Path) -> None:
    worksheet = tmp_path / "qualified_worksheet.csv"
    worksheet_fields = reviewer_worksheet_fields()
    with worksheet.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=worksheet_fields)
        writer.writeheader()
        writer.writerow(
            {
                "case_id": "val_gp_respiratory_001",
                "blinded_submission": "Submission A",
                "reviewer_id": "reviewer_clinician_001",
                "omission_score": "0.92",
                "omission_severity": "low",
                "reviewer_comments": "Strict registry import test.",
            }
    )
    registry = tmp_path / "reviewer_registry.csv"
    write_qualified_reviewer_registry(registry)
    output = tmp_path / "pairs.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/import_validation_ratings.py",
            "--worksheet",
            str(worksheet),
            "--judge-scores",
            "validation_pack/evidence/synthetic_scribeval_scores_v0.json",
            "--reviewer-registry",
            str(registry),
            "--require-qualified-reviewers",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    pairs = json.loads(output.read_text())
    assert "Wrote 1 calibration pairs" in result.stdout
    assert pairs[0]["reviewer_id"] == "reviewer_clinician_001"
    assert pairs[0]["case_id"] == "val_gp_respiratory_001"
    assert pairs[0]["blind_label"] == "Submission A"
    assert pairs[0]["dimension"] == "omission"


def test_clinician_review_readiness_audit_accepts_complete_qualified_inputs(
    tmp_path: Path,
) -> None:
    worksheet = tmp_path / "complete_worksheet.csv"
    registry = tmp_path / "reviewer_registry.csv"
    output_json = tmp_path / "readiness.json"
    output_md = tmp_path / "readiness.md"
    judge_scores = tmp_path / "judge_scores.json"
    write_qualified_reviewer_registry(registry)
    write_complete_review_worksheet_and_judge_scores(worksheet, judge_scores)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/audit_clinician_review_readiness.py",
            "--worksheet",
            str(worksheet),
            "--reviewer-registry",
            str(registry),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--fail-on-not-ready",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(output_json.read_text())
    assert "Clinician review readiness: ready" in result.stdout
    assert report["is_ready_for_independent_validation"] is True
    assert report["coverage"]["expected_case_submission_count"] == 100
    assert report["coverage"]["complete_case_submission_count"] == 100
    assert report["coverage"]["qualified_reviewer_count"] == 2
    assert all(not rows for rows in report["issues"].values())
    assert "Status: ready" in output_md.read_text()


def test_clinician_review_readiness_audit_reports_incomplete_template(
    tmp_path: Path,
) -> None:
    registry = tmp_path / "reviewer_registry.csv"
    output_json = tmp_path / "readiness.json"
    write_qualified_reviewer_registry(registry)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/audit_clinician_review_readiness.py",
            "--worksheet",
            "validation_pack/reviewer_worksheet.csv",
            "--reviewer-registry",
            str(registry),
            "--output-json",
            str(output_json),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(output_json.read_text())
    assert "Clinician review readiness: not ready" in result.stdout
    assert report["is_ready_for_independent_validation"] is False
    assert report["coverage"]["complete_case_submission_count"] == 0
    assert len(report["issues"]["under_reviewed_submissions"]) == 100


def test_reviewer_assignment_builder_balances_required_reviewers(
    tmp_path: Path,
) -> None:
    registry = tmp_path / "reviewer_registry.csv"
    output_dir = tmp_path / "reviewer_assignments"
    write_qualified_reviewer_registry(registry)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_reviewer_assignments.py",
            "--reviewer-registry",
            str(registry),
            "--output-dir",
            str(output_dir),
            "--seed",
            "7",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    manifest = json.loads((output_dir / "assignment_manifest.json").read_text())
    assert "Wrote reviewer assignments" in result.stdout
    assert manifest["case_submission_count"] == 100
    assert manifest["assignment_count"] == 200
    assert manifest["reviewer_count"] == 2
    assert all(
        len(reviewers) == 2
        for reviewers in manifest["case_submission_reviewers"].values()
    )
    assert {item["assignment_count"] for item in manifest["worksheet_files"]} == {100}
    assert len(manifest["worksheet_files"]) == 2

    assigned_pairs: set[tuple[str, str, str]] = set()
    for item in manifest["worksheet_files"]:
        worksheet_path = output_dir / item["path"]
        with worksheet_path.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert len(rows) == 100
        assert {row["reviewer_id"] for row in rows} == {item["reviewer_id"]}
        assert all(not row["omission_score"] for row in rows)
        for row in rows:
            assigned_pairs.add(
                (row["case_id"], row["blinded_submission"], row["reviewer_id"])
            )
    assert len(assigned_pairs) == 200


def test_validation_evidence_bundle_builder_creates_reproducible_run(
    tmp_path: Path,
) -> None:
    worksheet = tmp_path / "complete_worksheet.csv"
    registry = tmp_path / "reviewer_registry.csv"
    judge_scores = tmp_path / "judge_scores.json"
    output_dir = tmp_path / "evidence_runs"
    write_qualified_reviewer_registry(registry)
    write_complete_review_worksheet_and_judge_scores(worksheet, judge_scores)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_validation_evidence_bundle.py",
            "--run-id",
            "qualified_fixture_v1",
            "--worksheet",
            str(worksheet),
            "--reviewer-registry",
            str(registry),
            "--judge-scores",
            str(judge_scores),
            "--output-dir",
            str(output_dir),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    bundle_dir = output_dir / "qualified_fixture_v1"
    manifest = json.loads((bundle_dir / "evidence_manifest.json").read_text())
    readiness = json.loads((bundle_dir / "readiness_report.json").read_text())
    pairs = json.loads((bundle_dir / "calibration_pairs.json").read_text())
    stratified = json.loads((bundle_dir / "stratified_summary.json").read_text())
    reviewer_reliability = json.loads((bundle_dir / "reviewer_reliability.json").read_text())

    assert "Wrote validation evidence bundle" in result.stdout
    assert manifest["status"] == "independent_clinician_review"
    assert manifest["coverage"]["case_submission_count"] == 100
    assert manifest["coverage"]["complete_case_submission_count"] == 100
    assert manifest["coverage"]["qualified_reviewer_count"] == 2
    assert manifest["coverage"]["calibration_pair_count"] == 1200
    assert manifest["coverage"]["reviewer_reliability_pair_count"] == 600
    assert manifest["reviewer_reliability"] == "reviewer_reliability.json"
    assert manifest["reviewer_reliability_report"] == "reviewer_reliability.md"
    assert set(manifest["source_hashes"]) == {
        "corpus_manifest_sha256",
        "judge_scores_sha256",
        "protocol_sha256",
        "reviewer_registry_sha256",
        "reviewer_worksheet_sha256",
    }
    assert readiness["is_ready_for_independent_validation"] is True
    assert len(pairs) == 1200
    assert stratified["coverage"]["pair_count"] == 1200
    assert stratified["evidence_status"] == "independent_clinician_review"
    assert reviewer_reliability["coverage"]["reliability_pair_count"] == 600
    assert reviewer_reliability["readiness"]["is_ready_for_independent_validation"] is True
    assert "Weighted kappa" in (bundle_dir / "calibration_report.md").read_text()
    assert "Status: ready" in (bundle_dir / "readiness_report.md").read_text()
    assert "Reviewer Reliability" in (bundle_dir / "reviewer_reliability.md").read_text()


def test_validation_judge_score_exporter_writes_importable_scores(
    tmp_path: Path,
) -> None:
    exporter = load_script_module("export_validation_judge_scores")
    output = tmp_path / "judge_scores.json"
    manifest_output = tmp_path / "judge_scores_manifest.json"

    scores, manifest = exporter.export_judge_scores(
        corpus_manifest=CORPUS / "corpus_manifest.json",
        output=output,
        manifest_output=manifest_output,
        dimensions=["omission"],
        judge=MockJudge(),
        rubric_dir=ROOT / "rubrics",
        runs=1,
        max_cases=1,
        max_submissions=1,
    )

    assert len(scores) == 1
    assert output.exists()
    assert manifest_output.exists()
    assert manifest["benchmark_unit"] == "whole transcript -> final note quality score"
    assert manifest["case_count"] == 1
    assert manifest["submission_count"] == 1
    assert manifest["score_count"] == 1
    assert manifest["dimensions"] == ["omission"]
    assert set(manifest["source_hashes"]) == {
        "case_files_sha256",
        "corpus_manifest_sha256",
    }

    row = json.loads(output.read_text())[0]
    assert row["case_id"] == "val_gp_respiratory_001"
    assert row["submission_id"] == "submission_a"
    assert row["blind_label"] == "Submission A"
    assert row["dimension"] == "omission"
    assert row["judge_score"] == 0.75
    assert row["judge_severity"] == "moderate"
    assert row["judge_type"] == "mock"
    assert "transcript" not in row
    assert "note" not in row
    assert "raw_judge_response" not in row

    load_judge_scores = load_script_module("import_validation_ratings").load_judge_scores
    imported = load_judge_scores(output)
    assert ("val_gp_respiratory_001", "submission_a", "omission") in imported


def test_reviewer_reliability_summary_accepts_complete_qualified_inputs(
    tmp_path: Path,
) -> None:
    worksheet = tmp_path / "complete_worksheet.csv"
    registry = tmp_path / "reviewer_registry.csv"
    judge_scores = tmp_path / "judge_scores.json"
    output_json = tmp_path / "reviewer_reliability.json"
    output_md = tmp_path / "reviewer_reliability.md"
    write_qualified_reviewer_registry(registry)
    write_complete_review_worksheet_and_judge_scores(worksheet, judge_scores)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/summarize_reviewer_reliability.py",
            "--worksheet",
            str(worksheet),
            "--reviewer-registry",
            str(registry),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--fail-on-not-ready",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    summary = json.loads(output_json.read_text())
    assert "Reviewer reliability pairs: 600" in result.stdout
    assert summary["benchmark_unit"] == "whole transcript -> final note quality score"
    assert summary["readiness"]["is_ready_for_independent_validation"] is True
    assert summary["coverage"]["case_count"] == 20
    assert summary["coverage"]["submission_count"] == 100
    assert summary["coverage"]["reviewer_pair_count"] == 1
    assert summary["coverage"]["reliability_pair_count"] == 600
    assert {row["dimension"] for row in summary["dimension_agreement"]} == set(
        REQUIRED_CLINICIAN_REVIEW_DIMENSIONS
    )
    assert all(row["weighted_kappa"] == 1.0 for row in summary["dimension_agreement"])
    assert "Clinician Reviewer Reliability Report" in output_md.read_text()


def test_evidence_run_audit_accepts_empty_directory(tmp_path: Path) -> None:
    evidence_runs = tmp_path / "evidence_runs"
    evidence_runs.mkdir()

    result = subprocess.run(
        [
            sys.executable,
            "scripts/audit_validation_evidence_runs.py",
            "--evidence-runs",
            str(evidence_runs),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Evidence run audit passed." in result.stdout
    assert "Bundles: 0" in result.stdout
    assert "Calibration pairs: 0" in result.stdout


def test_evidence_run_audit_accepts_generated_bundle(tmp_path: Path) -> None:
    worksheet = tmp_path / "complete_worksheet.csv"
    registry = tmp_path / "reviewer_registry.csv"
    judge_scores = tmp_path / "judge_scores.json"
    output_dir = tmp_path / "evidence_runs"
    write_qualified_reviewer_registry(registry)
    write_complete_review_worksheet_and_judge_scores(worksheet, judge_scores)

    subprocess.run(
        [
            sys.executable,
            "scripts/build_validation_evidence_bundle.py",
            "--run-id",
            "qualified_fixture_v1",
            "--worksheet",
            str(worksheet),
            "--reviewer-registry",
            str(registry),
            "--judge-scores",
            str(judge_scores),
            "--output-dir",
            str(output_dir),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/audit_validation_evidence_runs.py",
            "--evidence-runs",
            str(output_dir),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Evidence run audit passed." in result.stdout
    assert "Bundles: 1" in result.stdout
    assert "Calibration pairs: 1200" in result.stdout


def test_evidence_run_audit_rejects_raw_clinician_csv(tmp_path: Path) -> None:
    worksheet = tmp_path / "complete_worksheet.csv"
    registry = tmp_path / "reviewer_registry.csv"
    judge_scores = tmp_path / "judge_scores.json"
    output_dir = tmp_path / "evidence_runs"
    write_qualified_reviewer_registry(registry)
    write_complete_review_worksheet_and_judge_scores(worksheet, judge_scores)

    subprocess.run(
        [
            sys.executable,
            "scripts/build_validation_evidence_bundle.py",
            "--run-id",
            "qualified_fixture_v1",
            "--worksheet",
            str(worksheet),
            "--reviewer-registry",
            str(registry),
            "--judge-scores",
            str(judge_scores),
            "--output-dir",
            str(output_dir),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    (output_dir / "qualified_fixture_v1" / "reviewer_worksheet.csv").write_text(
        "reviewer_id,case_id\nreviewer_clinician_001,val_gp_respiratory_001\n"
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/audit_validation_evidence_runs.py",
            "--evidence-runs",
            str(output_dir),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "raw clinician CSV input" in result.stderr


def test_stratified_evidence_summary_reproduces_committed_artifacts(tmp_path: Path) -> None:
    output_json = tmp_path / "stratified_summary_v0.json"
    output_md = tmp_path / "stratified_summary_v0.md"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/summarize_validation_evidence.py",
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Wrote stratified evidence summary" in result.stdout
    assert json.loads(output_json.read_text()) == json.loads(
        (EVIDENCE / "stratified_summary_v0.json").read_text()
    )
    assert output_md.read_text() == (EVIDENCE / "stratified_summary_v0.md").read_text()


def test_frontend_exposes_validation_pilot_summary() -> None:
    demo_data = json.loads((ROOT / "frontend" / "demo-data.json").read_text())
    pilot = demo_data["validation_pilot"]

    assert pilot["case_count"] == 20
    assert pilot["corpus_case_packets"] == 20
    assert pilot["submissions_per_case"] == 5
    assert pilot["evidence_pairs"] == 118
    assert len(pilot["agreement"]) == 7
    assert pilot["summary"]["median_weighted_kappa"] >= 0.70
