"""Plan clinician validation collection coverage from the public corpus."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS_MANIFEST = ROOT / "validation_pack" / "corpus" / "corpus_manifest.json"
DEFAULT_PROTOCOL = ROOT / "validation_pack" / "clinician_review_protocol.json"
DEFAULT_OUTPUT_JSON = ROOT / "validation_pack" / "collection_plan.json"
DEFAULT_OUTPUT_MD = ROOT / "validation_pack" / "collection_plan.md"
BENCHMARK_UNIT = "whole transcript -> final note quality score"
STRATA = ("specialty", "note_source", "prompt_strategy", "failure_mode")


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
    required_dimensions = list(
        requirements.get(
            "required_dimensions",
            ["omission", "hallucination", "medicolegal", "ahpra", "pdqi9", "qnote"],
        )
    )
    scored_dimensions = list(required_dimensions)
    if requirements.get("required_overall_rating", False):
        scored_dimensions.append("overall")
    return {
        "reviewers_per_case_submission": int(
            requirements.get(
                "reviewers_per_case_submission",
                requirements.get("reviewers_per_case", 2),
            )
        ),
        "required_dimensions": required_dimensions,
        "required_overall_rating": bool(requirements.get("required_overall_rating", False)),
        "scored_dimensions": scored_dimensions,
        "required_strata": list(thresholds.get("required_strata", STRATA)),
        "minimum_pairs_per_stratum_value": int(
            thresholds.get("minimum_pairs_per_stratum_value", 2)
        ),
    }


class StratumPlan:
    def __init__(self) -> None:
        self.case_ids: set[str] = set()
        self.submission_refs: set[str] = set()

    def add(self, *, case_id: str, submission_id: str) -> None:
        self.case_ids.add(case_id)
        self.submission_refs.add(f"{case_id}:{submission_id}")

    def as_dict(
        self,
        *,
        value: str,
        reviewers_per_case_submission: int,
        scored_dimension_count: int,
        minimum_pairs_per_stratum_value: int,
    ) -> dict[str, Any]:
        case_submission_count = len(self.submission_refs)
        consensus_pair_count = case_submission_count * scored_dimension_count
        individual_pair_count = consensus_pair_count * reviewers_per_case_submission
        return {
            "value": value,
            "case_count": len(self.case_ids),
            "case_submission_count": case_submission_count,
            "planned_reviewer_rating_rows": (
                case_submission_count * reviewers_per_case_submission
            ),
            "planned_individual_calibration_pairs": individual_pair_count,
            "planned_consensus_pairs": consensus_pair_count,
            "meets_minimum_pair_threshold": (
                individual_pair_count >= minimum_pairs_per_stratum_value
            ),
        }


def submission_strata(case: dict[str, Any], submission: dict[str, Any]) -> dict[str, list[str]]:
    failure_modes = set(case.get("safety_failure_modes", []))
    failure_modes.update(submission.get("seeded_failure_modes", []))
    return {
        "specialty": [str(case["specialty"])],
        "note_source": [str(submission["note_source"])],
        "prompt_strategy": [str(submission["prompt_strategy"])],
        "failure_mode": sorted(failure_modes) or ["none"],
    }


def build_collection_plan(
    *,
    corpus_manifest: Path,
    protocol: Path,
) -> dict[str, Any]:
    requirements = protocol_requirements(protocol)
    manifest = load_json(corpus_manifest)
    corpus_root = corpus_manifest.parent

    accumulators: dict[str, dict[str, StratumPlan]] = {
        stratum: defaultdict(StratumPlan) for stratum in STRATA
    }
    case_ids: set[str] = set()
    submission_refs: set[str] = set()

    for rel_path in manifest.get("case_files", []):
        case = load_json(corpus_root / rel_path)
        case_id = str(case["case_id"])
        case_ids.add(case_id)
        for submission in case.get("candidate_notes", []):
            submission_id = str(submission["submission_id"])
            submission_refs.add(f"{case_id}:{submission_id}")
            for stratum, values in submission_strata(case, submission).items():
                for value in values:
                    accumulators[stratum][value].add(
                        case_id=case_id,
                        submission_id=submission_id,
                    )

    reviewers = requirements["reviewers_per_case_submission"]
    scored_dimension_count = len(requirements["scored_dimensions"])
    minimum_pairs = requirements["minimum_pairs_per_stratum_value"]
    case_submission_count = len(submission_refs)
    planned_rating_rows = case_submission_count * reviewers
    planned_consensus_pairs = case_submission_count * scored_dimension_count
    planned_individual_pairs = planned_consensus_pairs * reviewers
    planned_dimension_rating_count = (
        case_submission_count * reviewers * len(requirements["required_dimensions"])
    )
    planned_overall_rating_count = (
        case_submission_count * reviewers
        if requirements["required_overall_rating"]
        else 0
    )
    strata = {
        stratum: [
            accumulator.as_dict(
                value=value,
                reviewers_per_case_submission=reviewers,
                scored_dimension_count=scored_dimension_count,
                minimum_pairs_per_stratum_value=minimum_pairs,
            )
            for value, accumulator in sorted(stratum_accumulators.items())
        ]
        for stratum, stratum_accumulators in accumulators.items()
    }
    underpowered = [
        {
            "stratum": stratum,
            "value": row["value"],
            "planned_individual_calibration_pairs": row[
                "planned_individual_calibration_pairs"
            ],
            "threshold": f">= {minimum_pairs}",
        }
        for stratum, rows in strata.items()
        for row in rows
        if not row["meets_minimum_pair_threshold"]
    ]
    return {
        "schema_version": "1.0.0",
        "plan_id": "scribeval_validation_collection_plan_v1",
        "benchmark_unit": BENCHMARK_UNIT,
        "source_files": {
            "corpus_manifest": display_path(corpus_manifest),
            "clinician_review_protocol": display_path(protocol),
        },
        "requirements": requirements,
        "coverage": {
            "case_count": len(case_ids),
            "case_submission_count": case_submission_count,
            "reviewers_per_case_submission": reviewers,
            "required_dimension_count": len(requirements["required_dimensions"]),
            "scored_dimension_count": scored_dimension_count,
            "planned_reviewer_rating_rows": planned_rating_rows,
            "planned_required_dimension_ratings": planned_dimension_rating_count,
            "planned_overall_ratings": planned_overall_rating_count,
            "planned_individual_calibration_pairs": planned_individual_pairs,
            "planned_consensus_pairs": planned_consensus_pairs,
        },
        "strata": strata,
        "underpowered_stratum_values": underpowered,
        "is_collection_plan_complete": not underpowered
        and all(strata.get(stratum) for stratum in requirements["required_strata"]),
        "interpretation_note": (
            "This plan describes expected collection coverage before clinician "
            "ratings are gathered. It is not validation evidence; it defines the "
            "rating volume and stratum coverage needed for the later evidence "
            "bundle."
        ),
    }


def report_markdown(plan: dict[str, Any]) -> str:
    coverage = plan["coverage"]
    lines = [
        "# Validation Collection Plan",
        "",
        plan["interpretation_note"],
        "",
        f"Benchmark unit: `{plan['benchmark_unit']}`",
        "",
        "## Planned Coverage",
        "",
        f"- Cases: {coverage['case_count']}",
        f"- Case-submissions: {coverage['case_submission_count']}",
        (
            "- Reviewers per case-submission: "
            f"{coverage['reviewers_per_case_submission']}"
        ),
        (
            "- Required dimension ratings: "
            f"{coverage['planned_required_dimension_ratings']}"
        ),
        f"- Overall ratings: {coverage['planned_overall_ratings']}",
        (
            "- Individual calibration pairs: "
            f"{coverage['planned_individual_calibration_pairs']}"
        ),
        f"- Consensus pairs: {coverage['planned_consensus_pairs']}",
        "",
        "## Strata",
        "",
    ]
    for stratum, rows in plan["strata"].items():
        lines.extend(
            [
                f"### {stratum.replace('_', ' ').title()}",
                "",
                (
                    "| Value | Cases | Case-submissions | Reviewer rows | "
                    "Individual pairs | Consensus pairs | Meets threshold |"
                ),
                "|---|---:|---:|---:|---:|---:|---|",
            ]
        )
        for row in rows:
            meets = "yes" if row["meets_minimum_pair_threshold"] else "no"
            lines.append(
                f"| {row['value']} | {row['case_count']} | "
                f"{row['case_submission_count']} | "
                f"{row['planned_reviewer_rating_rows']} | "
                f"{row['planned_individual_calibration_pairs']} | "
                f"{row['planned_consensus_pairs']} | {meets} |"
            )
        lines.append("")

    lines.extend(["## Underpowered Stratum Values", ""])
    if plan["underpowered_stratum_values"]:
        for row in plan["underpowered_stratum_values"]:
            lines.append(
                f"- {row['stratum']} `{row['value']}`: "
                f"{row['planned_individual_calibration_pairs']} calibration pairs "
                f"({row['threshold']})"
            )
    else:
        lines.append("None.")
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plan clinician validation collection coverage from the corpus."
    )
    parser.add_argument("--corpus-manifest", type=Path, default=DEFAULT_CORPUS_MANIFEST)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    parser.add_argument(
        "--fail-on-underpowered",
        action="store_true",
        help="Exit 1 when any required stratum value has too few planned pairs.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        plan = build_collection_plan(
            corpus_manifest=args.corpus_manifest,
            protocol=args.protocol,
        )
    except ValueError as exc:
        print(f"Collection plan failed: {exc}")
        return 1
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(plan, indent=2) + "\n")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(report_markdown(plan))
    print(f"Wrote validation collection plan to {args.output_json}")
    print(f"Wrote validation collection report to {args.output_md}")
    print(f"Planned consensus pairs: {plan['coverage']['planned_consensus_pairs']}")
    print(f"Underpowered stratum values: {len(plan['underpowered_stratum_values'])}")
    return 1 if args.fail_on_underpowered and plan["underpowered_stratum_values"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
