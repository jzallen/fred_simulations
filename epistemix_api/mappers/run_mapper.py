"""
Run mapper for converting between Run domain objects and RunRecord database records.
"""

from epistemix_api.repositories.database import RunRecord, RunStatusEnum, PodPhaseEnum
from epistemix_api.models.run import Run, RunStatus, PodPhase


class RunMapper:
    """
    Handles conversion between Run domain objects and RunRecord database records.
    
    This mapper provides bidirectional conversion methods to separate
    the mapping logic from the repository implementation.
    """
    
    @staticmethod
    def record_to_domain(run_record: RunRecord) -> Run:
        """
        Convert a RunRecord database record to a Run domain object.
        
        Args:
            run_record: The database record to convert
            
        Returns:
            A Run domain object with the same data
        """
        return Run.create_persisted(
            run_id=run_record.id,
            job_id=run_record.job_id,
            user_id=run_record.user_id,
            created_at=run_record.created_at,
            updated_at=run_record.updated_at,
            request=run_record.request,
            pod_phase=RunMapper._enum_to_pod_phase(run_record.pod_phase),
            container_status=run_record.container_status,
            status=RunMapper._enum_to_run_status(run_record.status),
            user_deleted=bool(run_record.user_deleted),
            epx_client_version=run_record.epx_client_version
        )
    
    @staticmethod
    def domain_to_record(run: Run) -> RunRecord:
        """
        Convert a Run domain object to a RunRecord database record.
        
        Args:
            run: The domain object to convert
            
        Returns:
            A RunRecord database record with the same data
        """
        return RunRecord(
            id=run.id,
            job_id=run.job_id,
            user_id=run.user_id,
            created_at=run.created_at,
            updated_at=run.updated_at,
            request=run.request,
            pod_phase=RunMapper._pod_phase_to_enum(run.pod_phase),
            container_status=run.container_status,
            status=RunMapper._run_status_to_enum(run.status),
            user_deleted=1 if run.user_deleted else 0,
            epx_client_version=run.epx_client_version
        )
    
    @staticmethod
    def update_record_from_domain(record: RunRecord, run: Run) -> None:
        """
        Update a RunRecord database record from a Run domain object.
        
        Args:
            record: The database record to update
            run: The domain object with new data
        """
        record.job_id = run.job_id
        record.user_id = run.user_id
        record.created_at = run.created_at
        record.updated_at = run.updated_at
        record.request = run.request
        record.pod_phase = RunMapper._pod_phase_to_enum(run.pod_phase)
        record.container_status = run.container_status
        record.status = RunMapper._run_status_to_enum(run.status)
        record.user_deleted = 1 if run.user_deleted else 0
        record.epx_client_version = run.epx_client_version
    
    @staticmethod
    def _run_status_to_enum(status: RunStatus) -> RunStatusEnum:
        """Convert RunStatus to RunStatusEnum."""
        return RunStatusEnum(status.value)
    
    @staticmethod
    def _enum_to_run_status(status_enum: RunStatusEnum) -> RunStatus:
        """Convert RunStatusEnum to RunStatus."""
        return RunStatus(status_enum.value)
    
    @staticmethod
    def _pod_phase_to_enum(pod_phase: PodPhase) -> PodPhaseEnum:
        """Convert PodPhase to PodPhaseEnum."""
        return PodPhaseEnum(pod_phase.value)
    
    @staticmethod
    def _enum_to_pod_phase(pod_phase_enum: PodPhaseEnum) -> PodPhase:
        """Convert PodPhaseEnum to PodPhase."""
        return PodPhase(pod_phase_enum.value)
