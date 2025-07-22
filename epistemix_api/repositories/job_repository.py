"""
In-memory job repository implementation.
This is a concrete implementation of the IJobRepository interface.
"""

from typing import Dict, List, Optional
import logging

from ..models.job import Job, JobStatus


logger = logging.getLogger(__name__)


class InMemoryJobRepository:
    """
    In-memory implementation of the job repository.
    
    This implementation stores jobs in memory and is suitable for development
    and testing. In production, this would be replaced with a database-backed
    implementation.
    """
    
    def __init__(self, starting_id: int = 123):
        """
        Initialize the repository.
        
        Args:
            starting_id: The starting ID for job generation (defaults to Pact contract value)
        """
        self._jobs: Dict[int, Job] = {}
        self._next_id = starting_id
    
    def save(self, job: Job) -> Job:
        """
        Save a job to the repository.
        
        For unpersisted jobs (id is None), assigns a new ID.
        For persisted jobs (id is not None), updates the existing record.
        
        Args:
            job: The job to save
            
        Returns:
            The saved job with an assigned ID
        """
        if not job.is_persisted():
            # Assign new ID for unpersisted jobs
            job.id = self.get_next_id()
            logger.info(f"Assigned new ID {job.id} to unpersisted job for user {job.user_id}")
        
        self._jobs[job.id] = job
        logger.info(f"Job {job.id} saved to in-memory repository")
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
        """
        Get the next available job ID.
        
        This method should only be called internally by the repository
        when persisting new jobs. External callers should not generate
        IDs directly.
        
        Returns:
            The next available ID
        """
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
            logger.info(f"Job {job_id} deleted from in-memory repository")
            return True
        return False
    
    def find_all(self) -> List[Job]:
        """Find all jobs in the repository."""
        return list(self._jobs.values())
    
    def clear(self) -> None:
        """
        Clear all jobs from the repository.
        Useful for testing and development.
        """
        self._jobs.clear()
        logger.info("All jobs cleared from in-memory repository")
    
    def count(self) -> int:
        """
        Get the total number of jobs in the repository.
        
        Returns:
            The number of jobs
        """
        return len(self._jobs)
    
    def reset_id_counter(self, starting_id: int = 123) -> None:
        """
        Reset the ID counter.
        Useful for testing.
        
        Args:
            starting_id: The new starting ID
        """
        self._next_id = starting_id
        logger.info(f"ID counter reset to {starting_id}")


# Type alias for easier imports
JobRepository = InMemoryJobRepository
