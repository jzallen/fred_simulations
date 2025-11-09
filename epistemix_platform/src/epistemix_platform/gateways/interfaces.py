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

    AWS Batch is the source of truth for job state. Jobs are tracked by
    name (run.natural_key) rather than storing job IDs in the database.
    """

    def submit_run(self, run: Run) -> None:
        """
        Submit a run for execution.

        Uses run.natural_key as the job name for tracking in AWS Batch.
        Does not modify the run object; AWS Batch is the source of truth.

        Args:
            run: The Run to submit for execution

        Note:
            Implementation will call aws_batch.submit_job internally with
            jobName=run.natural_key. Job definition ARN and queue name
            are constants within the implementation.
        """
        ...

    def describe_run(self, run: Run) -> RunStatusDetail:
        """
        Get current status of a run from AWS Batch.

        Looks up the job by name (run.natural_key), then queries status.
        AWS Batch is the source of truth for job state.

        Args:
            run: The Run to query status for

        Returns:
            RunStatusDetail with current state and message from AWS Batch

        Raises:
            ValueError: If job not found in AWS Batch

        Note:
            Implementation will call aws_batch.list_jobs (with name filter)
            and aws_batch.describe_jobs internally. Maps AWS Batch status
            to RunStatus enum.
        """
        ...

    def cancel_run(self, run: Run) -> None:
        """
        Cancel a running simulation on AWS Batch.

        Looks up the job by name (run.natural_key), then terminates it.
        AWS Batch is the source of truth for job state.

        Args:
            run: The Run to cancel

        Raises:
            ValueError: If job not found in AWS Batch

        Note:
            Implementation will call aws_batch.list_jobs (with name filter)
            and aws_batch.terminate_job internally.
        """
        ...
