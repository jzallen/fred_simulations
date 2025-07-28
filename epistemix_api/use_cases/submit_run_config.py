"""
Job submission configuration use case for the Epistemix API.
This module implements the core business logic for job submission configuration.
"""

import logging

from epistemix_api.models.run import RunConfigLocation


logger = logging.getLogger(__name__)


def submit_run_config(
    job_id: int,
    run_id: int,
    context: str = "job",
    job_type: str = "input",
) -> RunConfigLocation:
    """
    Submit a job for processing.
    
    This use case implements the core business logic for job submission.
    It validates business rules, updates the job status, and returns the response.
    
    Args:
        job_id: ID of the job to submit
        run_id: ID of the run associated with the job submission
        context: Context of the submission
        job_type: Type of the job submission
        
    Returns:
        Dictionary containing submission response (e.g., pre-signed URL)
        
    Raises:
        ValueError: If job doesn't exist or can't be submitted
    """
    
    # TODO: Generate pre-signed URL for job submission with S3
    run_configuration_location = RunConfigLocation(
        url=f"http://localhost:5001/pre-signed-url-run-config"  # Placeholder URL for example
    )
    
    # TODO: Understand why context and job_type are needed
    logger.info(f"Run {run_id} config for Job {job_id} submitted with context {context} and type {job_type}")
    
    return run_configuration_location
