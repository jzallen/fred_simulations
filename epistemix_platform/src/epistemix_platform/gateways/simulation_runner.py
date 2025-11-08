"""
AWS Batch implementation of simulation runner gateway.

Uses boto3 to submit and manage simulation runs on AWS Batch.
"""

import boto3
from botocore.config import Config
from epistemix_platform.models import Run, RunStatus, RunStatusDetail


class AWSBatchSimulationRunner:
    """
    AWS Batch implementation of simulation runner gateway.

    Uses boto3 client to submit, monitor, and cancel simulation runs
    on AWS Batch compute infrastructure.
    """

    def __init__(self, batch_client=None, job_queue_name=None, job_definition_name=None):
        """
        Initialize the AWS Batch simulation runner.

        Args:
            batch_client: Optional boto3 Batch client (for testing).
                         If None, creates a new client with timeout configuration.
            job_queue_name: AWS Batch job queue name (set by factory method)
            job_definition_name: AWS Batch job definition name (set by factory method)
        """
        if batch_client is None:
            # Configure boto3 with explicit timeouts to fail fast on network issues
            config = Config(
                connect_timeout=5,  # 5 seconds to establish connection
                read_timeout=60,    # 60 seconds to read response
                retries={'max_attempts': 3, 'mode': 'standard'}  # Retry on transient failures
            )
            batch_client = boto3.client("batch", config=config)

        self._batch_client = batch_client
        self._job_queue_name = job_queue_name
        self._job_definition_name = job_definition_name

    @classmethod
    def create(cls, environment: str, region: str = "us-east-1", batch_client=None):
        """
        Factory method to create an AWS Batch simulation runner for a specific environment.

        Args:
            environment: Environment name (dev, staging, prod)
            region: AWS region (default: us-east-1)
            batch_client: Optional boto3 Batch client (for testing)

        Returns:
            AWSBatchSimulationRunner configured for the environment
        """
        job_queue_name = f"fred-batch-queue-{environment}"
        job_definition_name = f"fred-simulation-runner-{environment}"

        if batch_client is None:
            # Configure boto3 with explicit timeouts to fail fast on network issues
            config = Config(
                connect_timeout=5,  # 5 seconds to establish connection
                read_timeout=60,    # 60 seconds to read response
                retries={'max_attempts': 3, 'mode': 'standard'}  # Retry on transient failures
            )
            batch_client = boto3.client("batch", region_name=region, config=config)

        return cls(
            batch_client=batch_client,
            job_queue_name=job_queue_name,
            job_definition_name=job_definition_name
        )

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
        job_name = run.natural_key

        # Prepare command to invoke simulation-runner CLI with job and run IDs
        # Command format: ["run", "--job-id", "11", "--run-id", "3"]
        command = [
            "run",
            "--job-id", str(run.job_id),
            "--run-id", str(run.id),
        ]

        # Submit job to AWS Batch with command override
        # Environment variables are set in the job definition
        self._batch_client.submit_job(
            jobName=job_name,
            jobQueue=self._job_queue_name,
            jobDefinition=self._job_definition_name,
            containerOverrides={"command": command},
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
            jobQueue=self._job_queue_name,
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
            jobQueue=self._job_queue_name,
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
