"""
Job submission use case for the Epistemix API.
This module implements the core business logic for job submission operations.
"""

from typing import Dict, Any
import logging

from epistemix_api.models.job import JobStatus
from epistemix_api.models.upload_location import UploadLocation
from epistemix_api.repositories.interfaces import IJobRepository, IUploadLocationRepository


logger = logging.getLogger(__name__)


def submit_job(
    job_repository: IJobRepository,
    upload_location_repository: IUploadLocationRepository,
    job_id: int,
    context: str = "job",
    job_type: str = "input"
) -> UploadLocation:
    """
    Submit a job for processing.
    
    This use case implements the core business logic for job submission.
    It validates business rules, updates the job status, and returns the response.
    
    Args:
        job_repository: Repository for job persistence
        upload_location_repository: Repository for generating upload locations
        job_id: ID of the job to submit
        context: Context of the submission
        job_type: Type of the job submission
        
    Returns:
        UploadLocation containing pre-signed URL for job submission
        
    Raises:
        ValueError: If job doesn't exist or can't be submitted
    """
    job = job_repository.find_by_id(job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")
    
    if job.status != JobStatus.CREATED:
        raise ValueError(
            f"Job {job_id} must be in CREATED status to be submitted, "
            f"current status: {job.status.value}"
        )
    
    # Generate the resource name for the upload location based on context and job type
    resource_name = f"job_{job_id}_{context}_{job_type}"
    
    # Use the upload location repository to generate the pre-signed URL
    job_input_location = upload_location_repository.get_upload_location(resource_name)
    
    # Update job status and save the upload URL
    job.update_status(JobStatus.SUBMITTED)
    
    # Store the URL based on the type
    if job_type == "input":
        job.input_location = job_input_location.url
    elif job_type == "config":
        job.config_location = job_input_location.url
    
    job_repository.save(job)
    
    logger.info(f"Job {job_id} submitted with context {context} and type {job_type}, URL: {job_input_location.url}")

    return job_input_location
