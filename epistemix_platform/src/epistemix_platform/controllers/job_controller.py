"""
Job service for handling job-related business operations.
This service layer orchestrates business logic and coordinates between
the web layer and domain models.
"""

# TODO: Clean up imports - consolidate multiple imports from same module
import functools
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any, Self

from returns.result import Failure, Result, Success

from epistemix_platform.models.job import Job
from epistemix_platform.models.job_upload import JobUpload
from epistemix_platform.models.requests import RunRequest
from epistemix_platform.models.run import Run
from epistemix_platform.models.upload_content import UploadContent
from epistemix_platform.models.upload_location import UploadLocation
from epistemix_platform.repositories import (
    IJobRepository,
    IRunRepository,
    IUploadLocationRepository,
)
from epistemix_platform.use_cases import archive_uploads as archive_uploads_use_case
from epistemix_platform.use_cases import (
    get_job_uploads,
    read_upload_content,
    write_to_local,
)
from epistemix_platform.use_cases import get_runs_by_job_id as get_runs_by_job_id_use_case
from epistemix_platform.use_cases import register_job as register_job_use_case
from epistemix_platform.use_cases import submit_job as submit_job_use_case
from epistemix_platform.use_cases import submit_job_config as submit_job_config_use_case
from epistemix_platform.use_cases import submit_run_config as submit_run_config_use_case
from epistemix_platform.use_cases import submit_runs as submit_runs_use_case


logger = logging.getLogger(__name__)


class JobControllerDependencies:
    """
    Dependencies for the JobController.

    This class encapsulates the dependencies required by the JobController,
    allowing for easier testing and dependency injection.
    """

    def __init__(
        self,
        register_job_fn: Callable[[str, list[str]], Job],
        submit_job_fn: Callable[[int, str, str], UploadLocation],
        submit_job_config_fn: Callable[[int, str, str], UploadLocation],
        submit_runs_fn: Callable[[list[dict[str, Any]], str, str], list[Run]],
        submit_run_config_fn: Callable[[int, str, str, int | None], UploadLocation],
        get_runs_by_job_id_fn: Callable[[int], Run | None],
        get_job_uploads_fn: Callable[[int], list[JobUpload]],
        read_upload_content_fn: Callable[[UploadLocation], UploadContent],
        write_to_local_fn: Callable[[Path, UploadContent, bool], None],
        archive_uploads_fn: Callable | None = None,
    ):
        self.register_job_fn = register_job_fn
        self.submit_job_fn = submit_job_fn
        self.submit_job_config_fn = submit_job_config_fn
        self.submit_runs_fn = submit_runs_fn
        self.submit_run_config_fn = submit_run_config_fn
        self.get_runs_by_job_id_fn = get_runs_by_job_id_fn
        self.get_job_uploads_fn = get_job_uploads_fn
        self.read_upload_content_fn = read_upload_content_fn
        self.write_to_local_fn = write_to_local_fn
        self.archive_uploads_fn = archive_uploads_fn or archive_uploads_use_case


class JobController:
    """Controller for job-related operations in epistemix platform."""

    def __init__(self):
        """Initialize the job controller without dependencies.
        This constructor is best for tests when you need to override dependencies. The dependencies
        are intended to be private so there is not public method to set them directly.

        Example:
        from unittest.mock import Mock
        from epistemix_platform.models.upload_location import UploadLocation

        mock_job = Job.create_persisted(job_id=1, user_id=123, tags=["test"])
        mock_location = UploadLocation(url="http://example.com/pre-signed-url", key="test.zip")
        job_controller = JobController()
        job_controller._dependencies = JobControllerDependencies(
            register_job_fn=Mock(return_value=mock_job),
            submit_job_fn=Mock(return_value=mock_location),
            submit_job_config_fn=Mock(return_value=mock_location),
            submit_runs_fn=Mock(return_value=[]),
            submit_run_config_fn=Mock(return_value=mock_location),
            get_runs_by_job_id_fn=Mock(return_value=[]),
            get_job_uploads_fn=Mock(return_value=[]),
            read_upload_content_fn=Mock(),
            write_to_local_fn=Mock(),
            archive_uploads_fn=Mock(return_value=[])
        )

        Use `create_with_repositories` to instantiate with a repository for production use.
        """
        self._dependencies = None

    @classmethod
    def create_with_repositories(
        cls,
        job_repository: IJobRepository,
        run_repository: IRunRepository,
        upload_location_repository: IUploadLocationRepository,
    ) -> Self:
        """
        Create JobController with repositories.

        Args:
            job_repository: Repository for job persistence
            run_repository: Repository for run persistence
            upload_location_repository: Repository for upload locations (handles storage details)

        Returns:
            Configured JobController instance
        """
        service = cls()

        service._dependencies = JobControllerDependencies(
            register_job_fn=functools.partial(register_job_use_case, job_repository),
            submit_job_fn=functools.partial(
                submit_job_use_case, job_repository, upload_location_repository
            ),
            submit_job_config_fn=functools.partial(
                submit_job_config_use_case, job_repository, upload_location_repository
            ),
            submit_runs_fn=functools.partial(
                submit_runs_use_case, run_repository, upload_location_repository
            ),
            submit_run_config_fn=functools.partial(
                submit_run_config_use_case, run_repository, upload_location_repository
            ),
            get_runs_by_job_id_fn=functools.partial(get_runs_by_job_id_use_case, run_repository),
            get_job_uploads_fn=functools.partial(get_job_uploads, job_repository, run_repository),
            read_upload_content_fn=functools.partial(
                read_upload_content, upload_location_repository
            ),
            write_to_local_fn=write_to_local,
            archive_uploads_fn=functools.partial(
                archive_uploads_use_case, upload_location_repository
            ),
        )
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
            job = self._dependencies.register_job_fn(user_token_value=user_token_value, tags=tags)
            return Success(job.to_dict())
        except ValueError as e:
            logger.exception(f"Validation error in register_job: {e}")
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
                    upload_location = self._dependencies.submit_job_fn(job_upload)
                case ("job", "config"):
                    upload_location = self._dependencies.submit_job_config_fn(job_upload)
                case ("run", "config"):
                    upload_location = self._dependencies.submit_run_config_fn(job_upload)
                case _:
                    raise ValueError(f"Unsupported context '{context}' or job type '{job_type}'")
            return Success(upload_location.to_dict())
        except ValueError as e:
            logger.error(f"Validation error in submit_job: {e}")
            return Failure(str(e))
        except Exception as e:
            logger.exception(f"Unexpected error in submit_job: {e}")
            return Failure("An unexpected error occurred while submitting the job")

    def submit_runs(
        self,
        user_token_value: str,
        run_requests: list[RunRequest],
        epx_version: str = "epx_client_1.2.2",
    ) -> Result[dict[str, list[dict[str, Any]]], str]:
        """
        Submit multiple run requests for processing.

        This is a public interface that delegates to the submit_runs use case.
        The service layer orchestrates the call to the business use case.

        Args:
            user_token_value: User token value for authentication
            run_requests: List of run requests to process
            user_agent: User agent from request headers for client version

        Returns:
            Result containing either the run responses dict (Success)
            or an error message (Failure)
        """
        try:
            runs = self._dependencies.submit_runs_fn(
                run_requests=run_requests,
                user_token_value=user_token_value,
                epx_version=epx_version,
            )
            run_responses = [run.to_run_response_dict() for run in runs]
            return Success(run_responses)
        except ValueError as e:
            logger.error(f"Validation error in submit_runs: {e}")
            return Failure(str(e))
        except Exception as e:
            logger.exception(f"Unexpected error in submit_runs: {e}")
            return Failure("An unexpected error occurred while submitting the runs")

    def get_runs(self, job_id: int) -> Result[list[dict[str, Any]], str]:
        """
        Get all runs for a specific job.

        This is a public interface that delegates to the get_runs_by_job_id use case.
        The service layer orchestrates the call to the business use case.

        Args:
            job_id: ID of the job to get runs for

        Returns:
            Result containing either the list of runs (Success)
            or an error message (Failure)
        """
        try:
            runs = self._dependencies.get_runs_by_job_id_fn(job_id=job_id)
            return Success([run.to_dict() for run in runs])
        except ValueError as e:
            logger.error(f"Validation error in get_runs_by_job_id: {e}")
            return Failure(str(e))
        except Exception as e:
            logger.exception(f"Unexpected error in get_runs_by_job_id: {e}")
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
            uploads = self._dependencies.get_job_uploads_fn(job_id=job_id)

            # Process uploads based on whether content is requested
            results = []
            for upload in uploads:
                # Use sanitized dict to show sanitized URLs to users
                upload_dict = upload.to_sanitized_dict()

                if include_content:
                    try:
                        # Read content for this upload
                        content = self._dependencies.read_upload_content_fn(upload.location)
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
            logger.error(f"Validation error in get_job_uploads: {e}")
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
            uploads = self._dependencies.get_job_uploads_fn(job_id=job_id)

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
                    content = self._dependencies.read_upload_content_fn(upload.location)

                    # Use the write_to_local use case to handle the write operation
                    self._dependencies.write_to_local_fn(file_path, content, force=should_force)

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
            logger.error(f"Validation error in download_job_uploads: {e}")
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
            uploads = self._dependencies.get_job_uploads_fn(job_id=job_id)

            if not uploads:
                logger.info(f"No uploads found for job {job_id}")
                return Success([])

            # Extract UploadLocation objects from JobUpload objects
            upload_locations = [upload.location for upload in uploads]

            logger.info(f"Found {len(upload_locations)} uploads for job {job_id}")

            # Use the archive_uploads use case
            archived_locations = self._dependencies.archive_uploads_fn(
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
            logger.error(f"Validation error in archive_job_uploads: {e}")
            return Failure(str(e))
        except Exception:
            logger.exception("Unexpected error in archive_job_uploads")
            return Failure("An unexpected error occurred while archiving uploads")
