"""Build consensus clinician calibration pairs from reviewer worksheets.

This produces a judge-vs-consensus clinician evidence layer. It does not
replace individual reviewer ratings or reviewer reliability; it adds a cleaner
clinical comparator for agreement reporting and flags disagreements that need
adjudication.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
for path in (SRC, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from audit_clinician_review_readiness import DEFAULT_PROTOCOL, load_protocol  # noqa: E402
from import_validation_ratings import load_judge_scores  # noqa: E402
from summarize_reviewer_reliability import (  # noqa: E402
    DEFAULT_CORPUS_MANIFEST,
    load_corpus_index,
    load_ratings,
    parse_dimensions,
)

from scribeval.calibration import RatingPair, compute_agreement  # noqa: E402
from scribeval.models.score import SeverityLevel  # noqa: E402

BENCHMARK_UNIT = "whole transcript -> final note quality score"
SEVERITY_ORDER = [severity.value for severity in SeverityLevel]
SEVERITY_INDEX = {severity: index for index, severity in enumerate(SEVERITY_ORDER)}


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def consensus_severity(severities: list[str]) -> tuple[str, str]:
    counts = Counter(severities)
    most_common = counts.most_common()
    if len(most_common) == 1:
        return most_common[0][0], "unanimous"
    top_count = most_common[0][1]
    top_values = [severity for severity, count in most_common if count == top_count]
    if len(top_values) == 1:
        return top_values[0], "majority"
    return max(top_values, key=lambda severity: SEVERITY_INDEX[severity]), "conservative_tie"


def adjudication_required(
    *,
    scores: list[float],
    severities: list[str],
    score_disagreement_threshold: float,
) -> bool:
    severity_gap = max(SEVERITY_INDEX[severity] for severity in severities) - min(
        SEVERITY_INDEX[severity] for severity in severities
    )
    score_gap = max(scores) - min(scores)
    return severity_gap > 0 or score_gap >= score_disagreement_threshold


def build_consensus_pairs(
    *,
    worksheet: Path,
    reviewer_registry: Path,
    judge_scores_path: Path,
    corpus_manifest: Path,
    protocol: Path,
    dimensions: tuple[str, ...] | None = None,
    minimum_reviewers: int | None = None,
    score_disagreement_threshold: float = 0.15,
) -> list[dict[str, Any]]:
    selected_dimensions = dimensions or parse_dimensions(None, protocol)
    required_reviewers = minimum_reviewers or int(
        load_protocol(protocol)["reviewers_per_submission"]
    )
    corpus_index = load_corpus_index(corpus_manifest)
    judge_scores = load_judge_scores(judge_scores_path)
    ratings = load_ratings(
        worksheet=worksheet,
        reviewer_registry=reviewer_registry,
        corpus_index=corpus_index,
        dimensions=selected_dimensions,
    )

    pairs: list[dict[str, Any]] = []
    for (case_id, blind_label, dimension), reviewer_ratings in sorted(ratings.items()):
        if len(reviewer_ratings) < required_reviewers:
            continue
        submission = corpus_index["submissions_by_blind_label"][(case_id, blind_label)]
        submission_id = submission["submission_id"]
        judge_score = judge_scores.get((case_id, submission_id, dimension))
        if judge_score is None:
            raise ValueError(f"No judge score for {case_id}/{submission_id}/{dimension}")

        reviewer_ids = sorted(reviewer_ratings)
        scores = [
            float(reviewer_ratings[reviewer_id]["score"]) for reviewer_id in reviewer_ids
        ]
        severities = [
            str(reviewer_ratings[reviewer_id]["severity"]) for reviewer_id in reviewer_ids
        ]
        severity, severity_method = consensus_severity(severities)
        score_gap = round(max(scores) - min(scores), 4)
        severity_gap = max(SEVERITY_INDEX[item] for item in severities) - min(
            SEVERITY_INDEX[item] for item in severities
        )
        needs_adjudication = adjudication_required(
            scores=scores,
            severities=severities,
            score_disagreement_threshold=score_disagreement_threshold,
        )
        pairs.append(
            {
                "case_id": case_id,
                "submission_id": submission_id,
                "blind_label": blind_label,
                "dimension": dimension,
                "judge_score": float(judge_score["judge_score"]),
                "human_score": round(statistics.mean(scores), 4),
                "judge_severity": judge_score["judge_severity"],
                "human_severity": severity,
                "consensus_method": "mean_score_and_consensus_severity",
                "severity_consensus_method": severity_method,
                "reviewer_count": len(reviewer_ids),
                "reviewer_ids": reviewer_ids,
                "reviewer_score_min": min(scores),
                "reviewer_score_max": max(scores),
                "reviewer_score_range": score_gap,
                "reviewer_severity_values": sorted(set(severities)),
                "reviewer_severity_gap": severity_gap,
                "adjudication_required": needs_adjudication,
            }
        )
    if not pairs:
        raise ValueError("No consensus ratings could be built")
    return pairs


def consensus_summary(pairs: list[dict[str, Any]]) -> dict[str, Any]:
    case_ids = {pair["case_id"] for pair in pairs}
    submission_refs = {f"{pair['case_id']}:{pair['submission_id']}" for pair in pairs}
    dimensions = sorted({pair["dimension"] for pair in pairs})
    adjudication_required_count = sum(1 for pair in pairs if pair["adjudication_required"])
    rating_pairs = [
        RatingPair(
            dimension=pair["dimension"],
            judge_score=float(pair["judge_score"]),
            human_score=float(pair["human_score"]),
            judge_severity=str(pair["judge_severity"]),
            human_severity=str(pair["human_severity"]),
        )
        for pair in pairs
    ]
    return {
        "schema_version": "1.0.0",
        "summary_id": "clinician_consensus_validation_ratings_v1",
        "benchmark_unit": BENCHMARK_UNIT,
        "coverage": {
            "case_count": len(case_ids),
            "submission_count": len(submission_refs),
            "consensus_pair_count": len(pairs),
            "dimension_count": len(dimensions),
            "dimensions": dimensions,
            "adjudication_required_count": adjudication_required_count,
        },
        "dimension_agreement": [
            {
                "dimension": agreement.dimension,
                "n_pairs": agreement.n_pairs,
                "weighted_kappa": agreement.kappa,
                "kappa_interpretation": agreement.interpret_kappa(),
                "icc_2_1": agreement.icc,
                "mean_abs_difference": agreement.mean_abs_difference,
                "judge_mean": agreement.judge_mean,
                "consensus_mean": agreement.human_mean,
            }
            for agreement in compute_agreement(rating_pairs)
        ],
        "interpretation_note": (
            "Consensus ratings average qualified clinician scores for each blinded "
            "case-submission-dimension and use consensus severity as the clinical "
            "comparator. Rows flagged for adjudication should be reviewed before "
            "strong validation claims are made."
        ),
    }


def report_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Clinician Consensus Validation Ratings",
        "",
        summary["interpretation_note"],
        "",
        "## Coverage",
        "",
        f"- Cases: {summary['coverage']['case_count']}",
        f"- Submissions: {summary['coverage']['submission_count']}",
        f"- Consensus pairs: {summary['coverage']['consensus_pair_count']}",
        f"- Adjudication required: {summary['coverage']['adjudication_required_count']}",
        f"- Dimensions: {', '.join(summary['coverage']['dimensions'])}",
        "",
        "## Judge vs Consensus Agreement",
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
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build consensus clinician calibration pairs from reviewer ratings."
    )
    parser.add_argument("--worksheet", required=True, type=Path)
    parser.add_argument("--reviewer-registry", required=True, type=Path)
    parser.add_argument("--judge-scores", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--output-summary-json", required=True, type=Path)
    parser.add_argument("--output-summary-md", required=True, type=Path)
    parser.add_argument("--corpus-manifest", type=Path, default=DEFAULT_CORPUS_MANIFEST)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument(
        "--dimensions",
        default=None,
        help="Comma-separated dimensions. Defaults to protocol required dimensions.",
    )
    parser.add_argument("--minimum-reviewers", type=int, default=None)
    parser.add_argument("--score-disagreement-threshold", type=float, default=0.15)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.minimum_reviewers is not None and args.minimum_reviewers < 2:
        print("Consensus build failed: --minimum-reviewers must be >= 2", file=sys.stderr)
        return 1
    if not 0 <= args.score_disagreement_threshold <= 1:
        print(
            "Consensus build failed: --score-disagreement-threshold must be between 0 and 1",
            file=sys.stderr,
        )
        return 1

    try:
        pairs = build_consensus_pairs(
            worksheet=args.worksheet,
            reviewer_registry=args.reviewer_registry,
            judge_scores_path=args.judge_scores,
            corpus_manifest=args.corpus_manifest,
            protocol=args.protocol,
            dimensions=parse_dimensions(args.dimensions, args.protocol),
            minimum_reviewers=args.minimum_reviewers,
            score_disagreement_threshold=args.score_disagreement_threshold,
        )
        summary = consensus_summary(pairs)
    except ValueError as exc:
        print(f"Consensus build failed: {exc}", file=sys.stderr)
        return 1

    write_json(args.output, pairs)
    write_json(args.output_summary_json, summary)
    args.output_summary_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_summary_md.write_text(report_markdown(summary))
    print(f"Wrote {len(pairs)} consensus calibration pairs to {args.output}")
    print(f"Wrote consensus summary to {args.output_summary_json}")
    print(f"Wrote consensus report to {args.output_summary_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
