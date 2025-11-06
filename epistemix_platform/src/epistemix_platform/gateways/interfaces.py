"""
Gateway interface protocols.

Defines Protocol interfaces for external service integration.
Gateways handle communication with external systems like AWS Batch.
"""

from typing import Protocol
from epistemix_platform.models import Run, RunStatusDetail


class ISimulationRunner(Protocol):
    """
    Protocol for simulation execution gateways.

    Gateways implementing this protocol handle submission and monitoring
    of simulation runs on external compute infrastructure (e.g., AWS Batch).
    """

    def submit_run(self, run: Run) -> None:
        """
        Submit a run for execution.

        Args:
            run: The Run to submit for execution

        Side Effects:
            Updates run.aws_batch_job_id with the job ID returned from AWS Batch

        Note:
            Implementation will call aws_batch.submit_job internally
            Job definition ARN and queue name are constants within the implementation
        """
        ...

    def describe_run(self, run: Run) -> RunStatusDetail:
        """
        Get current status of a run.

        Args:
            run: The Run to query status for (must have aws_batch_job_id set)

        Returns:
            RunStatusDetail with current state and message from AWS Batch

        Raises:
            ValueError: If run.aws_batch_job_id is None

        Note:
            Implementation will call aws_batch.describe_jobs internally
            Maps AWS Batch status to RunStatus enum
        """
        ...

    def cancel_run(self, run: Run) -> None:
        """
        Cancel a running simulation.

        Args:
            run: The Run to cancel (must have aws_batch_job_id set)

        Raises:
            ValueError: If run.aws_batch_job_id is None

        Note:
            Implementation will call aws_batch.terminate_job internally
        """
        ...
