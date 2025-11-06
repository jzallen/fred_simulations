"""
Tests for AWSBatchSimulationRunner gateway.

Tests AWS Batch integration for simulation execution using mocked boto3 client.
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone

from epistemix_platform.gateways.simulation_runner import AWSBatchSimulationRunner
from epistemix_platform.models import Run, RunStatus, RunStatusDetail


class TestAWSBatchSimulationRunnerSubmit:
    """Tests for submit_run method."""

    def test_submit_run_calls_boto3_submit_job(self):
        """RED: Test that submit_run calls boto3 submit_job."""
        # ARRANGE
        mock_batch_client = Mock()
        mock_batch_client.submit_job.return_value = {"jobId": "abc-123-job-id"}

        runner = AWSBatchSimulationRunner(batch_client=mock_batch_client)

        run = Run.create_persisted(
            run_id=42,
            job_id=123,
            user_id=456,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            request={"simulation": "test"},
        )

        # ACT
        runner.submit_run(run)

        # ASSERT
        mock_batch_client.submit_job.assert_called_once()
        call_kwargs = mock_batch_client.submit_job.call_args[1]
        assert call_kwargs["jobName"] == "job-123-run-42"
        assert "jobDefinition" in call_kwargs
        assert "jobQueue" in call_kwargs

    def test_submit_run_updates_run_aws_batch_job_id(self):
        """RED: Test that submit_run updates run.aws_batch_job_id."""
        # ARRANGE
        mock_batch_client = Mock()
        mock_batch_client.submit_job.return_value = {"jobId": "abc-123-job-id"}

        runner = AWSBatchSimulationRunner(batch_client=mock_batch_client)

        run = Run.create_persisted(
            run_id=42,
            job_id=123,
            user_id=456,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            request={"simulation": "test"},
        )

        # ACT
        runner.submit_run(run)

        # ASSERT
        assert run.aws_batch_job_id == "abc-123-job-id"

    def test_submit_run_passes_job_and_run_ids_as_environment_variables(self):
        """RED: Test that submit_run passes job_id and run_id as env vars."""
        # ARRANGE
        mock_batch_client = Mock()
        mock_batch_client.submit_job.return_value = {"jobId": "abc-123-job-id"}

        runner = AWSBatchSimulationRunner(batch_client=mock_batch_client)

        run = Run.create_persisted(
            run_id=42,
            job_id=123,
            user_id=456,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            request={"simulation": "test"},
        )

        # ACT
        runner.submit_run(run)

        # ASSERT
        call_kwargs = mock_batch_client.submit_job.call_args[1]
        container_overrides = call_kwargs.get("containerOverrides", {})
        environment = container_overrides.get("environment", [])

        env_dict = {item["name"]: item["value"] for item in environment}
        assert env_dict.get("JOB_ID") == "123"
        assert env_dict.get("RUN_ID") == "42"


class TestAWSBatchSimulationRunnerDescribe:
    """Tests for describe_run method."""

    def test_describe_run_calls_boto3_describe_jobs(self):
        """RED: Test that describe_run calls boto3 describe_jobs."""
        # ARRANGE
        mock_batch_client = Mock()
        mock_batch_client.describe_jobs.return_value = {
            "jobs": [
                {
                    "status": "RUNNING",
                    "statusReason": "Job is running on compute environment",
                }
            ]
        }

        runner = AWSBatchSimulationRunner(batch_client=mock_batch_client)

        run = Run.create_persisted(
            run_id=42,
            job_id=123,
            user_id=456,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            request={"simulation": "test"},
            aws_batch_job_id="abc-123-job-id",
        )

        # ACT
        result = runner.describe_run(run)

        # ASSERT
        mock_batch_client.describe_jobs.assert_called_once_with(jobs=["abc-123-job-id"])

    def test_describe_run_returns_status_detail_with_running(self):
        """RED: Test that describe_run returns RunStatusDetail for RUNNING."""
        # ARRANGE
        mock_batch_client = Mock()
        mock_batch_client.describe_jobs.return_value = {
            "jobs": [
                {
                    "status": "RUNNING",
                    "statusReason": "Job is running on compute environment",
                }
            ]
        }

        runner = AWSBatchSimulationRunner(batch_client=mock_batch_client)

        run = Run.create_persisted(
            run_id=42,
            job_id=123,
            user_id=456,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            request={"simulation": "test"},
            aws_batch_job_id="abc-123-job-id",
        )

        # ACT
        result = runner.describe_run(run)

        # ASSERT
        assert isinstance(result, RunStatusDetail)
        assert result.status == RunStatus.RUNNING
        assert result.message == "Job is running on compute environment"

    def test_describe_run_maps_batch_status_to_run_status(self):
        """RED: Test that describe_run maps AWS Batch statuses to RunStatus."""
        # ARRANGE
        mock_batch_client = Mock()
        runner = AWSBatchSimulationRunner(batch_client=mock_batch_client)

        run = Run.create_persisted(
            run_id=42,
            job_id=123,
            user_id=456,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            request={"simulation": "test"},
            aws_batch_job_id="abc-123-job-id",
        )

        # Test SUBMITTED -> QUEUED
        mock_batch_client.describe_jobs.return_value = {
            "jobs": [{"status": "SUBMITTED", "statusReason": "Job submitted"}]
        }
        result = runner.describe_run(run)
        assert result.status == RunStatus.QUEUED

        # Test PENDING -> QUEUED
        mock_batch_client.describe_jobs.return_value = {
            "jobs": [{"status": "PENDING", "statusReason": "Job pending"}]
        }
        result = runner.describe_run(run)
        assert result.status == RunStatus.QUEUED

        # Test RUNNABLE -> QUEUED
        mock_batch_client.describe_jobs.return_value = {
            "jobs": [{"status": "RUNNABLE", "statusReason": "Job runnable"}]
        }
        result = runner.describe_run(run)
        assert result.status == RunStatus.QUEUED

        # Test STARTING -> RUNNING
        mock_batch_client.describe_jobs.return_value = {
            "jobs": [{"status": "STARTING", "statusReason": "Job starting"}]
        }
        result = runner.describe_run(run)
        assert result.status == RunStatus.RUNNING

        # Test RUNNING -> RUNNING
        mock_batch_client.describe_jobs.return_value = {
            "jobs": [{"status": "RUNNING", "statusReason": "Job running"}]
        }
        result = runner.describe_run(run)
        assert result.status == RunStatus.RUNNING

        # Test SUCCEEDED -> DONE
        mock_batch_client.describe_jobs.return_value = {
            "jobs": [{"status": "SUCCEEDED", "statusReason": "Job completed"}]
        }
        result = runner.describe_run(run)
        assert result.status == RunStatus.DONE

        # Test FAILED -> ERROR
        mock_batch_client.describe_jobs.return_value = {
            "jobs": [{"status": "FAILED", "statusReason": "Job failed"}]
        }
        result = runner.describe_run(run)
        assert result.status == RunStatus.ERROR

    def test_describe_run_raises_if_no_batch_job_id(self):
        """RED: Test that describe_run raises ValueError if no aws_batch_job_id."""
        # ARRANGE
        mock_batch_client = Mock()
        runner = AWSBatchSimulationRunner(batch_client=mock_batch_client)

        run = Run.create_persisted(
            run_id=42,
            job_id=123,
            user_id=456,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            request={"simulation": "test"},
            aws_batch_job_id=None,  # No batch job ID
        )

        # ACT & ASSERT
        with pytest.raises(ValueError, match="aws_batch_job_id"):
            runner.describe_run(run)


class TestAWSBatchSimulationRunnerCancel:
    """Tests for cancel_run method."""

    def test_cancel_run_calls_boto3_terminate_job(self):
        """RED: Test that cancel_run calls boto3 terminate_job."""
        # ARRANGE
        mock_batch_client = Mock()
        mock_batch_client.terminate_job.return_value = {}

        runner = AWSBatchSimulationRunner(batch_client=mock_batch_client)

        run = Run.create_persisted(
            run_id=42,
            job_id=123,
            user_id=456,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            request={"simulation": "test"},
            aws_batch_job_id="abc-123-job-id",
        )

        # ACT
        runner.cancel_run(run)

        # ASSERT
        mock_batch_client.terminate_job.assert_called_once_with(
            jobId="abc-123-job-id", reason="User requested cancellation"
        )

    def test_cancel_run_raises_if_no_batch_job_id(self):
        """RED: Test that cancel_run raises ValueError if no aws_batch_job_id."""
        # ARRANGE
        mock_batch_client = Mock()
        runner = AWSBatchSimulationRunner(batch_client=mock_batch_client)

        run = Run.create_persisted(
            run_id=42,
            job_id=123,
            user_id=456,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            request={"simulation": "test"},
            aws_batch_job_id=None,  # No batch job ID
        )

        # ACT & ASSERT
        with pytest.raises(ValueError, match="aws_batch_job_id"):
            runner.cancel_run(run)


class TestAWSBatchSimulationRunnerConstants:
    """Tests for gateway constants."""

    def test_gateway_uses_correct_job_definition_arn(self):
        """Test that gateway has correct job definition ARN constant."""
        # ARRANGE
        mock_batch_client = Mock()
        mock_batch_client.submit_job.return_value = {"jobId": "test-id"}

        runner = AWSBatchSimulationRunner(batch_client=mock_batch_client)

        run = Run.create_persisted(
            run_id=42,
            job_id=123,
            user_id=456,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            request={"simulation": "test"},
        )

        # ACT
        runner.submit_run(run)

        # ASSERT
        call_kwargs = mock_batch_client.submit_job.call_args[1]
        # Verify format looks like a job definition ARN
        assert call_kwargs["jobDefinition"].startswith("arn:aws:batch:")
        assert "job-definition/simulation-runner" in call_kwargs["jobDefinition"]

    def test_gateway_uses_correct_job_queue_name(self):
        """Test that gateway has correct job queue name constant."""
        # ARRANGE
        mock_batch_client = Mock()
        mock_batch_client.submit_job.return_value = {"jobId": "test-id"}

        runner = AWSBatchSimulationRunner(batch_client=mock_batch_client)

        run = Run.create_persisted(
            run_id=42,
            job_id=123,
            user_id=456,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            request={"simulation": "test"},
        )

        # ACT
        runner.submit_run(run)

        # ASSERT
        call_kwargs = mock_batch_client.submit_job.call_args[1]
        assert call_kwargs["jobQueue"] == "simulation-queue"
