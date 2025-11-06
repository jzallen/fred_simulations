"""
Unit tests for Run domain model.

Tests for core Run model functionality including AWS Batch integration fields.
"""

import pytest
from datetime import datetime, timezone
from epistemix_platform.models.run import Run, RunStatus, PodPhase


class TestRunModelBatchFields:
    """Tests for AWS Batch integration fields in Run model."""

    def test_run_model_accepts_batch_job_id(self):
        """RED: Test that Run model accepts aws_batch_job_id field."""
        # ARRANGE
        job_id = 123
        user_id = 456
        request = {"simulation": "test"}
        aws_batch_job_id = "abc123-batch-job-id"

        # ACT
        run = Run.create_unpersisted(
            job_id=job_id,
            user_id=user_id,
            request=request,
            aws_batch_job_id=aws_batch_job_id,
        )

        # ASSERT
        assert run.aws_batch_job_id == aws_batch_job_id

    def test_run_model_accepts_batch_status(self):
        """RED: Test that Run model accepts aws_batch_status field."""
        # ARRANGE
        job_id = 123
        user_id = 456
        request = {"simulation": "test"}
        aws_batch_status = "RUNNING"

        # ACT
        run = Run.create_unpersisted(
            job_id=job_id,
            user_id=user_id,
            request=request,
            aws_batch_status=aws_batch_status,
        )

        # ASSERT
        assert run.aws_batch_status == aws_batch_status

    def test_run_model_defaults_results_uploaded_false(self):
        """RED: Test that Run model defaults results_uploaded to False."""
        # ARRANGE
        job_id = 123
        user_id = 456
        request = {"simulation": "test"}

        # ACT
        run = Run.create_unpersisted(
            job_id=job_id,
            user_id=user_id,
            request=request,
        )

        # ASSERT
        assert run.results_uploaded is False

    def test_run_model_accepts_results_uploaded_true(self):
        """RED: Test that Run model accepts results_uploaded=True."""
        # ARRANGE
        job_id = 123
        user_id = 456
        request = {"simulation": "test"}

        # ACT
        run = Run.create_unpersisted(
            job_id=job_id,
            user_id=user_id,
            request=request,
            results_uploaded=True,
        )

        # ASSERT
        assert run.results_uploaded is True

    def test_create_persisted_accepts_batch_fields(self):
        """RED: Test that create_persisted method accepts Batch fields."""
        # ARRANGE
        run_id = 1
        job_id = 123
        user_id = 456
        created_at = datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)
        request = {"simulation": "test"}
        aws_batch_job_id = "abc123-batch-job-id"
        aws_batch_status = "SUBMITTED"
        results_uploaded = False

        # ACT
        run = Run.create_persisted(
            run_id=run_id,
            job_id=job_id,
            user_id=user_id,
            created_at=created_at,
            updated_at=updated_at,
            request=request,
            aws_batch_job_id=aws_batch_job_id,
            aws_batch_status=aws_batch_status,
            results_uploaded=results_uploaded,
        )

        # ASSERT
        assert run.aws_batch_job_id == aws_batch_job_id
        assert run.aws_batch_status == aws_batch_status
        assert run.results_uploaded is False

    def test_batch_fields_default_to_none_and_false(self):
        """Test that Batch fields have sensible defaults."""
        # ARRANGE & ACT
        run = Run.create_unpersisted(
            job_id=123,
            user_id=456,
            request={"simulation": "test"},
        )

        # ASSERT
        assert run.aws_batch_job_id is None
        assert run.aws_batch_status is None
        assert run.results_uploaded is False


class TestRunNaturalKey:
    """Tests for Run.natural_key() method for AWS Batch job naming."""

    def test_natural_key_returns_job_and_run_id(self):
        """RED: Test that natural_key() returns formatted string with job and run ID."""
        # ARRANGE
        run = Run.create_persisted(
            run_id=42,
            job_id=123,
            user_id=456,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            request={"simulation": "test"},
        )

        # ACT
        natural_key = run.natural_key()

        # ASSERT
        assert natural_key == "job-123-run-42"

    def test_natural_key_with_different_ids(self):
        """RED: Test that natural_key() works with different IDs."""
        # ARRANGE
        run = Run.create_persisted(
            run_id=999,
            job_id=1,
            user_id=456,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            request={"simulation": "test"},
        )

        # ACT
        natural_key = run.natural_key()

        # ASSERT
        assert natural_key == "job-1-run-999"

    def test_natural_key_raises_for_unpersisted_run(self):
        """RED: Test that natural_key() raises ValueError for unpersisted run."""
        # ARRANGE
        run = Run.create_unpersisted(
            job_id=123,
            user_id=456,
            request={"simulation": "test"},
        )

        # ACT & ASSERT
        with pytest.raises(ValueError, match="Cannot generate natural_key for unpersisted run"):
            run.natural_key()
