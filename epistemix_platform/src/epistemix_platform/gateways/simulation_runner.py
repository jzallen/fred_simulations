"""
AWS Batch implementation of simulation runner gateway.

Uses boto3 to submit and manage simulation runs on AWS Batch.
"""

import os
import boto3
from epistemix_platform.models import Run, RunStatus, RunStatusDetail


# Constants for AWS Batch configuration
# These come from environment variables or use defaults
JOB_DEFINITION_ARN = os.getenv(
    "AWS_BATCH_JOB_DEFINITION",
    "arn:aws:batch:us-east-1:123456789012:job-definition/simulation-runner:1"
)
JOB_QUEUE_NAME = os.getenv("AWS_BATCH_JOB_QUEUE", "simulation-queue")


class AWSBatchSimulationRunner:
    """
    AWS Batch implementation of simulation runner gateway.

    Uses boto3 client to submit, monitor, and cancel simulation runs
    on AWS Batch compute infrastructure.
    """

    def __init__(self, batch_client=None):
        """
        Initialize the AWS Batch simulation runner.

        Args:
            batch_client: Optional boto3 Batch client (for testing).
                         If None, creates a new client.
        """
        self._batch_client = batch_client or boto3.client("batch")

    def submit_run(self, run: Run) -> None:
        """
        Submit a run to AWS Batch for execution.

        Uses run.natural_key() as the AWS Batch job name for tracking.
        AWS Batch is the source of truth for job state; no job ID is stored in the database.

        Args:
            run: The Run to submit

        Note:
            Does not modify the run object. AWS Batch maintains job state,
            and jobs can be looked up by name using run.natural_key().
        """
        # Use natural_key for job name
        job_name = run.natural_key()

        # Prepare environment variables for container
        environment = [
            {"name": "JOB_ID", "value": str(run.job_id)},
            {"name": "RUN_ID", "value": str(run.id)},
        ]

        # Submit job to AWS Batch (job ID not stored - AWS Batch is source of truth)
        self._batch_client.submit_job(
            jobName=job_name,
            jobQueue=JOB_QUEUE_NAME,
            jobDefinition=JOB_DEFINITION_ARN,
            containerOverrides={"environment": environment},
        )

    def describe_run(self, run: Run) -> RunStatusDetail:
        """
        Get current status of a run from AWS Batch using name-based lookup.

        Looks up the job in AWS Batch by natural key (job name), then retrieves
        detailed status information. AWS Batch is the source of truth for job state.

        Args:
            run: The Run to query

        Returns:
            RunStatusDetail with current status and message

        Raises:
            ValueError: If job not found in AWS Batch
        """
        # Look up job by name using natural_key
        job_name = run.natural_key()

        list_response = self._batch_client.list_jobs(
            jobQueue=JOB_QUEUE_NAME,
            filters=[{"name": "JOB_NAME", "values": [job_name]}],
        )

        job_list = list_response.get("jobSummaryList", [])
        if not job_list:
            raise ValueError(f"Job not found in AWS Batch: {job_name}")

        # Get the job ID from list_jobs
        job_id = job_list[0]["jobId"]

        # Query AWS Batch for detailed job status
        response = self._batch_client.describe_jobs(jobs=[job_id])

        if not response.get("jobs"):
            raise ValueError(f"Job not found: {job_id}")

        job = response["jobs"][0]
        batch_status = job["status"]
        status_reason = job.get("statusReason", "")

        # Map AWS Batch status to RunStatus
        status_mapping = {
            "SUBMITTED": RunStatus.QUEUED,
            "PENDING": RunStatus.QUEUED,
            "RUNNABLE": RunStatus.QUEUED,
            "STARTING": RunStatus.RUNNING,
            "RUNNING": RunStatus.RUNNING,
            "SUCCEEDED": RunStatus.DONE,
            "FAILED": RunStatus.ERROR,
        }

        run_status = status_mapping.get(batch_status, RunStatus.ERROR)

        return RunStatusDetail(status=run_status, message=status_reason)

    def cancel_run(self, run: Run) -> None:
        """
        Cancel a running simulation on AWS Batch using name-based lookup.

        Looks up the job in AWS Batch by natural key (job name), then terminates it.
        AWS Batch is the source of truth for job state.

        Args:
            run: The Run to cancel

        Raises:
            ValueError: If job not found in AWS Batch
        """
        # Look up job by name using natural_key
        job_name = run.natural_key()

        list_response = self._batch_client.list_jobs(
            jobQueue=JOB_QUEUE_NAME,
            filters=[{"name": "JOB_NAME", "values": [job_name]}],
        )

        job_list = list_response.get("jobSummaryList", [])
        if not job_list:
            raise ValueError(f"Job not found in AWS Batch: {job_name}")

        # Get the job ID from list_jobs
        job_id = job_list[0]["jobId"]

        # Terminate the Batch job
        self._batch_client.terminate_job(
            jobId=job_id, reason="User requested cancellation"
        )


def create_simulation_runner(batch_client=None):
    """
    Factory function to create a simulation runner gateway.

    Args:
        batch_client: Optional boto3 Batch client (for testing).
                     If None, creates a new client.

    Returns:
        AWSBatchSimulationRunner instance
    """
    return AWSBatchSimulationRunner(batch_client=batch_client)
