"""
Repository interfaces for the Epistemix API.
Defines contracts for data persistence using Protocol for type safety.
"""

from datetime import datetime
from typing import List, Optional, Protocol, runtime_checkable

from epistemix_api.models.job import Job, JobStatus
from epistemix_api.models.job_upload import JobUpload
from epistemix_api.models.run import Run, RunStatus
from epistemix_api.models.upload_content import UploadContent
from epistemix_api.models.upload_location import UploadLocation


@runtime_checkable
class IJobRepository(Protocol):
    """
    Protocol (interface) for job repository operations.

    This defines the contract that any job repository implementation must follow.
    Using Protocol provides structural typing and dependency inversion.
    """

    def save(self, job: Job) -> Job:
        """
        Save a job to the repository.

        For unpersisted jobs (job.id is None), assigns a new ID and persists the job.
        For persisted jobs (job.id is not None), updates the existing record.

        Args:
            job: The job to save

        Returns:
            The saved job with an assigned ID (if it was unpersisted)
        """
        ...

    def find_by_id(self, job_id: int) -> Optional[Job]:
        """
        Find a job by its ID.

        Args:
            job_id: The ID of the job to find

        Returns:
            The job if found, None otherwise
        """
        ...

    def find_by_user_id(self, user_id: int) -> List[Job]:
        """
        Find all jobs for a specific user.

        Args:
            user_id: The ID of the user

        Returns:
            List of jobs for the user
        """
        ...

    def find_by_status(self, status: JobStatus) -> List[Job]:
        """
        Find all jobs with a specific status.

        Args:
            status: The status to filter by

        Returns:
            List of jobs with the specified status
        """
        ...

    def find_all(self, limit: Optional[int] = None, offset: int = 0) -> List[Job]:
        """
        Find all jobs in the repository.

        Args:
            limit: Maximum number of jobs to return (None for all)
            offset: Number of jobs to skip (for pagination)

        Returns:
            List of all jobs
        """
        ...

    def exists(self, job_id: int) -> bool:
        """
        Check if a job exists.

        Args:
            job_id: The ID of the job to check

        Returns:
            True if the job exists, False otherwise
        """
        ...

    def delete(self, job_id: int) -> bool:
        """
        Delete a job from the repository.

        Args:
            job_id: The ID of the job to delete

        Returns:
            True if the job was deleted, False if it didn't exist
        """
        ...


@runtime_checkable
class IRunRepository(Protocol):
    """
    Protocol (interface) for run repository operations.

    This defines the contract that any run repository implementation must follow.
    Using Protocol provides structural typing and dependency inversion.
    """

    def save(self, run: Run) -> Run:
        """
        Save a run to the repository.

        For unpersisted runs (run.id is None), assigns a new ID and persists the run.
        For persisted runs (run.id is not None), updates the existing record.

        Args:
            run: The run to save

        Returns:
            The saved run with an assigned ID (if it was unpersisted)
        """
        ...

    def find_by_id(self, run_id: int) -> Optional[Run]:
        """
        Find a run by its ID.

        Args:
            run_id: The ID of the run to find

        Returns:
            The run if found, None otherwise
        """
        ...

    def find_by_job_id(self, job_id: int) -> List[Run]:
        """
        Find all runs for a specific job.

        Args:
            job_id: The ID of the job

        Returns:
            List of runs for the job
        """
        ...

    def find_by_user_id(self, user_id: int) -> List[Run]:
        """
        Find all runs for a specific user.

        Args:
            user_id: The ID of the user

        Returns:
            List of runs for the user
        """
        ...

    def find_by_status(self, status: RunStatus) -> List[Run]:
        """
        Find all runs with a specific status.

        Args:
            status: The status to filter by

        Returns:
            List of runs with the specified status
        """
        ...

    def exists(self, run_id: int) -> bool:
        """
        Check if a run exists.

        Args:
            run_id: The ID of the run to check

        Returns:
            True if the run exists, False otherwise
        """
        ...

    def delete(self, run_id: int) -> bool:
        """
        Delete a run from the repository.

        Args:
            run_id: The ID of the run to delete

        Returns:
            True if the run was deleted, False if it didn't exist
        """
        ...


@runtime_checkable
class IUploadLocationRepository(Protocol):
    """
    Protocol (interface) for upload location repository operations.

    This defines the contract that any upload location repository implementation must follow.
    Provides access to pre-signed URLs for uploading various types of content.
    """

    def get_upload_location(self, job_upload: JobUpload) -> UploadLocation:
        """
        Get an upload location (pre-signed URL) for a given job upload.

        Args:
            job_upload: JobUpload object containing job_id, context, job_type, and optional run_id

        Returns:
            UploadLocation containing the pre-signed URL for upload

        Raises:
            ValueError: If the job_upload is invalid or upload location cannot be generated
        """
        ...

    def read_content(self, location: UploadLocation) -> UploadContent:
        """
        Read the content from an upload location.

        This method abstracts the storage implementation details and returns
        the content in a domain model format.

        Args:
            location: The upload location to read from

        Returns:
            UploadContent domain model

        Raises:
            ValueError: If the content cannot be read or parsed
        """
        ...

    def archive_uploads(
        self, upload_locations: List[UploadLocation], age_threshold: Optional[datetime]
    ) -> List[UploadLocation]:
        """

        Args:
            upload_locations: List of UploadLocation objects to archive
            age_threshold: Optional datetime to filter uploads by age

        Returns:
            List of UploadLocation objects representing the archived uploads
        """
        ...
