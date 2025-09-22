"""
Get runs use case for the Epistemix API.
This module implements the core business logic for retrieving runs.
"""

import logging
from typing import List

from epistemix_platform.models.run import Run
from epistemix_platform.repositories.interfaces import IRunRepository

logger = logging.getLogger(__name__)


def get_runs_by_job_id(run_repository: IRunRepository, job_id: int) -> List[Run]:
    """
    Get all runs for a specific job.

    This use case implements the core business logic for retrieving runs
    by job ID.

    Args:
        run_repository: Repository for run persistence
        job_id: ID of the job to get runs for

    Returns:
        List of run business models associated with the job ID.
    """
    return run_repository.find_by_job_id(job_id)
