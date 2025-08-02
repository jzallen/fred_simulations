"""
SQLAlchemy-based job repository implementation.
This is a concrete implementation of the IJobRepository interface using SQLite.
"""

import datetime
from typing import List, Optional, Callable
import logging
from contextlib import contextmanager

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from epistemix_api.repositories.database import get_db_session, JobRecord, JobStatusEnum
from epistemix_api.repositories.interfaces import IJobRepository
from epistemix_api.models.job import Job, JobStatus
from epistemix_api.mappers.job_mapper import JobMapper


logger = logging.getLogger(__name__)


class SQLAlchemyJobRepository:
    """
    SQLAlchemy-based implementation of the job repository.
    
    This implementation stores jobs in a SQLite database using SQLAlchemy ORM.
    It provides the same interface as the in-memory repository but with persistent storage.
    """
    
    def __init__(self, get_db_session_fn: Callable[[], Session] = get_db_session):
        """Initialize the repository."""
        self._session_factory = get_db_session_fn
    
    @contextmanager
    def _get_session(self):
        """Context manager for database sessions with automatic cleanup."""
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def save(self, job: Job) -> Job:
        """
        Save a job to the database.
        
        For unpersisted jobs (id is None), assigns a new ID from the database.
        For persisted jobs (id is not None), updates the existing record.
        
        Args:
            job: The job to save
            
        Returns:
            The saved job with an assigned ID
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            with self._get_session() as session:
                if not job.is_persisted():
                    # Create new job record
                    job_record = JobRecord(
                        user_id=job.user_id,
                        tags=job.tags,
                        status=JobStatusEnum(job.status.value),
                        job_metadata=job.metadata or {},
                        created_at=datetime.datetime.utcnow(),
                        updated_at=datetime.datetime.utcnow()
                    )
                    session.add(job_record)
                    session.flush()  # Get the assigned ID
                    
                    # Update the domain object with the assigned ID
                    job.id = job_record.id
                else:
                    job_record = session.get(JobRecord, job.id)
                    if job_record is None:
                        raise ValueError(f"Job {job.id} not found for update")
                    
                    # Update the record fields
                    job_record.user_id = job.user_id
                    job_record.tags = job.tags
                    job_record.status = JobMapper.domain_to_record(job).status
                    job_record.updated_at = datetime.datetime.utcnow()
                    job_record.job_metadata = job.metadata
                    session.add(job_record)
                    session.flush()
                
                logger.info(f"Job {job.id} saved to database for user {job.user_id}")
                return Job.create_persisted(
                    job_id=job_record.id,
                    user_id=job_record.user_id,
                    tags=job_record.tags,
                    status=JobStatus(job_record.status.value),
                    created_at=job_record.created_at,
                    updated_at=job_record.updated_at,
                    metadata=job_record.job_metadata,
                )
                
        except SQLAlchemyError as e:
            logger.error(f"Database error saving job: {e}")
            raise
    
    def find_by_id(self, job_id: int) -> Optional[Job]:
        """Find a job by its ID."""
        try:
            with self._get_session() as session:
                job_record = session.get(JobRecord, job_id)
                if job_record:
                    return JobMapper.record_to_domain(job_record)
                return None
        except SQLAlchemyError as e:
            logger.error(f"Database error finding job {job_id}: {e}")
            raise
    
    def find_by_user_id(self, user_id: int) -> List[Job]:
        """Find all jobs for a specific user."""
        try:
            with self._get_session() as session:
                job_records = session.query(JobRecord).filter(JobRecord.user_id == user_id).all()
                return [JobMapper.record_to_domain(record) for record in job_records]
        except SQLAlchemyError as e:
            logger.error(f"Database error finding jobs for user {user_id}: {e}")
            raise
    
    def find_by_status(self, status: JobStatus) -> List[Job]:
        """Find all jobs with a specific status."""
        try:
            with self._get_session() as session:
                # Convert domain status to SQLAlchemy enum
                status_mapping = {
                    JobStatus.CREATED: JobStatusEnum.CREATED,
                    JobStatus.SUBMITTED: JobStatusEnum.SUBMITTED,
                    JobStatus.PROCESSING: JobStatusEnum.PROCESSING,
                    JobStatus.COMPLETED: JobStatusEnum.COMPLETED,
                    JobStatus.FAILED: JobStatusEnum.FAILED,
                    JobStatus.CANCELLED: JobStatusEnum.CANCELLED,
                }
                db_status = status_mapping[status]
                
                job_records = session.query(JobRecord).filter(JobRecord.status == db_status).all()
                return [JobMapper.record_to_domain(record) for record in job_records]
        except SQLAlchemyError as e:
            logger.error(f"Database error finding jobs with status {status}: {e}")
            raise
    
    def exists(self, job_id: int) -> bool:
        """Check if a job exists."""
        try:
            with self._get_session() as session:
                return session.query(JobRecord).filter(JobRecord.id == job_id).first() is not None
        except SQLAlchemyError as e:
            logger.error(f"Database error checking if job {job_id} exists: {e}")
            raise
    
    def delete(self, job_id: int) -> bool:
        """Delete a job from the database."""
        try:
            with self._get_session() as session:
                job_record = session.get(JobRecord, job_id)
                if job_record:
                    session.delete(job_record)
                    logger.info(f"Job {job_id} deleted from database")
                    return True
                return False
        except SQLAlchemyError as e:
            logger.error(f"Database error deleting job {job_id}: {e}")
            raise


class InMemoryJobRepository(IJobRepository):
    """
    In-memory implementation of the job repository.
    
    This implementation stores jobs in memory and is suitable for development
    and testing. In production, use SQLAlchemyJobRepository instead.
    """
    
    def __init__(self, starting_id: int = 123):
        """
        Initialize the repository.
        
        Args:
            starting_id: The starting ID for job generation (defaults to Pact contract value)
        """
        from typing import Dict
        self._jobs: Dict[int, Job] = {}
        self._next_id = starting_id
    
    def save(self, job: Job) -> Job:
        """Save a job to memory."""
        if not job.is_persisted():
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
        """Get the next available job ID."""
        current_id = self._next_id
        self._next_id += 1
        return current_id
    
    def exists(self, job_id: int) -> bool:
        """Check if a job exists."""
        return job_id in self._jobs
    
    def delete(self, job_id: int) -> bool:
        """Delete a job from memory."""
        if job_id in self._jobs:
            del self._jobs[job_id]
            logger.info(f"Job {job_id} deleted from in-memory repository")
            return True
        return False
    
    def reset_id_counter(self, starting_id: int = 123) -> None:
        """Reset the ID counter (for testing)."""
        self._next_id = starting_id
        logger.info(f"ID counter reset to {starting_id}")
