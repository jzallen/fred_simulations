"""
Job service for handling job-related business operations.
This service layer orchestrates business logic and coordinates between
the web layer and domain models.
"""

import logging
from pathlib import Path
from typing import Any, Self

from returns.result import Failure, Result, Success

from epistemix_platform.models.job import Job
from epistemix_platform.models.job_upload import JobUpload
from epistemix_platform.models.requests import RunRequest
from epistemix_platform.models.run import Run
from epistemix_platform.models.upload_content import UploadContent
from epistemix_platform.models.upload_location import UploadLocation
from epistemix_platform.gateways.interfaces import ISimulationRunner
from epistemix_platform.repositories import (
    IJobRepository,
    IRunRepository,
    IUploadLocationRepository,
)
from epistemix_platform.repositories.interfaces import IResultsRepository
from epistemix_platform.services.results_packager import FredResultsPackager
from epistemix_platform.services.time_provider import SystemTimeProvider
from epistemix_platform.use_cases.archive_uploads import create_archive_uploads
from epistemix_platform.use_cases.get_job_uploads import create_get_job_uploads
from epistemix_platform.use_cases.get_runs import create_get_runs_by_job_id
from epistemix_platform.use_cases.read_upload_content import create_read_upload_content
from epistemix_platform.use_cases.register_job import create_register_job
from epistemix_platform.use_cases.run_simulation import create_run_simulation
from epistemix_platform.use_cases.submit_job import create_submit_job
from epistemix_platform.use_cases.submit_job_config import create_submit_job_config
from epistemix_platform.use_cases.submit_run_config import create_submit_run_config
from epistemix_platform.use_cases.submit_runs import create_submit_runs
from epistemix_platform.use_cases.upload_results import create_upload_results
from epistemix_platform.use_cases.write_to_local import write_to_local


logger = logging.getLogger(__name__)


class JobController:
    """Controller for job-related operations in epistemix platform."""

    def __init__(self):
        """Initialize the job controller without dependencies.

        This constructor is best for tests when you need to override dependencies.
        The use case methods are intended to be private, so there is no public method
        to set them directly.

        Example:
        from unittest.mock import Mock
        from epistemix_platform.models.upload_location import UploadLocation

        mock_job = Job.create_persisted(job_id=1, user_id=123, tags=["test"])
        mock_location = UploadLocation(url="http://example.com/pre-signed-url", key="test.zip")
        job_controller = JobController()
        job_controller._register_job = Mock(return_value=mock_job)
        job_controller._submit_job = Mock(return_value=mock_location)
        job_controller._submit_job_config = Mock(return_value=mock_location)
        job_controller._submit_runs = Mock(return_value=[])
        job_controller._submit_run_config = Mock(return_value=mock_location)
        job_controller._get_runs_by_job_id = Mock(return_value=[])
        job_controller._get_job_uploads = Mock(return_value=[])
        job_controller._read_upload_content = Mock()
        job_controller._write_to_local = Mock()
        job_controller._archive_uploads = Mock(return_value=[])
        job_controller._upload_results = Mock(return_value="http://s3.url/results.zip")
        job_controller._run_simulation = Mock(return_value=mock_job)

        Use `create_with_repositories` to instantiate with repositories for production use.
        """
        pass

    @classmethod
    def create_with_repositories(
        cls,
        job_repository: IJobRepository,
        run_repository: IRunRepository,
        upload_location_repository: IUploadLocationRepository,
        results_repository: IResultsRepository,
        simulation_runner: ISimulationRunner,
    ) -> Self:
        """
        Create JobController with repositories.

        Args:
            job_repository: Repository for job persistence
            run_repository: Repository for run persistence
            upload_location_repository: Repository for upload locations (handles storage details)
            results_repository: Repository for results uploads
            simulation_runner: Gateway for AWS Batch integration (REQUIRED)

        Returns:
            Configured JobController instance
        """
        service = cls()

        service._register_job = create_register_job(job_repository)
        service._submit_job = create_submit_job(job_repository, upload_location_repository)
        service._submit_job_config = create_submit_job_config(
            job_repository, upload_location_repository
        )
        service._submit_runs = create_submit_runs(
            job_repository, run_repository, upload_location_repository
        )
        service._submit_run_config = create_submit_run_config(
            job_repository, run_repository, upload_location_repository
        )
        service._get_runs_by_job_id = create_get_runs_by_job_id(run_repository)
        service._get_job_uploads = create_get_job_uploads(job_repository, run_repository)
        service._read_upload_content = create_read_upload_content(upload_location_repository)
        service._write_to_local = write_to_local
        service._archive_uploads = create_archive_uploads(upload_location_repository)
        service._upload_results = create_upload_results(
            run_repository,
            job_repository,
            FredResultsPackager(),
            results_repository,
            SystemTimeProvider(),
        )
        service._run_simulation = create_run_simulation(simulation_runner)

        # Store dependencies for AWS Batch status synchronization (FRED-46)
        service._simulation_runner = simulation_runner
        service._run_repository = run_repository

        return service

    def register_job(
        self, user_token_value: str, tags: list[str] = None
    ) -> Result[dict[str, Any], str]:
        """
        Register a new job for a user.

        This is a public interface that delegates to the register_job use case.
        The service layer orchestrates the call to the business use case.

        Args:
            user_token_value: Token value containing user ID and registered scopes
            tags: Optional list of tags for the job

        Returns:
            Result containing either the created Job entity as a dict (Success)
            or an error message (Failure)
        """
        try:
            job = self._register_job(user_token_value=user_token_value, tags=tags)
            return Success(job.to_dict())
        except ValueError as e:
            logger.exception("Validation error in register_job")
            return Failure(str(e))
        except Exception:
            logger.exception("Unexpected error in register_job")
            return Failure("An unexpected error occurred while registering the job")

    def submit_job(
        self,
        job_id: int,
        context: str = "job",
        job_type: str = "input",
        run_id: int | None = None,
    ) -> Result[dict[str, str], str]:
        """
        Submit a job for processing.

        This is a public interface that delegates to the submit_job use case.
        The service layer orchestrates the call to the business use case.

        Args:
            job_id: ID of the job to submit
            context: Context of the submission
            job_type: Type of the job submission

        Returns:
            Result containing either the submission response dict (Success)
            or an error message (Failure)
        """
        try:
            # Create JobUpload object from parameters
            job_upload = JobUpload(
                context=context, upload_type=job_type, job_id=job_id, run_id=run_id
            )

            # Route to the appropriate use case based on context and type
            match (context, job_type):
                case ("job", "input"):
                    upload_location = self._submit_job(job_upload)
                case ("job", "config"):
                    upload_location = self._submit_job_config(job_upload)
                case ("run", "config"):
                    upload_location = self._submit_run_config(job_upload)
                case _:
                    raise ValueError(f"Unsupported context '{context}' or job type '{job_type}'")
            return Success(upload_location.to_dict())
        except ValueError as e:
            logger.exception("Validation error in submit_job")
            return Failure(str(e))
        except Exception:
            logger.exception("Unexpected error in submit_job")
            return Failure("An unexpected error occurred while submitting the job")

    def submit_runs(
        self,
        user_token_value: str,
        run_requests: list[RunRequest],
        epx_version: str = "epx_client_1.2.2",
    ) -> Result[dict[str, list[dict[str, Any]]], str]:
        """
        Submit multiple run requests for processing and execute them on AWS Batch.

        This is a public interface that:
        1. Calls submit_runs use case to create Run records in DB
        2. Calls run_simulation for each run to submit to AWS Batch

        Args:
            user_token_value: User token value for authentication
            run_requests: List of run requests to process
            epx_version: User agent from request headers for client version

        Returns:
            Result containing either the run responses dict (Success)
            or an error message (Failure)
        """
        try:
            # Step 1: Create Run records in database
            runs = self._submit_runs(
                run_requests=run_requests,
                user_token_value=user_token_value,
                epx_version=epx_version,
            )

            # Step 2: Submit each run to AWS Batch (simulation_runner is REQUIRED)
            for run in runs:
                self._run_simulation(run=run)

            run_responses = [run.to_run_response_dict() for run in runs]
            return Success(run_responses)
        except ValueError as e:
            logger.exception("Validation error in submit_runs")
            return Failure(str(e))
        except Exception:
            logger.exception("Unexpected error in submit_runs")
            return Failure("An unexpected error occurred while submitting the runs")

    def get_runs(self, job_id: int) -> Result[list[dict[str, Any]], str]:
        """
        Get all runs for a specific job with AWS Batch status synchronization (FRED-46).

        Fetches runs from database, then queries AWS Batch for current status of ALL runs
        (per FRED-46 requirements: no conditionals, query all runs).
        Updates database with fresh status if changed.

        Implements graceful degradation: if AWS Batch is unavailable, returns stale
        database status with warning log (system stays operational).

        This is a public interface that delegates to the get_runs_by_job_id use case
        and adds AWS Batch synchronization.

        Args:
            job_id: ID of the job to get runs for

        Returns:
            Result containing either the list of runs with updated status (Success)
            or an error message (Failure)
        """
        try:
            # Get runs from database
            runs = self._get_runs_by_job_id(job_id=job_id)

            # Synchronize status from AWS Batch for ALL runs (FRED-46)
            # Track metrics for observability (ENGINEER-03 pattern)
            updated_count = 0
            failed_count = 0

            for run in runs:
                try:
                    # Query AWS Batch using run.natural_key (FRED-46 requirement)
                    status_detail = self._simulation_runner.describe_run(run)

                    # Check if AWS Batch returned ERROR (API unavailable)
                    if (
                        status_detail.status.name == "ERROR"
                        and "AWS Batch API error" in status_detail.message
                    ):
                        # AWS Batch unavailable - fallback to stale DB status (ENGINEER-02 pattern)
                        logger.warning(
                            f"AWS Batch unavailable for run {run.id}, using stale DB status. "
                            f"Current DB status: {run.status.name}, pod_phase: {run.pod_phase.name}"
                        )
                        failed_count += 1
                        continue  # Keep DB status

                    # Update if status or pod_phase changed
                    if (
                        run.status != status_detail.status
                        or run.pod_phase != status_detail.pod_phase
                    ):
                        # Log status transition (ENGINEER-03 pattern)
                        logger.info(
                            f"Status change for run {run.id}: "
                            f"{run.status.name}/{run.pod_phase.name} → "
                            f"{status_detail.status.name}/{status_detail.pod_phase.name}"
                        )

                        # Update run model
                        run.status = status_detail.status
                        run.pod_phase = status_detail.pod_phase

                        # Persist to database
                        self._run_repository.save(run)
                        updated_count += 1

                except Exception as e:
                    logger.exception(f"Error synchronizing status for run {run.id}")
                    failed_count += 1

            # Log metrics (ENGINEER-03 pattern, simplified)
            logger.info(
                f"Status sync for job {job_id}: {len(runs)} runs, "
                f"{updated_count} updated, {failed_count} failed"
            )

            return Success([run.to_dict() for run in runs])

        except ValueError as e:
            logger.exception("Validation error in get_runs_by_job_id")
            return Failure(str(e))
        except Exception:
            logger.exception("Unexpected error in get_runs_by_job_id")
            return Failure("An unexpected error occurred while retrieving the runs")

    def get_job_uploads(
        self, job_id: int, include_content: bool = True
    ) -> Result[list[dict[str, Any]], str]:
        """
        Get all uploads associated with a job, optionally with their contents.

        This method orchestrates retrieving upload metadata and optionally reading
        the actual content from storage, combining them into a complete response.

        Args:
            job_id: ID of the job to get uploads for
            include_content: If True, fetch and include file contents in response

        Returns:
            Result containing list of uploads with optional content (Success)
            or an error message (Failure)
        """
        try:
            # Get upload metadata from use case
            uploads = self._get_job_uploads(job_id=job_id)

            # Process uploads based on whether content is requested
            results = []
            for upload in uploads:
                # Use sanitized dict to show sanitized URLs to users
                upload_dict = upload.to_sanitized_dict()

                if include_content:
                    try:
                        # Read content for this upload
                        content = self._read_upload_content(upload.location)
                        upload_dict["content"] = content.to_dict()
                    except ValueError as e:
                        # Include error information if content couldn't be read
                        upload_dict["error"] = str(e)
                        logger.warning(
                            f"Failed to read content for upload "
                            f"{upload.context}_{upload.upload_type} (job_id={job_id}): {e}"
                        )

                results.append(upload_dict)

            logger.info(f"Retrieved {len(results)} uploads for job {job_id}")
            return Success(results)

        except ValueError as e:
            logger.exception("Validation error in get_job_uploads")
            return Failure(str(e))
        except Exception:
            logger.exception("Unexpected error in get_job_uploads")
            return Failure("An unexpected error occurred while retrieving uploads")

    def download_job_uploads(
        self, job_id: int, base_path: Path, should_force: bool = False
    ) -> Result[str, str]:
        """
        Download all uploads associated with a job to a local directory.

        This method orchestrates downloading all job and run uploads to the specified
        base path directory. Files are saved with their original names in a flat structure.
        Existing files will be overwritten only if should_force=True.

        Args:
            job_id: ID of the job to download uploads for
            base_path: Path to the directory where files should be downloaded
            should_force: If True, overwrite existing files. If False, skip existing files

        Returns:
            Result containing the download directory path (Success)
            or an error message (Failure)
        """
        try:
            # Get upload metadata
            uploads = self._get_job_uploads(job_id=job_id)

            if not uploads:
                return Failure(f"No uploads found for job {job_id}")

            # Ensure the base path exists
            base_path.mkdir(parents=True, exist_ok=True)

            # Check if directory has existing files
            existing_files = list(base_path.iterdir())
            if existing_files and should_force:
                logger.info(
                    f"Directory {base_path} contains {len(existing_files)} existing files "
                    f"that may be overwritten (should_force=True)"
                )
            elif existing_files:
                logger.warning(
                    f"Directory {base_path} contains {len(existing_files)} existing files - "
                    f"will skip existing files (use should_force=True to overwrite)"
                )

            logger.info(
                f"Downloading job {job_id} uploads to {base_path} (should_force={should_force})"
            )

            downloaded_files = []
            skipped_files = []
            errors = []

            for upload in uploads:
                try:
                    # Determine filename from URL or use a default from the model
                    filename = upload.location.extract_filename()
                    if not filename:
                        filename = upload.get_default_filename()

                    # Check if file exists and handle based on should_force
                    file_path = base_path / filename

                    if file_path.exists() and not should_force:
                        logger.warning(f"Skipping existing file: {file_path}")
                        skipped_files.append(str(file_path))
                        continue

                    # Read content from storage
                    content = self._read_upload_content(upload.location)

                    # Use the write_to_local use case to handle the write operation
                    self._write_to_local(file_path, content, force=should_force)

                    downloaded_files.append(str(file_path))
                    logger.info(f"Downloaded {upload.context}_{upload.upload_type} to {file_path}")

                except Exception as e:
                    error_msg = f"Failed to download {upload.context}_{upload.upload_type}: {e}"
                    errors.append(error_msg)
                    logger.exception(error_msg)

            # Report results
            if errors and not downloaded_files:
                return Failure(f"Failed to download any files. Errors: {'; '.join(errors)}")

            # Build summary message
            summary_parts = []
            if downloaded_files:
                summary_parts.append(f"Downloaded {len(downloaded_files)} files")
            if skipped_files:
                summary_parts.append(f"skipped {len(skipped_files)} existing files")
            if errors:
                summary_parts.append(f"{len(errors)} errors")

            summary_message = ", ".join(summary_parts)

            if errors:
                logger.warning(f"{summary_message}")
            elif skipped_files:
                logger.info(f"{summary_message} (use should_force=True to overwrite)")
            else:
                logger.info(f"{summary_message}")

            return Success(str(base_path))

        except ValueError as e:
            logger.exception("Validation error in download_job_uploads")
            return Failure(str(e))
        except Exception:
            logger.exception("Unexpected error in download_job_uploads")
            return Failure("An unexpected error occurred while downloading uploads")

    def archive_job_uploads(
        self,
        job_id: int,
        days_since_create: int | None = None,
        hours_since_create: int | None = None,
        dry_run: bool = False,
    ) -> Result[list[dict[str, str]], str]:
        """
        Archive uploads for a specific job.

        This method orchestrates archiving uploads for a job, transitioning them
        to Glacier storage class to reduce costs. If no time threshold is specified,
        archives all uploads for the job.

        Args:
            job_id: ID of the job whose uploads should be archived
            days_since_create: Optional - only archive uploads older than specified days
            hours_since_create: Optional - only archive uploads older than specified hours
            dry_run: If True, only report what would be archived without making changes

        Returns:
            Result containing list of archived upload locations (Success)
            or an error message (Failure)
        """
        try:
            logger.info(
                f"{'DRY RUN: ' if dry_run else ''}Archiving uploads for job {job_id} "
                f"(days={days_since_create}, hours={hours_since_create})"
            )

            # Get all upload locations for the job
            uploads = self._get_job_uploads(job_id=job_id)

            if not uploads:
                logger.info(f"No uploads found for job {job_id}")
                return Success([])

            # Extract UploadLocation objects from JobUpload objects
            upload_locations = [upload.location for upload in uploads]

            logger.info(f"Found {len(upload_locations)} uploads for job {job_id}")

            # Use the archive_uploads use case
            archived_locations = self._archive_uploads(
                upload_locations=upload_locations,
                days_since_create=days_since_create,
                hours_since_create=hours_since_create,
                dry_run=dry_run,
            )

            # Serialize the archived locations using the model's method
            archived_info = [location.to_sanitized_dict() for location in archived_locations]

            summary = f"{'Would archive' if dry_run else 'Archived'} {len(archived_info)} uploads"
            logger.info(f"{summary} for job {job_id}")

            return Success(archived_info)

        except ValueError as e:
            logger.exception("Validation error in archive_job_uploads")
            return Failure(str(e))
        except Exception:
            logger.exception("Unexpected error in archive_job_uploads")
            return Failure("An unexpected error occurred while archiving uploads")

    def upload_results_from_directory(
        self, job_id: int, run_id: int, results_dir: Path
    ) -> Result[str, str]:
        """
        Upload FRED simulation results from a directory to S3.

        This method orchestrates uploading simulation results as a ZIP file to S3
        and updating the run record with the results URL and timestamp.

        Args:
            job_id: ID of the job
            run_id: ID of the run
            results_dir: Path to directory containing FRED output files

        Returns:
            Result containing the S3 URL where results were uploaded (Success)
            or an error message (Failure)
        """
        try:
            logger.info(f"Uploading results for run {run_id} (job {job_id}) from {results_dir}")

            # Use the upload_results use case
            results_url = self._upload_results(
                job_id=job_id,
                run_id=run_id,
                results_dir=results_dir,
            )

            logger.info(f"Successfully uploaded results for run {run_id}: {results_url}")
            return Success(results_url)

        except ValueError as e:
            logger.exception("Validation error in upload_results")
            return Failure(str(e))
        except Exception:
            logger.exception("Unexpected error in upload_results")
            return Failure("An unexpected error occurred while uploading results")
