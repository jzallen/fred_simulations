"""
Job submission use case for the Epistemix API.
This module implements the core business logic for job submission operations.
"""

from typing import Dict, Any
import logging

from epistemix_api.models.job import JobStatus
from epistemix_api.models.upload_location import UploadLocation
from epistemix_api.repositories.interfaces import IJobRepository


logger = logging.getLogger(__name__)


def submit_job(
    job_repository: IJobRepository,
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
        job_id: ID of the job to submit
        context: Context of the submission
        job_type: Type of the job submission
        
    Returns:
        Dictionary containing submission response (e.g., pre-signed URL)
        
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
    
    job.update_status(JobStatus.SUBMITTED)
    job_repository.save(job)
    
    # TODO: Generate pre-signed URL for job submission with S3
    job_input_location = UploadLocation(
        url=f"http://localhost:5001/pre-signed-url"  # Placeholder URL for example
    )
    
    # TODO: Understand why context and job_type are needed
    logger.info(f"Job {job_id} submitted with context {context} and type {job_type}")

    return job_input_location
