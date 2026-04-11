"""Tests for rubric loading and validation."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from scribeval.rubrics.loader import RubricSchema, load_all_rubrics, load_rubric


class TestRubricLoading:
    def test_load_omission_rubric(self, rubrics_dir: Path):
        rubric = load_rubric(rubrics_dir / "omission.yaml")
        assert rubric.dimension == "omission"
        assert rubric.version == "1.0.0"
        assert rubric.display_name == "Clinical Omission Rate"
        assert "critical" in rubric.severity_criteria
        assert "high" in rubric.severity_criteria
        assert "moderate" in rubric.severity_criteria
        assert "low" in rubric.severity_criteria

    def test_load_hallucination_rubric(self, rubrics_dir: Path):
        rubric = load_rubric(rubrics_dir / "hallucination.yaml")
        assert rubric.dimension == "hallucination"
        assert len(rubric.references) > 0

    def test_load_medicolegal_rubric(self, rubrics_dir: Path):
        rubric = load_rubric(rubrics_dir / "medicolegal.yaml")
        assert rubric.dimension == "medicolegal"
        assert "australian_context" in rubric.model_fields_set or rubric.australian_context

    def test_load_ahpra_rubric(self, rubrics_dir: Path):
        rubric = load_rubric(rubrics_dir / "ahpra.yaml")
        assert rubric.dimension == "ahpra"

    def test_load_all_rubrics(self, rubrics_dir: Path):
        rubrics = load_all_rubrics(rubrics_dir)
        assert len(rubrics) == 4
        assert "omission" in rubrics
        assert "hallucination" in rubrics
        assert "medicolegal" in rubrics
        assert "ahpra" in rubrics

    def test_all_rubrics_have_required_fields(self, rubrics_dir: Path):
        rubrics = load_all_rubrics(rubrics_dir)
        for name, rubric in rubrics.items():
            assert rubric.dimension, f"{name}: missing dimension"
            assert rubric.version, f"{name}: missing version"
            assert rubric.display_name, f"{name}: missing display_name"
            assert rubric.description.strip(), f"{name}: missing description"
            assert rubric.evaluation_instructions.strip(), (
                f"{name}: missing evaluation_instructions"
            )
            assert rubric.australian_context.strip(), f"{name}: missing australian_context"
            assert len(rubric.severity_criteria) >= 3, f"{name}: too few severity criteria"
            assert len(rubric.references) >= 1, f"{name}: missing references"

    def test_all_rubrics_have_severity_examples(self, rubrics_dir: Path):
        rubrics = load_all_rubrics(rubrics_dir)
        for name, rubric in rubrics.items():
            for level, criterion in rubric.severity_criteria.items():
                assert criterion.description.strip(), (
                    f"{name}/{level}: missing description"
                )
                assert len(criterion.examples) >= 1, (
                    f"{name}/{level}: missing examples"
                )

    def test_invalid_rubric_path_raises(self):
        with pytest.raises(FileNotFoundError):
            load_rubric(Path("nonexistent.yaml"))

    def test_rubric_schema_validation(self):
        """Ensure RubricSchema rejects incomplete data."""
        with pytest.raises(ValidationError):
            RubricSchema(
                dimension="test",
                version="1.0",
                # Missing required fields
            )
