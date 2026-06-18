"""Build a stratified validation evidence summary from calibration pairs."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from scribeval.calibration import RatingPair, compute_agreement  # noqa: E402

DEFAULT_EVIDENCE_MANIFEST = ROOT / "validation_pack" / "evidence" / "evidence_manifest.json"

STRATA = ("specialty", "note_source", "prompt_strategy", "failure_mode")
MIN_AGREEMENT_PAIRS = 2


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def resolve_manifest_path(evidence_manifest: Path, manifest_value: str) -> Path:
    path = Path(manifest_value)
    if path.is_absolute():
        return path
    return (evidence_manifest.parent / path).resolve()


def round_metric(value: float) -> float:
    rounded = round(value, 4)
    return 0.0 if rounded == 0 else rounded


def clean_metric(value: float) -> float:
    return 0.0 if value == 0 else value


def display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


class StratumAccumulator:
    def __init__(self) -> None:
        self.case_ids: set[str] = set()
        self.submission_refs: set[str] = set()
        self.dimensions: set[str] = set()
        self.pair_count = 0
        self.abs_difference_total = 0.0
        self.severity_match_count = 0
        self.pairs: list[dict[str, Any]] = []

    def add(self, pair: dict[str, Any]) -> None:
        self.case_ids.add(pair["case_id"])
        self.submission_refs.add(f"{pair['case_id']}:{pair['submission_id']}")
        self.dimensions.add(pair["dimension"])
        self.pair_count += 1
        self.abs_difference_total += abs(float(pair["judge_score"]) - float(pair["human_score"]))
        if pair["judge_severity"] == pair["human_severity"]:
            self.severity_match_count += 1
        self.pairs.append(pair)

    def as_dict(self, value: str) -> dict[str, Any]:
        dimension_agreement = agreement_by_dimension(self.pairs)
        return {
            "value": value,
            "case_count": len(self.case_ids),
            "submission_count": len(self.submission_refs),
            "pair_count": self.pair_count,
            "dimension_count": len(self.dimensions),
            "dimensions": sorted(self.dimensions),
            "mean_abs_difference": round_metric(
                self.abs_difference_total / self.pair_count if self.pair_count else 0.0
            ),
            "severity_exact_agreement": round_metric(
                self.severity_match_count / self.pair_count if self.pair_count else 0.0
            ),
            "minimum_weighted_kappa": minimum_metric(
                dimension_agreement,
                "weighted_kappa",
            ),
            "minimum_icc_2_1": minimum_metric(dimension_agreement, "icc_2_1"),
            "agreement_by_dimension": dimension_agreement,
        }


def agreement_by_dimension(pairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rating_pairs = [
        RatingPair(
            dimension=str(pair["dimension"]),
            judge_score=float(pair["judge_score"]),
            human_score=float(pair["human_score"]),
            judge_severity=str(pair["judge_severity"]),
            human_severity=str(pair["human_severity"]),
        )
        for pair in pairs
    ]
    rows: list[dict[str, Any]] = []
    for agreement in compute_agreement(rating_pairs):
        enough_pairs = agreement.n_pairs >= MIN_AGREEMENT_PAIRS
        rows.append(
            {
                "dimension": agreement.dimension,
                "n_pairs": agreement.n_pairs,
                "weighted_kappa": clean_metric(agreement.kappa) if enough_pairs else None,
                "kappa_interpretation": (
                    agreement.interpret_kappa() if enough_pairs else "insufficient_pairs"
                ),
                "icc_2_1": clean_metric(agreement.icc) if enough_pairs else None,
                "mean_abs_difference": agreement.mean_abs_difference,
                "judge_mean": clean_metric(agreement.judge_mean),
                "human_mean": clean_metric(agreement.human_mean),
            }
        )
    return rows


def minimum_metric(rows: list[dict[str, Any]], field: str) -> float | None:
    values = [row[field] for row in rows if isinstance(row.get(field), int | float)]
    return min(values) if values else None


def format_optional_metric(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def load_corpus_index(corpus_manifest_path: Path) -> dict[str, Any]:
    manifest = load_json(corpus_manifest_path)
    corpus_root = corpus_manifest_path.parent
    case_index: dict[str, dict[str, Any]] = {}
    submission_index: dict[tuple[str, str], dict[str, Any]] = {}
    failure_modes: set[str] = set()

    for rel_path in manifest["case_files"]:
        case = load_json(corpus_root / rel_path)
        case_index[case["case_id"]] = case
        failure_modes.update(case.get("safety_failure_modes", []))
        for submission in case["candidate_notes"]:
            submission_index[(case["case_id"], submission["submission_id"])] = submission
            failure_modes.update(submission.get("seeded_failure_modes", []))

    return {
        "case_index": case_index,
        "submission_index": submission_index,
        "failure_modes": failure_modes,
    }


def pair_stratum_values(pair: dict[str, Any], corpus_index: dict[str, Any]) -> dict[str, list[str]]:
    case = corpus_index["case_index"][pair["case_id"]]
    submission = corpus_index["submission_index"][(pair["case_id"], pair["submission_id"])]
    failure_modes = set(case.get("safety_failure_modes", []))
    failure_modes.update(submission.get("seeded_failure_modes", []))
    return {
        "specialty": [case["specialty"]],
        "note_source": [submission["note_source"]],
        "prompt_strategy": [submission["prompt_strategy"]],
        "failure_mode": sorted(failure_modes) or ["none"],
    }


def summarize(evidence_manifest_path: Path) -> dict[str, Any]:
    manifest = load_json(evidence_manifest_path)
    corpus_manifest_path = resolve_manifest_path(
        evidence_manifest_path,
        manifest["corpus_manifest"],
    )
    pairs_path = resolve_manifest_path(evidence_manifest_path, manifest["calibration_pairs"])
    pairs = load_json(pairs_path)
    corpus_index = load_corpus_index(corpus_manifest_path)

    accumulators: dict[str, dict[str, StratumAccumulator]] = {
        stratum: defaultdict(StratumAccumulator) for stratum in STRATA
    }
    submission_refs: set[str] = set()
    dimensions: set[str] = set()

    for pair in pairs:
        submission_ref = f"{pair['case_id']}:{pair['submission_id']}"
        submission_refs.add(submission_ref)
        dimensions.add(pair["dimension"])
        for stratum, values in pair_stratum_values(pair, corpus_index).items():
            for value in values:
                accumulators[stratum][value].add(pair)

    strata = {
        stratum: [
            accumulator.as_dict(value)
            for value, accumulator in sorted(stratum_accumulators.items())
        ]
        for stratum, stratum_accumulators in accumulators.items()
    }
    return {
        "schema_version": "1.0.0",
        "summary_id": "stratified_evidence_summary_v0",
        "evidence_id": manifest["evidence_id"],
        "evidence_status": manifest["status"],
        "disclaimer": manifest["disclaimer"],
        "benchmark_unit": "whole transcript -> final note quality score",
        "source_files": {
            "evidence_manifest": display_path(evidence_manifest_path),
            "corpus_manifest": display_path(corpus_manifest_path),
            "calibration_pairs": display_path(pairs_path),
        },
        "coverage": {
            "case_count": len(corpus_index["case_index"]),
            "submission_count": len(submission_refs),
            "pair_count": len(pairs),
            "dimension_count": len(dimensions),
            "dimensions": sorted(dimensions),
        },
        "strata": strata,
    }


def report_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Stratified Validation Evidence Summary v0",
        "",
        "This report links calibration pairs back to corpus metadata so agreement",
        "coverage can be reviewed by specialty, note source, prompt strategy, and",
        "safety-critical failure mode.",
        "",
        summary["disclaimer"],
        "",
        "## Coverage",
        "",
        f"- Cases: {summary['coverage']['case_count']}",
        f"- Submissions with evidence pairs: {summary['coverage']['submission_count']}",
        f"- Evidence pairs: {summary['coverage']['pair_count']}",
        f"- Dimensions: {', '.join(summary['coverage']['dimensions'])}",
        "",
    ]
    for stratum, rows in summary["strata"].items():
        lines.extend(
            [
                f"## {stratum.replace('_', ' ').title()}",
                "",
                (
                    "| Value | Cases | Submissions | Pairs | Dimensions | "
                    "Mean abs diff | Severity exact agreement | Min weighted kappa | "
                    "Min ICC(2,1) |"
                ),
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for row in rows:
            lines.append(
                "| {value} | {case_count} | {submission_count} | {pair_count} | "
                "{dimension_count} | {mean_abs_difference:.3f} | "
                "{severity_exact_agreement:.3f} | {minimum_weighted_kappa} | "
                "{minimum_icc_2_1} |".format(
                    **{
                        **row,
                        "minimum_weighted_kappa": format_optional_metric(
                            row["minimum_weighted_kappa"]
                        ),
                        "minimum_icc_2_1": format_optional_metric(row["minimum_icc_2_1"]),
                    }
                )
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize validation evidence by corpus metadata strata."
    )
    parser.add_argument(
        "--evidence-manifest",
        type=Path,
        default=DEFAULT_EVIDENCE_MANIFEST,
        help="Path to validation_pack/evidence/evidence_manifest.json.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=ROOT / "validation_pack" / "evidence" / "stratified_summary_v0.json",
        help="Path for the stratified summary JSON.",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=ROOT / "validation_pack" / "evidence" / "stratified_summary_v0.md",
        help="Path for the stratified summary Markdown report.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = summarize(args.evidence_manifest)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(summary, indent=2) + "\n")
    args.output_md.write_text(report_markdown(summary))
    print(f"Wrote stratified evidence summary to {args.output_json}")
    print(f"Wrote stratified evidence report to {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
