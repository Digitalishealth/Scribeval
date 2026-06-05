"""Audit the public validation corpus and evidence trail.

This script is intentionally dependency-free so it can run in CI and by
clinician/governance reviewers without an API key. It verifies that the
validation corpus is internally reproducible: case manifests resolve, blinded
submissions are within Scribeval's supported range, and evidence pairs point to
real case/submission IDs with valid scores and severity labels.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "validation_pack"
CORPUS = PACK / "corpus"
EVIDENCE = PACK / "evidence"

VALID_DIMENSIONS = {
    "ahpra",
    "hallucination",
    "medicolegal",
    "medication_terminology",
    "omission",
    "pdqi9",
    "qnote",
}
VALID_SEVERITIES = {"none", "low", "moderate", "high", "critical"}


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise AssertionError(f"{path} is not valid JSON: {exc}") from exc


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def audit_corpus() -> dict[str, set[str]]:
    manifest_path = CORPUS / "corpus_manifest.json"
    manifest = load_json(manifest_path)
    case_files = manifest.get("case_files")
    require(isinstance(case_files, list) and case_files, "corpus_manifest has no case_files")
    require(
        manifest.get("current_case_count") == len(case_files),
        "current_case_count does not match case_files length",
    )
    min_submissions, max_submissions = manifest.get("required_submission_range", [0, 0])
    require(min_submissions == 2 and max_submissions == 5, "submission range must be 2 to 5")

    case_ids: set[str] = set()
    submission_refs: set[str] = set()
    note_sources: set[str] = set()
    prompt_strategies: set[str] = set()
    failure_modes: set[str] = set()

    for rel_path in case_files:
        case_path = CORPUS / rel_path
        require(case_path.exists(), f"missing case file: {rel_path}")
        case = load_json(case_path)
        case_id = case.get("case_id")
        require(isinstance(case_id, str) and case_id, f"{rel_path} has no case_id")
        require(case_id not in case_ids, f"duplicate case_id: {case_id}")
        case_ids.add(case_id)

        transcript = case.get("transcript")
        require(isinstance(transcript, list) and transcript, f"{case_id} has no transcript")
        for turn in transcript:
            require(
                turn.get("speaker") and turn.get("text"),
                f"{case_id} has invalid transcript turn",
            )

        submissions = case.get("candidate_notes")
        valid_submission_count = (
            isinstance(submissions, list)
            and min_submissions <= len(submissions) <= max_submissions
        )
        require(
            valid_submission_count,
            f"{case_id} must define {min_submissions} to {max_submissions} candidate_notes",
        )
        seen_submission_ids: set[str] = set()
        seen_blind_labels: set[str] = set()
        for submission in submissions:
            submission_id = submission.get("submission_id")
            blind_label = submission.get("blind_label")
            require(submission_id and blind_label, f"{case_id} has unlabelled submission")
            require(
                submission_id not in seen_submission_ids,
                f"{case_id} repeats submission_id {submission_id}",
            )
            require(
                blind_label not in seen_blind_labels,
                f"{case_id} repeats blind_label {blind_label}",
            )
            require(submission.get("note"), f"{case_id}/{submission_id} has empty note")
            require(submission.get("note_source"), f"{case_id}/{submission_id} has no note_source")
            require(
                submission.get("prompt_strategy"),
                f"{case_id}/{submission_id} has no prompt_strategy",
            )
            seen_submission_ids.add(submission_id)
            seen_blind_labels.add(blind_label)
            submission_refs.add(f"{case_id}:{submission_id}")
            note_sources.add(submission["note_source"])
            prompt_strategies.add(submission["prompt_strategy"])
            failure_modes.update(submission.get("seeded_failure_modes", []))
        failure_modes.update(case.get("safety_failure_modes", []))

    return {
        "case_ids": case_ids,
        "submission_refs": submission_refs,
        "note_sources": note_sources,
        "prompt_strategies": prompt_strategies,
        "failure_modes": failure_modes,
    }


def audit_evidence(corpus_refs: dict[str, set[str]]) -> int:
    manifest = load_json(EVIDENCE / "evidence_manifest.json")
    worksheet_path = EVIDENCE / manifest["reviewer_worksheet"]
    judge_scores_path = EVIDENCE / manifest["judge_scores"]
    pairs_path = EVIDENCE / manifest["calibration_pairs"]
    report_path = EVIDENCE / manifest["calibration_report"]
    require(worksheet_path.exists(), f"missing reviewer worksheet: {worksheet_path}")
    require(judge_scores_path.exists(), f"missing judge scores: {judge_scores_path}")
    require(pairs_path.exists(), f"missing calibration pairs: {pairs_path}")
    require(report_path.exists(), f"missing calibration report: {report_path}")

    pairs = load_json(pairs_path)
    require(isinstance(pairs, list) and pairs, "calibration pairs must be a non-empty list")
    referenced_cases: set[str] = set()
    referenced_submissions: set[str] = set()

    for index, pair in enumerate(pairs, start=1):
        case_id = pair.get("case_id")
        submission_id = pair.get("submission_id")
        blind_label = pair.get("blind_label")
        reviewer_id = pair.get("reviewer_id")
        reference = f"{case_id}:{submission_id}"
        require(blind_label, f"pair {index} has no blind_label")
        require(reviewer_id, f"pair {index} has no reviewer_id")
        require(
            case_id in corpus_refs["case_ids"],
            f"pair {index} references unknown case {case_id}",
        )
        require(
            reference in corpus_refs["submission_refs"],
            f"pair {index} references unknown submission {reference}",
        )
        require(pair.get("dimension") in VALID_DIMENSIONS, f"pair {index} has invalid dimension")
        for score_field in ("judge_score", "human_score"):
            score = pair.get(score_field)
            require(isinstance(score, int | float), f"pair {index} {score_field} is not numeric")
            require(0 <= score <= 1, f"pair {index} {score_field} is outside 0..1")
        for severity_field in ("judge_severity", "human_severity"):
            require(
                pair.get(severity_field) in VALID_SEVERITIES,
                f"pair {index} {severity_field} is invalid",
            )
        referenced_cases.add(case_id)
        referenced_submissions.add(reference)

    require(
        referenced_cases == corpus_refs["case_ids"],
        "evidence pairs do not cover every corpus case",
    )
    return len(pairs)


def main() -> int:
    try:
        corpus_refs = audit_corpus()
        pair_count = audit_evidence(corpus_refs)
    except AssertionError as exc:
        print(f"Validation pack audit failed: {exc}", file=sys.stderr)
        return 1

    print("Validation pack audit passed.")
    print(f"Cases: {len(corpus_refs['case_ids'])}")
    print(f"Submissions: {len(corpus_refs['submission_refs'])}")
    print(f"Evidence pairs: {pair_count}")
    print(f"Note sources: {', '.join(sorted(corpus_refs['note_sources']))}")
    print(f"Prompt strategies: {', '.join(sorted(corpus_refs['prompt_strategies']))}")
    print(f"Failure modes: {', '.join(sorted(corpus_refs['failure_modes']))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
