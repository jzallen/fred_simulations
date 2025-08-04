"""
Job submission configuration use case for the Epistemix API.
This module implements the core business logic for job submission configuration.
"""

import logging

from epistemix_api.models.upload_location import UploadLocation


logger = logging.getLogger(__name__)


def submit_job_config(
    job_id: int,
    context: str = "job",
    job_type: str = "input"
) -> UploadLocation:
    """
    Submit a job for processing.
    
    This use case implements the core business logic for job submission.
    It validates business rules, updates the job status, and returns the response.
    
    Args:
        job_id: ID of the job to submit
        context: Context of the submission
        job_type: Type of the job submission
        
    Returns:
        Dictionary containing submission response (e.g., pre-signed URL)
        
    Raises:
        ValueError: If job doesn't exist or can't be submitted
    """
    
    # TODO: Generate pre-signed URL for job submission with S3
    job_configuration_location = UploadLocation(
        url=f"http://localhost:5001/pre-signed-url-job-config"  # Placeholder URL for example
    )
    
    # TODO: Understand why context and job_type are needed
    logger.info(f"Job {job_id} submitted with context {context} and type {job_type}")
    
    return job_configuration_location
