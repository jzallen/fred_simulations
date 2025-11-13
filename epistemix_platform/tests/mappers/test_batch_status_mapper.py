"""
Tests for BatchStatusMapper - AWS Batch status to domain enum conversion.

"""

from epistemix_platform.mappers.batch_status_mapper import BatchStatusMapper
from epistemix_platform.models.run import PodPhase, RunStatus


class TestBatchStatusToRunStatus:
    def test_submitted_maps_to_queued(self):
        batch_status = "SUBMITTED"
        result = BatchStatusMapper.batch_status_to_run_status(batch_status)
        assert result == RunStatus.QUEUED

    def test_pending_maps_to_queued(self):
        batch_status = "PENDING"
        result = BatchStatusMapper.batch_status_to_run_status(batch_status)
        assert result == RunStatus.QUEUED

    def test_runnable_maps_to_queued(self):
        batch_status = "RUNNABLE"
        result = BatchStatusMapper.batch_status_to_run_status(batch_status)
        assert result == RunStatus.QUEUED

    def test_starting_maps_to_running(self):
        batch_status = "STARTING"
        result = BatchStatusMapper.batch_status_to_run_status(batch_status)
        assert result == RunStatus.RUNNING

    def test_running_maps_to_running(self):
        batch_status = "RUNNING"
        result = BatchStatusMapper.batch_status_to_run_status(batch_status)
        assert result == RunStatus.RUNNING

    def test_succeeded_maps_to_done(self):
        batch_status = "SUCCEEDED"
        result = BatchStatusMapper.batch_status_to_run_status(batch_status)
        assert result == RunStatus.DONE

    def test_failed_maps_to_error(self):
        batch_status = "FAILED"
        result = BatchStatusMapper.batch_status_to_run_status(batch_status)
        assert result == RunStatus.ERROR

    def test_unknown_status_maps_to_error(self):
        batch_status = "UNKNOWN_STATUS"
        result = BatchStatusMapper.batch_status_to_run_status(batch_status)
        assert result == RunStatus.ERROR


class TestBatchStatusToPodPhase:
    def test_submitted_maps_to_pending(self):
        batch_status = "SUBMITTED"
        result = BatchStatusMapper.batch_status_to_pod_phase(batch_status)
        assert result == PodPhase.PENDING

    def test_pending_maps_to_pending(self):
        batch_status = "PENDING"
        result = BatchStatusMapper.batch_status_to_pod_phase(batch_status)
        assert result == PodPhase.PENDING

    def test_runnable_maps_to_pending(self):
        batch_status = "RUNNABLE"
        result = BatchStatusMapper.batch_status_to_pod_phase(batch_status)
        assert result == PodPhase.PENDING

    def test_starting_maps_to_running(self):
        batch_status = "STARTING"
        result = BatchStatusMapper.batch_status_to_pod_phase(batch_status)
        assert result == PodPhase.RUNNING

    def test_running_maps_to_running(self):
        batch_status = "RUNNING"
        result = BatchStatusMapper.batch_status_to_pod_phase(batch_status)
        assert result == PodPhase.RUNNING

    def test_succeeded_maps_to_succeeded(self):
        batch_status = "SUCCEEDED"
        result = BatchStatusMapper.batch_status_to_pod_phase(batch_status)
        assert result == PodPhase.SUCCEEDED

    def test_failed_maps_to_failed(self):
        batch_status = "FAILED"
        result = BatchStatusMapper.batch_status_to_pod_phase(batch_status)
        assert result == PodPhase.FAILED

    def test_unknown_status_maps_to_unknown(self):
        batch_status = "UNKNOWN_STATUS"
        result = BatchStatusMapper.batch_status_to_pod_phase(batch_status)
        assert result == PodPhase.UNKNOWN


class TestPodPhaseToRunStatus:
    def test_pending_maps_to_queued(self):
        pod_phase = PodPhase.PENDING
        result = BatchStatusMapper.pod_phase_to_run_status(pod_phase)
        assert result == RunStatus.QUEUED

    def test_running_maps_to_running(self):
        pod_phase = PodPhase.RUNNING
        result = BatchStatusMapper.pod_phase_to_run_status(pod_phase)
        assert result == RunStatus.RUNNING

    def test_succeeded_maps_to_done(self):
        pod_phase = PodPhase.SUCCEEDED
        result = BatchStatusMapper.pod_phase_to_run_status(pod_phase)
        assert result == RunStatus.DONE

    def test_failed_maps_to_error(self):
        pod_phase = PodPhase.FAILED
        result = BatchStatusMapper.pod_phase_to_run_status(pod_phase)
        assert result == RunStatus.ERROR

    def test_unknown_maps_to_error(self):
        pod_phase = PodPhase.UNKNOWN
        result = BatchStatusMapper.pod_phase_to_run_status(pod_phase)
        assert result == RunStatus.ERROR
