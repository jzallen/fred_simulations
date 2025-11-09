"""
BatchStatusMapper - Maps AWS Batch statuses to domain enums.

This mapper provides stateless conversion between AWS Batch job statuses
and domain model enums (RunStatus and PodPhase).

Created for FRED-46: AWS Batch status synchronization.
"""

import logging

from epistemix_platform.models.run import PodPhase, RunStatus


logger = logging.getLogger(__name__)


class BatchStatusMapper:
    """
    Maps AWS Batch job statuses to domain model enums.

    This is a simple utility class with stateless methods for converting
    AWS Batch status strings to RunStatus and PodPhase enums.

    AWS Batch Status Values:
    - SUBMITTED: Job submitted but not yet scheduled
    - PENDING: Job accepted and scheduled for placement
    - RUNNABLE: Job ready to be placed on compute resource
    - STARTING: Job placed on compute resource and starting
    - RUNNING: Job actively executing
    - SUCCEEDED: Job completed successfully
    - FAILED: Job failed or was terminated

    Reference: https://docs.aws.amazon.com/batch/latest/userguide/job_states.html
    """

    @staticmethod
    def batch_status_to_run_status(batch_status: str) -> RunStatus:
        """
        Map AWS Batch status to RunStatus enum.

        Args:
            batch_status: AWS Batch job status (e.g., "SUBMITTED", "RUNNING")

        Returns:
            Corresponding RunStatus enum value

        Mapping:
            SUBMITTED, PENDING, RUNNABLE → QUEUED
            STARTING, RUNNING → RUNNING
            SUCCEEDED → DONE
            FAILED → ERROR
            Unknown → ERROR (with warning logged)
        """
        status_mapping = {
            "SUBMITTED": RunStatus.QUEUED,
            "PENDING": RunStatus.QUEUED,
            "RUNNABLE": RunStatus.QUEUED,
            "STARTING": RunStatus.RUNNING,
            "RUNNING": RunStatus.RUNNING,
            "SUCCEEDED": RunStatus.DONE,
            "FAILED": RunStatus.ERROR,
        }

        if batch_status not in status_mapping:
            logger.warning(f"Unknown AWS Batch status: {batch_status}, mapping to ERROR")
            return RunStatus.ERROR

        return status_mapping[batch_status]

    @staticmethod
    def batch_status_to_pod_phase(batch_status: str) -> PodPhase:
        """
        Map AWS Batch status to PodPhase enum.

        Args:
            batch_status: AWS Batch job status (e.g., "SUBMITTED", "RUNNING")

        Returns:
            Corresponding PodPhase enum value

        Mapping:
            SUBMITTED, PENDING, RUNNABLE → Pending
            STARTING, RUNNING → Running
            SUCCEEDED → Succeeded
            FAILED → Failed
            Unknown → Unknown (with warning logged)
        """
        phase_mapping = {
            "SUBMITTED": PodPhase.PENDING,
            "PENDING": PodPhase.PENDING,
            "RUNNABLE": PodPhase.PENDING,
            "STARTING": PodPhase.RUNNING,
            "RUNNING": PodPhase.RUNNING,
            "SUCCEEDED": PodPhase.SUCCEEDED,
            "FAILED": PodPhase.FAILED,
        }

        if batch_status not in phase_mapping:
            logger.warning(f"Unknown AWS Batch status: {batch_status}, mapping to UNKNOWN")
            return PodPhase.UNKNOWN

        return phase_mapping[batch_status]

    @staticmethod
    def pod_phase_to_run_status(pod_phase: PodPhase) -> RunStatus:
        """
        Map PodPhase to RunStatus for epx alignment.

        This provides the semantic mapping between Kubernetes pod execution phases
        and application-level run statuses as expected by epx.

        Args:
            pod_phase: PodPhase enum value

        Returns:
            Corresponding RunStatus enum value

        Mapping:
            Pending → QUEUED (job waiting to start)
            Running → RUNNING (job actively executing)
            Succeeded → DONE (job completed successfully)
            Failed → ERROR (job failed or terminated)
            Unknown → ERROR (unknown state, treat as error)
        """
        phase_to_status = {
            PodPhase.PENDING: RunStatus.QUEUED,
            PodPhase.RUNNING: RunStatus.RUNNING,
            PodPhase.SUCCEEDED: RunStatus.DONE,
            PodPhase.FAILED: RunStatus.ERROR,
            PodPhase.UNKNOWN: RunStatus.ERROR,
        }

        return phase_to_status[pod_phase]
