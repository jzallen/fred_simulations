"""
List jobs use case for the Epistemix API.
This module implements the core business logic for listing all jobs.
"""

from typing import List, Optional
import logging

from epistemix_api.models.job import Job
from epistemix_api.repositories.interfaces import IJobRepository


logger = logging.getLogger(__name__)


def list_jobs(
    job_repository: IJobRepository,
    limit: Optional[int] = None,
    offset: int = 0,
    user_id: Optional[int] = None
) -> List[Job]:
    """
    List jobs from the repository.
    
    This use case implements the core business logic for listing jobs.
    It can list all jobs or filter by user ID.
    
    Args:
        job_repository: Repository for job persistence
        limit: Maximum number of jobs to return (None for all)
        offset: Number of jobs to skip (for pagination)
        user_id: Optional user ID to filter jobs by
        
    Returns:
        List of Job entities
        
    Raises:
        ValueError: If offset is negative
    """
    # Input validation
    if offset < 0:
        raise ValueError("Offset must be non-negative")
    
    if limit is not None and limit <= 0:
        raise ValueError("Limit must be positive")
    
    # Get jobs based on whether user_id is provided
    if user_id is not None:
        # Get all jobs for a specific user
        jobs = job_repository.find_by_user_id(user_id)
        
        # Apply manual pagination for user-filtered results
        if offset > 0:
            jobs = jobs[offset:]
        if limit is not None:
            jobs = jobs[:limit]
        
        logger.info(f"Retrieved {len(jobs)} jobs for user {user_id}")
    else:
        # Get all jobs with built-in pagination
        jobs = job_repository.find_all(limit=limit, offset=offset)
        logger.info(f"Retrieved {len(jobs)} jobs (limit={limit}, offset={offset})")
    
    return jobs