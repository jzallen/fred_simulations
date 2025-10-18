"""
Job submission use case for the Epistemix API.
This module implements the core business logic for job submission operations.
"""

import logging

from epistemix_platform.models.job import JobStatus
from epistemix_platform.models.job_upload import JobUpload
from epistemix_platform.models.upload_location import UploadLocation
from epistemix_platform.repositories.interfaces import IJobRepository, IUploadLocationRepository


logger = logging.getLogger(__name__)


def submit_job(
    job_repository: IJobRepository,
    upload_location_repository: IUploadLocationRepository,
    job_upload: JobUpload,
) -> UploadLocation:
    """
    Submit a job for processing.

    This use case implements the core business logic for job submission.
    It validates business rules, updates the job status, and returns the response.

    Args:
        job_repository: Repository for job persistence
        upload_location_repository: Repository for generating upload locations
        job_upload: JobUpload object with job_id, context, and job_type

    Returns:
        UploadLocation containing pre-signed URL for job submission

    Raises:
        ValueError: If job doesn't exist or can't be submitted
    """
    job = job_repository.find_by_id(job_upload.job_id)
    if not job:
        raise ValueError(f"Job {job_upload.job_id} not found")

    if job.status != JobStatus.CREATED:
        raise ValueError(
            f"Job {job_upload.job_id} must be in CREATED status to be submitted, "
            f"current status: {job.status.value}"
        )

    # Use the upload location repository to generate the pre-signed URL
    job_input_location = upload_location_repository.get_upload_location(job_upload)

    # Update job status and save the upload URL
    job.update_status(JobStatus.SUBMITTED)

    # Store the URL based on the type
    if job_upload.upload_type == "input":
        job.input_location = job_input_location.url
    elif job_upload.upload_type == "config":
        job.config_location = job_input_location.url

    job_repository.save(job)

    # Log with sanitized URL to prevent credential leaks
    sanitized_url = job_input_location.get_sanitized_url()
    logger.info(
        f"Job {job_upload.job_id} submitted with context {job_upload.context} and type "
        f"{job_upload.upload_type}, URL: {sanitized_url}"
    )

    return job_input_location
