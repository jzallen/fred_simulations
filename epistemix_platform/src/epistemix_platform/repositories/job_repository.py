"""
SQLAlchemy-based job repository implementation.
This is a concrete implementation of the IJobRepository interface using SQLite.
"""

import logging
from collections.abc import Callable
from contextlib import contextmanager
from typing import TYPE_CHECKING

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from epistemix_platform.models.job import Job, JobStatus
from epistemix_platform.repositories.database import JobRecord, JobStatusEnum
from epistemix_platform.repositories.interfaces import IJobRepository


if TYPE_CHECKING:
    from epistemix_platform.mappers.job_mapper import JobMapper

logger = logging.getLogger(__name__)


class SQLAlchemyJobRepository:
    """
    SQLAlchemy-based implementation of the job repository.

    This implementation stores jobs in a SQLite database using SQLAlchemy ORM.
    It provides the same interface as the in-memory repository but with persistent storage.
    """

    def __init__(
        self, job_mapper: "JobMapper", get_db_session_fn: Callable[[], Session]
    ):
        """
        Initialize the repository with mapper dependency injection.

        Args:
            job_mapper: The JobMapper instance for converting between domain and database models
            get_db_session_fn: Factory function for creating database sessions
        """
        self._job_mapper = job_mapper
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

        Uses JobMapper for strict conversion with no defaults.
        The caller is responsible for setting appropriate timestamps and other fields.

        For unpersisted jobs (id is None), creates a new record and updates the job's ID.
        For persisted jobs (id is not None), updates the existing record.

        Args:
            job: The job to save (must have all required fields populated)

        Returns:
            The saved job as returned from the database

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            with self._get_session() as session:
                local_job_record = self._job_mapper.domain_to_record(job)
                save_strategy_fn = session.merge if job.is_persisted() else session.add
                # session.merge returns updated record, session.add returns None
                persisted_job_record = save_strategy_fn(local_job_record) or local_job_record
                session.flush()
                persisted_job = self._job_mapper.record_to_domain(persisted_job_record)
                logger.info(
                    f"Job {persisted_job.id} saved to database for user {persisted_job.user_id}"
                )

        except SQLAlchemyError:
            logger.exception("Database error saving job")
            raise

        return persisted_job

    def find_by_id(self, job_id: int) -> Job | None:
        try:
            with self._get_session() as session:
                job_record = session.get(JobRecord, job_id)
                if job_record:
                    return self._job_mapper.record_to_domain(job_record)
                return None
        except SQLAlchemyError:
            logger.exception(f"Database error finding job {job_id}")
            raise

    def find_by_user_id(self, user_id: int) -> list[Job]:
        """Find all jobs for a specific user."""
        try:
            with self._get_session() as session:
                job_records = session.query(JobRecord).filter(JobRecord.user_id == user_id).all()
                return [self._job_mapper.record_to_domain(record) for record in job_records]
        except SQLAlchemyError:
            logger.exception(f"Database error finding jobs for user {user_id}")
            raise

    def find_by_status(self, status: JobStatus) -> list[Job]:
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
                return [self._job_mapper.record_to_domain(record) for record in job_records]
        except SQLAlchemyError:
            logger.exception(f"Database error finding jobs with status {status}")
            raise

    def find_all(self, limit: int | None = None, offset: int = 0) -> list[Job]:
        """Find all jobs in the repository."""
        try:
            with self._get_session() as session:
                query = session.query(JobRecord).order_by(JobRecord.created_at.desc())

                if offset > 0:
                    query = query.offset(offset)

                if limit is not None:
                    query = query.limit(limit)

                job_records = query.all()
                return [self._job_mapper.record_to_domain(record) for record in job_records]
        except SQLAlchemyError:
            logger.exception("Database error finding all jobs")
            raise

    def exists(self, job_id: int) -> bool:
        """Check if a job exists."""
        try:
            with self._get_session() as session:
                return session.query(JobRecord).filter(JobRecord.id == job_id).first() is not None
        except SQLAlchemyError:
            logger.exception(f"Database error checking if job {job_id} exists")
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
        except SQLAlchemyError:
            logger.exception(f"Database error deleting job {job_id}")
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

        self._jobs: dict[int, Job] = {}
        self._next_id = starting_id

    def save(self, job: Job) -> Job:
        """Save a job to memory."""
        if not job.is_persisted():
            job.id = self.get_next_id()
            logger.info(f"Assigned new ID {job.id} to unpersisted job for user {job.user_id}")

        self._jobs[job.id] = job
        logger.info(f"Job {job.id} saved to in-memory repository")
        return job

    def find_by_id(self, job_id: int) -> Job | None:
        """Find a job by its ID."""
        return self._jobs.get(job_id)

    def find_by_user_id(self, user_id: int) -> list[Job]:
        """Find all jobs for a specific user."""
        return [job for job in self._jobs.values() if job.user_id == user_id]

    def find_by_status(self, status: JobStatus) -> list[Job]:
        """Find all jobs with a specific status."""
        return [job for job in self._jobs.values() if job.status == status]

    def find_all(self, limit: int | None = None, offset: int = 0) -> list[Job]:
        """Find all jobs in the repository."""
        all_jobs = sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)

        if offset > 0:
            all_jobs = all_jobs[offset:]

        if limit is not None:
            all_jobs = all_jobs[:limit]

        return all_jobs

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
