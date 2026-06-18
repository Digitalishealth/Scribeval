"""Summarize current progress toward independent clinician validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS_MANIFEST = ROOT / "validation_pack" / "corpus" / "corpus_manifest.json"
DEFAULT_COLLECTION_PLAN = ROOT / "validation_pack" / "collection_plan.json"
DEFAULT_PROTOCOL = ROOT / "validation_pack" / "clinician_review_protocol.json"
DEFAULT_REVIEWER_INTAKE = ROOT / "validation_pack" / "reviewer_intake_checklist.json"
DEFAULT_REVIEWER_TRAINING = ROOT / "validation_pack" / "reviewer_training_guide.json"
DEFAULT_SAP = ROOT / "validation_pack" / "statistical_analysis_plan.json"
DEFAULT_EVIDENCE_INDEX = ROOT / "validation_pack" / "evidence_runs" / "index.json"
DEFAULT_OUTPUT_JSON = ROOT / "validation_pack" / "validation_goal_status.json"
DEFAULT_OUTPUT_MD = ROOT / "validation_pack" / "validation_goal_status.md"
BENCHMARK_UNIT = "whole transcript -> final note quality score"


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} is not valid JSON: {exc}") from exc


def display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def component_status(*, passed: bool, evidence: Any, note: str) -> dict[str, Any]:
    return {
        "passed": passed,
        "evidence": evidence,
        "note": note,
    }


def summarize_goal_status(
    *,
    corpus_manifest: Path,
    collection_plan: Path,
    protocol: Path,
    reviewer_intake: Path,
    reviewer_training: Path,
    statistical_analysis_plan: Path,
    evidence_index: Path,
) -> dict[str, Any]:
    corpus = load_json(corpus_manifest)
    collection = load_json(collection_plan)
    review_protocol = load_json(protocol)
    intake = load_json(reviewer_intake)
    training = load_json(reviewer_training)
    sap = load_json(statistical_analysis_plan)
    index = load_json(evidence_index)

    claim_ready_runs = [
        run for run in index.get("runs", []) if run.get("is_ready_for_validation_claim")
    ]
    independent_claim_ready_runs = [
        run
        for run in claim_ready_runs
        if run.get("status") == review_protocol["validation_claim_thresholds"][
            "required_evidence_status"
        ]
    ]
    failed_checks = [
        {
            "evidence_id": run.get("evidence_id"),
            "check_id": check.get("id"),
            "observed": check.get("observed"),
            "threshold": check.get("threshold"),
        }
        for run in index.get("runs", [])
        for check in run.get("failed_checks", [])
    ]
    prepared_components = {
        "corpus_complete": component_status(
            passed=corpus.get("current_case_count") == corpus.get("target_case_count") == 20,
            evidence={
                "current_case_count": corpus.get("current_case_count"),
                "target_case_count": corpus.get("target_case_count"),
            },
            note="Synthetic validation corpus reaches the planned case count.",
        ),
        "collection_plan_complete": component_status(
            passed=collection.get("is_collection_plan_complete") is True,
            evidence={
                "planned_consensus_pairs": collection.get("coverage", {}).get(
                    "planned_consensus_pairs"
                ),
                "underpowered_stratum_values": len(
                    collection.get("underpowered_stratum_values", [])
                ),
            },
            note="Reviewer collection plan has no underpowered required strata.",
        ),
        "statistical_analysis_plan_prespecified": component_status(
            passed=sap.get("status") == "prespecified_for_independent_clinician_review",
            evidence={"plan_id": sap.get("plan_id"), "status": sap.get("status")},
            note="Analysis plan is fixed before independent clinician evidence is collected.",
        ),
        "reviewer_intake_ready": component_status(
            passed=intake.get("status") == "ready_for_independent_review",
            evidence={"checklist_id": intake.get("checklist_id"), "status": intake.get("status")},
            note="Reviewer intake and public/private evidence boundaries are defined.",
        ),
        "reviewer_training_defined": component_status(
            passed=training.get("status") == "required_before_independent_scoring",
            evidence={
                "training_id": training.get("training_id"),
                "status": training.get("status"),
            },
            note="Reviewer training and anchor-case requirements are defined.",
        ),
        "evidence_index_present": component_status(
            passed=index.get("index_id") == "validation_evidence_runs_index_v1",
            evidence={
                "run_count": index.get("run_count"),
                "claim_ready_run_count": index.get("claim_ready_run_count"),
            },
            note="Evidence-run index is publishable and reproducible.",
        ),
    }
    prepared = all(component["passed"] for component in prepared_components.values())
    independently_validated = bool(independent_claim_ready_runs)
    status = (
        "independent_clinician_validation_claim_ready"
        if independently_validated
        else (
            "prepared_for_independent_clinician_review_not_validated"
            if prepared
            else "not_ready_for_independent_clinician_review"
        )
    )
    blocking_gaps = []
    if not independently_validated:
        blocking_gaps.append(
            {
                "gap_id": "no_claim_ready_independent_clinician_evidence_run",
                "message": (
                    "No evidence run currently has independent clinician review status "
                    "and passes validation-claim readiness."
                ),
            }
        )
    if failed_checks:
        blocking_gaps.append(
            {
                "gap_id": "current_evidence_run_failed_checks",
                "message": "At least one evidence run has failed validation readiness checks.",
                "failed_checks": failed_checks,
            }
        )

    return {
        "schema_version": "1.0.0",
        "status_id": "scribeval_validation_goal_status_v1",
        "benchmark_unit": BENCHMARK_UNIT,
        "current_status": status,
        "is_ready_for_validation_claim": independently_validated,
        "prepared_components": prepared_components,
        "coverage": {
            "case_count": corpus.get("current_case_count"),
            "planned_case_submission_count": collection.get("coverage", {}).get(
                "case_submission_count"
            ),
            "planned_individual_calibration_pairs": collection.get("coverage", {}).get(
                "planned_individual_calibration_pairs"
            ),
            "planned_consensus_pairs": collection.get("coverage", {}).get(
                "planned_consensus_pairs"
            ),
            "evidence_run_count": index.get("run_count"),
            "claim_ready_run_count": index.get("claim_ready_run_count"),
        },
        "evidence_runs": index.get("runs", []),
        "blocking_gaps": blocking_gaps,
        "next_required_actions": [
            (
                "Recruit qualified independent clinician reviewers and retain private "
                "eligibility records outside the public repository."
            ),
            (
                "Collect complete blinded worksheet ratings for every case-submission "
                "from two qualified reviewers."
            ),
            "Export Scribeval judge scores for the same blinded submissions.",
            (
                "Resolve reviewer disagreement through qualified adjudication until no "
                "required adjudication remains."
            ),
            (
                "Build a versioned independent_clinician_review evidence bundle and "
                "re-run validation-claim readiness."
            ),
            "Publish only aggregate, hashed, non-identifying evidence artifacts.",
        ],
        "source_files": {
            "corpus_manifest": display_path(corpus_manifest),
            "collection_plan": display_path(collection_plan),
            "clinician_review_protocol": display_path(protocol),
            "reviewer_intake_checklist": display_path(reviewer_intake),
            "reviewer_training_guide": display_path(reviewer_training),
            "statistical_analysis_plan": display_path(statistical_analysis_plan),
            "evidence_run_index": display_path(evidence_index),
        },
        "claim_boundary": (
            "Prepared validation materials and synthetic bootstrap evidence are not "
            "independent clinical validation. A validation claim requires a claim-ready "
            "independent clinician evidence run."
        ),
    }


def report_markdown(status: dict[str, Any]) -> str:
    lines = [
        "# Scribeval Validation Goal Status",
        "",
        f"Status: `{status['current_status']}`",
        "",
        f"Benchmark unit: `{status['benchmark_unit']}`",
        "",
        status["claim_boundary"],
        "",
        "## Prepared Components",
        "",
        "| Component | Status | Evidence |",
        "|---|---|---|",
    ]
    for name, component in status["prepared_components"].items():
        component_status_text = "pass" if component["passed"] else "fail"
        evidence = json.dumps(component["evidence"], sort_keys=True)
        lines.append(f"| {name} | {component_status_text} | `{evidence}` |")

    lines.extend(
        [
            "",
            "## Coverage",
            "",
            f"- Cases: {status['coverage']['case_count']}",
            (
                "- Planned case-submissions: "
                f"{status['coverage']['planned_case_submission_count']}"
            ),
            (
                "- Planned individual calibration pairs: "
                f"{status['coverage']['planned_individual_calibration_pairs']}"
            ),
            f"- Planned consensus pairs: {status['coverage']['planned_consensus_pairs']}",
            f"- Evidence runs: {status['coverage']['evidence_run_count']}",
            f"- Claim-ready runs: {status['coverage']['claim_ready_run_count']}",
            "",
            "## Blocking Gaps",
            "",
        ]
    )
    if status["blocking_gaps"]:
        for gap in status["blocking_gaps"]:
            lines.append(f"- `{gap['gap_id']}`: {gap['message']}")
    else:
        lines.append("None.")

    lines.extend(["", "## Next Required Actions", ""])
    for action in status["next_required_actions"]:
        lines.append(f"- {action}")
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize progress toward Scribeval independent clinician validation."
    )
    parser.add_argument("--corpus-manifest", type=Path, default=DEFAULT_CORPUS_MANIFEST)
    parser.add_argument("--collection-plan", type=Path, default=DEFAULT_COLLECTION_PLAN)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--reviewer-intake", type=Path, default=DEFAULT_REVIEWER_INTAKE)
    parser.add_argument("--reviewer-training", type=Path, default=DEFAULT_REVIEWER_TRAINING)
    parser.add_argument(
        "--statistical-analysis-plan",
        type=Path,
        default=DEFAULT_SAP,
    )
    parser.add_argument("--evidence-index", type=Path, default=DEFAULT_EVIDENCE_INDEX)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        status = summarize_goal_status(
            corpus_manifest=args.corpus_manifest,
            collection_plan=args.collection_plan,
            protocol=args.protocol,
            reviewer_intake=args.reviewer_intake,
            reviewer_training=args.reviewer_training,
            statistical_analysis_plan=args.statistical_analysis_plan,
            evidence_index=args.evidence_index,
        )
    except ValueError as exc:
        print(f"Validation goal status failed: {exc}")
        return 1

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(status, indent=2) + "\n")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(report_markdown(status))
    print(f"Wrote validation goal status to {args.output_json}")
    print(f"Wrote validation goal report to {args.output_md}")
    print(f"Current status: {status['current_status']}")
    print(f"Claim-ready runs: {status['coverage']['claim_ready_run_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
