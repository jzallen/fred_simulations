"""
Job service for handling job-related business operations.
This service layer orchestrates business logic and coordinates between
the web layer and domain models.
"""

from typing import Dict, List, Any, Optional, Callable, Self
import logging
import functools

from returns.result import Result, Success, Failure

from epistemix_api.models.job import Job
from epistemix_api.models.run import Run
from epistemix_api.models.upload_location import UploadLocation
from epistemix_api.models.job_upload import JobUpload
from epistemix_api.models.upload_content import UploadContent
from epistemix_api.models.requests import RunRequest
from epistemix_api.repositories import IJobRepository, IRunRepository, IUploadLocationRepository
from epistemix_api.use_cases import (
    register_job as register_job_use_case, 
    submit_job as submit_job_use_case,
    submit_job_config as submit_job_config_use_case,
    submit_runs as submit_runs_use_case,
    submit_run_config as submit_run_config_use_case,    
    get_job as get_job_use_case,
    get_runs_by_job_id as get_runs_by_job_id_use_case,
    get_job_uploads,
    read_upload_content,
)



logger = logging.getLogger(__name__)


class JobControllerDependencies:
    """
    Dependencies for the JobController.
    
    This class encapsulates the dependencies required by the JobController,
    allowing for easier testing and dependency injection.
    """
    
    def __init__(
        self, register_job_fn: Callable[[int, List[str]], Job],
        submit_job_fn: Callable[[int, str, str], UploadLocation],
        submit_job_config_fn: Callable[[int, str, str], UploadLocation],
        submit_runs_fn: Callable[[List[Dict[str, Any]], str, str], List[Run]],
        submit_run_config_fn: Callable[[int, str, str, Optional[int]], UploadLocation],
        get_runs_by_job_id_fn: Callable[[int], Optional[Run]],
        get_job_uploads_fn: Callable[[int], List[JobUpload]],
        read_upload_content_fn: Callable[[UploadLocation], UploadContent],
    ):
        self.register_job_fn = register_job_fn
        self.submit_job_fn = submit_job_fn
        self.submit_job_config_fn = submit_job_config_fn
        self.submit_runs_fn = submit_runs_fn
        self.submit_run_config_fn = submit_run_config_fn
        self.get_runs_by_job_id_fn = get_runs_by_job_id_fn
        self.get_job_uploads_fn = get_job_uploads_fn
        self.read_upload_content_fn = read_upload_content_fn

class JobController:
    """Controller for job-related operations in epistemix platform."""
    
    def __init__(self):
        """Initialize the job controller without dependencies.
        This constructor is best for tests when you need to override dependencies. The dependencies
        are intended to be private so there is not public method to set them directly. 

        Example:
        from mock import Mock

        mock_job = Job.create_persisted(job_id=1, user_id=123, tags=["test"])
        job_controller = JobController()
        job_controller._dependencies = JobControllerDependencies(
            register_job_fn=Mock(return_value=mock_job),
            submit_job_fn=Mock(return_value={"url": "http://example.com/pre-signed-url"}),
            submit_runs_fn=Mock(return_value={"runResponses": []}),
            get_job_fn=Mock(return_value=mock_job),
            run_repository=Mock()
        )

        Use `create_with_repositories` to instantiate with a repository for production use.
        """
        self._dependencies = None

    @classmethod
    def create_with_repositories(
        cls, 
        job_repository: IJobRepository, 
        run_repository: IRunRepository, 
        upload_location_repository: IUploadLocationRepository
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
            submit_job_fn=functools.partial(submit_job_use_case, job_repository, upload_location_repository),
            submit_job_config_fn=functools.partial(submit_job_config_use_case, job_repository, upload_location_repository),
            submit_runs_fn=functools.partial(submit_runs_use_case, run_repository, upload_location_repository),
            submit_run_config_fn=functools.partial(submit_run_config_use_case, run_repository, upload_location_repository),
            get_runs_by_job_id_fn=functools.partial(get_runs_by_job_id_use_case, run_repository),
            get_job_uploads_fn=functools.partial(get_job_uploads, job_repository, run_repository),
            read_upload_content_fn=functools.partial(read_upload_content, upload_location_repository)
        )
        return service

    def register_job(self, user_token_value: str, tags: List[str] = None) -> Result[Dict[str, Any], str]:
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
            job = self._dependencies.register_job_fn(
                user_token_value=user_token_value,
                tags=tags
            )
            return Success(job.to_dict())
        except ValueError as e:
            logger.exception(f"Validation error in register_job: {e}")
            return Failure(str(e))
        except Exception as e:
            logger.exception(f"Unexpected error in register_job")
            return Failure("An unexpected error occurred while registering the job")
    
    def submit_job(self, job_id: int, context: str = "job", job_type: str = "input", run_id: Optional[int] = None) -> Result[Dict[str, str], str]:
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
                context=context,
                upload_type=job_type,
                job_id=job_id,
                run_id=run_id
            )
            
            # Route to the appropriate use case based on context and type
            match (context, job_type):
                case ("job", "input"):
                    job_configuration_location = self._dependencies.submit_job_fn(job_upload)
                case ("job", "config"):
                    job_configuration_location = self._dependencies.submit_job_config_fn(job_upload)
                case ("run", "config"):
                    job_configuration_location = self._dependencies.submit_run_config_fn(job_upload)
                case _:
                    raise ValueError(f"Unsupported context '{context}' or job type '{job_type}'")
            return Success(job_configuration_location.to_dict())
        except ValueError as e:
            return Failure(str(e))
        except Exception as e:
            logger.exception(f"Unexpected error in submit_job: {e}")
            return Failure("An unexpected error occurred while submitting the job")
    
    def submit_runs(self, user_token_value: str, run_requests: List[RunRequest], epx_version: str = "epx_client_1.2.2") -> Result[Dict[str, List[Dict[str, Any]]], str]:
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
                epx_version=epx_version
            )
            run_responses = [run.to_run_response_dict() for run in runs]
            return Success(run_responses)
        except ValueError as e:
            return Failure(str(e))
        except Exception as e:
            logger.exception(f"Unexpected error in submit_runs: {e}")
            return Failure("An unexpected error occurred while submitting the runs")
    
    def get_runs(self, job_id: int) -> Result[List[Dict[str, Any]], str]:
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
            return Failure(str(e))
        except Exception as e:
            logger.exception(f"Unexpected error in get_runs_by_job_id: {e}")
            return Failure("An unexpected error occurred while retrieving the runs")
    
    def get_job_uploads(self, job_id: int) -> Result[List[Dict[str, Any]], str]:
        """
        Get all uploads associated with a job and their contents.
        
        This method orchestrates retrieving upload metadata and reading
        the actual content from storage, combining them into a complete response.
        
        Args:
            job_id: ID of the job to get uploads for
            
        Returns:
            Result containing list of uploads with content (Success) 
            or an error message (Failure)
        """
        try:
            # Get upload metadata from use case
            uploads = self._dependencies.get_job_uploads_fn(job_id=job_id)
            
            # Enrich each upload with content
            results = []
            for upload in uploads:
                upload_dict = upload.to_dict()
                
                try:
                    # Read content for this upload
                    content = self._dependencies.read_upload_content_fn(upload.location)
                    upload_dict['content'] = content.to_dict()
                except ValueError as e:
                    # Include error information if content couldn't be read
                    upload_dict['error'] = str(e)
                    logger.warning(f"Failed to read content for upload {upload.context}_{upload.upload_type} (job_id={job_id}): {e}")
                
                results.append(upload_dict)
            
            logger.info(f"Retrieved {len(results)} uploads for job {job_id}")
            return Success(results)
            
        except ValueError as e:
            logger.error(f"Validation error in get_job_uploads: {e}")
            return Failure(str(e))
        except Exception as e:
            logger.exception(f"Unexpected error in get_job_uploads")
            return Failure("An unexpected error occurred while retrieving uploads")
