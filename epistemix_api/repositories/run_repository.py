"""
SQLAlchemy implementation of the Run repository.
"""

from typing import Optional, List, Callable
from sqlalchemy.orm import Session

from epistemix_api.models.run import Run, RunStatus, PodPhase
from epistemix_api.repositories.database import RunRecord, RunStatusEnum, PodPhaseEnum
from epistemix_api.repositories.interfaces import IRunRepository


class SQLAlchemyRunRepository:
    """SQLAlchemy implementation of the IRunRepository interface."""
    
    def __init__(self, session_factory: Callable[[], Session]):
        """
        Initialize the repository with a session factory.
        
        Args:
            session_factory: A callable that returns a SQLAlchemy Session
        """
        self.session_factory = session_factory
    
    def save(self, run: Run) -> Run:
        """Save a run to the database."""
        session = self.session_factory()
        
        if run.is_persisted():
            # Update existing run
            run_record = session.query(RunRecord).filter_by(id=run.id).first()
            if not run_record:
                raise ValueError(f"Run with ID {run.id} not found")
            
            self._update_record_from_run(run_record, run)
        else:
            # Create new run
            run_record = self._create_record_from_run(run)
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
            return self._create_run_from_record(run_record)
        return None
    
    def find_by_job_id(self, job_id: int) -> List[Run]:
        """Find all runs for a specific job."""
        session = self.session_factory()
        run_records = session.query(RunRecord).filter_by(job_id=job_id).all()
        
        return [self._create_run_from_record(record) for record in run_records]
    
    def find_by_user_id(self, user_id: int) -> List[Run]:
        """Find all runs for a specific user."""
        session = self.session_factory()
        run_records = session.query(RunRecord).filter_by(user_id=user_id).all()
        
        return [self._create_run_from_record(record) for record in run_records]
    
    def find_by_status(self, status: RunStatus) -> List[Run]:
        """Find all runs with a specific status."""
        session = self.session_factory()
        status_enum = self._run_status_to_enum(status)
        run_records = session.query(RunRecord).filter_by(status=status_enum).all()
        
        return [self._create_run_from_record(record) for record in run_records]
    
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
    
    def _create_record_from_run(self, run: Run) -> RunRecord:
        """Create a RunRecord from a Run domain object."""
        return RunRecord(
            job_id=run.job_id,
            user_id=run.user_id,
            created_ts=run.created_ts,
            request=run.request,
            pod_phase=self._pod_phase_to_enum(run.pod_phase),
            container_status=run.container_status,
            status=self._run_status_to_enum(run.status),
            user_deleted=1 if run.user_deleted else 0,
            epx_client_version=run.epx_client_version
        )
    
    def _update_record_from_run(self, record: RunRecord, run: Run) -> None:
        """Update a RunRecord from a Run domain object."""
        record.job_id = run.job_id
        record.user_id = run.user_id
        record.created_ts = run.created_ts
        record.request = run.request
        record.pod_phase = self._pod_phase_to_enum(run.pod_phase)
        record.container_status = run.container_status
        record.status = self._run_status_to_enum(run.status)
        record.user_deleted = 1 if run.user_deleted else 0
        record.epx_client_version = run.epx_client_version
    
    def _create_run_from_record(self, record: RunRecord) -> Run:
        """Create a Run domain object from a RunRecord."""
        return Run.create_persisted(
            run_id=record.id,
            job_id=record.job_id,
            user_id=record.user_id,
            created_ts=record.created_ts,
            request=record.request,
            pod_phase=self._enum_to_pod_phase(record.pod_phase),
            container_status=record.container_status,
            status=self._enum_to_run_status(record.status),
            user_deleted=bool(record.user_deleted),
            epx_client_version=record.epx_client_version
        )
    
    def _run_status_to_enum(self, status: RunStatus) -> RunStatusEnum:
        """Convert RunStatus to RunStatusEnum."""
        return RunStatusEnum(status.value)
    
    def _enum_to_run_status(self, status_enum: RunStatusEnum) -> RunStatus:
        """Convert RunStatusEnum to RunStatus."""
        return RunStatus(status_enum.value)
    
    def _pod_phase_to_enum(self, pod_phase: PodPhase) -> PodPhaseEnum:
        """Convert PodPhase to PodPhaseEnum."""
        return PodPhaseEnum(pod_phase.value)
    
    def _enum_to_pod_phase(self, pod_phase_enum: PodPhaseEnum) -> PodPhase:
        """Convert PodPhaseEnum to PodPhase."""
        return PodPhase(pod_phase_enum.value)
