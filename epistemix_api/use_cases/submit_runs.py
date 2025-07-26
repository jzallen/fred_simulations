"""
Run submission use case for the Epistemix API.
This module implements the core business logic for run submission operations.
"""

from typing import Dict, List, Any, TypedDict
from datetime import datetime
import logging

from epistemix_api.models.run import Run, RunStatus, PodPhase
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
    epx_version: str = "epx_client_1.2.2"
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Submit multiple run requests for processing.
    
    This use case implements the core business logic for run submission.
    It processes multiple run requests and returns run responses.
    
    Args:
        run_repository: Repository for run persistence
        run_requests: List of run request dictionaries to process
        user_agent: User agent from request headers for client version
        
    Returns:
        Dictionary containing run responses
    """
    run_responses = []
    
    for run_request in run_requests:
        # Extract client version from user agent
        epx_client_version = epx_version.split('_')[-1] if '_' in epx_version else "1.2.2"

        # Create a new Run domain object
        run = Run.create_unpersisted(
            job_id=run_request["jobId"],
            user_id=555,  # Mock user ID - should come from authentication
            created_ts=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            request=run_request,
            pod_phase=PodPhase.RUNNING,
            container_status=None,
            status=RunStatus.SUBMITTED,
            user_deleted=False,
            epx_client_version=epx_client_version
        )
        
        # Save the run to the repository (this assigns an ID)
        saved_run = run_repository.save(run)
        
        # Create run response using the domain object
        run_response = saved_run.to_run_response_dict()
        run_responses.append(run_response)
    
    return {
        "runResponses": run_responses
    }


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
