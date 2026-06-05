"""Export Scribeval judge scores for the public validation corpus.

The clinician validation workflow needs a reproducible `judge_scores.json`
file before reviewer ratings can be converted into calibration pairs. This
script evaluates each corpus case submission through the normal Scribeval
pipeline and writes the strict score shape consumed by
`scripts/import_validation_ratings.py`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from scribeval import __version__  # noqa: E402
from scribeval.clients.fhir import FHIRTerminologyClient  # noqa: E402
from scribeval.config import get_settings  # noqa: E402
from scribeval.judges.base import BaseJudge  # noqa: E402
from scribeval.judges.llm import LLMJudge  # noqa: E402
from scribeval.models.case import (  # noqa: E402
    ConsultationType,
    EvaluationCase,
    ScribeNote,
    Transcript,
)
from scribeval.pipeline import EvaluationPipeline  # noqa: E402

DEFAULT_CORPUS_MANIFEST = ROOT / "validation_pack" / "corpus" / "corpus_manifest.json"
BENCHMARK_UNIT = "whole transcript -> final note quality score"


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} is not valid JSON: {exc}") from exc


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative_or_absolute(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def default_manifest_output(output: Path) -> Path:
    return output.with_name(f"{output.stem}_manifest.json")


def parse_dimensions(raw_dimensions: str | None) -> list[str]:
    settings = get_settings()
    if raw_dimensions is None:
        return list(settings.default_dimensions)
    dimensions = [dimension.strip() for dimension in raw_dimensions.split(",")]
    return [dimension for dimension in dimensions if dimension]


def format_transcript(turns: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for index, turn in enumerate(turns, start=1):
        speaker = str(turn.get("speaker", "")).strip()
        text = str(turn.get("text", "")).strip()
        if not speaker or not text:
            raise ValueError(f"Transcript turn {index} is missing speaker/text")
        lines.append(f"{speaker}: {text}")
    if not lines:
        raise ValueError("Transcript has no turns")
    return "\n".join(lines)


def iter_corpus_submissions(
    corpus_manifest: Path,
    *,
    case_ids: set[str] | None = None,
    submission_ids: set[str] | None = None,
    max_cases: int | None = None,
    max_submissions: int | None = None,
) -> list[tuple[dict[str, Any], dict[str, Any], Path]]:
    manifest = load_json(corpus_manifest)
    corpus_root = corpus_manifest.parent
    selected: list[tuple[dict[str, Any], dict[str, Any], Path]] = []
    seen_cases = 0

    for rel_case_path in manifest.get("case_files", []):
        case_path = corpus_root / rel_case_path
        case = load_json(case_path)
        case_id = case.get("case_id")
        if case_ids is not None and case_id not in case_ids:
            continue
        if max_cases is not None and seen_cases >= max_cases:
            break
        seen_cases += 1

        selected_for_case = 0
        for submission in case.get("candidate_notes", []):
            submission_id = submission.get("submission_id")
            if submission_ids is not None and submission_id not in submission_ids:
                continue
            if max_submissions is not None and selected_for_case >= max_submissions:
                break
            selected.append((case, submission, case_path))
            selected_for_case += 1

    if not selected:
        raise ValueError("No corpus submissions matched the selection")
    return selected


def evaluation_case_from_corpus(
    case: dict[str, Any],
    submission: dict[str, Any],
) -> EvaluationCase:
    return EvaluationCase(
        case_id=case["case_id"],
        consultation_type=ConsultationType(case["consultation_type"]),
        transcript=Transcript(
            content=format_transcript(case["transcript"]),
            source_format="validation_pack_json",
            speaker_labels=True,
        ),
        scribe_note=ScribeNote(
            content=submission["note"],
            scribe_product=submission["blind_label"],
        ),
        metadata={
            "submission_id": submission["submission_id"],
            "blind_label": submission["blind_label"],
            "note_source": submission.get("note_source"),
            "prompt_strategy": submission.get("prompt_strategy"),
        },
    )


def score_rows_from_report(
    report: Any,
    *,
    submission: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for score in report.dimension_scores:
        row = {
            "case_id": report.case_id,
            "submission_id": submission["submission_id"],
            "blind_label": submission["blind_label"],
            "dimension": score.dimension,
            "judge_score": score.score,
            "judge_severity": score.severity_summary.value,
            "judge_confidence": score.confidence,
            "judge_type": score.judge_type,
            "judge_model": score.judge_model,
            "rubric_version": score.rubric_version,
            "report_id": report.report_id,
            "overall_score": report.overall_score,
            "overall_severity": report.overall_severity.value,
            "note_source": submission.get("note_source"),
            "prompt_strategy": submission.get("prompt_strategy"),
        }
        if report.reproducibility is not None:
            row["transcript_hash"] = report.reproducibility.transcript_hash
            row["candidate_note_hash"] = report.reproducibility.scribe_note_hash
        rows.append(row)
    return rows


def build_export_manifest(
    *,
    corpus_manifest: Path,
    selected: list[tuple[dict[str, Any], dict[str, Any], Path]],
    dimensions: list[str],
    scores: list[dict[str, Any]],
    judge: BaseJudge,
    runs: int,
    seed: int | None,
) -> dict[str, Any]:
    case_files = sorted({case_path for _, _, case_path in selected})
    return {
        "schema_version": "1.0.0",
        "export_id": "scribeval_validation_judge_scores",
        "generated_at": datetime.now(UTC).isoformat(),
        "generated_by": "python scripts/export_validation_judge_scores.py",
        "benchmark_unit": BENCHMARK_UNIT,
        "scribeval_version": __version__,
        "corpus_manifest": relative_or_absolute(corpus_manifest),
        "dimensions": dimensions,
        "runs": runs,
        "seed": seed,
        "judge_type": judge.judge_type,
        "judge_model": judge.judge_model,
        "case_count": len({case["case_id"] for case, _, _ in selected}),
        "submission_count": len(selected),
        "score_count": len(scores),
        "source_hashes": {
            "corpus_manifest_sha256": sha256_file(corpus_manifest),
            "case_files_sha256": {
                relative_or_absolute(path): sha256_file(path) for path in case_files
            },
        },
        "privacy_note": (
            "Judge score exports intentionally omit transcript text, candidate "
            "note text, raw judge responses, reasoning, and excerpts. Keep raw "
            "LLM reports outside public evidence bundles unless separately "
            "reviewed for PHI/PII."
        ),
    }


def export_judge_scores(
    *,
    corpus_manifest: Path,
    output: Path,
    manifest_output: Path,
    dimensions: list[str],
    judge: BaseJudge,
    rubric_dir: Path,
    runs: int,
    seed: int | None = None,
    case_ids: set[str] | None = None,
    submission_ids: set[str] | None = None,
    max_cases: int | None = None,
    max_submissions: int | None = None,
    fhir_client: FHIRTerminologyClient | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    selected = iter_corpus_submissions(
        corpus_manifest,
        case_ids=case_ids,
        submission_ids=submission_ids,
        max_cases=max_cases,
        max_submissions=max_submissions,
    )
    pipeline = EvaluationPipeline(
        dimensions=dimensions,
        judge=judge,
        rubric_dir=rubric_dir,
        fhir_client=fhir_client,
        runs=runs,
    )

    scores: list[dict[str, Any]] = []
    for case, submission, _case_path in selected:
        report = pipeline.evaluate_case(evaluation_case_from_corpus(case, submission))
        scores.extend(score_rows_from_report(report, submission=submission))

    manifest = build_export_manifest(
        corpus_manifest=corpus_manifest,
        selected=selected,
        dimensions=dimensions,
        scores=scores,
        judge=judge,
        runs=runs,
        seed=seed,
    )
    write_json(output, scores)
    write_json(manifest_output, manifest)
    return scores, manifest


def parse_csv_set(value: str | None) -> set[str] | None:
    if value is None:
        return None
    values = {item.strip() for item in value.split(",") if item.strip()}
    return values or None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export Scribeval judge scores for validation corpus submissions."
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--manifest-output",
        type=Path,
        help="Path for export provenance manifest. Defaults to <output_stem>_manifest.json.",
    )
    parser.add_argument("--corpus-manifest", type=Path, default=DEFAULT_CORPUS_MANIFEST)
    parser.add_argument(
        "--dimensions",
        default=None,
        help="Comma-separated dimensions to evaluate. Defaults to configured default dimensions.",
    )
    parser.add_argument("--model", default=None)
    parser.add_argument("--rubric-dir", type=Path, default=None)
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument(
        "--case-ids",
        default=None,
        help="Optional comma-separated case_id filter for smoke runs.",
    )
    parser.add_argument(
        "--submission-ids",
        default=None,
        help="Optional comma-separated submission_id filter for smoke runs.",
    )
    parser.add_argument("--max-cases", type=int, default=None)
    parser.add_argument("--max-submissions", type=int, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.runs < 1:
        print("Export failed: --runs must be >= 1", file=sys.stderr)
        return 1
    if args.max_cases is not None and args.max_cases < 1:
        print("Export failed: --max-cases must be >= 1", file=sys.stderr)
        return 1
    if args.max_submissions is not None and args.max_submissions < 1:
        print("Export failed: --max-submissions must be >= 1", file=sys.stderr)
        return 1

    settings = get_settings()
    dimensions = parse_dimensions(args.dimensions)
    fhir_client: FHIRTerminologyClient | None = None
    if "medication_terminology" in dimensions:
        if not settings.fhir_terminology_url:
            print(
                "Export failed: medication_terminology requires "
                "SCRIBEVAL_FHIR_TERMINOLOGY_URL.",
                file=sys.stderr,
            )
            return 1
        fhir_client = FHIRTerminologyClient(
            endpoint=settings.fhir_terminology_url,
            timeout_seconds=settings.fhir_timeout_seconds,
        )

    manifest_output = args.manifest_output or default_manifest_output(args.output)
    try:
        api_key = settings.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
        judge = LLMJudge(
            model=args.model or settings.default_model,
            api_key=api_key,
            seed=args.seed,
        )
        scores, manifest = export_judge_scores(
            corpus_manifest=args.corpus_manifest,
            output=args.output,
            manifest_output=manifest_output,
            dimensions=dimensions,
            judge=judge,
            rubric_dir=args.rubric_dir or settings.rubric_dir,
            runs=args.runs,
            seed=args.seed,
            case_ids=parse_csv_set(args.case_ids),
            submission_ids=parse_csv_set(args.submission_ids),
            max_cases=args.max_cases,
            max_submissions=args.max_submissions,
            fhir_client=fhir_client,
        )
    except ValueError as exc:
        print(f"Export failed: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {len(scores)} judge scores to {args.output}")
    print(f"Wrote export manifest to {manifest_output}")
    print(
        "Evaluated "
        f"{manifest['case_count']} case(s), {manifest['submission_count']} "
        f"submission(s), {len(manifest['dimensions'])} dimension(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
