"""
Unit tests for Boto3BatchClient.

Tests AWS Batch client implementation using mocked boto3.
"""

import pytest
from unittest.mock import Mock, MagicMock
from epistemix_platform.repositories.boto3_batch_client import Boto3BatchClient


class TestBoto3BatchClient:
    """Tests for Boto3BatchClient concrete implementation."""

    @pytest.fixture
    def mock_boto3_client(self):
        """Create a mock boto3 Batch client."""
        return Mock()

    @pytest.fixture
    def batch_client(self, mock_boto3_client, monkeypatch):
        """Create Boto3BatchClient with mocked boto3 client."""

        def mock_boto3_client_factory(service_name, region_name):
            return mock_boto3_client

        # Patch boto3.client to return our mock
        monkeypatch.setattr("boto3.client", mock_boto3_client_factory)

        return Boto3BatchClient(region_name="us-east-1")

    def test_submit_job_creates_batch_job_with_correct_parameters(
        self, batch_client, mock_boto3_client
    ):
        """RED: Test submit_job calls boto3 submit_job with correct parameters."""
        # ARRANGE
        mock_boto3_client.submit_job.return_value = {
            "jobId": "test-job-123",
            "jobName": "test-job",
            "jobArn": "arn:aws:batch:us-east-1:123456789012:job/test-job-123",
        }

        job_name = "test-job"
        job_queue = "arn:aws:batch:us-east-1:123456789012:job-queue/test-queue"
        job_definition = "arn:aws:batch:us-east-1:123456789012:job-definition/test-def"
        container_overrides = {
            "environment": [
                {"name": "JOB_ID", "value": "123"},
            ],
        }

        # ACT
        result = batch_client.submit_job(
            job_name=job_name,
            job_queue=job_queue,
            job_definition=job_definition,
            container_overrides=container_overrides,
        )

        # ASSERT
        mock_boto3_client.submit_job.assert_called_once_with(
            jobName=job_name,
            jobQueue=job_queue,
            jobDefinition=job_definition,
            containerOverrides=container_overrides,
        )
        assert result["job_id"] == "test-job-123"
        assert result["job_name"] == "test-job"
        assert result["job_arn"] == "arn:aws:batch:us-east-1:123456789012:job/test-job-123"

    def test_describe_jobs_queries_batch_api(self, batch_client, mock_boto3_client):
        """RED: Test describe_jobs calls boto3 describe_jobs."""
        # ARRANGE
        job_ids = ["job-123", "job-456"]
        mock_boto3_client.describe_jobs.return_value = {
            "jobs": [
                {
                    "jobId": "job-123",
                    "jobName": "test-job-1",
                    "status": "RUNNING",
                    "statusReason": None,
                    "startedAt": 1234567890,
                    "stoppedAt": None,
                    "container": {
                        "exitCode": None,
                        "logStreamName": "test-log-stream-1",
                    },
                },
                {
                    "jobId": "job-456",
                    "jobName": "test-job-2",
                    "status": "SUCCEEDED",
                    "statusReason": None,
                    "startedAt": 1234567890,
                    "stoppedAt": 1234567900,
                    "container": {
                        "exitCode": 0,
                        "logStreamName": "test-log-stream-2",
                    },
                },
            ]
        }

        # ACT
        results = batch_client.describe_jobs(job_ids)

        # ASSERT
        mock_boto3_client.describe_jobs.assert_called_once_with(jobs=job_ids)
        assert len(results) == 2
        assert results[0]["job_id"] == "job-123"
        assert results[0]["status"] == "RUNNING"
        assert results[1]["job_id"] == "job-456"
        assert results[1]["status"] == "SUCCEEDED"
        assert results[1]["exit_code"] == 0

    def test_describe_jobs_returns_empty_list_for_empty_input(
        self, batch_client, mock_boto3_client
    ):
        """RED: Test describe_jobs returns empty list for empty input."""
        # ARRANGE & ACT
        results = batch_client.describe_jobs([])

        # ASSERT
        mock_boto3_client.describe_jobs.assert_not_called()
        assert results == []

    def test_describe_jobs_handles_missing_optional_fields(
        self, batch_client, mock_boto3_client
    ):
        """RED: Test describe_jobs handles missing optional fields gracefully."""
        # ARRANGE
        job_ids = ["job-123"]
        mock_boto3_client.describe_jobs.return_value = {
            "jobs": [
                {
                    "jobId": "job-123",
                    "jobName": "test-job",
                    "status": "SUBMITTED",
                    # Missing statusReason, startedAt, stoppedAt, container
                }
            ]
        }

        # ACT
        results = batch_client.describe_jobs(job_ids)

        # ASSERT
        assert len(results) == 1
        assert results[0]["job_id"] == "job-123"
        assert results[0]["status_reason"] is None
        assert results[0]["started_at"] is None
        assert results[0]["stopped_at"] is None
        assert results[0]["exit_code"] is None
        assert results[0]["log_stream_name"] is None

    def test_cancel_job_terminates_batch_job(self, batch_client, mock_boto3_client):
        """RED: Test cancel_job calls boto3 terminate_job."""
        # ARRANGE
        job_id = "job-123"
        reason = "User requested cancellation"
        mock_boto3_client.terminate_job.return_value = {}

        # ACT
        batch_client.cancel_job(job_id, reason)

        # ASSERT
        mock_boto3_client.terminate_job.assert_called_once_with(
            jobId=job_id,
            reason=reason,
        )
