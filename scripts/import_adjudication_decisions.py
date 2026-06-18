"""Apply adjudicator decisions to disputed consensus clinician ratings."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from build_consensus_validation_ratings import consensus_summary, report_markdown  # noqa: E402
from import_validation_ratings import (  # noqa: E402
    load_reviewer_registry,
    validate_qualified_reviewer,
    validate_score,
    validate_severity,
)

DECISION_FIELDS = (
    "case_id",
    "blinded_submission",
    "dimension",
    "adjudicator_score",
    "adjudicator_severity",
)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} is not valid JSON: {exc}") from exc


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def decision_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (
        row.get("case_id", "").strip(),
        row.get("blinded_submission", "").strip(),
        row.get("dimension", "").strip(),
    )


def load_adjudication_decisions(
    worksheet: Path,
) -> dict[tuple[str, str, str], dict[str, Any]]:
    decisions: dict[tuple[str, str, str], dict[str, Any]] = {}
    with worksheet.open(newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        missing_fields = set(DECISION_FIELDS) - fieldnames
        if missing_fields:
            raise ValueError(
                f"Adjudication worksheet missing fields: {sorted(missing_fields)}"
            )
        for row_index, row in enumerate(reader, start=2):
            key = decision_key(row)
            if not all(key):
                continue
            score_text = row.get("adjudicator_score", "").strip()
            severity_text = row.get("adjudicator_severity", "").strip()
            if not score_text and not severity_text:
                continue
            if not score_text or not severity_text:
                raise ValueError(f"Adjudication row {row_index} has incomplete decision")
            if key in decisions:
                raise ValueError(
                    "Duplicate adjudication decision for "
                    f"{key[0]}/{key[1]}/{key[2]}"
                )
            decisions[key] = {
                "score": validate_score(score_text, f"adjudication row {row_index}"),
                "severity": validate_severity(
                    severity_text,
                    f"adjudication row {row_index}",
                ),
                "decision": row.get("adjudication_decision", "").strip()
                or "adjudicator_resolution",
                "comments_present": bool(row.get("adjudicator_comments", "").strip()),
            }
    return decisions


def validate_adjudicator(
    *,
    reviewer_registry: Path | None,
    adjudicator_id: str | None,
    require_qualified_adjudicator: bool,
) -> str | None:
    if not require_qualified_adjudicator and not reviewer_registry and not adjudicator_id:
        return None
    if reviewer_registry is None:
        raise ValueError("--reviewer-registry is required for adjudicator provenance")
    if not adjudicator_id:
        raise ValueError("--adjudicator-id is required for adjudicator provenance")

    registry = load_reviewer_registry(reviewer_registry)
    validate_qualified_reviewer(adjudicator_id, registry, row_index=1)
    role = registry[adjudicator_id]["review_role"].lower()
    if role != "adjudicator":
        raise ValueError(f"Reviewer {adjudicator_id} must have review_role adjudicator")
    return adjudicator_id


def pair_key(pair: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(pair.get("case_id", "")),
        str(pair.get("blind_label", "")),
        str(pair.get("dimension", "")),
    )


def apply_adjudication_decisions(
    *,
    consensus_pairs_path: Path,
    adjudication_worksheet: Path,
    reviewer_registry: Path | None = None,
    adjudicator_id: str | None = None,
    require_qualified_adjudicator: bool = False,
) -> tuple[list[dict[str, Any]], int]:
    raw_pairs = load_json(consensus_pairs_path)
    if not isinstance(raw_pairs, list):
        raise ValueError("Consensus pairs input must be a JSON list")
    consensus_pairs = [dict(pair) for pair in raw_pairs]
    decisions = load_adjudication_decisions(adjudication_worksheet)
    validated_adjudicator_id = validate_adjudicator(
        reviewer_registry=reviewer_registry,
        adjudicator_id=adjudicator_id,
        require_qualified_adjudicator=require_qualified_adjudicator,
    )

    disputed_keys = {
        pair_key(pair) for pair in consensus_pairs if pair.get("adjudication_required") is True
    }
    missing_decisions = sorted(disputed_keys - set(decisions))
    if missing_decisions:
        first = missing_decisions[0]
        raise ValueError(
            "Missing adjudication decision for "
            f"{first[0]}/{first[1]}/{first[2]}"
        )
    extra_decisions = sorted(set(decisions) - disputed_keys)
    if extra_decisions:
        first = extra_decisions[0]
        raise ValueError(
            "Adjudication worksheet contains decision for non-disputed row "
            f"{first[0]}/{first[1]}/{first[2]}"
        )

    resolved_count = 0
    for pair in consensus_pairs:
        key = pair_key(pair)
        if key not in decisions:
            continue
        decision = decisions[key]
        pair["pre_adjudication_human_score"] = pair["human_score"]
        pair["pre_adjudication_human_severity"] = pair["human_severity"]
        pair["human_score"] = decision["score"]
        pair["human_severity"] = decision["severity"]
        pair["consensus_method"] = "adjudicator_resolved_consensus"
        pair["adjudication_required"] = False
        pair["adjudicated"] = True
        pair["adjudication_decision"] = decision["decision"]
        pair["adjudicator_comments_present"] = decision["comments_present"]
        if validated_adjudicator_id is not None:
            pair["adjudicator_id"] = validated_adjudicator_id
        resolved_count += 1
    return consensus_pairs, resolved_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply adjudicator worksheet decisions to consensus rating pairs."
    )
    parser.add_argument("--consensus-pairs", required=True, type=Path)
    parser.add_argument("--adjudication-worksheet", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--output-summary-json", required=True, type=Path)
    parser.add_argument("--output-summary-md", required=True, type=Path)
    parser.add_argument("--reviewer-registry", type=Path)
    parser.add_argument("--adjudicator-id")
    parser.add_argument(
        "--require-qualified-adjudicator",
        action="store_true",
        help=(
            "Fail unless --reviewer-registry and --adjudicator-id are supplied and "
            "the adjudicator is registered, trained, conflict-free, and role=adjudicator."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        pairs, resolved_count = apply_adjudication_decisions(
            consensus_pairs_path=args.consensus_pairs,
            adjudication_worksheet=args.adjudication_worksheet,
            reviewer_registry=args.reviewer_registry,
            adjudicator_id=args.adjudicator_id,
            require_qualified_adjudicator=args.require_qualified_adjudicator,
        )
        summary = consensus_summary(pairs)
    except ValueError as exc:
        print(f"Adjudication import failed: {exc}", file=sys.stderr)
        return 1

    write_json(args.output, pairs)
    write_json(args.output_summary_json, summary)
    args.output_summary_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_summary_md.write_text(report_markdown(summary))
    print(f"Resolved adjudication decisions: {resolved_count}")
    print(f"Wrote adjudicated consensus pairs to {args.output}")
    print(f"Wrote adjudicated consensus summary to {args.output_summary_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
