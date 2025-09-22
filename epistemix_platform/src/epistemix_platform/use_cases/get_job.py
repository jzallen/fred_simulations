"""
Job retrieval use case for the Epistemix API.
This module implements the core business logic for job retrieval operations.
"""

import logging
from typing import Optional

from ..models.job import Job
from ..repositories.interfaces import IJobRepository

logger = logging.getLogger(__name__)


def get_job(job_repository: IJobRepository, job_id: int) -> Optional[Job]:
    """
    Retrieve a job by ID.

    This use case implements the core business logic for job retrieval.
    It validates business rules and returns the job if found.

    Args:
        job_repository: Repository for job persistence
        job_id: ID of the job to retrieve

    Returns:
        The Job entity if found, None otherwise

    Raises:
        ValueError: If job_id is invalid
    """
    # Input validation
    if job_id <= 0:
        raise ValueError("Job ID must be positive")

    # Retrieve the job
    job = job_repository.find_by_id(job_id)

    if job:
        logger.info(f"Job {job_id} retrieved successfully")
    else:
        logger.error(f"Job {job_id} not found")

    return job
