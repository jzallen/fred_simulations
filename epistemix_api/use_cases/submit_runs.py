"""
Run submission use case for the Epistemix API.
This module implements the core business logic for run submission operations.
"""

from typing import Dict, List, Any, TypedDict
from datetime import datetime
import logging

from epistemix_api.models.run import Run, RunStatus, PodPhase
from epistemix_api.models.user import UserToken
from epistemix_api.repositories.interfaces import IRunRepository


class FredArgDict(TypedDict):
    """Type definition for FRED command line arguments."""
    flag: str
    value: str


class PopulationDict(TypedDict):
    """Type definition for population configuration."""
    version: str
    locations: List[str]


class RunRequestDict(TypedDict):
    """Type definition for individual run request data."""
    jobId: int
    workingDir: str
    size: str
    fredVersion: str
    population: PopulationDict
    fredArgs: List[FredArgDict]
    fredFiles: List[str]


logger = logging.getLogger(__name__)


def submit_runs(
    run_repository: IRunRepository,
    run_requests: List[RunRequestDict],
    user_token_value: str,
    epx_version: str = "epx_client_1.2.2"
) -> List[Run]:
    """
    Submit multiple run requests for processing.
    
    This use case implements the core business logic for run submission.
    It processes multiple run requests and returns run responses.
    
    Args:
        run_repository: Repository for run persistence
        run_requests: List of run request dictionaries to process
        user_token_value: The bearer token string containing user authentication
        epx_version: The epx client version used by the user

    Returns:
        Dictionary containing run responses
    """
    user_token = UserToken.from_bearer_token(user_token_value)
    run_responses = []
    
    for run_request in run_requests:
        # Extract client version from user agent
        epx_client_version = epx_version.split('_')[-1] if '_' in epx_version else "1.2.2"

        # Create a new Run domain object
        run = Run.create_unpersisted(
            job_id=run_request["jobId"],
            user_id=user_token.user_id,
            request=run_request,
            pod_phase=PodPhase.PENDING,
            container_status=None,
            status=RunStatus.SUBMITTED,
            user_deleted=False,
            epx_client_version=epx_client_version
        )
        
        run_responses.append(run_repository.save(run))
    
    return run_responses


# Legacy functions for backward compatibility
# These will be removed once all code is migrated to use the repository pattern

runs_storage: Dict[int, Dict[str, Any]] = {}
next_run_id = 978

def get_runs_storage() -> Dict[int, Dict[str, Any]]:
    """
    Get the runs storage dictionary for external access.
    
    DEPRECATED: This function is for backward compatibility only.
    Use the RunRepository instead.
    """
    return runs_storage
