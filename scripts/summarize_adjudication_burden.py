"""Summarize unresolved adjudication burden in consensus validation pairs."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE_MANIFEST = (
    ROOT / "validation_pack" / "evidence_runs" / "synthetic_bootstrap_v1" / "evidence_manifest.json"
)
BENCHMARK_UNIT = "whole transcript -> final note quality score"
STRATA = ("dimension", "specialty", "note_source", "prompt_strategy", "failure_mode")


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


def display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.name


def round_metric(value: float) -> float:
    rounded = round(value, 4)
    return 0.0 if rounded == 0 else rounded


def load_corpus_index(corpus_manifest_path: Path) -> dict[str, Any]:
    manifest = load_json(corpus_manifest_path)
    corpus_root = corpus_manifest_path.parent
    cases: dict[str, dict[str, Any]] = {}
    submissions: dict[tuple[str, str], dict[str, Any]] = {}
    for rel_path in manifest["case_files"]:
        case = load_json(corpus_root / rel_path)
        cases[case["case_id"]] = case
        for submission in case["candidate_notes"]:
            submissions[(case["case_id"], submission["submission_id"])] = submission
    return {"cases": cases, "submissions": submissions}


class BurdenAccumulator:
    def __init__(self) -> None:
        self.case_ids: set[str] = set()
        self.submission_refs: set[str] = set()
        self.total_count = 0
        self.required_count = 0
        self.score_range_total = 0.0
        self.severity_gap_counts: Counter[int] = Counter()

    def add(self, pair: dict[str, Any]) -> None:
        self.case_ids.add(str(pair["case_id"]))
        self.submission_refs.add(f"{pair['case_id']}:{pair['submission_id']}")
        self.total_count += 1
        if pair.get("adjudication_required") is True:
            self.required_count += 1
            self.score_range_total += float(pair.get("reviewer_score_range", 0.0))
            self.severity_gap_counts[int(pair.get("reviewer_severity_gap", 0))] += 1

    def as_dict(self, value: str) -> dict[str, Any]:
        return {
            "value": value,
            "case_count": len(self.case_ids),
            "submission_count": len(self.submission_refs),
            "consensus_pair_count": self.total_count,
            "adjudication_required_count": self.required_count,
            "adjudication_required_rate": round_metric(
                self.required_count / self.total_count if self.total_count else 0.0
            ),
            "mean_reviewer_score_range_when_required": round_metric(
                self.score_range_total / self.required_count if self.required_count else 0.0
            ),
            "reviewer_severity_gap_counts": {
                str(gap): count for gap, count in sorted(self.severity_gap_counts.items())
            },
        }


def failure_modes_for_pair(
    pair: dict[str, Any],
    corpus_index: dict[str, Any],
) -> list[str]:
    case = corpus_index["cases"][pair["case_id"]]
    submission = corpus_index["submissions"][(pair["case_id"], pair["submission_id"])]
    failure_modes = set(case.get("safety_failure_modes", []))
    failure_modes.update(submission.get("seeded_failure_modes", []))
    return sorted(failure_modes) or ["none"]


def pair_strata(pair: dict[str, Any], corpus_index: dict[str, Any]) -> dict[str, list[str]]:
    case = corpus_index["cases"][pair["case_id"]]
    submission = corpus_index["submissions"][(pair["case_id"], pair["submission_id"])]
    return {
        "dimension": [str(pair["dimension"])],
        "specialty": [case["specialty"]],
        "note_source": [submission["note_source"]],
        "prompt_strategy": [submission["prompt_strategy"]],
        "failure_mode": failure_modes_for_pair(pair, corpus_index),
    }


def summarize_burden(
    *,
    evidence_manifest_path: Path,
    consensus_pairs_path: Path,
    corpus_manifest_path: Path,
) -> dict[str, Any]:
    manifest = load_json(evidence_manifest_path)
    consensus_pairs = load_json(consensus_pairs_path)
    if not isinstance(consensus_pairs, list) or not consensus_pairs:
        raise ValueError("Consensus pairs must be a non-empty JSON list")
    corpus_index = load_corpus_index(corpus_manifest_path)
    accumulators: dict[str, dict[str, BurdenAccumulator]] = {
        stratum: defaultdict(BurdenAccumulator) for stratum in STRATA
    }
    overall = BurdenAccumulator()
    for pair in consensus_pairs:
        if not isinstance(pair, dict):
            raise ValueError("Consensus pair rows must be JSON objects")
        overall.add(pair)
        for stratum, values in pair_strata(pair, corpus_index).items():
            for value in values:
                accumulators[stratum][value].add(pair)

    return {
        "schema_version": "1.0.0",
        "summary_id": "adjudication_burden_summary_v1",
        "evidence_id": manifest.get("evidence_id"),
        "evidence_status": manifest.get("status"),
        "benchmark_unit": BENCHMARK_UNIT,
        "source_files": {
            "evidence_manifest": display_path(evidence_manifest_path),
            "consensus_calibration_pairs": display_path(consensus_pairs_path),
            "corpus_manifest": display_path(corpus_manifest_path),
        },
        "privacy_note": (
            "This summary contains aggregate adjudication counts only. It excludes "
            "reviewer identifiers, reviewer comments, transcript text, and candidate "
            "note text."
        ),
        "coverage": overall.as_dict("overall"),
        "strata": {
            stratum: [
                accumulator.as_dict(value)
                for value, accumulator in sorted(stratum_accumulators.items())
            ]
            for stratum, stratum_accumulators in accumulators.items()
        },
    }


def summarize_from_manifest(evidence_manifest_path: Path) -> dict[str, Any]:
    manifest = load_json(evidence_manifest_path)
    return summarize_burden(
        evidence_manifest_path=evidence_manifest_path,
        consensus_pairs_path=resolve_manifest_path(
            evidence_manifest_path,
            manifest["consensus_calibration_pairs"],
        ),
        corpus_manifest_path=resolve_manifest_path(
            evidence_manifest_path,
            manifest["corpus_manifest"],
        ),
    )


def report_markdown(summary: dict[str, Any]) -> str:
    coverage = summary["coverage"]
    lines = [
        "# Adjudication Burden Summary",
        "",
        "This report summarizes unresolved consensus-rating disagreements that need",
        "qualified adjudicator review before strong validation claims.",
        "",
        summary["privacy_note"],
        "",
        "## Coverage",
        "",
        f"- Consensus pairs: {coverage['consensus_pair_count']}",
        f"- Adjudication required: {coverage['adjudication_required_count']}",
        f"- Adjudication required rate: {coverage['adjudication_required_rate']:.3f}",
        (
            "- Mean reviewer score range when required: "
            f"{coverage['mean_reviewer_score_range_when_required']:.3f}"
        ),
        "",
    ]
    for stratum, rows in summary["strata"].items():
        lines.extend(
            [
                f"## {stratum.replace('_', ' ').title()}",
                "",
                (
                    "| Value | Cases | Submissions | Consensus pairs | Required | "
                    "Required rate | Mean score range | Severity gaps |"
                ),
                "|---|---:|---:|---:|---:|---:|---:|---|",
            ]
        )
        for row in rows:
            severity_gaps = ", ".join(
                f"{gap}: {count}"
                for gap, count in row["reviewer_severity_gap_counts"].items()
            )
            lines.append(
                "| {value} | {case_count} | {submission_count} | {consensus_pair_count} | "
                "{adjudication_required_count} | {adjudication_required_rate:.3f} | "
                "{mean_reviewer_score_range_when_required:.3f} | {severity_gaps} |".format(
                    **row,
                    severity_gaps=severity_gaps or "none",
                )
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize unresolved adjudication burden for an evidence bundle."
    )
    parser.add_argument(
        "--evidence-manifest",
        type=Path,
        default=DEFAULT_EVIDENCE_MANIFEST,
    )
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-md", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        summary = summarize_from_manifest(args.evidence_manifest)
    except ValueError as exc:
        print(f"Adjudication burden summary failed: {exc}", file=sys.stderr)
        return 1
    write_json(args.output_json, summary)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(report_markdown(summary))
    print(f"Wrote adjudication burden summary to {args.output_json}")
    print(f"Wrote adjudication burden report to {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
