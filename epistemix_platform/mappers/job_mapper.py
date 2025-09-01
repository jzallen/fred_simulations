"""
Job mapper for converting between Job domain objects and JobRecord database records.
"""

from epistemix_platform.models.job import Job, JobStatus
from epistemix_platform.repositories.database import JobRecord, JobStatusEnum


class JobMapper:
    """
    Handles conversion between Job domain objects and JobRecord database records.

    This mapper provides bidirectional conversion methods to separate
    the mapping logic from the repository implementation.
    """

    @staticmethod
    def record_to_domain(job_record: JobRecord) -> Job:
        """
        Convert a JobRecord database record to a Job domain object.

        Args:
            job_record: The database record to convert

        Returns:
            A Job domain object with the same data
        """
        return Job.create_persisted(
            job_id=job_record.id,
            user_id=job_record.user_id,
            tags=job_record.tags,
            status=JobStatus(job_record.status.value),
            created_at=job_record.created_at,
            updated_at=job_record.updated_at,
            input_location=job_record.input_location,
            config_location=job_record.config_location,
            metadata=job_record.job_metadata,
        )

    @staticmethod
    def domain_to_record(job: Job) -> JobRecord:
        """
        Convert a Job domain object to a JobRecord database record.

        Args:
            job: The domain object to convert

        Returns:
            A JobRecord database record with the same data
        """
        return JobRecord(
            id=job.id,
            user_id=job.user_id,
            tags=job.tags,
            status=JobStatusEnum(job.status.value),
            created_at=job.created_at,
            updated_at=job.updated_at,
            input_location=job.input_location,
            config_location=job.config_location,
            job_metadata=job.metadata or {},
        )
