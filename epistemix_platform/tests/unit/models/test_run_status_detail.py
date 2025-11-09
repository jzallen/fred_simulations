"""
Unit tests for RunStatusDetail model.

Tests for detailed run status information returned from AWS Batch.
"""

import pytest
from epistemix_platform.models.run import PodPhase, RunStatus, RunStatusDetail


class TestRunStatusDetail:
    """Tests for RunStatusDetail model."""

    def test_run_status_detail_has_status_and_message(self):
        """RED: Test that RunStatusDetail holds status, message, and pod_phase."""
        # ARRANGE
        status = RunStatus.RUNNING
        message = "Job is running on compute environment"
        pod_phase = PodPhase.RUNNING

        # ACT
        detail = RunStatusDetail(status=status, message=message, pod_phase=pod_phase)

        # ASSERT
        assert detail.status == RunStatus.RUNNING
        assert detail.message == "Job is running on compute environment"
        assert detail.pod_phase == PodPhase.RUNNING

    def test_run_status_detail_accepts_different_statuses(self):
        """RED: Test RunStatusDetail with different status values."""
        # ARRANGE & ACT
        queued = RunStatusDetail(status=RunStatus.QUEUED, message="Job submitted to queue", pod_phase=PodPhase.PENDING)
        error = RunStatusDetail(status=RunStatus.ERROR, message="Job failed due to timeout", pod_phase=PodPhase.FAILED)
        done = RunStatusDetail(status=RunStatus.DONE, message="Job completed successfully", pod_phase=PodPhase.SUCCEEDED)

        # ASSERT
        assert queued.status == RunStatus.QUEUED
        assert queued.message == "Job submitted to queue"
        assert queued.pod_phase == PodPhase.PENDING
        assert error.status == RunStatus.ERROR
        assert error.message == "Job failed due to timeout"
        assert error.pod_phase == PodPhase.FAILED
        assert done.status == RunStatus.DONE
        assert done.message == "Job completed successfully"
        assert done.pod_phase == PodPhase.SUCCEEDED

    def test_run_status_detail_message_can_be_empty(self):
        """RED: Test RunStatusDetail with empty message."""
        # ARRANGE & ACT
        detail = RunStatusDetail(status=RunStatus.QUEUED, message="", pod_phase=PodPhase.PENDING)

        # ASSERT
        assert detail.status == RunStatus.QUEUED
        assert detail.message == ""
        assert detail.pod_phase == PodPhase.PENDING

    def test_run_status_detail_equality(self):
        """Test equality based on status, message, and pod_phase."""
        # ARRANGE
        detail1 = RunStatusDetail(status=RunStatus.RUNNING, message="Test message", pod_phase=PodPhase.RUNNING)
        detail2 = RunStatusDetail(status=RunStatus.RUNNING, message="Test message", pod_phase=PodPhase.RUNNING)
        detail3 = RunStatusDetail(status=RunStatus.RUNNING, message="Different message", pod_phase=PodPhase.RUNNING)

        # ACT & ASSERT
        assert detail1 == detail2
        assert detail1 != detail3
