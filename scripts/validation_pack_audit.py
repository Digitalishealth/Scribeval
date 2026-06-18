"""Audit the public validation corpus and evidence trail.

This script is intentionally dependency-free so it can run in CI and by
clinician/governance reviewers without an API key. It verifies that the
validation corpus is internally reproducible: case manifests resolve, blinded
submissions are within Scribeval's supported range, and evidence pairs point to
real case/submission IDs with valid scores and severity labels.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "validation_pack"
CORPUS = PACK / "corpus"
EVIDENCE = PACK / "evidence"
REVIEWER_PACKETS = PACK / "reviewer_packets"
REVIEWER_SCORING_GUIDE = PACK / "reviewer_scoring_guide.md"

VALID_DIMENSIONS = {
    "ahpra",
    "hallucination",
    "medicolegal",
    "medication_terminology",
    "omission",
    "pdqi9",
    "qnote",
}
VALID_SEVERITIES = {"none", "low", "moderate", "high", "critical"}
REQUIRED_CLINICIAN_REVIEW_DIMENSIONS = {
    "ahpra",
    "hallucination",
    "medicolegal",
    "omission",
    "pdqi9",
    "qnote",
}
REQUIRED_STRATA = {"failure_mode", "note_source", "prompt_strategy", "specialty"}
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
FORBIDDEN_REVIEWER_REGISTRY_FIELDS = {
    "email",
    "name",
    "phone",
    "provider_number",
    "registration_number",
}
REQUIRED_REVIEWER_INTAKE_STAGES = {
    "adjudication_and_publication",
    "analysis_readiness",
    "assignment_control",
    "material_preparation",
    "rating_collection",
    "reviewer_onboarding",
}
REQUIRED_REVIEWER_INTAKE_ATTESTATIONS = {
    "all_required_adjudication_resolved_before_validation_claim",
    "all_reviewers_qualified_and_conflict_screened",
    "no_direct_reviewer_identifiers_in_public_materials",
    "no_patient_identifiers_in_public_materials",
    "reviewer_training_completed_before_scoring",
    "reviewers_blinded_to_candidate_source_and_prompt_strategy",
}
REQUIRED_REVIEWER_INTAKE_OUTPUTS = {
    "adjudication_burden.json",
    "consensus_calibration_pairs.json",
    "evidence_manifest.json",
    "review_run_status.json",
    "reviewer_reliability.json",
    "validation_claim_readiness.json",
}
REQUIRED_REVIEWER_TRAINING_STEPS = {
    "complete_anchor_case_discussion",
    "confirm_blinding_and_comment_policy",
    "confirm_conflict_and_eligibility_screening",
    "read_scoring_guide",
    "review_score_and_severity_anchors",
}
REQUIRED_INDEPENDENT_REVIEW_RUNBOOK_STAGES = {
    "assess_goal_status",
    "build_consensus_and_adjudicate",
    "build_public_evidence_bundle",
    "check_review_readiness",
    "collect_blinded_ratings",
    "estimate_reviewer_reliability",
    "export_judge_scores",
    "generate_private_assignments",
    "onboard_reviewers",
    "prepare_public_materials",
    "publish_evidence_index",
}
REQUIRED_IGNORED_PRIVATE_PATHS = {
    "validation_pack/private_review_inputs/",
    "validation_pack/private_review_runs/",
    "validation_pack/reviewer_assignments/",
}
REQUIRED_SAP_PRIMARY_ENDPOINTS = {
    "clinician_reviewer_reliability_weighted_kappa",
    "judge_vs_clinician_consensus_weighted_kappa",
}
REQUIRED_SAP_SECONDARY_ENDPOINTS = {
    "adjudication_burden",
    "judge_vs_clinician_consensus_icc_2_1",
    "mean_absolute_score_difference",
    "severity_exact_agreement",
}
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


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise AssertionError(f"{path} is not valid JSON: {exc}") from exc


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def audit_corpus() -> dict[str, set[str]]:
    manifest_path = CORPUS / "corpus_manifest.json"
    manifest = load_json(manifest_path)
    case_files = manifest.get("case_files")
    require(isinstance(case_files, list) and case_files, "corpus_manifest has no case_files")
    require(
        manifest.get("current_case_count") == len(case_files),
        "current_case_count does not match case_files length",
    )
    min_submissions, max_submissions = manifest.get("required_submission_range", [0, 0])
    require(min_submissions == 2 and max_submissions == 5, "submission range must be 2 to 5")

    case_ids: set[str] = set()
    submission_refs: set[str] = set()
    note_sources: set[str] = set()
    prompt_strategies: set[str] = set()
    failure_modes: set[str] = set()
    specialties: set[str] = set()
    blind_labels_by_case: dict[str, set[str]] = {}

    for rel_path in case_files:
        case_path = CORPUS / rel_path
        require(case_path.exists(), f"missing case file: {rel_path}")
        case = load_json(case_path)
        case_id = case.get("case_id")
        require(isinstance(case_id, str) and case_id, f"{rel_path} has no case_id")
        require(case_id not in case_ids, f"duplicate case_id: {case_id}")
        case_ids.add(case_id)
        require(case.get("specialty"), f"{case_id} has no specialty")
        specialties.add(case["specialty"])

        transcript = case.get("transcript")
        require(isinstance(transcript, list) and transcript, f"{case_id} has no transcript")
        for turn in transcript:
            require(
                turn.get("speaker") and turn.get("text"),
                f"{case_id} has invalid transcript turn",
            )

        submissions = case.get("candidate_notes")
        valid_submission_count = (
            isinstance(submissions, list)
            and min_submissions <= len(submissions) <= max_submissions
        )
        require(
            valid_submission_count,
            f"{case_id} must define {min_submissions} to {max_submissions} candidate_notes",
        )
        seen_submission_ids: set[str] = set()
        seen_blind_labels: set[str] = set()
        for submission in submissions:
            submission_id = submission.get("submission_id")
            blind_label = submission.get("blind_label")
            require(submission_id and blind_label, f"{case_id} has unlabelled submission")
            require(
                submission_id not in seen_submission_ids,
                f"{case_id} repeats submission_id {submission_id}",
            )
            require(
                blind_label not in seen_blind_labels,
                f"{case_id} repeats blind_label {blind_label}",
            )
            require(submission.get("note"), f"{case_id}/{submission_id} has empty note")
            require(submission.get("note_source"), f"{case_id}/{submission_id} has no note_source")
            require(
                submission.get("prompt_strategy"),
                f"{case_id}/{submission_id} has no prompt_strategy",
            )
            seen_submission_ids.add(submission_id)
            seen_blind_labels.add(blind_label)
            submission_refs.add(f"{case_id}:{submission_id}")
            note_sources.add(submission["note_source"])
            prompt_strategies.add(submission["prompt_strategy"])
            failure_modes.update(submission.get("seeded_failure_modes", []))
        failure_modes.update(case.get("safety_failure_modes", []))
        blind_labels_by_case[case_id] = seen_blind_labels

    return {
        "case_ids": case_ids,
        "submission_refs": submission_refs,
        "note_sources": note_sources,
        "prompt_strategies": prompt_strategies,
        "failure_modes": failure_modes,
        "specialties": specialties,
        "blind_labels_by_case": blind_labels_by_case,
    }


def audit_evidence(corpus_refs: dict[str, set[str]]) -> int:
    manifest = load_json(EVIDENCE / "evidence_manifest.json")
    worksheet_path = EVIDENCE / manifest["reviewer_worksheet"]
    judge_scores_path = EVIDENCE / manifest["judge_scores"]
    pairs_path = EVIDENCE / manifest["calibration_pairs"]
    report_path = EVIDENCE / manifest["calibration_report"]
    summary_path = EVIDENCE / manifest["stratified_summary"]
    summary_report_path = EVIDENCE / manifest["stratified_summary_report"]
    require(worksheet_path.exists(), f"missing reviewer worksheet: {worksheet_path}")
    require(judge_scores_path.exists(), f"missing judge scores: {judge_scores_path}")
    require(pairs_path.exists(), f"missing calibration pairs: {pairs_path}")
    require(report_path.exists(), f"missing calibration report: {report_path}")
    require(summary_path.exists(), f"missing stratified summary: {summary_path}")
    require(
        summary_report_path.exists(),
        f"missing stratified summary report: {summary_report_path}",
    )

    pairs = load_json(pairs_path)
    require(isinstance(pairs, list) and pairs, "calibration pairs must be a non-empty list")
    referenced_cases: set[str] = set()
    referenced_submissions: set[str] = set()

    for index, pair in enumerate(pairs, start=1):
        case_id = pair.get("case_id")
        submission_id = pair.get("submission_id")
        blind_label = pair.get("blind_label")
        reviewer_id = pair.get("reviewer_id")
        reference = f"{case_id}:{submission_id}"
        require(blind_label, f"pair {index} has no blind_label")
        require(reviewer_id, f"pair {index} has no reviewer_id")
        require(
            case_id in corpus_refs["case_ids"],
            f"pair {index} references unknown case {case_id}",
        )
        require(
            reference in corpus_refs["submission_refs"],
            f"pair {index} references unknown submission {reference}",
        )
        require(pair.get("dimension") in VALID_DIMENSIONS, f"pair {index} has invalid dimension")
        for score_field in ("judge_score", "human_score"):
            score = pair.get(score_field)
            require(isinstance(score, int | float), f"pair {index} {score_field} is not numeric")
            require(0 <= score <= 1, f"pair {index} {score_field} is outside 0..1")
        for severity_field in ("judge_severity", "human_severity"):
            require(
                pair.get(severity_field) in VALID_SEVERITIES,
                f"pair {index} {severity_field} is invalid",
            )
        referenced_cases.add(case_id)
        referenced_submissions.add(reference)

    require(
        referenced_cases == corpus_refs["case_ids"],
        "evidence pairs do not cover every corpus case",
    )
    audit_stratified_summary(summary_path, corpus_refs, len(pairs), referenced_submissions)
    return len(pairs)


def audit_stratified_summary(
    summary_path: Path,
    corpus_refs: dict[str, set[str]],
    pair_count: int,
    referenced_submissions: set[str],
) -> None:
    summary = load_json(summary_path)
    require(
        summary.get("benchmark_unit") == "whole transcript -> final note quality score",
        "stratified summary has invalid benchmark_unit",
    )
    coverage = summary.get("coverage", {})
    require(coverage.get("case_count") == len(corpus_refs["case_ids"]), "summary case_count drift")
    require(
        coverage.get("submission_count") == len(referenced_submissions),
        "summary submission_count drift",
    )
    require(coverage.get("pair_count") == pair_count, "summary pair_count drift")
    require(set(coverage.get("dimensions", [])) == VALID_DIMENSIONS, "summary dimensions drift")

    strata = summary.get("strata", {})
    expected_values = {
        "specialty": corpus_refs["specialties"],
        "note_source": corpus_refs["note_sources"],
        "prompt_strategy": corpus_refs["prompt_strategies"],
        "failure_mode": corpus_refs["failure_modes"],
    }
    for stratum, values in expected_values.items():
        rows = strata.get(stratum)
        require(isinstance(rows, list) and rows, f"summary missing {stratum} rows")
        observed_values = {row.get("value") for row in rows}
        require(observed_values == values, f"summary {stratum} coverage drift")
        for row in rows:
            require(row.get("pair_count", 0) > 0, f"summary {stratum} row has no pairs")
            dimension_rows = row.get("agreement_by_dimension")
            require(
                isinstance(dimension_rows, list) and dimension_rows,
                f"summary {stratum} row missing dimension agreement",
            )
            require(
                {item.get("dimension") for item in dimension_rows}
                == set(row.get("dimensions", [])),
                f"summary {stratum} row dimension agreement drift",
            )
            require(
                0 <= row.get("mean_abs_difference", -1) <= 1,
                f"summary {stratum} row mean_abs_difference outside 0..1",
            )
            require(
                0 <= row.get("severity_exact_agreement", -1) <= 1,
                f"summary {stratum} row severity agreement outside 0..1",
            )
            for metric in ("minimum_weighted_kappa", "minimum_icc_2_1"):
                value = row.get(metric)
                require(
                    value is None or -1 <= value <= 1,
                    f"summary {stratum} row {metric} outside -1..1",
                )
            for item in dimension_rows:
                require(
                    item.get("n_pairs", 0) > 0,
                    f"summary {stratum} dimension row has no pairs",
                )
                require(
                    0 <= item.get("mean_abs_difference", -1) <= 1,
                    f"summary {stratum} dimension mean_abs_difference outside 0..1",
                )
                for metric in ("weighted_kappa", "icc_2_1"):
                    value = item.get(metric)
                    require(
                        value is None or -1 <= value <= 1,
                        f"summary {stratum} dimension {metric} outside -1..1",
                    )


def audit_corpus_benchmark_manifest(corpus_refs: dict[str, set[str]]) -> None:
    benchmark_manifest = load_json(CORPUS / "benchmark_manifest.json")
    require(
        benchmark_manifest.get("source") == "validation_corpus",
        "validation corpus benchmark manifest has invalid source",
    )
    require(
        benchmark_manifest.get("benchmark_unit")
        == "whole transcript -> final note quality score",
        "validation corpus benchmark manifest has invalid benchmark_unit",
    )
    require(
        benchmark_manifest.get("corpus_manifest") == "corpus_manifest.json",
        "validation corpus benchmark manifest must reference corpus_manifest.json",
    )
    label_map = benchmark_manifest.get("candidate_label_map")
    require(isinstance(label_map, dict), "validation corpus benchmark label map missing")
    require(len(label_map) == 5, "validation corpus benchmark must define five labels")
    require(
        set(label_map)
        == {"Submission A", "Submission B", "Submission C", "Submission D", "Submission E"},
        "validation corpus benchmark label map drift",
    )
    require(
        len(set(label_map.values())) == 5,
        "validation corpus benchmark labels must be unique",
    )

    corpus_manifest = load_json(CORPUS / "corpus_manifest.json")
    for rel_path in corpus_manifest["case_files"]:
        case = load_json(CORPUS / rel_path)
        case_id = case["case_id"]
        require(
            case_id in corpus_refs["case_ids"],
            f"validation benchmark references unknown case {case_id}",
        )
        blind_labels = {submission["blind_label"] for submission in case["candidate_notes"]}
        require(
            blind_labels == set(label_map),
            f"validation benchmark labels do not cover {case_id}",
        )


def audit_reviewer_packets(corpus_refs: dict[str, set[str]]) -> int:
    require((REVIEWER_PACKETS / "README.md").exists(), "missing reviewer packet README")
    require(REVIEWER_SCORING_GUIDE.exists(), "missing reviewer scoring guide")
    guide_text = REVIEWER_SCORING_GUIDE.read_text().lower()
    for required_phrase in (
        "whole transcript -> final note quality score",
        "overall note quality",
        "severity scale",
        "score scale",
    ):
        require(
            required_phrase in guide_text,
            f"reviewer scoring guide missing {required_phrase}",
        )
    manifest_path = REVIEWER_PACKETS / "reviewer_packet_manifest.json"
    manifest = load_json(manifest_path)
    packet_files = manifest.get("packet_files")
    require(isinstance(packet_files, list) and packet_files, "reviewer packet manifest is empty")
    require(
        manifest.get("case_count") == len(corpus_refs["case_ids"]),
        "reviewer packet case_count does not match corpus",
    )
    require(
        manifest.get("case_count") == len(packet_files),
        "reviewer packet case_count does not match packet_files length",
    )

    labels_by_case = corpus_refs["blind_labels_by_case"]
    seen_case_ids: set[str] = set()
    for rel_path in packet_files:
        packet_path = REVIEWER_PACKETS / rel_path
        require(packet_path.exists(), f"missing reviewer packet: {rel_path}")
        case_id = packet_path.stem
        require(case_id in corpus_refs["case_ids"], f"reviewer packet has unknown case: {case_id}")
        seen_case_ids.add(case_id)

        text = packet_path.read_text()
        lower_text = text.lower()
        for token in FORBIDDEN_REVIEWER_PACKET_TOKENS:
            require(token not in lower_text, f"{rel_path} exposes hidden metadata token {token}")
        for blind_label in labels_by_case[case_id]:
            require(
                f"### {blind_label}" in text,
                f"{rel_path} missing blinded submission heading {blind_label}",
            )

    require(
        seen_case_ids == corpus_refs["case_ids"],
        "reviewer packets do not cover every corpus case",
    )
    return len(packet_files)


def audit_clinician_review_protocol() -> None:
    protocol = load_json(PACK / "clinician_review_protocol.json")
    require(
        protocol.get("benchmark_unit") == "whole transcript -> final note quality score",
        "clinician review protocol has invalid benchmark_unit",
    )
    require(
        "build_reviewer_assignments.py" in protocol.get("assignment_builder_command", ""),
        "clinician review protocol missing assignment builder command",
    )
    require(
        "plan_validation_collection.py" in protocol.get("collection_plan_command", ""),
        "clinician review protocol missing collection plan command",
    )
    require(
        "summarize_validation_goal_status.py"
        in protocol.get("validation_goal_status_command", ""),
        "clinician review protocol missing validation goal status command",
    )
    review_materials = protocol.get("review_materials", {})
    require(
        review_materials.get("reviewer_intake_checklist")
        == "reviewer_intake_checklist.json",
        "clinician review protocol missing reviewer intake checklist",
    )
    require(
        review_materials.get("independent_review_runbook")
        == "independent_review_runbook.json",
        "clinician review protocol missing independent review runbook",
    )
    require(
        review_materials.get("reviewer_training_guide")
        == "reviewer_training_guide.json",
        "clinician review protocol missing reviewer training guide",
    )
    require(
        review_materials.get("statistical_analysis_plan")
        == "statistical_analysis_plan.json",
        "clinician review protocol missing statistical analysis plan",
    )
    require(
        "export_validation_judge_scores.py" in protocol.get("judge_score_export_command", ""),
        "clinician review protocol missing judge score export command",
    )
    require(
        "<scribeval_scores.json>" in protocol.get("judge_score_export_command", ""),
        "clinician review protocol judge score export command missing score output placeholder",
    )
    require(
        "summarize_validation_review_run.py"
        in protocol.get("review_run_status_command", ""),
        "clinician review protocol missing review run status command",
    )
    require(
        "summarize_reviewer_reliability.py"
        in protocol.get("reviewer_reliability_command", ""),
        "clinician review protocol missing reviewer reliability command",
    )
    require(
        "build_consensus_validation_ratings.py"
        in protocol.get("consensus_rating_command", ""),
        "clinician review protocol missing consensus rating command",
    )
    require(
        "build_adjudication_packets.py" in protocol.get("adjudication_packet_command", ""),
        "clinician review protocol missing adjudication packet command",
    )
    require(
        "import_adjudication_decisions.py"
        in protocol.get("adjudication_import_command", ""),
        "clinician review protocol missing adjudication import command",
    )
    require(
        "assess_validation_claim_readiness.py"
        in protocol.get("validation_claim_readiness_command", ""),
        "clinician review protocol missing validation claim readiness command",
    )
    require(
        "index_validation_evidence_runs.py"
        in protocol.get("evidence_run_index_command", ""),
        "clinician review protocol missing evidence run index command",
    )
    require(
        "--adjudicated-consensus-pairs"
        in protocol.get("evidence_bundle_command", ""),
        "clinician review protocol bundle command missing adjudicated consensus input",
    )
    require(
        "--reviewer-assignments-dir" in protocol.get("evidence_bundle_command", ""),
        "clinician review protocol bundle command missing reviewer assignments input",
    )
    thresholds = protocol.get("validation_claim_thresholds", {})
    require(
        thresholds.get("minimum_case_count") == 20,
        "clinician review protocol validation claim thresholds missing full corpus case count",
    )
    require(
        thresholds.get("minimum_pairs_per_stratum_value", 0) >= 2,
        "clinician review protocol must require at least two pairs per stratum value",
    )
    requirements = protocol.get("minimum_independent_review_requirements", {})
    require(
        requirements.get("reviewers_per_case") >= 2,
        "clinician review protocol must require at least two reviewers per case",
    )
    require(
        requirements.get("reviewers_per_case_submission") >= 2,
        "clinician review protocol must require at least two reviewers per case-submission",
    )
    require(
        set(requirements.get("required_dimensions", [])) == REQUIRED_CLINICIAN_REVIEW_DIMENSIONS,
        "clinician review protocol required_dimensions drift",
    )
    require(
        requirements.get("required_overall_rating") is True,
        "clinician review protocol must require overall note-quality ratings",
    )
    require(
        requirements.get("eligible_registration_status") == "current",
        "clinician review protocol must require current registration",
    )
    require(
        requirements.get("required_training_completed") is True,
        "clinician review protocol must require training completion",
    )

    registry_path = PACK / "reviewer_registry_template.csv"
    require(registry_path.exists(), "missing reviewer registry template")
    with registry_path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
    missing_fields = REQUIRED_REVIEWER_REGISTRY_FIELDS - fields
    forbidden_fields = FORBIDDEN_REVIEWER_REGISTRY_FIELDS & fields
    require(not missing_fields, f"reviewer registry template missing fields {missing_fields}")
    require(
        not forbidden_fields,
        f"reviewer registry template includes direct identifiers {forbidden_fields}",
    )


def audit_collection_plan(corpus_refs: dict[str, set[str]]) -> None:
    plan_path = PACK / "collection_plan.json"
    report_path = PACK / "collection_plan.md"
    require(plan_path.exists(), "missing validation collection plan JSON")
    require(report_path.exists(), "missing validation collection plan report")
    plan = load_json(plan_path)
    require(
        plan.get("benchmark_unit") == "whole transcript -> final note quality score",
        "validation collection plan has invalid benchmark_unit",
    )
    require(
        plan.get("plan_id") == "scribeval_validation_collection_plan_v1",
        "validation collection plan has invalid plan_id",
    )
    coverage = plan.get("coverage", {})
    require(
        coverage.get("case_count") == len(corpus_refs["case_ids"]),
        "validation collection plan case_count drift",
    )
    require(
        coverage.get("case_submission_count") == len(corpus_refs["submission_refs"]),
        "validation collection plan case_submission_count drift",
    )
    require(
        coverage.get("planned_consensus_pairs", 0) >= len(corpus_refs["submission_refs"]),
        "validation collection plan consensus pair count is too low",
    )
    require(
        not plan.get("underpowered_stratum_values"),
        "validation collection plan has underpowered stratum values",
    )
    strata = plan.get("strata", {})
    expected_values = {
        "specialty": corpus_refs["specialties"],
        "note_source": corpus_refs["note_sources"],
        "prompt_strategy": corpus_refs["prompt_strategies"],
        "failure_mode": corpus_refs["failure_modes"],
    }
    for stratum, values in expected_values.items():
        rows = strata.get(stratum)
        require(isinstance(rows, list) and rows, f"collection plan missing {stratum}")
        observed_values = {row.get("value") for row in rows}
        require(observed_values == values, f"collection plan {stratum} coverage drift")
        for row in rows:
            require(
                row.get("meets_minimum_pair_threshold") is True,
                f"collection plan underpowers {stratum}={row.get('value')}",
            )


def audit_statistical_analysis_plan() -> None:
    plan_path = PACK / "statistical_analysis_plan.json"
    report_path = PACK / "statistical_analysis_plan.md"
    require(plan_path.exists(), "missing statistical analysis plan JSON")
    require(report_path.exists(), "missing statistical analysis plan report")
    sap = load_json(plan_path)
    require(
        sap.get("benchmark_unit") == "whole transcript -> final note quality score",
        "statistical analysis plan has invalid benchmark_unit",
    )
    require(
        sap.get("plan_id") == "scribeval_statistical_analysis_plan_v1",
        "statistical analysis plan has invalid plan_id",
    )
    primary_endpoints = {
        endpoint.get("endpoint_id") for endpoint in sap.get("primary_endpoints", [])
    }
    secondary_endpoints = {
        endpoint.get("endpoint_id") for endpoint in sap.get("secondary_endpoints", [])
    }
    require(
        primary_endpoints >= REQUIRED_SAP_PRIMARY_ENDPOINTS,
        "statistical analysis plan missing primary endpoints",
    )
    require(
        secondary_endpoints >= REQUIRED_SAP_SECONDARY_ENDPOINTS,
        "statistical analysis plan missing secondary endpoints",
    )
    require(
        set(sap.get("required_strata", [])) == REQUIRED_STRATA,
        "statistical analysis plan required_strata drift",
    )
    minimum_coverage = sap.get("minimum_coverage", {})
    require(
        minimum_coverage.get("case_count") == 20,
        "statistical analysis plan must require full corpus case count",
    )
    require(
        minimum_coverage.get("submission_count") == 100,
        "statistical analysis plan must require full corpus submission count",
    )
    require(
        minimum_coverage.get("unresolved_adjudication_required_count") == 0,
        "statistical analysis plan must require resolved adjudication",
    )
    claim_thresholds = sap.get("claim_thresholds", {})
    require(
        claim_thresholds.get("required_evidence_status") == "independent_clinician_review",
        "statistical analysis plan must require independent clinician review status",
    )
    require(
        claim_thresholds.get("minimum_consensus_weighted_kappa", 0) >= 0.6,
        "statistical analysis plan consensus kappa threshold too low",
    )
    require(
        "not validation evidence" in sap.get("publication_boundary", ""),
        "statistical analysis plan must preserve validation evidence boundary",
    )


def audit_reviewer_training_guide() -> None:
    guide_path = PACK / "reviewer_training_guide.json"
    report_path = PACK / "reviewer_training_guide.md"
    require(guide_path.exists(), "missing reviewer training guide JSON")
    require(report_path.exists(), "missing reviewer training guide report")
    guide = load_json(guide_path)
    require(
        guide.get("benchmark_unit") == "whole transcript -> final note quality score",
        "reviewer training guide has invalid benchmark_unit",
    )
    require(
        guide.get("training_id") == "scribeval_clinician_reviewer_training_v1",
        "reviewer training guide has invalid training_id",
    )
    require(
        guide.get("status") == "required_before_independent_scoring",
        "reviewer training guide status drift",
    )
    materials = set(guide.get("required_materials", []))
    require(
        materials >= {"reviewer_scoring_guide.md", "statistical_analysis_plan.json"},
        "reviewer training guide missing required materials",
    )
    step_ids = {step.get("step_id") for step in guide.get("required_training_steps", [])}
    require(
        step_ids == REQUIRED_REVIEWER_TRAINING_STEPS,
        "reviewer training guide required steps drift",
    )
    anchor = guide.get("anchor_case_requirements", {})
    require(
        anchor.get("minimum_anchor_cases", 0) >= 2,
        "reviewer training guide must require at least two anchor cases",
    )
    require(
        "clinically_significant_omission" in set(anchor.get("must_include_failure_examples", [])),
        "reviewer training guide must include omission anchor",
    )
    public_policy = guide.get("public_record_policy", {})
    require(
        public_policy.get("publish_training_completed_flag_only") is True,
        "reviewer training guide must keep training records private",
    )
    require(
        "not itself validation evidence" in guide.get("claim_boundary", ""),
        "reviewer training guide must preserve validation claim boundary",
    )


def audit_independent_review_runbook() -> None:
    runbook_path = PACK / "independent_review_runbook.json"
    report_path = PACK / "independent_review_runbook.md"
    require(runbook_path.exists(), "missing independent review runbook JSON")
    require(report_path.exists(), "missing independent review runbook report")
    runbook = load_json(runbook_path)
    require(
        runbook.get("benchmark_unit") == "whole transcript -> final note quality score",
        "independent review runbook has invalid benchmark_unit",
    )
    require(
        runbook.get("runbook_id") == "scribeval_independent_review_runbook_v1",
        "independent review runbook has invalid runbook_id",
    )
    require(
        runbook.get("status") == "ready_for_external_collection",
        "independent review runbook status drift",
    )
    materials = set(runbook.get("required_public_materials", []))
    require(
        materials
        >= {
            "clinician_review_protocol.json",
            "statistical_analysis_plan.json",
            "reviewer_training_guide.json",
            "reviewer_packets/",
            "corpus/corpus_manifest.json",
        },
        "independent review runbook missing required public materials",
    )
    stage_ids = {stage.get("stage_id") for stage in runbook.get("stages", [])}
    require(
        stage_ids == REQUIRED_INDEPENDENT_REVIEW_RUNBOOK_STAGES,
        "independent review runbook stage drift",
    )
    commands = "\n".join(
        command
        for stage in runbook.get("stages", [])
        for command in stage.get("commands", [])
    )
    for script_name in (
        "audit_clinician_review_readiness.py",
        "summarize_validation_review_run.py",
        "summarize_reviewer_reliability.py",
        "build_validation_evidence_bundle.py",
        "audit_validation_evidence_runs.py",
        "summarize_validation_goal_status.py",
    ):
        require(script_name in commands, f"independent review runbook missing {script_name}")
    private_policy = runbook.get("private_input_policy", {})
    ignored_paths = set(private_policy.get("ignored_workspace_paths", []))
    require(
        ignored_paths >= REQUIRED_IGNORED_PRIVATE_PATHS,
        "independent review runbook missing ignored private workspace paths",
    )
    require(
        private_policy.get("retain_outside_public_repository") is True,
        "independent review runbook must keep private records outside public repo",
    )
    never_commit = set(private_policy.get("never_commit", []))
    require(
        {"raw filled reviewer worksheets", "reviewer-specific assignment worksheets"}
        <= never_commit,
        "independent review runbook must forbid raw reviewer inputs",
    )
    gitignore_text = (ROOT / ".gitignore").read_text()
    for ignored_path in REQUIRED_IGNORED_PRIVATE_PATHS:
        require(
            ignored_path in gitignore_text,
            f".gitignore missing private validation path {ignored_path}",
        )
    report_text = report_path.read_text()
    require(
        "Private Input Policy" in report_text,
        "independent review runbook report missing private input policy",
    )
    require(
        "not validation evidence" in runbook.get("claim_boundary", ""),
        "independent review runbook must preserve validation claim boundary",
    )


def audit_validation_goal_status(corpus_refs: dict[str, set[str]]) -> None:
    status_path = PACK / "validation_goal_status.json"
    report_path = PACK / "validation_goal_status.md"
    require(status_path.exists(), "missing validation goal status JSON")
    require(report_path.exists(), "missing validation goal status report")
    status = load_json(status_path)
    require(
        status.get("benchmark_unit") == "whole transcript -> final note quality score",
        "validation goal status has invalid benchmark_unit",
    )
    require(
        status.get("status_id") == "scribeval_validation_goal_status_v1",
        "validation goal status has invalid status_id",
    )
    coverage = status.get("coverage", {})
    require(
        coverage.get("case_count") == len(corpus_refs["case_ids"]),
        "validation goal status case_count drift",
    )
    require(
        coverage.get("planned_case_submission_count") == len(corpus_refs["submission_refs"]),
        "validation goal status planned submission count drift",
    )
    require(
        status.get("current_status")
        in {
            "independent_clinician_validation_claim_ready",
            "not_ready_for_independent_clinician_review",
            "prepared_for_independent_clinician_review_not_validated",
        },
        "validation goal status has invalid current_status",
    )
    if status.get("current_status") != "independent_clinician_validation_claim_ready":
        require(
            status.get("is_ready_for_validation_claim") is False,
            "validation goal status overclaims validation readiness",
        )
        gap_ids = {gap.get("gap_id") for gap in status.get("blocking_gaps", [])}
        require(
            "no_claim_ready_independent_clinician_evidence_run" in gap_ids,
            "validation goal status must name missing independent evidence run",
        )
    components = status.get("prepared_components", {})
    require(
        components.get("independent_review_runbook_ready", {}).get("passed") is True,
        "validation goal status missing prepared runbook component",
    )
    source_files = status.get("source_files", {})
    require(
        source_files.get("independent_review_runbook")
        == "validation_pack/independent_review_runbook.json",
        "validation goal status missing independent review runbook source",
    )
    require(
        "not independent clinical validation" in status.get("claim_boundary", ""),
        "validation goal status must preserve validation claim boundary",
    )


def audit_reviewer_intake_checklist() -> None:
    checklist = load_json(PACK / "reviewer_intake_checklist.json")
    require(
        checklist.get("benchmark_unit") == "whole transcript -> final note quality score",
        "reviewer intake checklist has invalid benchmark_unit",
    )
    require(
        checklist.get("status") == "ready_for_independent_review",
        "reviewer intake checklist status drift",
    )
    public_fields = set(checklist.get("public_registry_fields", []))
    forbidden_fields = set(checklist.get("forbidden_public_fields", []))
    require(
        public_fields >= REQUIRED_REVIEWER_REGISTRY_FIELDS,
        "reviewer intake checklist missing required public registry fields",
    )
    require(
        forbidden_fields >= FORBIDDEN_REVIEWER_REGISTRY_FIELDS,
        "reviewer intake checklist missing forbidden public identifier fields",
    )
    require(
        not (public_fields & forbidden_fields),
        "reviewer intake checklist publishes forbidden identifier fields",
    )

    stages = checklist.get("stages", [])
    require(isinstance(stages, list) and stages, "reviewer intake checklist has no stages")
    stage_ids = {stage.get("stage_id") for stage in stages}
    require(
        stage_ids == REQUIRED_REVIEWER_INTAKE_STAGES,
        "reviewer intake checklist stage coverage drift",
    )
    for stage in stages:
        checks = stage.get("required_checks")
        require(
            isinstance(checks, list) and checks,
            f"reviewer intake checklist stage {stage.get('stage_id')} has no checks",
        )

    outputs = set(checklist.get("minimum_publishable_outputs", []))
    require(
        outputs >= REQUIRED_REVIEWER_INTAKE_OUTPUTS,
        "reviewer intake checklist missing minimum publishable outputs",
    )
    attestations = {
        item.get("attestation_id")
        for item in checklist.get("completion_attestations", [])
        if item.get("required") is True
    }
    require(
        attestations >= REQUIRED_REVIEWER_INTAKE_ATTESTATIONS,
        "reviewer intake checklist missing required completion attestations",
    )
    require(
        "not itself clinical validation evidence" in checklist.get("claim_boundary", ""),
        "reviewer intake checklist must preserve validation claim boundary",
    )


def main() -> int:
    try:
        corpus_refs = audit_corpus()
        audit_corpus_benchmark_manifest(corpus_refs)
        audit_collection_plan(corpus_refs)
        audit_statistical_analysis_plan()
        audit_reviewer_training_guide()
        audit_independent_review_runbook()
        audit_validation_goal_status(corpus_refs)
        pair_count = audit_evidence(corpus_refs)
        packet_count = audit_reviewer_packets(corpus_refs)
        audit_clinician_review_protocol()
        audit_reviewer_intake_checklist()
    except AssertionError as exc:
        print(f"Validation pack audit failed: {exc}", file=sys.stderr)
        return 1

    print("Validation pack audit passed.")
    print(f"Cases: {len(corpus_refs['case_ids'])}")
    print(f"Submissions: {len(corpus_refs['submission_refs'])}")
    print(f"Reviewer packets: {packet_count}")
    print("Validation collection plan: ready")
    print("Statistical analysis plan: prespecified")
    print("Reviewer training guide: required_before_independent_scoring")
    print("Independent review runbook: ready_for_external_collection")
    print("Validation goal status: tracked")
    print("Clinician review protocol: ready_for_independent_review")
    print("Reviewer intake checklist: ready_for_independent_review")
    print(f"Evidence pairs: {pair_count}")
    print(f"Note sources: {', '.join(sorted(corpus_refs['note_sources']))}")
    print(f"Prompt strategies: {', '.join(sorted(corpus_refs['prompt_strategies']))}")
    print(f"Failure modes: {', '.join(sorted(corpus_refs['failure_modes']))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
