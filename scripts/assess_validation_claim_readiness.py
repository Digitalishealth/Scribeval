"""Assess whether an evidence bundle supports a validation claim.

This is stricter than the publication audit. A bundle can be structurally
publishable while still not strong enough for clinical validation claims. This
script makes that distinction explicit.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
for path in (SRC, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from build_consensus_validation_ratings import consensus_summary  # noqa: E402

DEFAULT_PROTOCOL = ROOT / "validation_pack" / "clinician_review_protocol.json"
BENCHMARK_UNIT = "whole transcript -> final note quality score"


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} is not valid JSON: {exc}") from exc


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def resolve_manifest_path(evidence_manifest: Path, manifest_value: str) -> Path:
    path = Path(manifest_value)
    if path.is_absolute():
        return path
    return (evidence_manifest.parent / path).resolve()


def default_thresholds(protocol: dict[str, Any]) -> dict[str, Any]:
    requirements = protocol.get("minimum_independent_review_requirements", {})
    return {
        "required_evidence_status": "independent_clinician_review",
        "minimum_case_count": 20,
        "minimum_submission_count": 100,
        "minimum_qualified_reviewers": requirements.get("reviewers_per_case_submission", 2),
        "maximum_consensus_adjudication_required_count": 0,
        "minimum_reviewer_reliability_weighted_kappa": 0.6,
        "minimum_consensus_weighted_kappa": 0.6,
        "required_strata": ["specialty", "note_source", "prompt_strategy", "failure_mode"],
    }


def load_thresholds(protocol_path: Path) -> dict[str, Any]:
    protocol = load_json(protocol_path)
    thresholds = default_thresholds(protocol)
    thresholds.update(protocol.get("validation_claim_thresholds", {}))
    return thresholds


def check_item(
    checks: list[dict[str, Any]],
    *,
    check_id: str,
    passed: bool,
    observed: Any,
    threshold: Any,
    message: str,
) -> None:
    checks.append(
        {
            "id": check_id,
            "passed": bool(passed),
            "observed": observed,
            "threshold": threshold,
            "message": message,
        }
    )


def dimension_kappa_checks(
    checks: list[dict[str, Any]],
    *,
    check_prefix: str,
    rows: list[dict[str, Any]],
    required_dimensions: list[str],
    minimum_kappa: float,
    message_prefix: str,
) -> None:
    by_dimension = {row["dimension"]: row for row in rows}
    for dimension in required_dimensions:
        row = by_dimension.get(dimension)
        if row is None:
            check_item(
                checks,
                check_id=f"{check_prefix}.{dimension}",
                passed=False,
                observed=None,
                threshold=f">= {minimum_kappa}",
                message=f"{message_prefix} missing {dimension}",
            )
            continue
        observed = float(row["weighted_kappa"])
        check_item(
            checks,
            check_id=f"{check_prefix}.{dimension}",
            passed=observed >= minimum_kappa,
            observed=observed,
            threshold=f">= {minimum_kappa}",
            message=f"{message_prefix} {dimension} weighted kappa",
        )


def assess_claim_readiness(
    *,
    evidence_manifest_path: Path,
    protocol_path: Path,
) -> dict[str, Any]:
    manifest = load_json(evidence_manifest_path)
    thresholds = load_thresholds(protocol_path)

    readiness = load_json(
        resolve_manifest_path(evidence_manifest_path, manifest["readiness_report"])
    )
    reviewer_reliability = load_json(
        resolve_manifest_path(evidence_manifest_path, manifest["reviewer_reliability"])
    )
    consensus_pairs = load_json(
        resolve_manifest_path(evidence_manifest_path, manifest["consensus_calibration_pairs"])
    )
    stratified_summary = load_json(
        resolve_manifest_path(evidence_manifest_path, manifest["stratified_summary"])
    )
    consensus = consensus_summary(consensus_pairs)
    manifest_coverage = manifest.get("coverage", {})
    readiness_coverage = readiness.get("coverage", {})
    strata = stratified_summary.get("strata", {})

    checks: list[dict[str, Any]] = []
    check_item(
        checks,
        check_id="benchmark_unit",
        passed=manifest.get("benchmark_unit") == BENCHMARK_UNIT,
        observed=manifest.get("benchmark_unit"),
        threshold=BENCHMARK_UNIT,
        message="Evidence bundle uses the transcript-to-note benchmark unit",
    )
    check_item(
        checks,
        check_id="evidence_status",
        passed=manifest.get("status") == thresholds["required_evidence_status"],
        observed=manifest.get("status"),
        threshold=thresholds["required_evidence_status"],
        message="Evidence status supports independent clinician validation claims",
    )
    check_item(
        checks,
        check_id="review_readiness",
        passed=readiness.get("is_ready_for_independent_validation") is True,
        observed=readiness.get("is_ready_for_independent_validation"),
        threshold=True,
        message="Clinician review readiness audit passed",
    )
    check_item(
        checks,
        check_id="case_count",
        passed=consensus["coverage"]["case_count"] >= thresholds["minimum_case_count"],
        observed=consensus["coverage"]["case_count"],
        threshold=f">= {thresholds['minimum_case_count']}",
        message="Consensus evidence covers enough validation cases",
    )
    check_item(
        checks,
        check_id="submission_count",
        passed=consensus["coverage"]["submission_count"]
        >= thresholds["minimum_submission_count"],
        observed=consensus["coverage"]["submission_count"],
        threshold=f">= {thresholds['minimum_submission_count']}",
        message="Consensus evidence covers enough scored submissions",
    )
    check_item(
        checks,
        check_id="qualified_reviewer_count",
        passed=readiness_coverage.get("qualified_reviewer_count", 0)
        >= thresholds["minimum_qualified_reviewers"],
        observed=readiness_coverage.get("qualified_reviewer_count", 0),
        threshold=f">= {thresholds['minimum_qualified_reviewers']}",
        message="Enough qualified reviewers are represented",
    )
    check_item(
        checks,
        check_id="complete_case_submission_count",
        passed=manifest_coverage.get("complete_case_submission_count")
        == manifest_coverage.get("case_submission_count"),
        observed=manifest_coverage.get("complete_case_submission_count"),
        threshold=manifest_coverage.get("case_submission_count"),
        message="All expected case-submissions have complete clinician ratings",
    )
    check_item(
        checks,
        check_id="consensus_adjudication_required_count",
        passed=consensus["coverage"]["adjudication_required_count"]
        <= thresholds["maximum_consensus_adjudication_required_count"],
        observed=consensus["coverage"]["adjudication_required_count"],
        threshold=f"<= {thresholds['maximum_consensus_adjudication_required_count']}",
        message="Consensus ratings have no unresolved adjudication burden",
    )

    required_dimensions = list(readiness["requirements"]["required_dimensions"])
    dimension_kappa_checks(
        checks,
        check_prefix="reviewer_reliability",
        rows=reviewer_reliability.get("dimension_agreement", []),
        required_dimensions=required_dimensions,
        minimum_kappa=float(thresholds["minimum_reviewer_reliability_weighted_kappa"]),
        message_prefix="Clinician reviewer reliability",
    )
    dimension_kappa_checks(
        checks,
        check_prefix="consensus_agreement",
        rows=consensus.get("dimension_agreement", []),
        required_dimensions=required_dimensions,
        minimum_kappa=float(thresholds["minimum_consensus_weighted_kappa"]),
        message_prefix="Scribeval judge vs clinician consensus",
    )

    for stratum in thresholds["required_strata"]:
        rows = strata.get(stratum)
        check_item(
            checks,
            check_id=f"stratum.{stratum}",
            passed=isinstance(rows, list) and len(rows) > 0,
            observed=len(rows) if isinstance(rows, list) else None,
            threshold="> 0 rows",
            message=f"Stratified evidence includes {stratum}",
        )

    is_ready = all(check["passed"] for check in checks)
    return {
        "schema_version": "1.0.0",
        "assessment_id": "validation_claim_readiness_v1",
        "evidence_id": manifest.get("evidence_id"),
        "benchmark_unit": BENCHMARK_UNIT,
        "is_ready_for_validation_claim": is_ready,
        "thresholds": thresholds,
        "coverage": {
            "case_count": consensus["coverage"]["case_count"],
            "submission_count": consensus["coverage"]["submission_count"],
            "consensus_pair_count": consensus["coverage"]["consensus_pair_count"],
            "individual_calibration_pair_count": manifest_coverage.get(
                "calibration_pair_count"
            ),
            "reviewer_reliability_pair_count": manifest_coverage.get(
                "reviewer_reliability_pair_count"
            ),
            "adjudication_required_count": consensus["coverage"][
                "adjudication_required_count"
            ],
        },
        "checks": checks,
        "failed_checks": [check for check in checks if not check["passed"]],
        "interpretation_note": (
            "A structurally valid evidence bundle is not automatically strong enough "
            "for validation claims. This assessment requires completed independent "
            "clinician review, reliable clinician agreement, judge-vs-consensus "
            "agreement across required dimensions, full corpus coverage, and no "
            "unresolved adjudication flags."
        ),
    }


def report_markdown(report: dict[str, Any]) -> str:
    status = "ready" if report["is_ready_for_validation_claim"] else "not ready"
    lines = [
        "# Validation Claim Readiness",
        "",
        f"Status: {status}",
        "",
        report["interpretation_note"],
        "",
        "## Coverage",
        "",
        f"- Cases: {report['coverage']['case_count']}",
        f"- Submissions: {report['coverage']['submission_count']}",
        f"- Consensus pairs: {report['coverage']['consensus_pair_count']}",
        (
            "- Individual calibration pairs: "
            f"{report['coverage']['individual_calibration_pair_count']}"
        ),
        (
            "- Reviewer reliability pairs: "
            f"{report['coverage']['reviewer_reliability_pair_count']}"
        ),
        f"- Adjudication required: {report['coverage']['adjudication_required_count']}",
        "",
        "## Checks",
        "",
        "| Check | Status | Observed | Threshold |",
        "|---|---|---:|---:|",
    ]
    for check in report["checks"]:
        check_status = "pass" if check["passed"] else "fail"
        lines.append(
            f"| {check['id']} | {check_status} | {check['observed']} | "
            f"{check['threshold']} |"
        )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Assess whether a validation evidence bundle supports a claim."
    )
    parser.add_argument("--evidence-manifest", required=True, type=Path)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-md", required=True, type=Path)
    parser.add_argument(
        "--fail-on-not-ready",
        action="store_true",
        help="Exit 1 when the assessment is not ready for validation claims.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = assess_claim_readiness(
            evidence_manifest_path=args.evidence_manifest,
            protocol_path=args.protocol,
        )
    except ValueError as exc:
        print(f"Validation claim readiness failed: {exc}", file=sys.stderr)
        return 1

    write_json(args.output_json, report)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(report_markdown(report))
    status = "ready" if report["is_ready_for_validation_claim"] else "not ready"
    print(f"Validation claim readiness: {status}")
    print(f"Failed checks: {len(report['failed_checks'])}")
    if args.fail_on_not_ready and not report["is_ready_for_validation_claim"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
