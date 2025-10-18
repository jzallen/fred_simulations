"""
Get job uploads use case for the Epistemix API.
This module retrieves upload metadata associated with a job.
"""

import logging
from typing import List

from epistemix_platform.models.job_upload import JobUpload
from epistemix_platform.models.upload_location import UploadLocation
from epistemix_platform.repositories.interfaces import IJobRepository, IRunRepository


logger = logging.getLogger(__name__)


def get_job_uploads(
    job_repository: IJobRepository, run_repository: IRunRepository, job_id: int
) -> List[JobUpload]:
    """
    Get all upload metadata associated with a job and its runs.

    This use case retrieves all upload locations for a job (config, input)
    and its associated runs. It returns only metadata, not the actual content.

    Args:
        job_repository: Repository for job persistence
        run_repository: Repository for run persistence
        job_id: ID of the job to get uploads for

    Returns:
        List of JobUpload domain models containing upload metadata

    Raises:
        ValueError: If job doesn't exist
    """
    # Check if job exists
    job = job_repository.find_by_id(job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")

    uploads = []

    # Add job-level uploads if they exist
    if job.input_location:
        upload = JobUpload(
            context="job",
            upload_type="input",
            job_id=job_id,
            location=UploadLocation(url=job.input_location),
            run_id=None,
        )
        uploads.append(upload)
        logger.info(f"Found job_input for job {job_id}")

    if job.config_location:
        upload = JobUpload(
            context="job",
            upload_type="config",
            job_id=job_id,
            location=UploadLocation(url=job.config_location),
            run_id=None,
        )
        uploads.append(upload)
        logger.info(f"Found job_config for job {job_id}")

    # Get runs for the job
    runs = run_repository.find_by_job_id(job_id)
    logger.info(f"Found {len(runs)} runs for job {job_id}")

    # Add run-related uploads
    for run in runs:
        # Check if run has a config URL stored
        if hasattr(run, "config_url") and run.config_url:
            upload = JobUpload(
                context="run",
                upload_type="config",  # This is a config URL, not output
                job_id=job_id,
                location=UploadLocation(url=run.config_url),
                run_id=run.id,
            )
            uploads.append(upload)
            logger.info(f"Found run_config for run {run.id}")

        # Check for run config if stored separately
        if hasattr(run, "config_location") and run.config_location:
            upload = JobUpload(
                context="run",
                upload_type="config",
                job_id=job_id,
                location=UploadLocation(url=run.config_location),
                run_id=run.id,
            )
            uploads.append(upload)
            logger.info(f"Found run_config for run {run.id}")

    return uploads
