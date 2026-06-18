"""Plan reviewer recruitment targets from the public validation corpus."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS_MANIFEST = ROOT / "validation_pack" / "corpus" / "corpus_manifest.json"
DEFAULT_PROTOCOL = ROOT / "validation_pack" / "clinician_review_protocol.json"
DEFAULT_OUTPUT_JSON = ROOT / "validation_pack" / "reviewer_recruitment_plan.json"
DEFAULT_OUTPUT_MD = ROOT / "validation_pack" / "reviewer_recruitment_plan.md"
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


def protocol_requirements(protocol_path: Path) -> dict[str, Any]:
    protocol = load_json(protocol_path)
    requirements = protocol.get("minimum_independent_review_requirements", {})
    thresholds = protocol.get("validation_claim_thresholds", {})
    reviewers_per_submission = int(
        requirements.get(
            "reviewers_per_case_submission",
            requirements.get("reviewers_per_case", 2),
        )
    )
    minimum_adjudicators = 1
    return {
        "reviewers_per_case_submission": reviewers_per_submission,
        "minimum_primary_secondary_reviewers": reviewers_per_submission,
        "minimum_adjudicators": minimum_adjudicators,
        "minimum_total_qualified_reviewers": reviewers_per_submission
        + minimum_adjudicators,
        "minimum_claim_qualified_reviewers": int(
            thresholds.get("minimum_qualified_reviewers", reviewers_per_submission)
        ),
        "eligible_registration_status": requirements.get(
            "eligible_registration_status",
            "current",
        ),
        "minimum_years_post_registration": int(
            requirements.get("minimum_years_post_registration", 1)
        ),
        "required_training_completed": bool(
            requirements.get("required_training_completed", True)
        ),
        "allowed_review_roles": list(requirements.get("allowed_review_roles", [])),
        "conflict_of_interest": requirements.get("conflict_of_interest", "none"),
    }


def corpus_specialty_targets(corpus_manifest: Path) -> tuple[list[dict[str, Any]], int, int]:
    manifest = load_json(corpus_manifest)
    corpus_root = corpus_manifest.parent
    case_counts: dict[str, set[str]] = defaultdict(set)
    submission_counts: dict[str, int] = defaultdict(int)
    total_case_count = 0
    total_submission_count = 0

    for rel_path in manifest.get("case_files", []):
        case = load_json(corpus_root / rel_path)
        case_id = str(case["case_id"])
        specialty = str(case["specialty"])
        submissions = case.get("candidate_notes", [])
        total_case_count += 1
        total_submission_count += len(submissions)
        case_counts[specialty].add(case_id)
        submission_counts[specialty] += len(submissions)

    targets = [
        {
            "specialty": specialty,
            "case_count": len(case_counts[specialty]),
            "case_submission_count": submission_counts[specialty],
            "recruitment_target": (
                "At least one recruited reviewer or adjudicator should declare "
                "familiarity with this clinical area, or the coordinator must "
                "document why generalist review is sufficient."
            ),
        }
        for specialty in sorted(case_counts)
    ]
    return targets, total_case_count, total_submission_count


def build_recruitment_plan(*, corpus_manifest: Path, protocol: Path) -> dict[str, Any]:
    requirements = protocol_requirements(protocol)
    specialty_targets, case_count, submission_count = corpus_specialty_targets(
        corpus_manifest
    )
    return {
        "schema_version": "1.0.0",
        "plan_id": "scribeval_reviewer_recruitment_plan_v1",
        "status": "ready_for_reviewer_recruitment",
        "benchmark_unit": BENCHMARK_UNIT,
        "source_files": {
            "corpus_manifest": display_path(corpus_manifest),
            "clinician_review_protocol": display_path(protocol),
        },
        "coverage": {
            "case_count": case_count,
            "case_submission_count": submission_count,
            "specialty_count": len(specialty_targets),
        },
        "recruitment_targets": requirements,
        "specialty_familiarity_targets": specialty_targets,
        "privacy_and_publication_controls": {
            "public_registry_only": True,
            "retain_names_contact_registration_and_attestations_privately": True,
            "completed_attestations_must_not_be_committed": True,
            "public_reviewer_fields": [
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
        },
        "is_recruitment_plan_complete": bool(specialty_targets)
        and requirements["minimum_total_qualified_reviewers"]
        >= requirements["minimum_claim_qualified_reviewers"],
        "claim_boundary": (
            "This recruitment plan supports reviewer sourcing and governance only. "
            "It is not validation evidence; validation claims require completed "
            "independent clinician ratings, reliability analysis, adjudicated "
            "consensus, and claim-readiness checks."
        ),
    }


def report_markdown(plan: dict[str, Any]) -> str:
    targets = plan["recruitment_targets"]
    coverage = plan["coverage"]
    lines = [
        "# Reviewer Recruitment Plan",
        "",
        plan["claim_boundary"],
        "",
        f"Benchmark unit: `{plan['benchmark_unit']}`",
        "",
        "## Recruitment Targets",
        "",
        (
            "- Primary/secondary reviewers: "
            f"{targets['minimum_primary_secondary_reviewers']}"
        ),
        f"- Adjudicators: {targets['minimum_adjudicators']}",
        (
            "- Total qualified reviewers: "
            f"{targets['minimum_total_qualified_reviewers']}"
        ),
        (
            "- Minimum years post registration: "
            f"{targets['minimum_years_post_registration']}"
        ),
        f"- Registration status: `{targets['eligible_registration_status']}`",
        f"- Conflict of interest: `{targets['conflict_of_interest']}`",
        f"- Training completed required: {targets['required_training_completed']}",
        "",
        "## Corpus Coverage",
        "",
        f"- Cases: {coverage['case_count']}",
        f"- Case-submissions: {coverage['case_submission_count']}",
        f"- Specialties: {coverage['specialty_count']}",
        "",
        "| Specialty | Cases | Case-submissions | Recruitment Target |",
        "|---|---:|---:|---|",
    ]
    for row in plan["specialty_familiarity_targets"]:
        lines.append(
            f"| {row['specialty']} | {row['case_count']} | "
            f"{row['case_submission_count']} | {row['recruitment_target']} |"
        )
    lines.extend(
        [
            "",
            "## Privacy Controls",
            "",
            "- Publish only pseudonymous reviewer registry fields.",
            "- Keep names, contact details, registration evidence, and completed "
            "attestations private.",
            "- Do not commit completed attestation forms or raw recruitment records.",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plan independent clinician reviewer recruitment targets."
    )
    parser.add_argument("--corpus-manifest", type=Path, default=DEFAULT_CORPUS_MANIFEST)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    parser.add_argument(
        "--fail-on-incomplete",
        action="store_true",
        help="Return non-zero if recruitment targets are incomplete.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plan = build_recruitment_plan(
        corpus_manifest=args.corpus_manifest,
        protocol=args.protocol,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(plan, indent=2) + "\n")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(report_markdown(plan))
    print(f"Wrote reviewer recruitment plan to {args.output_json}")
    print(f"Wrote reviewer recruitment report to {args.output_md}")
    print(
        "Minimum total qualified reviewers: "
        f"{plan['recruitment_targets']['minimum_total_qualified_reviewers']}"
    )
    print(f"Specialty targets: {plan['coverage']['specialty_count']}")
    if args.fail_on_incomplete and not plan["is_recruitment_plan_complete"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
