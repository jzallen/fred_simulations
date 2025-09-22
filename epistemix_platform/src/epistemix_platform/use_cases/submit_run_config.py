"""
Run submission configuration use case for the Epistemix API.
This module implements the core business logic for run submission configuration.
"""

import logging

from epistemix_platform.models.job_upload import JobUpload
from epistemix_platform.models.upload_location import UploadLocation
from epistemix_platform.repositories.interfaces import IRunRepository, IUploadLocationRepository

logger = logging.getLogger(__name__)


def submit_run_config(
    run_repository: IRunRepository,
    upload_location_repository: IUploadLocationRepository,
    job_upload: JobUpload,
) -> UploadLocation:
    """
    Submit a run configuration for processing.

    This use case implements the core business logic for run configuration submission.
    It generates a pre-signed URL for uploading run configuration files.

    Args:
        run_repository: Repository for run persistence
        upload_location_repository: Repository for generating upload locations
        job_upload: JobUpload object with job_id, context, job_type, and optional run_id

    Returns:
        UploadLocation containing pre-signed URL for run configuration upload

    Raises:
        ValueError: If run configuration can't be submitted
    """

    # Use the upload location repository to generate the pre-signed URL
    run_configuration_location = upload_location_repository.get_upload_location(job_upload)

    # If we have a run_id, persist the URL to the run
    if job_upload.run_id is not None:
        run = run_repository.find_by_id(job_upload.run_id)
        if not run:
            raise ValueError(f"Run {job_upload.run_id} not found")

        run.config_url = run_configuration_location.url
        run_repository.save(run)
        # Log with sanitized URL to prevent credential leaks
        sanitized_url = run_configuration_location.get_sanitized_url()
        logger.info(f"Run {job_upload.run_id} config URL persisted: {sanitized_url}")

    logger.info(
        f"Run {job_upload.run_id} config for Job {job_upload.job_id} submitted with context "
        f"{job_upload.context} and type {job_upload.upload_type}"
    )

    return run_configuration_location
