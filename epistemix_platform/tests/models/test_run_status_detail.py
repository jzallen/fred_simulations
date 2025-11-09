"""
Tests for RunStatusDetail model with pod_phase field.

Following TDD Red-Green-Refactor cycle for FRED-46.
"""

from epistemix_platform.models.run import PodPhase, RunStatus, RunStatusDetail


class TestRunStatusDetail:
    """Test RunStatusDetail with pod_phase field."""

    def test_run_status_detail_includes_pod_phase(self):
        """RunStatusDetail should include pod_phase field."""
        # ARRANGE
        status = RunStatus.RUNNING
        message = "Job is running"
        pod_phase = PodPhase.RUNNING

        # ACT
        status_detail = RunStatusDetail(status=status, message=message, pod_phase=pod_phase)

        # ASSERT
        assert status_detail.status == RunStatus.RUNNING
        assert status_detail.message == "Job is running"
        assert status_detail.pod_phase == PodPhase.RUNNING

    def test_run_status_detail_with_queued_status(self):
        """RunStatusDetail should support QUEUED status with PENDING phase."""
        # ARRANGE
        status = RunStatus.QUEUED
        message = "Job submitted to queue"
        pod_phase = PodPhase.PENDING

        # ACT
        status_detail = RunStatusDetail(status=status, message=message, pod_phase=pod_phase)

        # ASSERT
        assert status_detail.status == RunStatus.QUEUED
        assert status_detail.pod_phase == PodPhase.PENDING

    def test_run_status_detail_with_done_status(self):
        """RunStatusDetail should support DONE status with SUCCEEDED phase."""
        # ARRANGE
        status = RunStatus.DONE
        message = "Job completed successfully"
        pod_phase = PodPhase.SUCCEEDED

        # ACT
        status_detail = RunStatusDetail(status=status, message=message, pod_phase=pod_phase)

        # ASSERT
        assert status_detail.status == RunStatus.DONE
        assert status_detail.pod_phase == PodPhase.SUCCEEDED

    def test_run_status_detail_with_error_status(self):
        """RunStatusDetail should support ERROR status with FAILED phase."""
        # ARRANGE
        status = RunStatus.ERROR
        message = "Job failed with exit code 1"
        pod_phase = PodPhase.FAILED

        # ACT
        status_detail = RunStatusDetail(status=status, message=message, pod_phase=pod_phase)

        # ASSERT
        assert status_detail.status == RunStatus.ERROR
        assert status_detail.pod_phase == PodPhase.FAILED
