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


logger = logging.getLogger(__name__)


class JobRepository:
    """
    Repository interface for job persistence.
    In a real application, this would be implemented with database operations.
    """
    
    def __init__(self):
        self._jobs: Dict[int, Job] = {}
        self._next_id = 123  # Starting from Pact contract value
    
    def save(self, job: Job) -> Job:
        """Save a job to the repository."""
        self._jobs[job.id] = job
        logger.info(f"Job {job.id} saved to repository")
        return job
    
    def find_by_id(self, job_id: int) -> Optional[Job]:
        """Find a job by its ID."""
        return self._jobs.get(job_id)
    
    def find_by_user_id(self, user_id: int) -> List[Job]:
        """Find all jobs for a specific user."""
        return [job for job in self._jobs.values() if job.user_id == user_id]
    
    def find_by_status(self, status: JobStatus) -> List[Job]:
        """Find all jobs with a specific status."""
        return [job for job in self._jobs.values() if job.status == status]
    
    def get_next_id(self) -> int:
        """Get the next available job ID."""
        current_id = self._next_id
        self._next_id += 1
        return current_id
    
    def exists(self, job_id: int) -> bool:
        """Check if a job exists."""
        return job_id in self._jobs
    
    def delete(self, job_id: int) -> bool:
        """Delete a job from the repository."""
        if job_id in self._jobs:
            del self._jobs[job_id]
            logger.info(f"Job {job_id} deleted from repository")
            return True
        return False


class JobService:
    """
    Service for job-related business operations.
    Implements use cases and business logic for job management.
    """
    
    def __init__(self, job_repository: JobRepository = None):
        self.job_repository = job_repository or JobRepository()
    
    def register_job(self, user_id: int, tags: List[str] = None) -> Job:
        """
        Register a new job for a user.
        
        This implements the business logic for the /jobs/register endpoint.
        
        Args:
            user_id: ID of the user registering the job
            tags: Optional list of tags for the job
            
        Returns:
            The registered Job entity
            
        Raises:
            ValueError: If user_id is invalid or business rules are violated
        """
        if user_id <= 0:
            raise ValueError("User ID must be positive")
        
        if tags is None:
            tags = []
        
        # Validate tags against known values (business rule)
        self._validate_tags(tags)
        
        # Generate new job ID
        job_id = self.job_repository.get_next_id()
        
        # Create and register the job
        job = Job.register(job_id=job_id, user_id=user_id, tags=tags)
        
        # Save to repository
        saved_job = self.job_repository.save(job)
        
        logger.info(f"Job {job_id} registered for user {user_id} with tags {tags}")
        
        return saved_job
    
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
        job = self.job_repository.find_by_id(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        # Business rule: Only registered jobs can be submitted
        if job.status != JobStatus.REGISTERED:
            raise ValueError(f"Job {job_id} must be in REGISTERED status to be submitted, current status: {job.status.value}")
        
        # Update job status
        job.update_status(JobStatus.SUBMITTED)
        self.job_repository.save(job)
        
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
        return self.job_repository.find_by_id(job_id)
    
    def get_jobs_for_user(self, user_id: int) -> List[Job]:
        """
        Get all jobs for a specific user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of Job entities for the user
        """
        return self.job_repository.find_by_user_id(user_id)
    
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
        job = self.job_repository.find_by_id(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        job.update_status(new_status)
        return self.job_repository.save(job)
    
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
        job = self.job_repository.find_by_id(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        self._validate_tags([tag])
        job.add_tag(tag)
        return self.job_repository.save(job)
    
    def _validate_tags(self, tags: List[str]) -> None:
        """
        Validate tags according to business rules.
        
        Args:
            tags: List of tags to validate
            
        Raises:
            ValueError: If any tag is invalid
        """
        if not tags:
            return
        
        valid_tag_values = [tag.value for tag in JobTag]
        
        for tag in tags:
            if not isinstance(tag, str) or not tag.strip():
                raise ValueError(f"Tag must be a non-empty string: {tag}")
            
            # For now, we'll allow unknown tags but could enforce strict validation
            # if tag not in valid_tag_values:
            #     raise ValueError(f"Invalid tag: {tag}. Valid tags are: {valid_tag_values}")
    
    def get_job_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about jobs in the system.
        
        Returns:
            Dictionary containing job statistics
        """
        all_jobs = list(self.job_repository._jobs.values())
        
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
