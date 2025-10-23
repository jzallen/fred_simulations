"""
Upload simulation results use case for the Epistemix API.

This module implements the core business logic for uploading FRED simulation
results to S3. Following clean architecture principles, this use case orchestrates
services and repositories without implementing business logic directly.
"""

import logging
from pathlib import Path

from epistemix_platform.exceptions import ResultsMetadataError
from epistemix_platform.models.run import RunStatus
from epistemix_platform.repositories.interfaces import IResultsRepository, IRunRepository
from epistemix_platform.services import IResultsPackager, ITimeProvider


logger = logging.getLogger(__name__)


def upload_results(
    run_repository: IRunRepository,
    results_packager: IResultsPackager,
    results_repository: IResultsRepository,
    time_provider: ITimeProvider,
    job_id: int,
    run_id: int,
    results_dir: Path,
) -> str:
    """
    Upload FRED simulation results to S3.

    This is a USE CASE (orchestration) function - it delegates all implementation
    details to services and repositories.

    Workflow:
    1. Validate run exists and belongs to job
    2. Package results directory into ZIP (delegated to results_packager)
    3. Upload ZIP to S3 (delegated to results_repository)
    4. Update run metadata with results URL and timestamp
    5. Handle failures with proper error types

    Args:
        run_repository: Repository for run persistence
        results_packager: Service for packaging results into ZIP
        results_repository: Repository for S3 results storage
        time_provider: Service for getting current time
        job_id: Job identifier
        run_id: Run identifier
        results_dir: Path to results directory

    Returns:
        S3 URL where results were uploaded

    Raises:
        ValueError: If run not found or doesn't belong to job
        InvalidResultsDirectoryError: If results directory is invalid
        ResultsStorageError: If S3 upload fails
        ResultsMetadataError: If database update fails after upload
    """
    # Step 1: Validate run exists and belongs to job
    run = run_repository.find_by_id(run_id)
    if not run:
        raise ValueError(f"Run {run_id} not found")

    if run.job_id != job_id:
        raise ValueError(f"Run {run_id} does not belong to job {job_id}")

    # Step 2: Package results directory into ZIP (delegates to service)
    # Raises: InvalidResultsDirectoryError, ResultsPackagingError
    packaged = results_packager.package_directory(results_dir)
    logger.info(
        f"Packaged {packaged.file_count} files from {packaged.directory_name} "
        f"({packaged.total_size_bytes / 1024 / 1024:.2f} MB)"
    )

    # Step 3: Upload ZIP to S3 (delegates to repository)
    # Raises: ResultsStorageError (with sanitized credentials)
    upload_location = results_repository.upload_results(
        job_id=job_id,
        run_id=run_id,
        zip_content=packaged.zip_content,
    )

    # Step 4: Update run metadata
    run.results_url = upload_location.url
    run.results_uploaded_at = time_provider.now_utc()
    run.status = RunStatus.DONE

    try:
        run_repository.save(run)
        logger.info(
            f"Updated run {run_id}: results_url={upload_location.url}, "
            f"status={run.status.value}, uploaded_at={run.results_uploaded_at.isoformat()}"
        )
    except Exception as e:
        # Database failed AFTER successful upload = orphaned S3 file
        logger.exception("CRITICAL: Results uploaded to S3 but database update failed")
        raise ResultsMetadataError(
            f"Results uploaded to S3 but database update failed: {e}",
            orphaned_s3_url=upload_location.url,
        ) from e

    return run.results_url
