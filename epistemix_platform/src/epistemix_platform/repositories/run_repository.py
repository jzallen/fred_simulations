"""
SQLAlchemy implementation of the Run repository.
"""

from typing import TYPE_CHECKING, Callable, List, Optional

from sqlalchemy.orm import Session

from epistemix_platform.models.run import Run, RunStatus
from epistemix_platform.repositories.database import RunRecord, get_db_session


if TYPE_CHECKING:
    from epistemix_platform.mappers.run_mapper import RunMapper


class SQLAlchemyRunRepository:
    """SQLAlchemy implementation of the IRunRepository interface."""

    def __init__(
        self, run_mapper: "RunMapper", get_db_session_fn: Callable[[], Session] = get_db_session
    ):
        """
        Initialize the repository with mapper dependency injection.

        Args:
            run_mapper: The RunMapper instance for converting between domain and database models
            get_db_session_fn: Factory function for creating database sessions
        """
        self._run_mapper = run_mapper
        self.session_factory = get_db_session_fn

    def save(self, run: Run) -> Run:
        """Save a run to the database."""
        session = self.session_factory()

        if run.is_persisted():
            run_record = session.query(RunRecord).filter_by(id=run.id).first()
            if not run_record:
                raise ValueError(f"Run with ID {run.id} not found")

            self._run_mapper.update_record_from_domain(run_record, run)
        else:
            # Create new run
            run_record = self._run_mapper.domain_to_record(run)
            session.add(run_record)
            session.flush()  # Get the ID without committing

            # Update the run with the assigned ID
            run.id = run_record.id

        return run

    def find_by_id(self, run_id: int) -> Optional[Run]:
        """Find a run by its ID."""
        session = self.session_factory()
        run_record = session.query(RunRecord).filter_by(id=run_id).first()

        if run_record:
            return self._run_mapper.record_to_domain(run_record)
        return None

    def find_by_job_id(self, job_id: int) -> List[Run]:
        """Find all runs for a specific job."""
        session = self.session_factory()
        run_records = session.query(RunRecord).filter_by(job_id=job_id).all()

        return [self._run_mapper.record_to_domain(record) for record in run_records]

    def find_by_user_id(self, user_id: int) -> List[Run]:
        """Find all runs for a specific user."""
        session = self.session_factory()
        run_records = session.query(RunRecord).filter_by(user_id=user_id).all()

        return [self._run_mapper.record_to_domain(record) for record in run_records]

    def find_by_status(self, status: RunStatus) -> List[Run]:
        """Find all runs with a specific status."""
        session = self.session_factory()
        status_enum = self._run_mapper._run_status_to_enum(status)
        run_records = session.query(RunRecord).filter_by(status=status_enum).all()

        return [self._run_mapper.record_to_domain(record) for record in run_records]

    def exists(self, run_id: int) -> bool:
        """Check if a run exists."""
        session = self.session_factory()
        return session.query(RunRecord).filter_by(id=run_id).first() is not None

    def delete(self, run_id: int) -> bool:
        """Delete a run from the repository."""
        session = self.session_factory()
        run_record = session.query(RunRecord).filter_by(id=run_id).first()

        if run_record:
            session.delete(run_record)
            return True
        return False
