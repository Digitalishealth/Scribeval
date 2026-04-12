"""Minimal FHIR R4 terminology client for AMT medication validation.

Implements a narrow subset of the FHIR R4 terminology service spec —
specifically, the CodeSystem $validate-code and ValueSet $expand operations
needed to validate medication names against the Australian Medicines
Terminology (AMT). Does not implement the full FHIR client surface.

Privacy notes:
- This client only ever sends extracted medication strings (e.g.,
  "amoxicillin 500mg") to the FHIR server.
- Patient identifiers, transcript content, and other clinical context
  must NEVER be passed to this client.
- Callers are responsible for ensuring inputs are de-identified.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import httpx

# AMT (Australian Medicines Terminology) is published as a SNOMED CT-AU
# substrate. The canonical URL identifies AMT within a SNOMED CT-AU edition
# served by Ontoserver. We default to the AMT value set published by NCTS.
AMT_VALUESET_URL = (
    "http://snomed.info/sct/32506021000036107"
    "?fhir_vs=ecl/^929360071000036103|Trade product unit refset|"
)
SNOMED_CT_AU_SYSTEM = "http://snomed.info/sct"

DEFAULT_TIMEOUT_SECONDS = 5.0


class FHIRUnreachableError(Exception):
    """Raised when the FHIR endpoint cannot be reached at all."""


class ValidationOutcome(StrEnum):
    """Outcome of a single medication validation."""

    VALID_EXACT = "valid_exact"
    VALID_VARIANT = "valid_variant"
    VALID_LESS_SPECIFIC = "valid_less_specific"
    AMBIGUOUS = "ambiguous"
    INVALID = "invalid"
    LOOKUP_FAILED = "lookup_failed"


@dataclass
class ValidationResult:
    """Result of validating a single medication string against AMT."""

    medication: str
    outcome: ValidationOutcome
    matched_display: str | None = None
    match_count: int = 0
    message: str | None = None


class FHIRTerminologyClient:
    """Minimal FHIR R4 terminology client targeting AMT.

    Uses two operations:
    - ValueSet $expand with a filter to find AMT concepts matching a string
    - The match count and quality determine the validation outcome
    """

    def __init__(
        self,
        endpoint: str,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        valueset_url: str = AMT_VALUESET_URL,
    ):
        self.endpoint = endpoint.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.valueset_url = valueset_url

    def validate_medication(self, medication: str) -> ValidationResult:
        """Validate a medication name against AMT.

        Returns a ValidationResult. Never raises for normal lookup
        failures — returns LOOKUP_FAILED outcome instead. Raises
        FHIRUnreachableError only if the endpoint cannot be reached
        at all (e.g., DNS failure, connection refused).
        """
        cleaned = medication.strip()
        if not cleaned:
            return ValidationResult(
                medication=medication,
                outcome=ValidationOutcome.INVALID,
                message="Empty medication string",
            )

        try:
            matches = self._expand_with_filter(cleaned)
        except httpx.ConnectError as exc:
            raise FHIRUnreachableError(
                f"Cannot reach FHIR endpoint {self.endpoint}: {exc}"
            ) from exc
        except httpx.TimeoutException:
            return ValidationResult(
                medication=medication,
                outcome=ValidationOutcome.LOOKUP_FAILED,
                message="FHIR request timed out",
            )
        except httpx.HTTPStatusError as exc:
            return ValidationResult(
                medication=medication,
                outcome=ValidationOutcome.LOOKUP_FAILED,
                message=f"FHIR returned HTTP {exc.response.status_code}",
            )
        except Exception as exc:  # noqa: BLE001
            return ValidationResult(
                medication=medication,
                outcome=ValidationOutcome.LOOKUP_FAILED,
                message=f"FHIR lookup error: {exc.__class__.__name__}",
            )

        return self._classify_matches(medication, matches)

    def _expand_with_filter(self, filter_text: str) -> list[dict[str, Any]]:
        """Call ValueSet/$expand with a filter and return matching concepts."""
        url = f"{self.endpoint}/ValueSet/$expand"
        params = {
            "url": self.valueset_url,
            "filter": filter_text,
            "count": 5,
            "includeDesignations": "false",
        }
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        expansion = data.get("expansion", {})
        contains = expansion.get("contains", [])
        return contains

    def _classify_matches(
        self, medication: str, matches: list[dict[str, Any]]
    ) -> ValidationResult:
        """Classify expansion matches into a ValidationOutcome."""
        match_count = len(matches)

        if match_count == 0:
            return ValidationResult(
                medication=medication,
                outcome=ValidationOutcome.INVALID,
                match_count=0,
                message="No AMT concept matches this medication name",
            )

        first_display = matches[0].get("display", "") or ""
        normalised_input = medication.strip().lower()
        normalised_match = first_display.strip().lower()

        if match_count == 1:
            if normalised_input == normalised_match:
                outcome = ValidationOutcome.VALID_EXACT
            elif normalised_input in normalised_match:
                outcome = ValidationOutcome.VALID_LESS_SPECIFIC
            else:
                outcome = ValidationOutcome.VALID_VARIANT
            return ValidationResult(
                medication=medication,
                outcome=outcome,
                matched_display=first_display,
                match_count=1,
            )

        # Multiple matches — check if one is an exact match
        for m in matches:
            if (m.get("display", "") or "").strip().lower() == normalised_input:
                return ValidationResult(
                    medication=medication,
                    outcome=ValidationOutcome.VALID_EXACT,
                    matched_display=m.get("display"),
                    match_count=match_count,
                )

        return ValidationResult(
            medication=medication,
            outcome=ValidationOutcome.AMBIGUOUS,
            matched_display=first_display,
            match_count=match_count,
            message=f"{match_count} AMT concepts match — disambiguation needed",
        )
