"""Summarize validation review-run progress without exposing raw review data."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS_MANIFEST = ROOT / "validation_pack" / "corpus" / "corpus_manifest.json"
DEFAULT_PROTOCOL = ROOT / "validation_pack" / "clinician_review_protocol.json"

BENCHMARK_UNIT = "whole transcript -> final note quality score"
FORBIDDEN_JUDGE_SCORE_FIELDS = {
    "candidate_note",
    "candidate_note_text",
    "excerpts",
    "note",
    "raw_judge_response",
    "reasoning",
    "transcript",
    "transcript_text",
}


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} is not valid JSON: {exc}") from exc


def relative_or_absolute(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def corpus_counts(corpus_manifest_path: Path) -> dict[str, int]:
    manifest = load_json(corpus_manifest_path)
    corpus_root = corpus_manifest_path.parent
    case_ids: set[str] = set()
    case_submission_count = 0
    for rel_path in manifest.get("case_files", []):
        case = load_json(corpus_root / rel_path)
        case_ids.add(case["case_id"])
        case_submission_count += len(case.get("candidate_notes", []))
    if not case_ids or not case_submission_count:
        raise ValueError("Corpus manifest did not resolve any case submissions")
    return {
        "case_count": len(case_ids),
        "case_submission_count": case_submission_count,
    }


def reviewer_role_counts(registry: dict[str, dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for reviewer in registry.values():
        role = reviewer.get("review_role", "unknown").strip().lower() or "unknown"
        counts[role] = counts.get(role, 0) + 1
    return dict(sorted(counts.items()))


def summarize_assignments(
    *,
    assignments_dir: Path | None,
    expected_case_submission_count: int,
    required_reviewer_count: int,
) -> dict[str, Any]:
    if assignments_dir is None:
        return {
            "provided": False,
            "assignment_count": 0,
            "case_submission_count": 0,
            "reviewer_count": 0,
            "worksheet_file_count": 0,
            "ready": None,
            "issue_counts": {},
        }

    manifest_path = assignments_dir / "assignment_manifest.json"
    if not manifest_path.exists():
        return {
            "provided": True,
            "assignment_count": 0,
            "case_submission_count": 0,
            "reviewer_count": 0,
            "worksheet_file_count": 0,
            "ready": False,
            "issue_counts": {"missing_assignment_manifest": 1},
        }

    manifest = load_json(manifest_path)
    expected_assignment_count = expected_case_submission_count * required_reviewer_count
    worksheet_files = manifest.get("worksheet_files", [])
    issue_counts = {
        "case_submission_count_mismatch": int(
            manifest.get("case_submission_count") != expected_case_submission_count
        ),
        "assignment_count_mismatch": int(
            manifest.get("assignment_count") != expected_assignment_count
        ),
        "reviewer_requirement_mismatch": int(
            manifest.get("reviewers_per_case_submission") != required_reviewer_count
        ),
    }
    issue_counts = {key: value for key, value in issue_counts.items() if value}
    return {
        "provided": True,
        "assignment_count": int(manifest.get("assignment_count", 0)),
        "case_submission_count": int(manifest.get("case_submission_count", 0)),
        "reviewer_count": int(manifest.get("reviewer_count", 0)),
        "worksheet_file_count": len(worksheet_files) if isinstance(worksheet_files, list) else 0,
        "ready": not issue_counts,
        "issue_counts": issue_counts,
    }


def summarize_worksheet(
    *,
    worksheet_path: Path | None,
    expected_submissions: set[tuple[str, str]],
    registry: dict[str, dict[str, str]],
    required_dimensions: tuple[str, ...],
    required_reviewer_count: int,
    required_overall_rating: bool,
) -> dict[str, Any]:
    if worksheet_path is None:
        return {
            "provided": False,
            "row_count": 0,
            "complete_rating_row_count": 0,
            "complete_dimension_rating_count": 0,
            "complete_overall_rating_count": 0,
            "complete_case_submission_count": 0,
            "ready": None,
            "issue_counts": {},
        }

    from audit_clinician_review_readiness import (
        DIRECT_IDENTIFIER_FIELDS,
        row_has_complete_overall_rating,
        row_has_complete_required_dimensions,
    )

    reviewer_ids_by_submission: dict[tuple[str, str], set[str]] = {
        submission: set() for submission in expected_submissions
    }
    row_count = 0
    complete_rating_row_count = 0
    incomplete_rating_row_count = 0
    incomplete_overall_rating_row_count = 0
    empty_assignment_row_count = 0
    unknown_submission_row_count = 0
    unknown_reviewer_row_count = 0

    with worksheet_path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        forbidden_fields = DIRECT_IDENTIFIER_FIELDS & fieldnames
        if forbidden_fields:
            raise ValueError(
                "Worksheet must not contain direct identifiers: "
                f"{sorted(forbidden_fields)}"
            )
        for row in reader:
            row_count += 1
            case_id = row.get("case_id", "").strip()
            blind_label = row.get("blinded_submission", "").strip()
            reviewer_id = row.get("reviewer_id", "").strip()
            if not case_id or not blind_label or not reviewer_id:
                empty_assignment_row_count += 1
                continue
            submission_key = (case_id, blind_label)
            if submission_key not in expected_submissions:
                unknown_submission_row_count += 1
                continue
            if reviewer_id not in registry:
                unknown_reviewer_row_count += 1
                continue
            dimensions_complete = row_has_complete_required_dimensions(
                row,
                required_dimensions,
            )
            overall_complete = (
                row_has_complete_overall_rating(row) if required_overall_rating else True
            )
            if not dimensions_complete or not overall_complete:
                incomplete_rating_row_count += 1
                if required_overall_rating and not overall_complete:
                    incomplete_overall_rating_row_count += 1
                continue
            complete_rating_row_count += 1
            reviewer_ids_by_submission[submission_key].add(reviewer_id)

    under_reviewed_count = sum(
        1
        for reviewer_ids in reviewer_ids_by_submission.values()
        if len(reviewer_ids) < required_reviewer_count
    )
    complete_case_submission_count = len(expected_submissions) - under_reviewed_count
    issue_counts = {
        "empty_assignment_rows": empty_assignment_row_count,
        "incomplete_rating_rows": incomplete_rating_row_count,
        "incomplete_overall_rating_rows": incomplete_overall_rating_row_count,
        "unknown_submission_rows": unknown_submission_row_count,
        "unknown_reviewer_rows": unknown_reviewer_row_count,
        "under_reviewed_case_submissions": under_reviewed_count,
    }
    issue_counts = {key: value for key, value in issue_counts.items() if value}
    return {
        "provided": True,
        "row_count": row_count,
        "complete_rating_row_count": complete_rating_row_count,
        "complete_dimension_rating_count": complete_rating_row_count * len(required_dimensions),
        "complete_overall_rating_count": (
            complete_rating_row_count if required_overall_rating else 0
        ),
        "complete_case_submission_count": complete_case_submission_count,
        "ready": not issue_counts,
        "issue_counts": issue_counts,
    }


def summarize_judge_scores(
    *,
    judge_scores_path: Path | None,
    corpus_manifest_path: Path,
    expected_submissions: set[tuple[str, str]],
    required_dimensions: tuple[str, ...],
    required_overall_rating: bool,
) -> dict[str, Any]:
    if judge_scores_path is None:
        return {
            "provided": False,
            "score_count": 0,
            "raw_score_row_count": 0,
            "required_score_count": 0,
            "ready": None,
            "issue_counts": {},
        }

    from import_validation_ratings import load_blind_label_map, load_judge_scores

    raw_scores = load_json(judge_scores_path)
    if not isinstance(raw_scores, list):
        raise ValueError("Judge scores must be a list of score objects")

    forbidden_field_row_count = sum(
        1 for row in raw_scores if FORBIDDEN_JUDGE_SCORE_FIELDS & set(row)
    )
    score_map = load_judge_scores(judge_scores_path)
    blind_label_map = load_blind_label_map(corpus_manifest_path)
    expected_score_keys: set[tuple[str, str, str]] = set()
    for case_id, blind_label in expected_submissions:
        submission_id = blind_label_map[(case_id, blind_label)]
        for dimension in required_dimensions:
            expected_score_keys.add((case_id, submission_id, dimension))

    observed_required_keys = {
        key for key in score_map if key[2] in set(required_dimensions)
    }
    if required_overall_rating:
        for case_id, blind_label in expected_submissions:
            submission_id = blind_label_map[(case_id, blind_label)]
            expected_score_keys.add((case_id, submission_id, "overall"))
        observed_required_keys = {
            key
            for key in score_map
            if key[2] in set(required_dimensions) or key[2] == "overall"
        }
    missing_score_count = len(expected_score_keys - observed_required_keys)
    extra_required_dimension_score_count = len(observed_required_keys - expected_score_keys)
    issue_counts = {
        "missing_required_scores": missing_score_count,
        "extra_required_dimension_scores": extra_required_dimension_score_count,
        "rows_with_forbidden_raw_fields": forbidden_field_row_count,
    }
    issue_counts = {key: value for key, value in issue_counts.items() if value}
    return {
        "provided": True,
        "score_count": len(score_map),
        "raw_score_row_count": len(raw_scores),
        "required_score_count": len(expected_score_keys),
        "ready": not issue_counts,
        "issue_counts": issue_counts,
    }


def build_review_run_status(
    *,
    reviewer_registry: Path,
    worksheet: Path | None,
    judge_scores: Path | None,
    assignments_dir: Path | None,
    corpus_manifest: Path,
    protocol_path: Path,
) -> dict[str, Any]:
    from audit_clinician_review_readiness import (
        load_expected_submissions,
        load_protocol,
        load_reviewer_registry,
    )

    protocol = load_protocol(protocol_path)
    expected_submissions = load_expected_submissions(corpus_manifest)
    registry = load_reviewer_registry(reviewer_registry, protocol)
    counts = corpus_counts(corpus_manifest)
    required_dimensions = protocol["required_dimensions"]
    required_reviewer_count = protocol["reviewers_per_submission"]
    expected_dimension_rating_count = (
        len(expected_submissions) * required_reviewer_count * len(required_dimensions)
    )
    expected_overall_rating_count = (
        len(expected_submissions) * required_reviewer_count
        if protocol["required_overall_rating"]
        else 0
    )

    assignments = summarize_assignments(
        assignments_dir=assignments_dir,
        expected_case_submission_count=len(expected_submissions),
        required_reviewer_count=required_reviewer_count,
    )
    worksheet_summary = summarize_worksheet(
        worksheet_path=worksheet,
        expected_submissions=expected_submissions,
        registry=registry,
        required_dimensions=required_dimensions,
        required_reviewer_count=required_reviewer_count,
        required_overall_rating=protocol["required_overall_rating"],
    )
    judge_score_summary = summarize_judge_scores(
        judge_scores_path=judge_scores,
        corpus_manifest_path=corpus_manifest,
        expected_submissions=expected_submissions,
        required_dimensions=required_dimensions,
        required_overall_rating=protocol["required_overall_rating"],
    )
    ready_for_consensus = (
        worksheet_summary["ready"] is True and judge_score_summary["ready"] is True
    )
    ready_for_evidence_bundle = ready_for_consensus

    source_files: dict[str, str | None] = {
        "corpus_manifest": relative_or_absolute(corpus_manifest),
        "clinician_review_protocol": relative_or_absolute(protocol_path),
        "reviewer_registry": reviewer_registry.name,
        "worksheet": worksheet.name if worksheet else None,
        "judge_scores": judge_scores.name if judge_scores else None,
        "assignments_dir": assignments_dir.name if assignments_dir else None,
    }

    return {
        "schema_version": "1.0.0",
        "summary_id": "scribeval_validation_review_run_status_v1",
        "benchmark_unit": BENCHMARK_UNIT,
        "requirements": {
            "reviewers_per_case_submission": required_reviewer_count,
            "required_dimensions": list(required_dimensions),
            "required_overall_rating": protocol["required_overall_rating"],
            "expected_dimension_rating_count": expected_dimension_rating_count,
            "expected_overall_rating_count": expected_overall_rating_count,
        },
        "coverage": {
            "case_count": counts["case_count"],
            "case_submission_count": counts["case_submission_count"],
            "expected_case_submission_count": len(expected_submissions),
            "qualified_reviewer_count": len(registry),
            "reviewer_role_counts": reviewer_role_counts(registry),
            "assignment_count": assignments["assignment_count"],
            "complete_case_submission_count": worksheet_summary[
                "complete_case_submission_count"
            ],
            "complete_dimension_rating_count": worksheet_summary[
                "complete_dimension_rating_count"
            ],
            "complete_overall_rating_count": worksheet_summary[
                "complete_overall_rating_count"
            ],
            "judge_score_count": judge_score_summary["score_count"],
            "raw_judge_score_row_count": judge_score_summary["raw_score_row_count"],
            "required_judge_score_count": judge_score_summary["required_score_count"],
        },
        "readiness": {
            "reviewer_registry_ready": True,
            "assignments_ready": assignments["ready"],
            "worksheet_ready_for_independent_validation": worksheet_summary["ready"],
            "judge_scores_ready": judge_score_summary["ready"],
            "ready_for_consensus_build": ready_for_consensus,
            "ready_for_evidence_bundle": ready_for_evidence_bundle,
        },
        "inputs": {
            "assignments": assignments,
            "worksheet": worksheet_summary,
            "judge_scores": judge_score_summary,
        },
        "source_files": source_files,
        "privacy_note": (
            "This status summary intentionally reports aggregate progress only. "
            "It omits reviewer identifiers, reviewer comments, transcript text, "
            "candidate note text, raw judge responses, reasoning, and excerpts."
        ),
    }


def report_markdown(report: dict[str, Any]) -> str:
    readiness = report["readiness"]
    status = (
        "ready"
        if readiness["ready_for_evidence_bundle"]
        else "not ready"
    )
    coverage = report["coverage"]
    lines = [
        "# Validation Review Run Status",
        "",
        f"Status: {status}",
        "",
        f"Benchmark unit: `{report['benchmark_unit']}`",
        "",
        "## Coverage",
        "",
        f"- Cases: {coverage['case_count']}",
        f"- Case-submissions: {coverage['case_submission_count']}",
        f"- Qualified reviewers: {coverage['qualified_reviewer_count']}",
        f"- Complete case-submissions: {coverage['complete_case_submission_count']}",
        (
            "- Complete required dimension ratings: "
            f"{coverage['complete_dimension_rating_count']} / "
            f"{report['requirements']['expected_dimension_rating_count']}"
        ),
        (
            "- Complete overall ratings: "
            f"{coverage['complete_overall_rating_count']} / "
            f"{report['requirements']['expected_overall_rating_count']}"
        ),
        (
            "- Judge scores: "
            f"{coverage['judge_score_count']} / {coverage['required_judge_score_count']}"
        ),
        "",
        "## Readiness",
        "",
    ]
    for key, value in readiness.items():
        lines.append(f"- {key.replace('_', ' ').title()}: {value}")

    lines.extend(["", "## Issue Counts", ""])
    for input_name in ("assignments", "worksheet", "judge_scores"):
        issue_counts = report["inputs"][input_name]["issue_counts"]
        lines.append(f"### {input_name.replace('_', ' ').title()}")
        lines.append("")
        if issue_counts:
            for issue_name, count in issue_counts.items():
                lines.append(f"- {issue_name.replace('_', ' ')}: {count}")
        else:
            lines.append("None.")
        lines.append("")

    lines.extend(
        [
            "## Privacy",
            "",
            report["privacy_note"],
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize validation review-run progress without exposing raw data."
    )
    parser.add_argument("--reviewer-registry", required=True, type=Path)
    parser.add_argument("--worksheet", type=Path)
    parser.add_argument("--judge-scores", type=Path)
    parser.add_argument("--assignments-dir", type=Path)
    parser.add_argument("--corpus-manifest", type=Path, default=DEFAULT_CORPUS_MANIFEST)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-md", type=Path)
    parser.add_argument(
        "--fail-on-not-ready",
        action="store_true",
        help="Exit 1 when supplied run inputs are not ready for evidence bundling.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = build_review_run_status(
            reviewer_registry=args.reviewer_registry,
            worksheet=args.worksheet,
            judge_scores=args.judge_scores,
            assignments_dir=args.assignments_dir,
            corpus_manifest=args.corpus_manifest,
            protocol_path=args.protocol,
        )
    except ValueError as exc:
        print(f"Review run status failed: {exc}", file=sys.stderr)
        return 1

    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(report, indent=2) + "\n")
    if args.output_md is not None:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(report_markdown(report))

    status = "ready" if report["readiness"]["ready_for_evidence_bundle"] else "not ready"
    print(f"Validation review run status: {status}")
    print(f"Case-submissions: {report['coverage']['case_submission_count']}")
    print(
        "Complete required dimension ratings: "
        f"{report['coverage']['complete_dimension_rating_count']} / "
        f"{report['requirements']['expected_dimension_rating_count']}"
    )
    print(
        "Complete overall ratings: "
        f"{report['coverage']['complete_overall_rating_count']} / "
        f"{report['requirements']['expected_overall_rating_count']}"
    )
    print(
        "Judge scores: "
        f"{report['coverage']['judge_score_count']} / "
        f"{report['coverage']['required_judge_score_count']}"
    )
    return (
        1
        if args.fail_on_not_ready
        and not report["readiness"]["ready_for_evidence_bundle"]
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
