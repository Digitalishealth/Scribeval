"""Convert blinded reviewer worksheets into Scribeval calibration pairs.

The clinician workflow starts in a spreadsheet because that is the least
fragile interface for independent reviewers. This script turns that worksheet
back into the JSON shape consumed by `scribeval calibrate`, while preserving
case IDs, blinded labels, submission IDs, dimensions, scores, and severity
ratings for audit.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS_MANIFEST = ROOT / "validation_pack" / "corpus" / "corpus_manifest.json"

DIMENSIONS = (
    "omission",
    "hallucination",
    "medicolegal",
    "ahpra",
    "pdqi9",
    "qnote",
    "medication_terminology",
)
VALID_SEVERITIES = {"none", "low", "moderate", "high", "critical"}


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} is not valid JSON: {exc}") from exc


def load_blind_label_map(corpus_manifest: Path) -> dict[tuple[str, str], str]:
    manifest = load_json(corpus_manifest)
    corpus_root = corpus_manifest.parent
    mapping: dict[tuple[str, str], str] = {}

    for rel_case_path in manifest.get("case_files", []):
        case = load_json(corpus_root / rel_case_path)
        case_id = case["case_id"]
        for submission in case.get("candidate_notes", []):
            key = (case_id, submission["blind_label"])
            if key in mapping:
                raise ValueError(f"Duplicate blind label mapping for {case_id}/{key[1]}")
            mapping[key] = submission["submission_id"]
    return mapping


def load_judge_scores(judge_scores_path: Path) -> dict[tuple[str, str, str], dict[str, Any]]:
    raw_scores = load_json(judge_scores_path)
    if not isinstance(raw_scores, list):
        raise ValueError("Judge scores must be a list of score objects")

    scores: dict[tuple[str, str, str], dict[str, Any]] = {}
    for index, item in enumerate(raw_scores, start=1):
        case_id = item.get("case_id")
        submission_id = item.get("submission_id")
        dimension = item.get("dimension")
        if not case_id or not submission_id or not dimension:
            raise ValueError(f"Judge score {index} is missing case_id/submission_id/dimension")
        key = (case_id, submission_id, dimension)
        if key in scores:
            raise ValueError(f"Duplicate judge score for {case_id}/{submission_id}/{dimension}")
        validate_score(item.get("judge_score"), f"judge score {index}")
        validate_severity(item.get("judge_severity"), f"judge score {index}")
        scores[key] = item
    return scores


def validate_score(value: Any, label: str) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} is not numeric") from exc
    if not 0 <= score <= 1:
        raise ValueError(f"{label} must be between 0 and 1")
    return score


def validate_severity(value: Any, label: str) -> str:
    severity = str(value)
    if severity not in VALID_SEVERITIES:
        raise ValueError(f"{label} severity must be one of {sorted(VALID_SEVERITIES)}")
    return severity


def build_pairs(
    worksheet_path: Path,
    judge_scores: dict[tuple[str, str, str], dict[str, Any]],
    blind_label_map: dict[tuple[str, str], str],
) -> list[dict[str, Any]]:
    pairs: list[dict[str, Any]] = []
    with worksheet_path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row_index, row in enumerate(reader, start=2):
            case_id = row.get("case_id", "").strip()
            blind_label = row.get("blinded_submission", "").strip()
            reviewer_id = row.get("reviewer_id", "").strip()
            if not case_id or not blind_label:
                raise ValueError(f"Worksheet row {row_index} is missing case_id/blinded_submission")
            if not reviewer_id:
                continue

            submission_id = blind_label_map.get((case_id, blind_label))
            if submission_id is None:
                raise ValueError(
                    f"Worksheet row {row_index} references unknown "
                    f"{case_id}/{blind_label}"
                )

            for dimension in DIMENSIONS:
                score_text = row.get(f"{dimension}_score", "").strip()
                severity_text = row.get(f"{dimension}_severity", "").strip()
                if not score_text and not severity_text:
                    continue
                if not score_text or not severity_text:
                    raise ValueError(
                        f"Worksheet row {row_index} has incomplete {dimension} rating"
                    )
                human_score = validate_score(score_text, f"worksheet row {row_index} {dimension}")
                human_severity = validate_severity(
                    severity_text,
                    f"worksheet row {row_index} {dimension}",
                )
                judge_score = judge_scores.get((case_id, submission_id, dimension))
                if judge_score is None:
                    raise ValueError(
                        f"No judge score for worksheet row {row_index}: "
                        f"{case_id}/{submission_id}/{dimension}"
                    )
                pairs.append(
                    {
                        "case_id": case_id,
                        "submission_id": submission_id,
                        "blind_label": blind_label,
                        "reviewer_id": reviewer_id,
                        "dimension": dimension,
                        "judge_score": float(judge_score["judge_score"]),
                        "human_score": human_score,
                        "judge_severity": judge_score["judge_severity"],
                        "human_severity": human_severity,
                    }
                )
    if not pairs:
        raise ValueError("No complete reviewer ratings found in worksheet")
    return pairs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a blinded reviewer worksheet to calibration JSON."
    )
    parser.add_argument("--worksheet", required=True, type=Path)
    parser.add_argument("--judge-scores", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--corpus-manifest",
        type=Path,
        default=DEFAULT_CORPUS_MANIFEST,
        help="Path to validation corpus_manifest.json.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        blind_label_map = load_blind_label_map(args.corpus_manifest)
        judge_scores = load_judge_scores(args.judge_scores)
        pairs = build_pairs(args.worksheet, judge_scores, blind_label_map)
    except ValueError as exc:
        print(f"Import failed: {exc}", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(pairs, indent=2) + "\n")
    print(f"Wrote {len(pairs)} calibration pairs to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
