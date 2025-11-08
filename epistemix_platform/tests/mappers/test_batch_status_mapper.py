"""
Tests for BatchStatusMapper - AWS Batch status to domain enum conversion.

Following TDD Red-Green-Refactor cycle for FRED-46.
"""

import pytest
from epistemix_platform.mappers.batch_status_mapper import BatchStatusMapper
from epistemix_platform.models.run import PodPhase, RunStatus


class TestBatchStatusToRunStatus:
    """Test AWS Batch status to RunStatus mapping."""

    def test_submitted_maps_to_queued(self):
        """AWS Batch SUBMITTED status maps to RunStatus.QUEUED."""
        # ARRANGE
        batch_status = "SUBMITTED"

        # ACT
        result = BatchStatusMapper.batch_status_to_run_status(batch_status)

        # ASSERT
        assert result == RunStatus.QUEUED

    def test_pending_maps_to_queued(self):
        """AWS Batch PENDING status maps to RunStatus.QUEUED."""
        # ARRANGE
        batch_status = "PENDING"

        # ACT
        result = BatchStatusMapper.batch_status_to_run_status(batch_status)

        # ASSERT
        assert result == RunStatus.QUEUED

    def test_runnable_maps_to_queued(self):
        """AWS Batch RUNNABLE status maps to RunStatus.QUEUED."""
        # ARRANGE
        batch_status = "RUNNABLE"

        # ACT
        result = BatchStatusMapper.batch_status_to_run_status(batch_status)

        # ASSERT
        assert result == RunStatus.QUEUED

    def test_starting_maps_to_running(self):
        """AWS Batch STARTING status maps to RunStatus.RUNNING."""
        # ARRANGE
        batch_status = "STARTING"

        # ACT
        result = BatchStatusMapper.batch_status_to_run_status(batch_status)

        # ASSERT
        assert result == RunStatus.RUNNING

    def test_running_maps_to_running(self):
        """AWS Batch RUNNING status maps to RunStatus.RUNNING."""
        # ARRANGE
        batch_status = "RUNNING"

        # ACT
        result = BatchStatusMapper.batch_status_to_run_status(batch_status)

        # ASSERT
        assert result == RunStatus.RUNNING

    def test_succeeded_maps_to_done(self):
        """AWS Batch SUCCEEDED status maps to RunStatus.DONE."""
        # ARRANGE
        batch_status = "SUCCEEDED"

        # ACT
        result = BatchStatusMapper.batch_status_to_run_status(batch_status)

        # ASSERT
        assert result == RunStatus.DONE

    def test_failed_maps_to_error(self):
        """AWS Batch FAILED status maps to RunStatus.ERROR."""
        # ARRANGE
        batch_status = "FAILED"

        # ACT
        result = BatchStatusMapper.batch_status_to_run_status(batch_status)

        # ASSERT
        assert result == RunStatus.ERROR

    def test_unknown_status_maps_to_error(self):
        """Unknown AWS Batch status maps to RunStatus.ERROR."""
        # ARRANGE
        batch_status = "UNKNOWN_STATUS"

        # ACT
        result = BatchStatusMapper.batch_status_to_run_status(batch_status)

        # ASSERT
        assert result == RunStatus.ERROR


class TestBatchStatusToPodPhase:
    """Test AWS Batch status to PodPhase mapping."""

    def test_submitted_maps_to_pending(self):
        """AWS Batch SUBMITTED status maps to PodPhase.PENDING."""
        # ARRANGE
        batch_status = "SUBMITTED"

        # ACT
        result = BatchStatusMapper.batch_status_to_pod_phase(batch_status)

        # ASSERT
        assert result == PodPhase.PENDING

    def test_pending_maps_to_pending(self):
        """AWS Batch PENDING status maps to PodPhase.PENDING."""
        # ARRANGE
        batch_status = "PENDING"

        # ACT
        result = BatchStatusMapper.batch_status_to_pod_phase(batch_status)

        # ASSERT
        assert result == PodPhase.PENDING

    def test_runnable_maps_to_pending(self):
        """AWS Batch RUNNABLE status maps to PodPhase.PENDING."""
        # ARRANGE
        batch_status = "RUNNABLE"

        # ACT
        result = BatchStatusMapper.batch_status_to_pod_phase(batch_status)

        # ASSERT
        assert result == PodPhase.PENDING

    def test_starting_maps_to_running(self):
        """AWS Batch STARTING status maps to PodPhase.RUNNING."""
        # ARRANGE
        batch_status = "STARTING"

        # ACT
        result = BatchStatusMapper.batch_status_to_pod_phase(batch_status)

        # ASSERT
        assert result == PodPhase.RUNNING

    def test_running_maps_to_running(self):
        """AWS Batch RUNNING status maps to PodPhase.RUNNING."""
        # ARRANGE
        batch_status = "RUNNING"

        # ACT
        result = BatchStatusMapper.batch_status_to_pod_phase(batch_status)

        # ASSERT
        assert result == PodPhase.RUNNING

    def test_succeeded_maps_to_succeeded(self):
        """AWS Batch SUCCEEDED status maps to PodPhase.SUCCEEDED."""
        # ARRANGE
        batch_status = "SUCCEEDED"

        # ACT
        result = BatchStatusMapper.batch_status_to_pod_phase(batch_status)

        # ASSERT
        assert result == PodPhase.SUCCEEDED

    def test_failed_maps_to_failed(self):
        """AWS Batch FAILED status maps to PodPhase.FAILED."""
        # ARRANGE
        batch_status = "FAILED"

        # ACT
        result = BatchStatusMapper.batch_status_to_pod_phase(batch_status)

        # ASSERT
        assert result == PodPhase.FAILED

    def test_unknown_status_maps_to_unknown(self):
        """Unknown AWS Batch status maps to PodPhase.UNKNOWN."""
        # ARRANGE
        batch_status = "UNKNOWN_STATUS"

        # ACT
        result = BatchStatusMapper.batch_status_to_pod_phase(batch_status)

        # ASSERT
        assert result == PodPhase.UNKNOWN
