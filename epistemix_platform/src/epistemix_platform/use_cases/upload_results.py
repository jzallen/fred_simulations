"""
Upload simulation results use case for the Epistemix API.

This module implements the core business logic for uploading FRED simulation
results to S3. Following clean architecture principles, this use case orchestrates
services and repositories without implementing business logic directly.
"""

import functools
import io
import logging
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from epistemix_platform.exceptions import (
    InvalidResultsDirectoryError,
    ResultsMetadataError,
    ResultsPackagingError,
)
from epistemix_platform.models.job_s3_prefix import JobS3Prefix
from epistemix_platform.models.run import RunStatus
from epistemix_platform.repositories.interfaces import (
    IJobRepository,
    IResultsRepository,
    IRunRepository,
)


logger = logging.getLogger(__name__)


# ============================================================================
# Results Packager - Internal to this use case
# ============================================================================


@dataclass(slots=True, frozen=True)
class PackagedResults:
    """
    Value object representing packaged simulation results.

    Immutable to ensure integrity - once created, content cannot change.
    This follows the value object pattern from Domain-Driven Design.

    Attributes:
        zip_content: Binary ZIP file content
        file_count: Number of files included in ZIP
        total_size_bytes: Total size of ZIP file in bytes
        directory_name: Name of the results directory (e.g., "RUN4")
    """

    zip_content: bytes
    file_count: int
    total_size_bytes: int
    directory_name: str


class _IResultsPackager(Protocol):
    """
    Protocol (interface) for packaging FRED simulation results (internal).

    This service abstracts file system operations and ZIP creation for
    the upload_results use case.
    """

    def package_directory(self, results_dir: Path) -> PackagedResults:
        """
        Package a FRED results directory into a ZIP file.

        Validates that:
        - Directory exists and is readable
        - Contains at least one RUN* subdirectory OR is itself a RUN* directory
        - Files can be zipped successfully

        Args:
            results_dir: Path to results directory

        Returns:
            PackagedResults value object with ZIP content and metadata

        Raises:
            InvalidResultsDirectoryError: If directory validation fails
            ResultsPackagingError: If ZIP creation fails
        """
        ...


class _FredResultsPackager:
    """
    Concrete implementation for packaging FRED simulation results.

    This service handles the FRED-specific directory structure conventions:
    - Results can be in a single RUN* directory
    - Or in a parent directory containing multiple RUN* subdirectories

    The ZIP file preserves the directory structure for compatibility with
    FRED analysis tools.
    """

    def package_directory(self, results_dir: Path) -> PackagedResults:
        """
        Package FRED results following current ZIP structure.

        The ZIP structure depends on input:
        - Single RUN4 directory: ZIP contains RUN4/file1.txt, RUN4/file2.txt
        - Parent with RUN1, RUN2: ZIP contains RUN1/..., RUN2/...

        Args:
            results_dir: Path to results directory

        Returns:
            PackagedResults with ZIP content and metadata

        Raises:
            InvalidResultsDirectoryError: If directory is invalid
            ResultsPackagingError: If ZIP creation fails
        """
        # Step 1: Validate directory exists
        self._validate_directory_exists(results_dir)

        # Step 2: Find RUN* directories
        run_dirs = self._find_run_directories(results_dir)
        is_single_run_dir = self._is_run_directory(results_dir)

        if not run_dirs and not is_single_run_dir:
            logger.warning(
                "No RUN* directories found: path=%s is_run_dir=%s run_dirs_count=%s. "
                "Expected either a RUN* directory or a parent containing RUN*/ subdirectories.",
                results_dir,
                is_single_run_dir,
                len(run_dirs),
            )
            raise InvalidResultsDirectoryError("No FRED output directories found")

        logger.info(
            "Found %s in %s",
            f"{len(run_dirs)} RUN directories"
            if run_dirs
            else f"single directory {results_dir.name}",
            results_dir,
        )

        # Step 3: Create ZIP in memory
        try:
            zip_content, file_count = self._create_zip(results_dir, run_dirs)
        except Exception as e:
            logger.exception("ZIP creation failed for %s", results_dir)
            raise ResultsPackagingError("Failed to create ZIP file") from e

        # Step 4: Get metadata
        total_size = len(zip_content)
        logger.info(f"Created ZIP file: {total_size} bytes ({total_size / 1024 / 1024:.2f} MB)")

        return PackagedResults(
            zip_content=zip_content,
            file_count=file_count,
            total_size_bytes=total_size,
            directory_name=results_dir.name,
        )

    def _validate_directory_exists(self, results_dir: Path) -> None:
        """
        Validate that directory exists and is actually a directory.

        Args:
            results_dir: Path to validate

        Raises:
            InvalidResultsDirectoryError: If validation fails
        """
        if not results_dir.exists():
            logger.error("Results directory does not exist: %s", results_dir)
            raise InvalidResultsDirectoryError("Results directory does not exist")

        if not results_dir.is_dir():
            logger.error("Path is not a directory: %s", results_dir)
            raise InvalidResultsDirectoryError("Path is not a directory")

    def _find_run_directories(self, path: Path) -> list[Path]:
        """
        Find all RUN* subdirectories in the given path.

        Args:
            path: Directory to search

        Returns:
            List of RUN* subdirectories
        """
        return [p for p in path.glob("RUN*") if p.is_dir()]

    def _is_run_directory(self, path: Path) -> bool:
        """
        Check if path itself is a RUN* directory.

        Args:
            path: Path to check

        Returns:
            True if path name starts with "RUN" (case-insensitive)
        """
        return path.name.upper().startswith("RUN") and path.is_dir()

    def _create_zip(self, results_dir: Path, run_dirs: list[Path]) -> tuple[bytes, int]:
        """
        Create ZIP file from results directory.

        SECURITY: Only includes files from RUN* directories and prevents symlink escape attacks.
        - Restricts iteration to RUN* subdirectories only
        - Skips symlinks to prevent directory traversal attacks
        - Validates resolved paths stay within results_dir root

        Args:
            results_dir: Root directory to zip
            run_dirs: List of RUN* subdirectories (if parent directory)

        Returns:
            Tuple of (zip_content_bytes, file_count)

        Raises:
            Exception: If ZIP creation fails (I/O error, permissions, etc.)
        """
        zip_buffer = io.BytesIO()
        file_count = 0

        # Resolve root path once for security checks
        root_path = results_dir.resolve()

        # Determine which directories to iterate (only RUN* dirs)
        targets = run_dirs if run_dirs else [results_dir]

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for base in targets:
                for file_path in base.rglob("*"):
                    if not file_path.is_file():
                        continue

                    # SECURITY: Prevent packaging files outside root via symlinks
                    try:
                        resolved = file_path.resolve()
                        resolved.relative_to(root_path)
                    except (ValueError, RuntimeError):
                        # File is outside root or symlink escape attempt
                        logger.warning("Skipping file outside root via symlink: %s", file_path)
                        continue

                    arcname = self._calculate_archive_name(file_path, results_dir, run_dirs)
                    zip_file.write(file_path, arcname=arcname.as_posix())
                    file_count += 1
                    logger.debug("Added to ZIP: %s", arcname)

        return zip_buffer.getvalue(), file_count

    def _calculate_archive_name(
        self, file_path: Path, results_dir: Path, run_dirs: list[Path]
    ) -> Path:
        """
        Calculate the archive path for a file in the ZIP.

        Logic:
        - Parent with multiple RUN* dirs: preserve relative path from parent
        - Single RUN* directory: prefix with RUN directory name

        Args:
            file_path: Path to file being added
            results_dir: Root results directory
            run_dirs: List of RUN* subdirectories

        Returns:
            Path to use as archive name in ZIP
        """
        if run_dirs:
            # Parent directory case: preserve relative path from results_dir
            # Example: results_dir=/output, file=/output/RUN1/data.txt -> RUN1/data.txt
            return file_path.relative_to(results_dir)
        # Single RUN* directory case: prefix with directory name
        # Example: results_dir=/output/RUN4, file=/output/RUN4/data.txt -> RUN4/data.txt
        return Path(results_dir.name) / file_path.relative_to(results_dir)


# ============================================================================
# Upload Results Use Case
# ============================================================================


def upload_results(
    run_repository: IRunRepository,
    job_repository: IJobRepository,
    results_packager: _IResultsPackager,
    results_repository: IResultsRepository,
    job_id: int,
    run_id: int,
    results_dir: Path,
) -> str:
    """
    Upload FRED simulation results to S3.

    This is a USE CASE (orchestration) function - it delegates all implementation
    details to services and repositories.

    Workflow:
    1. Fetch job to get created_at timestamp
    2. Validate run exists and belongs to job
    3. Create JobS3Prefix from job.created_at for consistent paths
    4. Package results directory into ZIP (delegated to results_packager)
    5. Upload ZIP to S3 with consistent prefix (delegated to results_repository)
    6. Update run metadata with results URL and timestamp
    7. Handle failures with proper error types

    Args:
        run_repository: Repository for run persistence
        job_repository: Repository for job persistence (to get job.created_at)
        results_packager: Service for packaging results into ZIP
        results_repository: Repository for S3 results storage
        job_id: Job identifier
        run_id: Run identifier
        results_dir: Path to results directory

    Returns:
        S3 URL where results were uploaded

    Raises:
        ValueError: If job/run not found or run doesn't belong to job
        InvalidResultsDirectoryError: If results directory is invalid
        ResultsStorageError: If S3 upload fails
        ResultsMetadataError: If database update fails after upload
    """
    # Step 1: Fetch job to get created_at timestamp for S3 prefix
    job = job_repository.find_by_id(job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")

    # Step 2: Validate run exists and belongs to job
    run = run_repository.find_by_id(run_id)
    if not run:
        raise ValueError(f"Run {run_id} not found")

    if run.job_id != job_id:
        raise ValueError(f"Run {run_id} does not belong to job {job_id}")

    # Step 3: Create S3 prefix from job.created_at for consistent timestamps
    s3_prefix = JobS3Prefix.from_job(job)

    # Step 4: Package results directory into ZIP (delegates to service)
    # Raises: InvalidResultsDirectoryError, ResultsPackagingError
    packaged = results_packager.package_directory(results_dir)
    logger.info(
        f"Packaged {packaged.file_count} files from {packaged.directory_name} "
        f"({packaged.total_size_bytes / 1024 / 1024:.2f} MB)"
    )

    # Step 5: Upload ZIP to S3 with consistent prefix (delegates to repository)
    # Raises: ResultsStorageError (with sanitized credentials)
    upload_location = results_repository.upload_results(
        job_id=job_id,
        run_id=run_id,
        zip_content=packaged.zip_content,
        s3_prefix=s3_prefix,
    )

    # Step 6: Update run metadata
    run.results_url = upload_location.url
    run.results_uploaded_at = datetime.utcnow()
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


def create_upload_results(
    run_repository: IRunRepository,
    job_repository: IJobRepository,
    results_repository: IResultsRepository,
):
    """
    Factory to create upload_results function with dependencies wired.

    Creates internal instance of results_packager that is only used by this use case.
    Time is obtained directly via datetime.utcnow() (can be mocked with freezegun in tests).
    """
    # Create internal dependencies
    results_packager = _FredResultsPackager()

    return functools.partial(
        upload_results,
        run_repository,
        job_repository,
        results_packager,
        results_repository,
    )
