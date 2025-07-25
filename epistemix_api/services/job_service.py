"""
Job service for handling job-related business operations.
This service layer orchestrates business logic and coordinates between
the web layer and domain models.
"""

from typing import Dict, List, Any, Optional, Callable, Self
import logging
import functools

from returns.result import Result, Success, Failure

from epistemix_api.models.job import Job, JobStatus
from epistemix_api.repositories import IJobRepository
from epistemix_api.use_cases import (
    register_job as register_job_use_case, 
    submit_job as submit_job_use_case,
    get_job as get_job_use_case,
    validate_tags
)


logger = logging.getLogger(__name__)


class JobServiceDependencies:
    """
    Dependencies for the JobService.
    
    This class encapsulates the dependencies required by the JobService,
    allowing for easier testing and dependency injection.
    """
    
    def __init__(
        self, register_job_fn: Callable[[int, List[str]], Job],
        submit_job_fn: Callable[[int, str, str], Dict[str, str]],
        get_job_fn: Callable[[int], Optional[Job]]
    ):
        self.register_job_fn = register_job_fn
        self.submit_job_fn = submit_job_fn
        self.get_job_fn = get_job_fn

class JobService:
    """Controller for job-related operations in epistemix platform."""
    
    def __init__(self):
        """Initialize the job service without dependencies.
        This constructor is best for tests when you need to override dependencies. The dependencies
        are intended to be private so there is not public method to set them directly. 

        Example:
        from mock import Mock

        mock_job = Job.create_persisted(job_id=1, user_id=123, tags=["test"])
        job_service = JobService()
        job_service._dependencies = JobServiceDependencies(
            register_job_fn=Mock(return_value=mock_job),
            submit_job_fn=Mock(return_value={"url": "http://example.com/pre-signed-url"}),
            get_job_fn=Mock(return_value=mock_job)
        )

        Use `create_with_job_repository` to instantiate with a repository for production use.
        """
        self._dependencies = None

    @classmethod
    def create_with_job_repository(cls, job_repository: IJobRepository) -> Self:
        service = cls()
        service._dependencies = JobServiceDependencies(
            register_job_fn=functools.partial(register_job_use_case, job_repository),
            submit_job_fn=functools.partial(submit_job_use_case, job_repository),
            get_job_fn=functools.partial(get_job_use_case, job_repository)
        )
        return service

    def register_job(self, user_id: int, tags: List[str] = None) -> Result[Dict[str, Any], str]:
        """
        Register a new job for a user.
        
        This is a public interface that delegates to the register_job use case.
        The service layer orchestrates the call to the business use case.
        
        Args:
            user_id: ID of the user registering the job
            tags: Optional list of tags for the job
            
        Returns:
            Result containing either the created Job entity as a dict (Success) 
            or an error message (Failure)
        """
        try:
            job = self._dependencies.register_job_fn(
                user_id=user_id,
                tags=tags
            )
            return Success(job.to_dict())
        except ValueError as e:
            return Failure(str(e))
        except Exception as e:
            logger.exception(f"Unexpected error in register_job")
            return Failure("An unexpected error occurred while registering the job")
    
    def submit_job(self, job_id: int, context: str = "job", job_type: str = "input") -> Result[Dict[str, str], str]:
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
            job_configuration_location = self._dependencies.submit_job_fn(
                job_id=job_id,
                context=context,
                job_type=job_type
            )
            return Success(job_configuration_location.to_dict())
        except ValueError as e:
            return Failure(str(e))
        except Exception as e:
            logger.error(f"Unexpected error in submit_job: {e}")
            return Failure("An unexpected error occurred while submitting the job")
    
    def get_job(self, job_id: int) -> Result[Optional[Dict[str, Any]], str]:
        """
        Get a job by ID.
        
        This is a public interface that delegates to the get_job use case.
        The service layer orchestrates the call to the business use case.
        
        Args:
            job_id: ID of the job to retrieve
            
        Returns:
            Result containing either the Job entity as a dict (Success) 
            or an error message (Failure). Returns None if job not found.
        """
        try:
            job = self._dependencies.get_job_fn(job_id=job_id)
            if job:
                return Success(job.to_dict())
            return Success(None)
        except ValueError as e:
            return Failure(str(e))
        except Exception as e:
            logger.error(f"Unexpected error in get_job: {e}")
            return Failure("An unexpected error occurred while retrieving the job")
