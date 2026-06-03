"""Evaluation pipeline orchestration."""

from __future__ import annotations

import math
import statistics
import uuid
from pathlib import Path

from scribeval import __version__
from scribeval.clients.fhir import FHIRTerminologyClient
from scribeval.evaluators import (
    EVALUATOR_REGISTRY,
    OPT_IN_DIMENSIONS,
    get_evaluator,
)
from scribeval.judges.base import BaseJudge
from scribeval.judges.llm import LLMJudge
from scribeval.models.case import EvaluationCase
from scribeval.models.report import (
    AggregateReport,
    DimensionRunStatistics,
    DimensionStatistics,
    EvaluationReport,
)
from scribeval.models.score import DimensionScore, SeverityLevel
from scribeval.reproducibility import ReproducibilityMetadata, content_hash
from scribeval.rubrics.loader import RubricSchema, load_all_rubrics

# Dimension weights in overall score, informed by clinical safety literature.
#
# Rationale (see METHODOLOGY.md for full references):
# - Hallucination (2.0): Fabricated clinical information is the highest-risk
#   failure mode. Kernberg et al. (2024) found hallucinated findings led to
#   inappropriate management in simulated scenarios. Wrong information is
#   more dangerous than missing information because it may not be questioned.
# - Omission (1.5): Clinically significant omissions can cause harm through
#   missed allergies, red flags, or management steps. Tierney et al. (2024)
#   found omission of safety-critical items in ~12% of ambient scribe notes.
#   Weighted lower than hallucination because clinicians often catch omissions
#   during note review, whereas hallucinations may go undetected.
# - QNOTE (1.2): Domain-based quality instrument with safety-critical domains
#   (medications/allergies, assessment/plan) receiving elevated sub-weights.
#   Burke et al. (2014) validated QNOTE as predictive of clinical note utility.
# - Medicolegal (1.0): Documentation adequacy for medicolegal protection.
#   Avant Mutual data shows documentation deficiencies contribute to ~30% of
#   successful malpractice claims in Australian general practice.
# - AHPRA (1.0): Regulatory compliance. Important but less directly tied to
#   immediate patient safety than clinical accuracy dimensions.
# - PDQI-9 (1.0): Holistic quality instrument. Stetson et al. (2012) validated
#   PDQI-9 as a reliable measure of overall documentation quality.
#   Weighted at baseline because it overlaps with other dimension assessments.
DIMENSION_WEIGHTS: dict[str, float] = {
    "hallucination": 2.0,
    "omission": 1.5,
    "medication_terminology": 1.5,
    "qnote": 1.2,
    "medicolegal": 1.0,
    "ahpra": 1.0,
    "pdqi9": 1.0,
}

# Severity-based finding weights for computing adjusted dimension scores.
# Literature basis: Medication errors and allergy omissions cause
# disproportionate harm (Slight et al., BMJ Quality & Safety, 2019;
# Westbrook et al., BMJ, 2010). Critical findings should dominate the
# score more than a simple average would suggest.
SEVERITY_FINDING_WEIGHTS: dict[str, float] = {
    "critical": 4.0,
    "high": 2.0,
    "moderate": 1.0,
    "low": 0.25,
    "none": 0.0,
}

DEFAULT_RUBRIC_DIR = Path("rubrics")


def _generate_id() -> str:
    return uuid.uuid4().hex[:12]


def compute_severity_penalty(scores: list[DimensionScore]) -> float:
    """Compute a severity-weighted penalty based on individual findings.

    Each finding's severity contributes a weighted penalty that pulls the
    overall score down. This ensures a note with one critical error (e.g.,
    missed penicillin allergy) is penalised more heavily than a note with
    several low-severity issues, even if the dimension-level scores are
    similar.

    Literature basis:
    - Slight et al. (2019): medication errors account for disproportionate
      patient harm relative to their frequency.
    - Westbrook et al. (2010): severity of clinical errors follows a
      power-law distribution in harm outcomes.
    - Reason J (2000): Swiss cheese model — critical errors represent
      aligned failure points with outsized consequences.

    Returns a penalty in [0.0, 1.0] where 0.0 = no penalty, 1.0 = maximum.
    """
    if not scores:
        return 0.0

    total_penalty = 0.0
    for s in scores:
        for f in s.findings:
            weight = SEVERITY_FINDING_WEIGHTS.get(f.severity.value, 0.0)
            total_penalty += weight

    # Normalise: 1 critical finding (weight 4.0) produces penalty ~0.20,
    # 5 critical findings saturate at ~0.60. This uses a soft-cap function
    # to prevent a single dimension from zeroing the entire score.
    max_penalty = 0.60
    normalised = min(total_penalty / 20.0, max_penalty)
    return round(normalised, 4)


def _compute_overall_score(
    scores: list[DimensionScore],
    specialty_multipliers: dict[str, float] | None = None,
) -> float:
    """Compute weighted average score across dimensions, adjusted by severity penalty.

    The score combines two signals:
    1. Dimension-weighted average (how well did the note score on each dimension?)
    2. Severity penalty (how many high-impact errors were found?)

    This dual approach ensures that a note cannot achieve a high overall score
    if it contains critical safety errors, even if other dimensions score well.

    ``specialty_multipliers`` is an optional per-dimension weight multiplier
    supplied by rubric specialty overlays. For example, an ED overlay may set
    hallucination's multiplier to 1.3, boosting its contribution.
    """
    if not scores:
        return 0.0
    multipliers = specialty_multipliers or {}
    total_weight = 0.0
    weighted_sum = 0.0
    for s in scores:
        base = DIMENSION_WEIGHTS.get(s.dimension, 1.0)
        weight = base * multipliers.get(s.dimension, 1.0)
        weighted_sum += s.score * weight
        total_weight += weight
    base_score = weighted_sum / total_weight if total_weight > 0 else 0.0

    penalty = compute_severity_penalty(scores)
    adjusted = base_score * (1.0 - penalty)
    return round(max(adjusted, 0.0), 4)


def _compute_overall_severity(scores: list[DimensionScore]) -> SeverityLevel:
    """Overall severity is the worst severity across all dimensions."""
    severity_order = list(SeverityLevel)
    worst = SeverityLevel.NONE
    for s in scores:
        if severity_order.index(s.severity_summary) > severity_order.index(worst):
            worst = s.severity_summary
    return worst


def _generate_summary(scores: list[DimensionScore]) -> str:
    """Generate a human-readable summary of evaluation results."""
    if not scores:
        return "No dimensions evaluated."

    overall = _compute_overall_score(scores)
    worst = _compute_overall_severity(scores)
    penalty = compute_severity_penalty(scores)

    lines = [f"Overall score: {overall:.2f}/1.00 ({worst.value} severity)."]

    if penalty > 0:
        lines.append(
            f"Severity penalty applied: -{penalty:.0%} "
            "(weighted by finding severity — critical errors penalised 4x, "
            "high 2x, moderate 1x, low 0.25x)."
        )

    # Count findings by severity
    severity_counts: dict[str, int] = {}
    for s in scores:
        for f in s.findings:
            severity_counts[f.severity.value] = (
                severity_counts.get(f.severity.value, 0) + 1
            )

    if severity_counts:
        counts_str = ", ".join(
            f"{count} {level}"
            for level, count in sorted(
                severity_counts.items(),
                key=lambda x: list(SeverityLevel).index(SeverityLevel(x[0])),
                reverse=True,
            )
        )
        lines.append(f"Findings breakdown: {counts_str}.")

    critical_findings = []
    for s in scores:
        for f in s.findings:
            if f.severity == SeverityLevel.CRITICAL:
                critical_findings.append(f"{s.dimension}: {f.description}")

    if critical_findings:
        lines.append(f"Critical findings ({len(critical_findings)}):")
        for cf in critical_findings:
            lines.append(f"  - {cf}")
    else:
        lines.append("No critical findings.")

    return "\n".join(lines)


def _data_flow_statement(
    judge: BaseJudge,
    dimensions: list[str] | None = None,
    fhir_client: FHIRTerminologyClient | None = None,
) -> str:
    """Generate explicit disclosure of data handling.

    Discloses every external service that received data during this
    evaluation. The medication_terminology dimension introduces a second
    external service (FHIR terminology server) that receives only extracted
    medication strings — never the transcript or patient identifiers.
    """
    parts: list[str] = []
    if isinstance(judge, LLMJudge):
        parts.append(
            f"Evaluation performed using {judge.judge_model} via the Anthropic API. "
            "The consultation transcript and candidate final note were sent to "
            "Anthropic's API for evaluation. Anthropic's data retention policy "
            "applies (see https://www.anthropic.com/policies). No data is stored "
            "by Scribeval beyond local report files. If a reference note was "
            "provided, it was also sent to the API as optional adjudication context."
        )
    else:
        parts.append(
            f"Evaluation performed locally using {judge.judge_type} scoring. "
            "No clinical data was transmitted to the judge."
        )

    used_fhir = (
        fhir_client is not None
        and dimensions is not None
        and "medication_terminology" in dimensions
    )
    if used_fhir:
        assert fhir_client is not None
        parts.append(
            f"Medication terminology validation sent extracted medication "
            f"name strings to the FHIR terminology server at "
            f"{fhir_client.endpoint}. Only medication names (e.g., "
            f"'amoxicillin') were transmitted — the consultation transcript, "
            f"patient identifiers, and other clinical context were NOT sent "
            f"to the FHIR server. For sensitive data, run your own Ontoserver "
            f"instance and configure SCRIBEVAL_FHIR_TERMINOLOGY_URL."
        )

    return "\n\n".join(parts)


def _rubric_hashes(rubrics: dict[str, RubricSchema], dimensions: list[str]) -> dict[str, str]:
    """Hash each rubric used in an evaluation for provenance."""
    return {
        dim: content_hash(rubrics[dim].model_dump_json())
        for dim in dimensions
        if dim in rubrics
    }


def _reproducibility_metadata(
    case: EvaluationCase,
    judge: BaseJudge,
    rubrics: dict[str, RubricSchema],
    dimensions: list[str],
) -> ReproducibilityMetadata:
    """Build the reproducibility metadata for a single evaluation run."""
    ref_hash: str | None = None
    if case.reference_note is not None:
        ref_hash = content_hash(case.reference_note.content)
    temperature: float | None = None
    seed: int | None = None
    if isinstance(judge, LLMJudge):
        temperature = judge.temperature
        seed = judge.seed
    return ReproducibilityMetadata(
        scribeval_version=__version__,
        judge_type=judge.judge_type,
        judge_model=judge.judge_model,
        judge_temperature=temperature,
        judge_seed=seed,
        transcript_hash=content_hash(case.transcript.content),
        scribe_note_hash=content_hash(case.scribe_note.content),
        reference_note_hash=ref_hash,
        rubric_hashes=_rubric_hashes(rubrics, dimensions),
        dimensions=list(dimensions),
    )


def _aggregate_run_scores(
    dimension: str, runs: list[DimensionScore]
) -> tuple[DimensionScore, DimensionRunStatistics]:
    """Combine N runs of the same dimension into an averaged score + variance stats.

    The canonical DimensionScore returned uses the MEAN score across runs and
    the UNION of all findings (deduplicated by description). Confidence is
    lowered when the per-run variance is high.
    """
    per_run_scores = [r.score for r in runs]
    mean_score = statistics.mean(per_run_scores)
    std_score = statistics.stdev(per_run_scores) if len(per_run_scores) > 1 else 0.0

    # 95% CI using normal approximation — fine for our small-N variance
    # reporting, which is descriptive not inferential.
    se = std_score / math.sqrt(len(per_run_scores)) if per_run_scores else 0.0
    ci95_low = max(0.0, mean_score - 1.96 * se)
    ci95_high = min(1.0, mean_score + 1.96 * se)

    stats = DimensionRunStatistics(
        dimension=dimension,
        run_count=len(runs),
        mean_score=round(mean_score, 4),
        std_score=round(std_score, 4),
        ci95_low=round(ci95_low, 4),
        ci95_high=round(ci95_high, 4),
        per_run_scores=[round(s, 4) for s in per_run_scores],
    )

    # Findings union across runs — deduplicate by description to avoid
    # exploding the report with duplicate issues from a stable judge.
    seen: set[str] = set()
    merged_findings = []
    for run in runs:
        for finding in run.findings:
            key = finding.description.strip().lower()
            if key in seen:
                continue
            seen.add(key)
            merged_findings.append(finding)

    # Confidence: mean of per-run confidences, penalised by variance. A high
    # std across runs indicates the judge is uncertain in ways it did not
    # self-report, so we reduce confidence proportionally.
    raw_confidence = statistics.mean(r.confidence for r in runs)
    variance_penalty = min(std_score * 2.0, 0.5)
    effective_confidence = max(0.0, raw_confidence - variance_penalty)

    # Severity: worst severity observed across runs (conservative)
    severity_order = list(SeverityLevel)
    worst_severity = SeverityLevel.NONE
    for run in runs:
        if severity_order.index(run.severity_summary) > severity_order.index(worst_severity):
            worst_severity = run.severity_summary

    template = runs[0]
    merged_reasoning = (
        f"{template.reasoning}\n\n"
        f"[Multi-run: mean={mean_score:.3f}, std={std_score:.3f}, "
        f"95% CI [{ci95_low:.3f}, {ci95_high:.3f}], N={len(runs)}]"
    )

    averaged = DimensionScore(
        dimension=dimension,
        score=round(mean_score, 4),
        confidence=round(effective_confidence, 4),
        severity_summary=worst_severity,
        findings=merged_findings,
        reasoning=merged_reasoning,
        rubric_version=template.rubric_version,
        judge_type=template.judge_type,
        judge_model=template.judge_model,
        raw_judge_response=template.raw_judge_response,
    )
    return averaged, stats


class EvaluationPipeline:
    """Orchestrates evaluation of candidate notes across multiple dimensions."""

    def __init__(
        self,
        dimensions: list[str] | None = None,
        judge: BaseJudge | None = None,
        rubric_dir: Path | None = None,
        fhir_client: FHIRTerminologyClient | None = None,
        runs: int = 1,
    ):
        self.rubric_dir = rubric_dir or DEFAULT_RUBRIC_DIR
        self.rubrics = load_all_rubrics(self.rubric_dir)
        self.judge = judge or LLMJudge()
        # Default to all dimensions EXCEPT opt-in ones (those need explicit
        # configuration like a FHIR client and may have privacy implications).
        self.dimensions = dimensions or [
            d for d in EVALUATOR_REGISTRY if d not in OPT_IN_DIMENSIONS
        ]
        self.fhir_client = fhir_client
        if runs < 1:
            raise ValueError("runs must be >= 1")
        self.runs = runs

        # Validate requested dimensions
        for dim in self.dimensions:
            if dim not in EVALUATOR_REGISTRY:
                available = ", ".join(sorted(EVALUATOR_REGISTRY.keys()))
                raise ValueError(
                    f"Unknown dimension '{dim}'. Available: {available}"
                )
            if dim not in self.rubrics:
                raise ValueError(
                    f"No rubric found for dimension '{dim}' in {self.rubric_dir}"
                )

    def evaluate_case(self, case: EvaluationCase) -> EvaluationReport:
        """Run all configured evaluators against a single case.

        When runs > 1, each dimension is evaluated N times and the per-run
        variance is captured in `run_statistics`. The canonical
        `dimension_scores` list reports the mean across runs.

        If a rubric defines a specialty_overlay for the case's consultation
        type, the overlay is applied BEFORE the evaluator runs (additional
        criteria prepended to instructions) and the overlay's
        weight_multiplier is applied when computing the overall score.
        """
        scores: list[DimensionScore] = []
        run_stats: list[DimensionRunStatistics] = []
        consultation_type = case.consultation_type.value

        # Build the specialty weight multipliers map once — used by the
        # overall-score computation to boost dimensions that matter more in
        # this specialty (e.g., hallucination × 1.3 in ED).
        specialty_multipliers: dict[str, float] = {
            dim: self.rubrics[dim].specialty_weight_multiplier(consultation_type)
            for dim in self.dimensions
        }

        for dim in self.dimensions:
            specialty_rubric = self.rubrics[dim].for_specialty(consultation_type)
            evaluator = get_evaluator(
                dim,
                specialty_rubric,
                self.judge,
                fhir_client=self.fhir_client,
            )
            if self.runs == 1:
                scores.append(evaluator.evaluate(case))
                continue

            per_run = [evaluator.evaluate(case) for _ in range(self.runs)]
            averaged, stats = _aggregate_run_scores(dim, per_run)
            scores.append(averaged)
            run_stats.append(stats)

        return EvaluationReport(
            report_id=_generate_id(),
            case_id=case.case_id,
            scribe_product=case.scribe_note.scribe_product,
            candidate_label=case.scribe_note.scribe_product,
            consultation_type=consultation_type,
            dimension_scores=scores,
            overall_score=_compute_overall_score(scores, specialty_multipliers),
            overall_severity=_compute_overall_severity(scores),
            summary=_generate_summary(scores),
            data_flow_disclosure=_data_flow_statement(
                self.judge, self.dimensions, self.fhir_client
            ),
            scribeval_version=__version__,
            reproducibility=_reproducibility_metadata(
                case, self.judge, self.rubrics, self.dimensions
            ),
            run_statistics=run_stats,
            specialty_weight_multipliers=specialty_multipliers,
        )

    def evaluate_batch(self, cases: list[EvaluationCase]) -> AggregateReport:
        """Evaluate multiple cases and aggregate statistics."""
        reports = [self.evaluate_case(c) for c in cases]
        return self._aggregate(reports)

    def _aggregate(self, reports: list[EvaluationReport]) -> AggregateReport:
        """Compute aggregate statistics across multiple reports."""
        dim_scores: dict[str, list[float]] = {d: [] for d in self.dimensions}
        for report in reports:
            for ds in report.dimension_scores:
                if ds.dimension in dim_scores:
                    dim_scores[ds.dimension].append(ds.score)

        dim_stats: dict[str, DimensionStatistics] = {}
        for dim, scores in dim_scores.items():
            if not scores:
                continue
            critical_count = sum(
                1
                for report in reports
                for ds in report.dimension_scores
                if ds.dimension == dim
                for f in ds.findings
                if f.severity == SeverityLevel.CRITICAL
            )
            dim_stats[dim] = DimensionStatistics(
                dimension=dim,
                mean=round(statistics.mean(scores), 4),
                std=round(statistics.stdev(scores), 4) if len(scores) > 1 else 0.0,
                median=round(statistics.median(scores), 4),
                min_score=round(min(scores), 4),
                max_score=round(max(scores), 4),
                critical_finding_count=critical_count,
                case_scores=scores,
            )

        all_overall = [r.overall_score for r in reports]
        return AggregateReport(
            report_id=_generate_id(),
            case_count=len(reports),
            scribe_product=reports[0].scribe_product if reports else None,
            dimension_statistics=dim_stats,
            overall_mean=round(statistics.mean(all_overall), 4) if all_overall else 0.0,
            overall_std=(
                round(statistics.stdev(all_overall), 4)
                if len(all_overall) > 1
                else 0.0
            ),
        )
