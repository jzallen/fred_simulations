"""
Boto3 implementation of BatchClientProtocol.

Concrete implementation using AWS boto3 library for AWS Batch operations.
"""

import boto3
from .batch_client_protocol import (
    BatchClientProtocol,
    BatchJobSubmissionResult,
    BatchJobDetails,
)


class Boto3BatchClient:
    """Concrete implementation of BatchClientProtocol using boto3.

    Uses boto3 to interact with AWS Batch API.
    """

    def __init__(self, region_name: str = "us-east-1"):
        """Initialize boto3 Batch client.

        Args:
            region_name: AWS region name (default: us-east-1)
        """
        self.client = boto3.client("batch", region_name=region_name)

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
        response = self.client.submit_job(
            jobName=job_name,
            jobQueue=job_queue,
            jobDefinition=job_definition,
            containerOverrides=container_overrides,
        )

        return {
            "job_id": response["jobId"],
            "job_name": response["jobName"],
            "job_arn": response["jobArn"],
        }

    def describe_jobs(self, job_ids: list[str]) -> list[BatchJobDetails]:
        """Get details for multiple Batch jobs.

        Args:
            job_ids: List of AWS Batch job IDs (up to 100)

        Returns:
            List of BatchJobDetails for each job

        Raises:
            ClientException: If AWS Batch API call fails
        """
        if not job_ids:
            return []

        # AWS Batch supports up to 100 jobs per call
        response = self.client.describe_jobs(jobs=job_ids)

        return [
            {
                "job_id": job["jobId"],
                "job_name": job["jobName"],
                "status": job["status"],
                "status_reason": job.get("statusReason"),
                "started_at": job.get("startedAt"),
                "stopped_at": job.get("stoppedAt"),
                "exit_code": job.get("container", {}).get("exitCode"),
                "log_stream_name": job.get("container", {}).get("logStreamName"),
            }
            for job in response["jobs"]
        ]

    def cancel_job(self, job_id: str, reason: str) -> None:
        """Cancel a running Batch job.

        Args:
            job_id: AWS Batch job ID to cancel
            reason: Human-readable reason for cancellation

        Raises:
            ClientException: If AWS Batch API call fails
        """
        self.client.terminate_job(jobId=job_id, reason=reason)
