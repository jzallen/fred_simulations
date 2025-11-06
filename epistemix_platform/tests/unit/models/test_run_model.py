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
