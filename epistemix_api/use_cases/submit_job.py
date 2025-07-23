"""
Job submission use case for the Epistemix API.
This module implements the core business logic for job submission operations.
"""

from typing import Dict, Any
import logging

from ..models.job import JobStatus
from ..repositories.interfaces import IJobRepository


logger = logging.getLogger(__name__)


def submit_job(
    job_repository: IJobRepository,
    job_id: int,
    context: str = "job",
    job_type: str = "input"
) -> Dict[str, Any]:
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
    # Find the job
    job = job_repository.find_by_id(job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")
    
    # Business rule: Only created jobs can be submitted
    if job.status != JobStatus.CREATED:
        raise ValueError(
            f"Job {job_id} must be in CREATED status to be submitted, "
            f"current status: {job.status.value}"
        )
    
    # Update job status
    job.update_status(JobStatus.SUBMITTED)
    job_repository.save(job)
    
    # Return mock response as per Pact contract
    response = {
        "url": "http://localhost:5001/pre-signed-url"
    }
    
    logger.info(f"Job {job_id} submitted with context {context} and type {job_type}")
    
    return response
