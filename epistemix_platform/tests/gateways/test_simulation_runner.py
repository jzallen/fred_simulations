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

    def test_submit_run_does_not_modify_run_object(self):
        """Test that submit_run does not modify the run object (AWS Batch is source of truth)."""
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

        # Store original attributes
        original_dict = run.to_dict()

        # ACT
        runner.submit_run(run)

        # ASSERT - Run object should be unchanged (AWS Batch is source of truth)
        assert run.to_dict() == original_dict

    def test_submit_run_passes_job_and_run_ids_as_command_arguments(self):
        """Test that submit_run passes job_id and run_id as command args to simulation-runner CLI."""
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
        command = container_overrides.get("command", [])

        # Expect: ["run", "--job-id", "123", "--run-id", "42"]
        assert command == ["run", "--job-id", "123", "--run-id", "42"]


class TestAWSBatchSimulationRunnerDescribe:
    """Tests for describe_run method."""

    def test_describe_run_calls_boto3_list_jobs_with_name_filter(self):
        """Test that describe_run uses list_jobs with JOB_NAME filter."""
        # ARRANGE
        mock_batch_client = Mock()
        mock_batch_client.list_jobs.return_value = {
            "jobSummaryList": [
                {
                    "jobId": "abc-123-job-id",
                    "jobName": "job-123-run-42",
                    "status": "RUNNING",
                    "createdAt": 1234567890,
                }
            ]
        }
        mock_batch_client.describe_jobs.return_value = {
            "jobs": [
                {
                    "jobId": "abc-123-job-id",
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
        )

        # ACT
        result = runner.describe_run(run)

        # ASSERT
        mock_batch_client.list_jobs.assert_called_once()
        call_kwargs = mock_batch_client.list_jobs.call_args[1]
        assert call_kwargs["filters"] == [{"name": "JOB_NAME", "values": ["job-123-run-42"]}]
        mock_batch_client.describe_jobs.assert_called_once_with(jobs=["abc-123-job-id"])

    def test_describe_run_returns_status_detail_with_running(self):
        """Test that describe_run returns RunStatusDetail for RUNNING."""
        # ARRANGE
        mock_batch_client = Mock()
        mock_batch_client.list_jobs.return_value = {
            "jobSummaryList": [
                {
                    "jobId": "abc-123-job-id",
                    "jobName": "job-123-run-42",
                    "status": "RUNNING",
                }
            ]
        }
        mock_batch_client.describe_jobs.return_value = {
            "jobs": [
                {
                    "jobId": "abc-123-job-id",
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
        )

        # ACT
        result = runner.describe_run(run)

        # ASSERT
        assert isinstance(result, RunStatusDetail)
        assert result.status == RunStatus.RUNNING
        assert result.message == "Job is running on compute environment"

    def test_describe_run_maps_batch_status_to_run_status(self):
        """Test that describe_run maps AWS Batch statuses to RunStatus."""
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
        )

        # Mock list_jobs to return a job ID
        mock_batch_client.list_jobs.return_value = {
            "jobSummaryList": [{"jobId": "abc-123-job-id", "jobName": "job-123-run-42"}]
        }

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

    def test_describe_run_raises_if_job_not_found_in_batch(self):
        """Test that describe_run raises ValueError if job not found in AWS Batch."""
        # ARRANGE
        mock_batch_client = Mock()
        mock_batch_client.list_jobs.return_value = {"jobSummaryList": []}  # No jobs found

        runner = AWSBatchSimulationRunner(batch_client=mock_batch_client)

        run = Run.create_persisted(
            run_id=42,
            job_id=123,
            user_id=456,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            request={"simulation": "test"},
        )

        # ACT & ASSERT
        with pytest.raises(ValueError, match="Job not found"):
            runner.describe_run(run)


class TestAWSBatchSimulationRunnerCancel:
    """Tests for cancel_run method."""

    def test_cancel_run_uses_name_lookup_and_terminates_job(self):
        """Test that cancel_run looks up job by name then terminates it."""
        # ARRANGE
        mock_batch_client = Mock()
        mock_batch_client.list_jobs.return_value = {
            "jobSummaryList": [
                {
                    "jobId": "abc-123-job-id",
                    "jobName": "job-123-run-42",
                    "status": "RUNNING",
                }
            ]
        }
        mock_batch_client.terminate_job.return_value = {}

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
        runner.cancel_run(run)

        # ASSERT
        mock_batch_client.list_jobs.assert_called_once()
        call_kwargs = mock_batch_client.list_jobs.call_args[1]
        assert call_kwargs["filters"] == [{"name": "JOB_NAME", "values": ["job-123-run-42"]}]
        mock_batch_client.terminate_job.assert_called_once_with(
            jobId="abc-123-job-id", reason="User requested cancellation"
        )

    def test_cancel_run_raises_if_job_not_found(self):
        """Test that cancel_run raises ValueError if job not found in AWS Batch."""
        # ARRANGE
        mock_batch_client = Mock()
        mock_batch_client.list_jobs.return_value = {"jobSummaryList": []}  # No jobs found

        runner = AWSBatchSimulationRunner(batch_client=mock_batch_client)

        run = Run.create_persisted(
            run_id=42,
            job_id=123,
            user_id=456,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            request={"simulation": "test"},
        )

        # ACT & ASSERT
        with pytest.raises(ValueError, match="Job not found"):
            runner.cancel_run(run)


class TestAWSBatchSimulationRunnerConstants:
    """Tests for gateway constants."""

    def test_gateway_uses_correct_job_definition_arn(self):
        """Test that gateway has correct job definition name format."""
        # ARRANGE
        mock_batch_client = Mock()
        mock_batch_client.submit_job.return_value = {"jobId": "test-id"}

        runner = AWSBatchSimulationRunner(
            batch_client=mock_batch_client,
            job_queue_name="fred-batch-queue-dev",
            job_definition_name="fred-simulation-runner-dev"
        )

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
        # Verify job definition name matches expected format
        assert call_kwargs["jobDefinition"] == "fred-simulation-runner-dev"

    def test_gateway_uses_correct_job_queue_name(self):
        """Test that gateway has correct job queue name format."""
        # ARRANGE
        mock_batch_client = Mock()
        mock_batch_client.submit_job.return_value = {"jobId": "test-id"}

        runner = AWSBatchSimulationRunner(
            batch_client=mock_batch_client,
            job_queue_name="fred-batch-queue-dev",
            job_definition_name="fred-simulation-runner-dev"
        )

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
        assert call_kwargs["jobQueue"] == "fred-batch-queue-dev"
