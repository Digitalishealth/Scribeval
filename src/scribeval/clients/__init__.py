"""External service clients (FHIR terminology, etc.)."""

from __future__ import annotations

from scribeval.clients.fhir import (
    FHIRTerminologyClient,
    FHIRUnreachableError,
    ValidationResult,
)

__all__ = [
    "FHIRTerminologyClient",
    "FHIRUnreachableError",
    "ValidationResult",
]
