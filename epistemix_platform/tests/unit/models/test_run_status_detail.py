"""
Unit tests for RunStatusDetail model.

Tests for detailed run status information returned from AWS Batch.
"""

import pytest
from epistemix_platform.models.run import RunStatus, RunStatusDetail


class TestRunStatusDetail:
    """Tests for RunStatusDetail model."""

    def test_run_status_detail_has_status_and_message(self):
        """RED: Test that RunStatusDetail holds status and message."""
        # ARRANGE
        status = RunStatus.RUNNING
        message = "Job is running on compute environment"

        # ACT
        detail = RunStatusDetail(status=status, message=message)

        # ASSERT
        assert detail.status == RunStatus.RUNNING
        assert detail.message == "Job is running on compute environment"

    def test_run_status_detail_accepts_different_statuses(self):
        """RED: Test RunStatusDetail with different status values."""
        # ARRANGE & ACT
        queued = RunStatusDetail(status=RunStatus.QUEUED, message="Job submitted to queue")
        error = RunStatusDetail(status=RunStatus.ERROR, message="Job failed due to timeout")
        done = RunStatusDetail(status=RunStatus.DONE, message="Job completed successfully")

        # ASSERT
        assert queued.status == RunStatus.QUEUED
        assert queued.message == "Job submitted to queue"
        assert error.status == RunStatus.ERROR
        assert error.message == "Job failed due to timeout"
        assert done.status == RunStatus.DONE
        assert done.message == "Job completed successfully"

    def test_run_status_detail_message_can_be_empty(self):
        """RED: Test RunStatusDetail with empty message."""
        # ARRANGE & ACT
        detail = RunStatusDetail(status=RunStatus.QUEUED, message="")

        # ASSERT
        assert detail.status == RunStatus.QUEUED
        assert detail.message == ""

    def test_run_status_detail_equality(self):
        """Test equality based on status and message."""
        # ARRANGE
        detail1 = RunStatusDetail(status=RunStatus.RUNNING, message="Test message")
        detail2 = RunStatusDetail(status=RunStatus.RUNNING, message="Test message")
        detail3 = RunStatusDetail(status=RunStatus.RUNNING, message="Different message")

        # ACT & ASSERT
        assert detail1 == detail2
        assert detail1 != detail3
