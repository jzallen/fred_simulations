"""
SQLAlchemy implementation of the Run repository.
"""

from typing import Optional, List, Callable
from sqlalchemy.orm import Session

from epistemix_api.models.run import Run, RunStatus
from epistemix_api.repositories.database import RunRecord, get_db_session
from epistemix_api.repositories.interfaces import IRunRepository
from epistemix_api.mappers.run_mapper import RunMapper


class SQLAlchemyRunRepository:
    """SQLAlchemy implementation of the IRunRepository interface."""
    
    def __init__(self, get_db_session_fn: Callable[[], Session] = get_db_session):
        """
        Initialize the repository with a session factory.
        
        Args:
            session_factory: A callable that returns a SQLAlchemy Session
        """
        self.session_factory = get_db_session_fn
    
    def save(self, run: Run) -> Run:
        """Save a run to the database."""
        session = self.session_factory()
        
        if run.is_persisted():
            run_record = session.query(RunRecord).filter_by(id=run.id).first()
            if not run_record:
                raise ValueError(f"Run with ID {run.id} not found")
            
            RunMapper.update_record_from_domain(run_record, run)
        else:
            # Create new run
            run_record = RunMapper.domain_to_record(run)
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
            return RunMapper.record_to_domain(run_record)
        return None
    
    def find_by_job_id(self, job_id: int) -> List[Run]:
        """Find all runs for a specific job."""
        session = self.session_factory()
        run_records = session.query(RunRecord).filter_by(job_id=job_id).all()
        
        return [RunMapper.record_to_domain(record) for record in run_records]
    
    def find_by_user_id(self, user_id: int) -> List[Run]:
        """Find all runs for a specific user."""
        session = self.session_factory()
        run_records = session.query(RunRecord).filter_by(user_id=user_id).all()
        
        return [RunMapper.record_to_domain(record) for record in run_records]
    
    def find_by_status(self, status: RunStatus) -> List[Run]:
        """Find all runs with a specific status."""
        session = self.session_factory()
        status_enum = RunMapper._run_status_to_enum(status)
        run_records = session.query(RunRecord).filter_by(status=status_enum).all()
        
        return [RunMapper.record_to_domain(record) for record in run_records]
    
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
