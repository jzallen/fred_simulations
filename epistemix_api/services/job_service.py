"""
Job service for handling job-related business operations.
This service layer orchestrates business logic and coordinates between
the web layer and domain models.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

from ..models.job import Job, JobStatus, JobTag
from ..models.user import User
from ..repositories.interfaces import IJobRepository
from ..use_cases.job_use_cases import register_job as register_job_use_case, validate_tags


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
    
    def register_job(self, user_id: int, tags: List[str] = None) -> Job:
        """
        Register a new job for a user.
        
        This is a public interface that delegates to the register_job use case.
        The service layer orchestrates the call to the business use case.
        
        Args:
            user_id: ID of the user registering the job
            tags: Optional list of tags for the job
            
        Returns:
            The created Job entity
            
        Raises:
            ValueError: If user_id is invalid or business rules are violated
        """
        return register_job_use_case(
            job_repository=self._job_repository,
            user_id=user_id,
            tags=tags
        )
    
    def submit_job(self, job_id: int, context: str = "job", job_type: str = "input") -> Dict[str, str]:
        """
        Submit a job for processing.
        
        This implements the business logic for the /jobs endpoint.
        
        Args:
            job_id: ID of the job to submit
            context: Context of the submission
            job_type: Type of the job submission
            
        Returns:
            Dictionary containing submission response (e.g., pre-signed URL)
            
        Raises:
            ValueError: If job doesn't exist or can't be submitted
        """
        # Find the job
        job = self._job_repository.find_by_id(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        # Business rule: Only created jobs can be submitted
        if job.status != JobStatus.CREATED:
            raise ValueError(f"Job {job_id} must be in CREATED status to be submitted, current status: {job.status.value}")
        
        # Update job status
        job.update_status(JobStatus.SUBMITTED)
        self._job_repository.save(job)
        
        # Return mock response as per Pact contract
        response = {
            "url": "http://localhost:5001/pre-signed-url"
        }
        
        logger.info(f"Job {job_id} submitted with context {context} and type {job_type}")
        
        return response
    
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
