"""
Job service for handling job-related business operations.
This service layer orchestrates business logic and coordinates between
the web layer and domain models.
"""

from typing import Dict, List, Any, Optional
import logging

from returns.result import Result, Success, Failure

from ..models.job import Job, JobStatus
from ..repositories.interfaces import IJobRepository
from ..use_cases.job_use_cases import (
    register_job as register_job_use_case, 
    submit_job as submit_job_use_case,
    validate_tags
)


logger = logging.getLogger(__name__)


class JobService:
    """
    Service for job-related business operations.
    Implements use cases and business logic for job management.
    
    This service depends on the IJobRepository interface, following
    the Dependency Inversion Principle.
    """
    
    def __init__(self, job_repository: IJobRepository):
        """
        Initialize the job service.
        
        Args:
            job_repository: Repository implementation for job persistence.
                          Defaults to InMemoryJobRepository if not provided.
        """
        self._job_repository = job_repository
    
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
            job = register_job_use_case(
                job_repository=self._job_repository,
                user_id=user_id,
                tags=tags
            )
            return Success(job.to_dict())
        except ValueError as e:
            return Failure(str(e))
        except Exception as e:
            # Log unexpected errors
            logger.error(f"Unexpected error in register_job: {e}")
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
            response = submit_job_use_case(
                job_repository=self._job_repository,
                job_id=job_id,
                context=context,
                job_type=job_type
            )
            return Success(response)
        except ValueError as e:
            return Failure(str(e))
        except Exception as e:
            # Log unexpected errors
            logger.error(f"Unexpected error in submit_job: {e}")
            return Failure("An unexpected error occurred while submitting the job")
    
    def get_job(self, job_id: int) -> Optional[Job]:
        """
        Get a job by ID.
        
        Args:
            job_id: ID of the job to retrieve
            
        Returns:
            The Job entity if found, None otherwise
        """
        return self._job_repository.find_by_id(job_id)
    
    def get_jobs_for_user(self, user_id: int) -> List[Job]:
        """
        Get all jobs for a specific user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of Job entities for the user
        """
        return self._job_repository.find_by_user_id(user_id)
    
    def update_job_status(self, job_id: int, new_status: JobStatus) -> Job:
        """
        Update the status of a job.
        
        Args:
            job_id: ID of the job to update
            new_status: New status for the job
            
        Returns:
            The updated Job entity
            
        Raises:
            ValueError: If job doesn't exist or status transition is invalid
        """
        job = self._job_repository.find_by_id(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        job.update_status(new_status)
        return self._job_repository.save(job)
    
    def add_tag_to_job(self, job_id: int, tag: str) -> Job:
        """
        Add a tag to a job.
        
        Args:
            job_id: ID of the job
            tag: Tag to add
            
        Returns:
            The updated Job entity
            
        Raises:
            ValueError: If job doesn't exist or tag is invalid
        """
        job = self._job_repository.find_by_id(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        # Use the use case validation function
        validate_tags([tag])
        job.add_tag(tag)
        return self._job_repository.save(job)
    
    def get_job_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about jobs in the system.
        
        Returns:
            Dictionary containing job statistics
        """
        all_jobs = self._job_repository.find_all()
        
        status_counts = {}
        for status in JobStatus:
            status_counts[status.value] = len([j for j in all_jobs if j.status == status])
        
        tag_counts = {}
        for job in all_jobs:
            for tag in job.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        return {
            "total_jobs": len(all_jobs),
            "status_breakdown": status_counts,
            "tag_breakdown": tag_counts,
            "active_jobs": len([j for j in all_jobs if j.is_active()])
        }
