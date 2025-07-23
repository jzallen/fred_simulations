"""
Repository interfaces for the Epistemix API.
Defines contracts for data persistence using Protocol for type safety.
"""

from typing import Protocol, Optional, List, runtime_checkable
from ..models.job import Job, JobStatus


@runtime_checkable
class IJobRepository(Protocol):
    """
    Protocol (interface) for job repository operations.
    
    This defines the contract that any job repository implementation must follow.
    Using Protocol provides structural typing and dependency inversion.
    """
    
    def save(self, job: Job) -> Job:
        """
        Save a job to the repository.
        
        For unpersisted jobs (job.id is None), assigns a new ID and persists the job.
        For persisted jobs (job.id is not None), updates the existing record.
        
        Args:
            job: The job to save
            
        Returns:
            The saved job with an assigned ID (if it was unpersisted)
        """
        ...
    
    def find_by_id(self, job_id: int) -> Optional[Job]:
        """
        Find a job by its ID.
        
        Args:
            job_id: The ID of the job to find
            
        Returns:
            The job if found, None otherwise
        """
        ...
    
    def find_by_user_id(self, user_id: int) -> List[Job]:
        """
        Find all jobs for a specific user.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            List of jobs for the user
        """
        ...
    
    def find_by_status(self, status: JobStatus) -> List[Job]:
        """
        Find all jobs with a specific status.
        
        Args:
            status: The status to filter by
            
        Returns:
            List of jobs with the specified status
        """
        ...
    
    
    def exists(self, job_id: int) -> bool:
        """
        Check if a job exists.
        
        Args:
            job_id: The ID of the job to check
            
        Returns:
            True if the job exists, False otherwise
        """
        ...
    
    def delete(self, job_id: int) -> bool:
        """
        Delete a job from the repository.
        
        Args:
            job_id: The ID of the job to delete
            
        Returns:
            True if the job was deleted, False if it didn't exist
        """
        ...
    
    def find_all(self) -> List[Job]:
        """
        Find all jobs in the repository.
        
        Returns:
            List of all jobs
        """
        ...
