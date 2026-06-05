"""Audit whether clinician reviewer inputs are ready for validation analysis."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS_MANIFEST = ROOT / "validation_pack" / "corpus" / "corpus_manifest.json"
DEFAULT_PROTOCOL = ROOT / "validation_pack" / "clinician_review_protocol.json"

DIRECT_IDENTIFIER_FIELDS = {
    "email",
    "name",
    "phone",
    "provider_number",
    "registration_number",
}
TRUE_VALUES = {"1", "true", "yes", "y"}
NO_CONFLICT_VALUES = {"none", "no", "n"}


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} is not valid JSON: {exc}") from exc


def load_protocol(protocol_path: Path) -> dict[str, Any]:
    protocol = load_json(protocol_path)
    requirements = protocol.get("minimum_independent_review_requirements", {})
    required_dimensions = requirements.get(
        "required_dimensions",
        ["omission", "hallucination", "medicolegal", "ahpra", "pdqi9", "qnote"],
    )
    return {
        "reviewers_per_submission": int(
            requirements.get(
                "reviewers_per_case_submission",
                requirements.get("reviewers_per_case", 2),
            )
        ),
        "minimum_years_post_registration": int(
            requirements.get("minimum_years_post_registration", 1)
        ),
        "allowed_review_roles": set(requirements.get("allowed_review_roles", [])),
        "required_dimensions": tuple(required_dimensions),
    }


def load_expected_submissions(corpus_manifest_path: Path) -> set[tuple[str, str]]:
    manifest = load_json(corpus_manifest_path)
    corpus_root = corpus_manifest_path.parent
    expected: set[tuple[str, str]] = set()
    for rel_path in manifest["case_files"]:
        case = load_json(corpus_root / rel_path)
        for submission in case["candidate_notes"]:
            expected.add((case["case_id"], submission["blind_label"]))
    if not expected:
        raise ValueError("Corpus manifest did not resolve any blinded submissions")
    return expected


def load_reviewer_registry(
    registry_path: Path,
    protocol: dict[str, Any],
) -> dict[str, dict[str, str]]:
    reviewers: dict[str, dict[str, str]] = {}
    with registry_path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        forbidden_fields = DIRECT_IDENTIFIER_FIELDS & fieldnames
        if forbidden_fields:
            raise ValueError(
                "Reviewer registry must not contain direct identifiers: "
                f"{sorted(forbidden_fields)}"
            )
        for row_index, row in enumerate(reader, start=2):
            reviewer_id = row.get("reviewer_id", "").strip()
            if not reviewer_id:
                raise ValueError(f"Reviewer registry row {row_index} has no reviewer_id")
            if reviewer_id in reviewers:
                raise ValueError(f"Duplicate reviewer_id in registry: {reviewer_id}")
            reviewers[reviewer_id] = {key: value.strip() for key, value in row.items()}

    for reviewer_id, reviewer in reviewers.items():
        validate_reviewer(reviewer_id, reviewer, protocol)
    return reviewers


def validate_reviewer(reviewer_id: str, reviewer: dict[str, str], protocol: dict[str, Any]) -> None:
    if reviewer_id.lower().startswith("synthetic"):
        raise ValueError(f"Reviewer {reviewer_id} is synthetic")
    if reviewer.get("registration_status", "").lower() != "current":
        raise ValueError(f"Reviewer {reviewer_id} is not currently registered")
    if reviewer.get("training_completed", "").lower() not in TRUE_VALUES:
        raise ValueError(f"Reviewer {reviewer_id} has not completed training")
    if reviewer.get("conflict_of_interest", "").lower() not in NO_CONFLICT_VALUES:
        raise ValueError(f"Reviewer {reviewer_id} has a conflict of interest")
    allowed_roles = protocol["allowed_review_roles"]
    if allowed_roles and reviewer.get("review_role", "").lower() not in allowed_roles:
        raise ValueError(f"Reviewer {reviewer_id} has an invalid review_role")
    try:
        years = int(reviewer.get("years_post_registration", ""))
    except ValueError as exc:
        raise ValueError(
            f"Reviewer {reviewer_id} years_post_registration is not an integer"
        ) from exc
    if years < protocol["minimum_years_post_registration"]:
        raise ValueError(f"Reviewer {reviewer_id} has insufficient experience")


def row_has_complete_required_dimensions(row: dict[str, str], dimensions: tuple[str, ...]) -> bool:
    for dimension in dimensions:
        if not row.get(f"{dimension}_score", "").strip():
            return False
        if not row.get(f"{dimension}_severity", "").strip():
            return False
    return True


def audit_readiness(
    *,
    worksheet_path: Path,
    reviewer_registry_path: Path,
    corpus_manifest_path: Path,
    protocol_path: Path,
) -> dict[str, Any]:
    protocol = load_protocol(protocol_path)
    expected_submissions = load_expected_submissions(corpus_manifest_path)
    registry = load_reviewer_registry(reviewer_registry_path, protocol)

    reviewers_by_submission: dict[tuple[str, str], set[str]] = defaultdict(set)
    incomplete_rows: list[dict[str, Any]] = []
    unknown_submission_rows: list[dict[str, Any]] = []
    unknown_reviewer_rows: list[dict[str, Any]] = []

    with worksheet_path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        forbidden_fields = DIRECT_IDENTIFIER_FIELDS & fieldnames
        if forbidden_fields:
            raise ValueError(
                "Worksheet must not contain direct identifiers: "
                f"{sorted(forbidden_fields)}"
            )
        for row_index, row in enumerate(reader, start=2):
            case_id = row.get("case_id", "").strip()
            blind_label = row.get("blinded_submission", "").strip()
            reviewer_id = row.get("reviewer_id", "").strip()
            if not case_id or not blind_label or not reviewer_id:
                continue

            submission_key = (case_id, blind_label)
            if submission_key not in expected_submissions:
                unknown_submission_rows.append(
                    {"row": row_index, "case_id": case_id, "blind_label": blind_label}
                )
                continue
            if reviewer_id not in registry:
                unknown_reviewer_rows.append({"row": row_index, "reviewer_id": reviewer_id})
                continue
            if not row_has_complete_required_dimensions(row, protocol["required_dimensions"]):
                incomplete_rows.append(
                    {
                        "row": row_index,
                        "case_id": case_id,
                        "blind_label": blind_label,
                        "reviewer_id": reviewer_id,
                    }
                )
                continue
            reviewers_by_submission[submission_key].add(reviewer_id)

    minimum_reviewers = protocol["reviewers_per_submission"]
    under_reviewed = [
        {
            "case_id": case_id,
            "blind_label": blind_label,
            "qualified_reviewer_count": len(reviewers_by_submission[(case_id, blind_label)]),
            "required_reviewer_count": minimum_reviewers,
        }
        for case_id, blind_label in sorted(expected_submissions)
        if len(reviewers_by_submission[(case_id, blind_label)]) < minimum_reviewers
    ]
    is_ready = not (
        under_reviewed or incomplete_rows or unknown_submission_rows or unknown_reviewer_rows
    )
    return {
        "schema_version": "1.0.0",
        "audit_id": "clinician_review_readiness_v1",
        "is_ready_for_independent_validation": is_ready,
        "requirements": {
            "reviewers_per_case_submission": minimum_reviewers,
            "required_dimensions": list(protocol["required_dimensions"]),
            "direct_identifier_fields_forbidden": sorted(DIRECT_IDENTIFIER_FIELDS),
        },
        "coverage": {
            "expected_case_submission_count": len(expected_submissions),
            "complete_case_submission_count": len(expected_submissions) - len(under_reviewed),
            "qualified_reviewer_count": len(registry),
        },
        "issues": {
            "under_reviewed_submissions": under_reviewed,
            "incomplete_rating_rows": incomplete_rows,
            "unknown_submission_rows": unknown_submission_rows,
            "unknown_reviewer_rows": unknown_reviewer_rows,
        },
    }


def report_markdown(report: dict[str, Any]) -> str:
    status = "ready" if report["is_ready_for_independent_validation"] else "not ready"
    lines = [
        "# Clinician Review Readiness Report",
        "",
        f"Status: {status}",
        "",
        "## Coverage",
        "",
        f"- Expected case-submissions: {report['coverage']['expected_case_submission_count']}",
        f"- Complete case-submissions: {report['coverage']['complete_case_submission_count']}",
        f"- Qualified reviewers: {report['coverage']['qualified_reviewer_count']}",
        "",
        "## Requirements",
        "",
        (
            "- Reviewers per case-submission: "
            f"{report['requirements']['reviewers_per_case_submission']}"
        ),
        "- Required dimensions: " + ", ".join(report["requirements"]["required_dimensions"]),
        "- Direct identifiers are forbidden in worksheet and registry files.",
        "",
    ]
    for issue_name, rows in report["issues"].items():
        lines.append(f"## {issue_name.replace('_', ' ').title()}")
        lines.append("")
        if not rows:
            lines.append("None.")
        else:
            for row in rows[:50]:
                lines.append(f"- `{json.dumps(row, sort_keys=True)}`")
            if len(rows) > 50:
                lines.append(f"- ... {len(rows) - 50} more")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit whether clinician reviewer inputs meet validation readiness rules."
    )
    parser.add_argument("--worksheet", required=True, type=Path)
    parser.add_argument("--reviewer-registry", required=True, type=Path)
    parser.add_argument("--corpus-manifest", type=Path, default=DEFAULT_CORPUS_MANIFEST)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-md", type=Path)
    parser.add_argument(
        "--fail-on-not-ready",
        action="store_true",
        help="Exit 1 when the worksheet is structurally valid but incomplete.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = audit_readiness(
            worksheet_path=args.worksheet,
            reviewer_registry_path=args.reviewer_registry,
            corpus_manifest_path=args.corpus_manifest,
            protocol_path=args.protocol,
        )
    except ValueError as exc:
        print(f"Readiness audit failed: {exc}", file=sys.stderr)
        return 1

    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(report, indent=2) + "\n")
    if args.output_md is not None:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(report_markdown(report))

    status = "ready" if report["is_ready_for_independent_validation"] else "not ready"
    print(f"Clinician review readiness: {status}")
    print(f"Expected case-submissions: {report['coverage']['expected_case_submission_count']}")
    print(f"Complete case-submissions: {report['coverage']['complete_case_submission_count']}")
    print(f"Qualified reviewers: {report['coverage']['qualified_reviewer_count']}")
    return 1 if args.fail_on_not_ready and not report["is_ready_for_independent_validation"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
