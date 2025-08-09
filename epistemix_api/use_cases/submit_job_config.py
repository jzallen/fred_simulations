"""
Job submission configuration use case for the Epistemix API.
This module implements the core business logic for job submission configuration.
"""

import logging

from epistemix_api.models.job_upload import JobUpload
from epistemix_api.models.upload_location import UploadLocation
from epistemix_api.repositories.interfaces import IJobRepository, IUploadLocationRepository

logger = logging.getLogger(__name__)


def submit_job_config(
    job_repository: IJobRepository,
    upload_location_repository: IUploadLocationRepository,
    job_upload: JobUpload,
) -> UploadLocation:
    """
    Submit a job configuration for processing.

    This use case implements the core business logic for job configuration submission.
    It generates a pre-signed URL for uploading job configuration files.

    Args:
        job_repository: Repository for job persistence
        upload_location_repository: Repository for generating upload locations
        job_upload: JobUpload object with job_id, context, and job_type

    Returns:
        UploadLocation containing pre-signed URL for job configuration upload

    Raises:
        ValueError: If job configuration can't be submitted
    """
    # Get the job to update it with the config URL
    job = job_repository.find_by_id(job_upload.job_id)
    if not job:
        raise ValueError(f"Job {job_upload.job_id} not found")

    # Use the upload location repository to generate the pre-signed URL
    job_configuration_location = upload_location_repository.get_upload_location(job_upload)

    # Persist the config URL to the job
    job.config_location = job_configuration_location.url
    job_repository.save(job)

    # Sanitize URL for logging (remove query string with AWS credentials)
    safe_url = (
        job_configuration_location.url.split("?")[0]
        if "?" in job_configuration_location.url
        else job_configuration_location.url
    )
    logger.info(
        f"Job {job_upload.job_id} configuration submitted with context {job_upload.context} and type {job_upload.upload_type}, URL: {safe_url}"
    )

    return job_configuration_location
