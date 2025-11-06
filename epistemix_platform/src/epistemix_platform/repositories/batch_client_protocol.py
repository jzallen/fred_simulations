"""
Protocol for AWS Batch operations.

Defines the interface for AWS Batch client implementations.
Uses Protocol (structural typing) for dependency injection flexibility.
"""

from typing import Protocol, TypedDict


class BatchJobSubmissionResult(TypedDict):
    """Result of submitting a job to AWS Batch."""

    job_id: str  # AWS Batch job ID
    job_name: str  # Job name
    job_arn: str  # Full ARN of the job


class BatchJobDetails(TypedDict):
    """Details of an AWS Batch job."""

    job_id: str  # AWS Batch job ID
    job_name: str  # Job name
    status: str  # AWS Batch status (SUBMITTED, RUNNING, SUCCEEDED, etc.)
    status_reason: str | None  # Reason for current status
    started_at: int | None  # Unix timestamp when job started
    stopped_at: int | None  # Unix timestamp when job stopped
    exit_code: int | None  # Container exit code
    log_stream_name: str | None  # CloudWatch Logs stream name


class BatchClientProtocol(Protocol):
    """Protocol for AWS Batch operations.

    Implementations must provide:
    - submit_job: Submit a job to AWS Batch
    - describe_jobs: Get details for multiple jobs
    - cancel_job: Cancel a running job
    """

    def submit_job(
        self,
        job_name: str,
        job_queue: str,
        job_definition: str,
        container_overrides: dict,
    ) -> BatchJobSubmissionResult:
        """Submit a job to AWS Batch.

        Args:
            job_name: Name for the job
            job_queue: ARN of the job queue
            job_definition: ARN of the job definition
            container_overrides: Container environment and command overrides

        Returns:
            BatchJobSubmissionResult with job_id, job_name, and job_arn

        Raises:
            ClientException: If AWS Batch API call fails
        """
        ...

    def describe_jobs(self, job_ids: list[str]) -> list[BatchJobDetails]:
        """Get details for multiple Batch jobs.

        Args:
            job_ids: List of AWS Batch job IDs (up to 100)

        Returns:
            List of BatchJobDetails for each job

        Raises:
            ClientException: If AWS Batch API call fails
        """
        ...

    def cancel_job(self, job_id: str, reason: str) -> None:
        """Cancel a running Batch job.

        Args:
            job_id: AWS Batch job ID to cancel
            reason: Human-readable reason for cancellation

        Raises:
            ClientException: If AWS Batch API call fails
        """
        ...
