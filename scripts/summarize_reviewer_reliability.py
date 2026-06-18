"""Summarize clinician reviewer inter-rater reliability.

Independent validation is only persuasive if the clinician comparator is
itself reliable. This script measures agreement between qualified reviewers
who scored the same blinded case-submission-dimension in a completed validation
worksheet.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
for path in (SRC, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from audit_clinician_review_readiness import (  # noqa: E402
    DEFAULT_PROTOCOL,
    audit_readiness,
    load_protocol,
)
from import_validation_ratings import (  # noqa: E402
    load_reviewer_registry,
    validate_qualified_reviewer,
    validate_score,
    validate_severity,
)

from scribeval.calibration import RatingPair, compute_agreement  # noqa: E402

DEFAULT_CORPUS_MANIFEST = ROOT / "validation_pack" / "corpus" / "corpus_manifest.json"
DEFAULT_PROTOCOL_PATH = DEFAULT_PROTOCOL
BENCHMARK_UNIT = "whole transcript -> final note quality score"
STRATA = ("specialty", "note_source", "prompt_strategy", "failure_mode")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} is not valid JSON: {exc}") from exc


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def parse_dimensions(raw_dimensions: str | None, protocol_path: Path) -> tuple[str, ...]:
    if raw_dimensions is not None:
        return tuple(item.strip() for item in raw_dimensions.split(",") if item.strip())
    protocol = load_protocol(protocol_path)
    dimensions = list(protocol["required_dimensions"])
    if protocol.get("required_overall_rating") and "overall" not in dimensions:
        dimensions.append("overall")
    return tuple(dimensions)


def load_corpus_index(corpus_manifest_path: Path) -> dict[str, Any]:
    manifest = load_json(corpus_manifest_path)
    corpus_root = corpus_manifest_path.parent
    cases: dict[str, dict[str, Any]] = {}
    submissions_by_blind_label: dict[tuple[str, str], dict[str, Any]] = {}

    for rel_path in manifest.get("case_files", []):
        case = load_json(corpus_root / rel_path)
        case_id = case["case_id"]
        cases[case_id] = case
        for submission in case.get("candidate_notes", []):
            submissions_by_blind_label[(case_id, submission["blind_label"])] = submission

    if not submissions_by_blind_label:
        raise ValueError("Corpus manifest did not resolve any blinded submissions")
    return {"cases": cases, "submissions_by_blind_label": submissions_by_blind_label}


def failure_modes_for_pair(
    pair: dict[str, Any],
    corpus_index: dict[str, Any],
) -> list[str]:
    case = corpus_index["cases"][pair["case_id"]]
    submission = corpus_index["submissions_by_blind_label"][
        (pair["case_id"], pair["blind_label"])
    ]
    failure_modes = set(case.get("safety_failure_modes", []))
    failure_modes.update(submission.get("seeded_failure_modes", []))
    return sorted(failure_modes) or ["none"]


def stratum_values(pair: dict[str, Any], corpus_index: dict[str, Any]) -> dict[str, list[str]]:
    case = corpus_index["cases"][pair["case_id"]]
    submission = corpus_index["submissions_by_blind_label"][
        (pair["case_id"], pair["blind_label"])
    ]
    return {
        "specialty": [case["specialty"]],
        "note_source": [submission["note_source"]],
        "prompt_strategy": [submission["prompt_strategy"]],
        "failure_mode": failure_modes_for_pair(pair, corpus_index),
    }


def load_ratings(
    *,
    worksheet: Path,
    reviewer_registry: Path,
    corpus_index: dict[str, Any],
    dimensions: tuple[str, ...],
) -> dict[tuple[str, str, str], dict[str, dict[str, Any]]]:
    registry = load_reviewer_registry(reviewer_registry)
    valid_submissions = set(corpus_index["submissions_by_blind_label"])
    ratings: dict[tuple[str, str, str], dict[str, dict[str, Any]]] = defaultdict(dict)

    with worksheet.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row_index, row in enumerate(reader, start=2):
            case_id = row.get("case_id", "").strip()
            blind_label = row.get("blinded_submission", "").strip()
            reviewer_id = row.get("reviewer_id", "").strip()
            if not case_id or not blind_label or not reviewer_id:
                continue
            if (case_id, blind_label) not in valid_submissions:
                raise ValueError(
                    f"Worksheet row {row_index} references unknown {case_id}/{blind_label}"
                )
            validate_qualified_reviewer(reviewer_id, registry, row_index=row_index)

            for dimension in dimensions:
                score_text = row.get(f"{dimension}_score", "").strip()
                severity_text = row.get(f"{dimension}_severity", "").strip()
                if not score_text and not severity_text:
                    continue
                if not score_text or not severity_text:
                    raise ValueError(
                        f"Worksheet row {row_index} has incomplete {dimension} rating"
                    )
                key = (case_id, blind_label, dimension)
                if reviewer_id in ratings[key]:
                    raise ValueError(
                        f"Duplicate reviewer rating for {case_id}/{blind_label}/"
                        f"{dimension}/{reviewer_id}"
                    )
                ratings[key][reviewer_id] = {
                    "score": validate_score(score_text, f"worksheet row {row_index} {dimension}"),
                    "severity": validate_severity(
                        severity_text,
                        f"worksheet row {row_index} {dimension}",
                    ),
                }
    return ratings


def build_reviewer_pairs(
    ratings: dict[tuple[str, str, str], dict[str, dict[str, Any]]],
    corpus_index: dict[str, Any],
) -> list[dict[str, Any]]:
    pairs: list[dict[str, Any]] = []
    for (case_id, blind_label, dimension), reviewer_ratings in sorted(ratings.items()):
        if len(reviewer_ratings) < 2:
            continue
        submission = corpus_index["submissions_by_blind_label"][(case_id, blind_label)]
        for reviewer_a, reviewer_b in combinations(sorted(reviewer_ratings), 2):
            rating_a = reviewer_ratings[reviewer_a]
            rating_b = reviewer_ratings[reviewer_b]
            pairs.append(
                {
                    "case_id": case_id,
                    "submission_id": submission["submission_id"],
                    "blind_label": blind_label,
                    "dimension": dimension,
                    "reviewer_a_id": reviewer_a,
                    "reviewer_b_id": reviewer_b,
                    "reviewer_a_score": rating_a["score"],
                    "reviewer_b_score": rating_b["score"],
                    "reviewer_a_severity": rating_a["severity"],
                    "reviewer_b_severity": rating_b["severity"],
                }
            )
    if not pairs:
        raise ValueError("No paired reviewer ratings found")
    return pairs


class StratumAccumulator:
    def __init__(self) -> None:
        self.case_ids: set[str] = set()
        self.submission_refs: set[str] = set()
        self.dimensions: set[str] = set()
        self.reviewer_pairs: set[tuple[str, str]] = set()
        self.pair_count = 0
        self.abs_difference_total = 0.0
        self.severity_match_count = 0

    def add(self, pair: dict[str, Any]) -> None:
        self.case_ids.add(pair["case_id"])
        self.submission_refs.add(f"{pair['case_id']}:{pair['submission_id']}")
        self.dimensions.add(pair["dimension"])
        self.reviewer_pairs.add((pair["reviewer_a_id"], pair["reviewer_b_id"]))
        self.pair_count += 1
        self.abs_difference_total += abs(
            float(pair["reviewer_a_score"]) - float(pair["reviewer_b_score"])
        )
        if pair["reviewer_a_severity"] == pair["reviewer_b_severity"]:
            self.severity_match_count += 1

    def as_dict(self, value: str) -> dict[str, Any]:
        return {
            "value": value,
            "case_count": len(self.case_ids),
            "submission_count": len(self.submission_refs),
            "reviewer_pair_count": len(self.reviewer_pairs),
            "pair_count": self.pair_count,
            "dimension_count": len(self.dimensions),
            "dimensions": sorted(self.dimensions),
            "mean_abs_difference": round(
                self.abs_difference_total / self.pair_count if self.pair_count else 0.0,
                4,
            ),
            "severity_exact_agreement": round(
                self.severity_match_count / self.pair_count if self.pair_count else 0.0,
                4,
            ),
        }


def dimension_agreements(pairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rating_pairs = [
        RatingPair(
            dimension=pair["dimension"],
            judge_score=float(pair["reviewer_a_score"]),
            human_score=float(pair["reviewer_b_score"]),
            judge_severity=pair["reviewer_a_severity"],
            human_severity=pair["reviewer_b_severity"],
        )
        for pair in pairs
    ]
    return [
        {
            "dimension": agreement.dimension,
            "n_pairs": agreement.n_pairs,
            "weighted_kappa": agreement.kappa,
            "kappa_interpretation": agreement.interpret_kappa(),
            "icc_2_1": agreement.icc,
            "mean_abs_difference": agreement.mean_abs_difference,
            "reviewer_a_mean": agreement.judge_mean,
            "reviewer_b_mean": agreement.human_mean,
        }
        for agreement in compute_agreement(rating_pairs)
    ]


def stratified_reliability(
    pairs: list[dict[str, Any]],
    corpus_index: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    accumulators: dict[str, dict[str, StratumAccumulator]] = {
        stratum: defaultdict(StratumAccumulator) for stratum in STRATA
    }
    for pair in pairs:
        for stratum, values in stratum_values(pair, corpus_index).items():
            for value in values:
                accumulators[stratum][value].add(pair)
    return {
        stratum: [
            accumulator.as_dict(value)
            for value, accumulator in sorted(stratum_accumulators.items())
        ]
        for stratum, stratum_accumulators in accumulators.items()
    }


def summarize_reviewer_reliability(
    *,
    worksheet: Path,
    reviewer_registry: Path,
    corpus_manifest: Path,
    protocol: Path,
    dimensions: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    selected_dimensions = dimensions or parse_dimensions(None, protocol)
    corpus_index = load_corpus_index(corpus_manifest)
    readiness = audit_readiness(
        worksheet_path=worksheet,
        reviewer_registry_path=reviewer_registry,
        corpus_manifest_path=corpus_manifest,
        protocol_path=protocol,
    )
    ratings = load_ratings(
        worksheet=worksheet,
        reviewer_registry=reviewer_registry,
        corpus_index=corpus_index,
        dimensions=selected_dimensions,
    )
    pairs = build_reviewer_pairs(ratings, corpus_index)
    reviewer_pair_ids = {
        tuple(sorted((pair["reviewer_a_id"], pair["reviewer_b_id"]))) for pair in pairs
    }
    submission_refs = {f"{pair['case_id']}:{pair['submission_id']}" for pair in pairs}
    case_ids = {pair["case_id"] for pair in pairs}

    return {
        "schema_version": "1.0.0",
        "report_id": "clinician_reviewer_reliability_v1",
        "benchmark_unit": BENCHMARK_UNIT,
        "source_files": {
            "worksheet": display_path(worksheet),
            "reviewer_registry": display_path(reviewer_registry),
            "corpus_manifest": display_path(corpus_manifest),
            "protocol": display_path(protocol),
        },
        "readiness": {
            "is_ready_for_independent_validation": readiness[
                "is_ready_for_independent_validation"
            ],
            "coverage": readiness["coverage"],
        },
        "coverage": {
            "case_count": len(case_ids),
            "submission_count": len(submission_refs),
            "reviewer_pair_count": len(reviewer_pair_ids),
            "reliability_pair_count": len(pairs),
            "dimension_count": len(selected_dimensions),
            "dimensions": list(selected_dimensions),
        },
        "dimension_agreement": dimension_agreements(pairs),
        "strata": stratified_reliability(pairs, corpus_index),
        "interpretation_note": (
            "Reviewer reliability describes agreement between clinician reviewers. "
            "Low reviewer reliability weakens judge-vs-clinician validation claims "
            "and should trigger rubric clarification, reviewer retraining, or "
            "adjudication before procurement or governance use."
        ),
    }


def report_markdown(summary: dict[str, Any]) -> str:
    status = (
        "ready"
        if summary["readiness"]["is_ready_for_independent_validation"]
        else "not ready"
    )
    lines = [
        "# Clinician Reviewer Reliability Report",
        "",
        summary["interpretation_note"],
        "",
        "## Coverage",
        "",
        f"- Readiness status: {status}",
        f"- Cases: {summary['coverage']['case_count']}",
        f"- Submissions: {summary['coverage']['submission_count']}",
        f"- Reviewer pairs: {summary['coverage']['reviewer_pair_count']}",
        f"- Reliability pairs: {summary['coverage']['reliability_pair_count']}",
        f"- Dimensions: {', '.join(summary['coverage']['dimensions'])}",
        "",
        "## Dimension Agreement",
        "",
        "| Dimension | N | Weighted kappa | Kappa interpretation | ICC(2,1) | Mean abs diff |",
        "|---|---:|---:|---|---:|---:|",
    ]
    for row in summary["dimension_agreement"]:
        lines.append(
            f"| {row['dimension']} | {row['n_pairs']} | "
            f"{row['weighted_kappa']:.3f} | {row['kappa_interpretation']} | "
            f"{row['icc_2_1']:.3f} | {row['mean_abs_difference']:.3f} |"
        )
    lines.append("")

    for stratum, rows in summary["strata"].items():
        lines.extend(
            [
                f"## {stratum.replace('_', ' ').title()}",
                "",
                (
                    "| Value | Cases | Submissions | Reviewer pairs | Pairs | "
                    "Dimensions | Mean abs diff | Severity exact agreement |"
                ),
                "|---|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for row in rows:
            lines.append(
                "| {value} | {case_count} | {submission_count} | {reviewer_pair_count} | "
                "{pair_count} | {dimension_count} | {mean_abs_difference:.3f} | "
                "{severity_exact_agreement:.3f} |".format(**row)
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize inter-rater reliability between clinician reviewers."
    )
    parser.add_argument("--worksheet", required=True, type=Path)
    parser.add_argument("--reviewer-registry", required=True, type=Path)
    parser.add_argument("--corpus-manifest", type=Path, default=DEFAULT_CORPUS_MANIFEST)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL_PATH)
    parser.add_argument(
        "--dimensions",
        default=None,
        help="Comma-separated dimensions. Defaults to protocol required dimensions.",
    )
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-md", required=True, type=Path)
    parser.add_argument(
        "--fail-on-not-ready",
        action="store_true",
        help="Exit 1 if readiness audit says the worksheet is not complete.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        summary = summarize_reviewer_reliability(
            worksheet=args.worksheet,
            reviewer_registry=args.reviewer_registry,
            corpus_manifest=args.corpus_manifest,
            protocol=args.protocol,
            dimensions=parse_dimensions(args.dimensions, args.protocol),
        )
    except ValueError as exc:
        print(f"Reviewer reliability summary failed: {exc}", file=sys.stderr)
        return 1

    write_json(args.output_json, summary)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(report_markdown(summary))

    print(f"Wrote reviewer reliability summary to {args.output_json}")
    print(f"Wrote reviewer reliability report to {args.output_md}")
    print(f"Reviewer reliability pairs: {summary['coverage']['reliability_pair_count']}")
    if args.fail_on_not_ready and not summary["readiness"]["is_ready_for_independent_validation"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
