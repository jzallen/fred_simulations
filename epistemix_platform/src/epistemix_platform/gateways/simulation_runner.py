"""
AWS Batch implementation of simulation runner gateway.

Uses boto3 to submit and manage simulation runs on AWS Batch.
"""

import boto3
from epistemix_platform.models import Run, RunStatus, RunStatusDetail


# Constants for AWS Batch configuration
# These should eventually come from environment variables or config
JOB_DEFINITION_ARN = (
    "arn:aws:batch:us-east-1:123456789012:job-definition/simulation-runner:1"
)
JOB_QUEUE_NAME = "simulation-queue"


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

        Args:
            run: The Run to submit

        Side Effects:
            Updates run.aws_batch_job_id with the returned job ID
        """
        # Use natural_key for job name
        job_name = run.natural_key()

        # Prepare environment variables for container
        environment = [
            {"name": "JOB_ID", "value": str(run.job_id)},
            {"name": "RUN_ID", "value": str(run.id)},
        ]

        # Submit job to AWS Batch
        response = self._batch_client.submit_job(
            jobName=job_name,
            jobQueue=JOB_QUEUE_NAME,
            jobDefinition=JOB_DEFINITION_ARN,
            containerOverrides={"environment": environment},
        )

        # Update run with Batch job ID
        run.aws_batch_job_id = response["jobId"]

    def describe_run(self, run: Run) -> RunStatusDetail:
        """
        Get current status of a run from AWS Batch.

        Args:
            run: The Run to query (must have aws_batch_job_id set)

        Returns:
            RunStatusDetail with current status and message

        Raises:
            ValueError: If run.aws_batch_job_id is None
        """
        if run.aws_batch_job_id is None:
            raise ValueError("Cannot describe run: aws_batch_job_id is None")

        # Query AWS Batch for job status
        response = self._batch_client.describe_jobs(jobs=[run.aws_batch_job_id])

        if not response.get("jobs"):
            raise ValueError(f"Job not found: {run.aws_batch_job_id}")

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
        Cancel a running simulation on AWS Batch.

        Args:
            run: The Run to cancel (must have aws_batch_job_id set)

        Raises:
            ValueError: If run.aws_batch_job_id is None
        """
        if run.aws_batch_job_id is None:
            raise ValueError("Cannot cancel run: aws_batch_job_id is None")

        # Terminate the Batch job
        self._batch_client.terminate_job(
            jobId=run.aws_batch_job_id, reason="User requested cancellation"
        )
