"""
Run submission configuration use case for the Epistemix API.
This module implements the core business logic for run submission configuration.
"""

import logging
from typing import Optional

from epistemix_api.models.upload_location import UploadLocation
from epistemix_api.repositories.interfaces import IUploadLocationRepository


logger = logging.getLogger(__name__)


def submit_run_config(
    upload_location_repository: IUploadLocationRepository,
    job_id: int,
    context: str = "run",
    job_type: str = "config",
    run_id: Optional[int] = None,
) -> UploadLocation:
    """
    Submit a run configuration for processing.
    
    This use case implements the core business logic for run configuration submission.
    It generates a pre-signed URL for uploading run configuration files.
    
    Args:
        upload_location_repository: Repository for generating upload locations
        job_id: ID of the job to submit
        context: Context of the submission (default: "run")
        job_type: Type of the job submission (default: "config")
        run_id: Optional ID of the run associated with the job submission
        
    Returns:
        UploadLocation containing pre-signed URL for run configuration upload
        
    Raises:
        ValueError: If run configuration can't be submitted
    """
    
    # Generate the resource name for the upload location
    if run_id is not None:
        resource_name = f"job_{job_id}_run_{run_id}_{context}_{job_type}"
    else:
        resource_name = f"job_{job_id}_{context}_{job_type}"
    
    # Use the upload location repository to generate the pre-signed URL
    run_configuration_location = upload_location_repository.get_upload_location(resource_name)
    
    logger.info(f"Run {run_id} config for Job {job_id} submitted with context {context} and type {job_type}")
    
    return run_configuration_location
