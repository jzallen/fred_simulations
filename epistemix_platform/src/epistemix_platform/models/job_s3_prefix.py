"""
JobS3Prefix value object for consistent S3 path generation.

This module provides a value object that ensures ALL artifacts for a job
use the same S3 prefix based on job.created_at, preventing timestamp
fragmentation when uploads happen seconds apart.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from epistemix_platform.models.job import Job  # pants: no-infer-dep


@dataclass(frozen=True)
class JobS3Prefix:
    """
    Value object representing the S3 prefix for all job artifacts.

    This ensures consistent S3 paths by using job.created_at as the timestamp
    for ALL uploads (job configs, run configs, results, logs). This prevents
    artifacts from being split across different S3 directories when uploads
    happen 1+ seconds apart.

    Immutable (frozen) to ensure the timestamp never changes once created.

    Example S3 structure:
        jobs/12/2025/10/23/211500/
          ├── job_config.json
          ├── job_input.zip
          ├── run_4_config.json
          ├── run_4_results.zip
          └── run_5_config.json

    Attributes:
        job_id: The job identifier
        timestamp: The job creation timestamp (from job.created_at)
    """

    job_id: int
    timestamp: datetime

    @classmethod
    def from_job(cls, job: "Job") -> "JobS3Prefix":
        """
        Create a JobS3Prefix from a Job domain model.

        Args:
            job: Job domain model with id and created_at

        Returns:
            JobS3Prefix instance using job's creation timestamp

        Example:
            >>> job = Job(id=12, user_id=1, tags=[], created_at=datetime(2025, 10, 23, 21, 15, 0))
            >>> prefix = JobS3Prefix.from_job(job)
            >>> prefix.base_prefix
            'jobs/12/2025/10/23/211500'
        """
        return cls(job_id=job.id, timestamp=job.created_at)

    @property
    def base_prefix(self) -> str:
        """
        Get the base S3 prefix for this job.

        Format: jobs/{job_id}/{yyyy}/{mm}/{dd}/{HHMMSS}

        Returns:
            S3 prefix string without trailing slash

        Example:
            >>> prefix = JobS3Prefix(job_id=12, timestamp=datetime(2025, 10, 23, 21, 15, 0))
            >>> prefix.base_prefix
            'jobs/12/2025/10/23/211500'
        """
        ts_path = self.timestamp.strftime("%Y/%m/%d/%H%M%S")
        return f"jobs/{self.job_id}/{ts_path}"

    # ==========================================================================
    # Job-level artifact keys
    # ==========================================================================

    def job_config_key(self) -> str:
        """
        Generate S3 key for job configuration file.

        Returns:
            S3 object key for job config JSON

        Example:
            'jobs/12/2025/10/23/211500/job_config.json'
        """
        return f"{self.base_prefix}/job_config.json"

    def job_input_key(self) -> str:
        """
        Generate S3 key for job input ZIP file.

        Returns:
            S3 object key for job input

        Example:
            'jobs/12/2025/10/23/211500/job_input.zip'
        """
        return f"{self.base_prefix}/job_input.zip"

    # ==========================================================================
    # Run-level artifact keys
    # ==========================================================================

    def run_config_key(self, run_id: int) -> str:
        """
        Generate S3 key for run configuration file.

        Args:
            run_id: The run identifier

        Returns:
            S3 object key for run config JSON

        Example:
            'jobs/12/2025/10/23/211500/run_4_config.json'
        """
        return f"{self.base_prefix}/run_{run_id}_config.json"

    def run_results_key(self, run_id: int) -> str:
        """
        Generate S3 key for run results ZIP file.

        Args:
            run_id: The run identifier

        Returns:
            S3 object key for run results

        Example:
            'jobs/12/2025/10/23/211500/run_4_results.zip'
        """
        return f"{self.base_prefix}/run_{run_id}_results.zip"

    def run_logs_key(self, run_id: int) -> str:
        """
        Generate S3 key for run logs file.

        Args:
            run_id: The run identifier

        Returns:
            S3 object key for run logs

        Example:
            'jobs/12/2025/10/23/211500/run_4_logs.log'
        """
        return f"{self.base_prefix}/run_{run_id}_logs.log"
