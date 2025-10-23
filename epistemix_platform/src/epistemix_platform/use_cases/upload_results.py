"""
Upload simulation results use case for the Epistemix API.
This module implements the core business logic for uploading FRED simulation results to S3.
"""

import io
import logging
import zipfile
from datetime import datetime
from pathlib import Path

from epistemix_platform.models.job_upload import JobUpload
from epistemix_platform.models.run import RunStatus
from epistemix_platform.repositories.interfaces import IRunRepository, IUploadLocationRepository


logger = logging.getLogger(__name__)


def upload_results(
    run_repository: IRunRepository,
    upload_location_repository: IUploadLocationRepository,
    job_id: int,
    run_id: int,
    results_dir: Path,
) -> str:
    """
    Upload FRED simulation results to S3 as a ZIP file.

    This use case:
    1. Validates the run exists and results directory contains FRED output
    2. Creates a ZIP file preserving directory structure
    3. Gets a presigned S3 URL for upload
    4. Uploads the ZIP to S3
    5. Updates the run with results_url and results_uploaded_at

    Args:
        run_repository: Repository for run persistence
        upload_location_repository: Repository for generating upload locations and S3 operations
        job_id: ID of the job
        run_id: ID of the run
        results_dir: Path to directory containing FRED output files

    Returns:
        S3 URL where results were uploaded

    Raises:
        ValueError: If validation fails or upload fails
    """
    # 1. Validate run exists
    run = run_repository.find_by_id(run_id)
    if not run:
        raise ValueError(f"Run {run_id} not found")

    if run.job_id != job_id:
        raise ValueError(f"Run {run_id} does not belong to job {job_id}")

    # 2. Validate results directory exists and contains FRED output
    if not results_dir.exists():
        raise ValueError(f"Results directory does not exist: {results_dir}")

    if not results_dir.is_dir():
        raise ValueError(f"Results path is not a directory: {results_dir}")

    # Accept either parent dir containing RUN* subdirs or a single RUN* dir
    run_dirs = [p for p in results_dir.glob("RUN*") if p.is_dir()]
    single_run_dir = results_dir.name.upper().startswith("RUN") and results_dir.is_dir()

    if not run_dirs and not single_run_dir:
        raise ValueError(
            f"No FRED output directories (RUN*) found in {results_dir}. "
            "Pass the parent directory containing RUN*/ subdirectories or a single RUN* directory."
        )

    logger.info(
        "Found %s in %s",
        f"{len(run_dirs)} RUN directories" if run_dirs else f"single directory {results_dir.name}",
        results_dir,
    )

    # 3. Create ZIP file in memory preserving directory structure
    zip_buffer = io.BytesIO()
    try:
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # Add all files recursively
            for file_path in results_dir.rglob("*"):
                if file_path.is_file():
                    # Build arcname, ensuring RUN*/ prefix at ZIP root
                    if run_dirs:
                        # Parent directory case: preserve relative path from results_dir
                        arcname = file_path.relative_to(results_dir)
                    else:
                        # Single RUN* directory case: prefix with directory name
                        arcname = Path(results_dir.name) / file_path.relative_to(results_dir)
                    zip_file.write(file_path, arcname=arcname.as_posix())
                    logger.debug(f"Added to ZIP: {arcname}")

        zip_buffer.seek(0)
        zip_size = len(zip_buffer.getvalue())
        logger.info(f"Created ZIP file: {zip_size} bytes ({zip_size / 1024 / 1024:.2f} MB)")

    except Exception as e:
        raise ValueError(f"Failed to create ZIP file: {e}")

    # 4. Get presigned S3 URL for upload
    job_upload = JobUpload(
        context="run",
        upload_type="results",
        job_id=job_id,
        run_id=run_id,
    )

    try:
        upload_location = upload_location_repository.get_upload_location(job_upload)
        logger.info(f"Got presigned URL for run {run_id} results upload")
    except Exception as e:
        raise ValueError(f"Failed to get upload location: {e}")

    # 5. Upload ZIP to S3 using presigned URL
    try:
        # Extract bucket and key from the upload location repository
        # We need direct S3 access to upload the actual content
        # The presigned URL is for PUT, so we use requests or boto3
        import requests

        response = requests.put(
            upload_location.url,
            data=zip_buffer.getvalue(),
            headers={"Content-Type": "application/zip"},
            timeout=300,  # 5 minute timeout for large files
        )

        if not response.ok:
            raise ValueError(
                f"S3 upload failed with status {response.status_code}: {response.text}"
            )

        logger.info(f"Successfully uploaded results ZIP to S3 ({zip_size} bytes)")

    except requests.exceptions.RequestException as e:
        raise ValueError(f"Failed to upload to S3: {e}")

    # 6. Update run with results URL and timestamp
    run.results_url = upload_location.url.split("?")[0]  # Remove query params (credentials)
    run.results_uploaded_at = datetime.utcnow()
    run.status = RunStatus.DONE  # Mark run as completed

    try:
        run_repository.save(run)
        logger.info(
            f"Updated run {run_id}: results_url set, status={run.status.value}, "
            f"uploaded_at={run.results_uploaded_at.isoformat()}"
        )
    except Exception as e:
        # Results were uploaded but database update failed
        logger.error(f"CRITICAL: Results uploaded to S3 but DB update failed: {e}")
        raise ValueError(f"Results uploaded to S3, but failed to update database: {e}")

    # Return the clean S3 URL (without credentials)
    return run.results_url
