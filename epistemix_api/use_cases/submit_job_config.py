"""
Job submission configuration use case for the Epistemix API.
This module implements the core business logic for job submission configuration.
"""

import logging

from epistemix_api.models.upload_location import UploadLocation
from epistemix_api.repositories.interfaces import IJobRepository, IUploadLocationRepository


logger = logging.getLogger(__name__)


def submit_job_config(
    job_repository: IJobRepository,
    upload_location_repository: IUploadLocationRepository,
    job_id: int,
    context: str = "job",
    job_type: str = "config"
) -> UploadLocation:
    """
    Submit a job configuration for processing.
    
    This use case implements the core business logic for job configuration submission.
    It generates a pre-signed URL for uploading job configuration files.
    
    Args:
        job_repository: Repository for job persistence
        upload_location_repository: Repository for generating upload locations
        job_id: ID of the job to submit configuration for
        context: Context of the submission (default: "job")
        job_type: Type of the job submission (default: "config")
        
    Returns:
        UploadLocation containing pre-signed URL for job configuration upload
        
    Raises:
        ValueError: If job configuration can't be submitted
    """
    # Get the job to update it with the config URL
    job = job_repository.find_by_id(job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")
    
    # Generate the resource name for the upload location based on context and job type
    resource_name = f"job_{job_id}_{context}_{job_type}"
    
    # Use the upload location repository to generate the pre-signed URL
    job_configuration_location = upload_location_repository.get_upload_location(resource_name)
    
    # Persist the config URL to the job
    job.config_location = job_configuration_location.url
    job_repository.save(job)
    
    logger.info(f"Job {job_id} configuration submitted with context {context} and type {job_type}, URL: {job_configuration_location.url}")
    
    return job_configuration_location
