"""
Run submission use case for the Epistemix API.
This module implements the core business logic for run submission operations.
"""

import logging
import re
from typing import Any, Dict, List, TypedDict

from epistemix_platform.models.job_upload import JobUpload
from epistemix_platform.models.run import PodPhase, Run, RunStatus
from epistemix_platform.models.user import UserToken
from epistemix_platform.repositories.interfaces import IRunRepository, IUploadLocationRepository


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


def _parse_client_version(epx_version: str) -> str:
    """
    Parse and validate client version from user agent string.

    Extracts version number from strings like 'epx_client_1.2.2' or similar formats.
    Returns a valid semantic version or defaults to '1.2.2' if parsing fails.

    Args:
        epx_version: The client version string to parse

    Returns:
        Validated semantic version string (e.g., '1.2.2')
    """
    if not epx_version:
        logger.warning("Empty epx_version provided, using default 1.2.2")
        return "1.2.2"

    # Match semantic version pattern (major.minor.patch with optional additional parts)
    version_pattern = r"(\d+\.\d+\.\d+(?:\.\d+)*)"
    match = re.search(version_pattern, epx_version)

    if match:
        version = match.group(1)
        logger.debug(f"Extracted client version '{version}' from '{epx_version}'")
        return version

    # Fallback: try to extract version from common patterns like 'epx_client_1.2.2'
    parts = epx_version.split("_")
    if len(parts) >= 2:
        potential_version = parts[-1]
        # Validate it looks like a version number
        if re.match(r"^\d+\.\d+\.\d+", potential_version):
            logger.debug(f"Extracted fallback version '{potential_version}' from '{epx_version}'")
            return potential_version

    logger.warning(f"Could not parse version from '{epx_version}', using default 1.2.2")
    return "1.2.2"


def submit_runs(
    run_repository: IRunRepository,
    upload_location_repository: IUploadLocationRepository,
    run_requests: List[RunRequestDict],
    user_token_value: str,
    epx_version: str = "epx_client_1.2.2",
) -> List[Run]:
    """
    Submit multiple run requests for processing.

    This use case implements the core business logic for run submission.
    It processes multiple run requests and returns run responses.

    Args:
        run_repository: Repository for run persistence
        upload_location_repository: Repository for generating upload locations
        run_requests: List of run request dictionaries to process
        user_token_value: The bearer token string containing user authentication
        epx_version: The epx client version used by the user

    Returns:
        List of Run objects with persisted data
    """
    user_token = UserToken.from_bearer_token(user_token_value)
    run_responses = []

    for run_request in run_requests:
        # Extract and validate client version from user agent
        epx_client_version = _parse_client_version(epx_version)

        # Create a new Run domain object (without URL initially)
        run = Run.create_unpersisted(
            job_id=run_request["jobId"],
            user_id=user_token.user_id,
            request=run_request,
            pod_phase=PodPhase.PENDING,
            container_status=None,
            status=RunStatus.SUBMITTED,
            user_deleted=False,
            epx_client_version=epx_client_version,
        )

        # Save the run to get an ID
        persisted_run = run_repository.save(run)

        # Generate URL for this run using the persisted ID
        job_upload = JobUpload(
            context="run",
            upload_type="config",
            job_id=persisted_run.job_id,
            run_id=persisted_run.id,
        )
        upload_location = upload_location_repository.get_upload_location(job_upload)

        # Update the run with the URL
        persisted_run.config_url = upload_location.url

        # Save the updated run with the URL
        final_run = run_repository.save(persisted_run)

        run_responses.append(final_run)

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
