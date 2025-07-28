"""
Run domain model for the Epistemix API.
Contains the core business logic and rules for run entities.
"""

from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any


class RunStatus(Enum):
    """Enumeration of possible run statuses."""
    SUBMITTED = "Submitted"
    RUNNING = "Running"
    DONE = "DONE"
    FAILED = "Failed"
    CANCELLED = "Cancelled"


class PodPhase(Enum):
    """Enumeration of possible pod phases."""
    PENDING = "Pending"
    RUNNING = "Running"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    UNKNOWN = "Unknown"


@dataclass
class Run:
    """
    Run domain entity representing a run in the Epistemix system.
    
    This is a core business entity that encapsulates the essential
    properties and behaviors of a run.
    
    A Run can exist in two states:
    - Unpersisted: id is None (run has not been saved to repository)
    - Persisted: id is an integer (run has been saved and assigned an ID by repository)
    """
    
    # Required fields
    job_id: int
    user_id: int
    created_at: str  # ISO timestamp string
    updated_at: str  # ISO timestamp string
    request: Dict[str, Any]  # Full run request data
    pod_phase: PodPhase = PodPhase.RUNNING
    
    # Repository-managed field (None until persisted)
    id: Optional[int] = None
    
    # Optional fields with defaults
    pod_phase: PodPhase = PodPhase.RUNNING
    container_status: Optional[str] = None
    status: RunStatus = RunStatus.SUBMITTED
    user_deleted: bool = False
    epx_client_version: str = "1.2.2"
    
    @classmethod
    def create_unpersisted(
        cls,
        job_id: int,
        user_id: int,
        request: Dict[str, Any],
        pod_phase: PodPhase = PodPhase.RUNNING,
        container_status: Optional[str] = None,
        status: RunStatus = RunStatus.SUBMITTED,
        user_deleted: bool = False,
        epx_client_version: str = "1.2.2"
    ) -> "Run":
        """
        Create a new unpersisted run.
        
        Args:
            job_id: ID of the associated job
            user_id: ID of the user who created the run
            request: Full run request data
            pod_phase: Phase of the pod
            container_status: Status of the container
            status: Status of the run
            user_deleted: Whether the user has deleted the run
            epx_client_version: Version of the EPX client
            
        Returns:
            A new Run instance with id=None
        """
        return cls(
            job_id=job_id,
            user_id=user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            request=request,
            id=None,
            pod_phase=pod_phase,
            container_status=container_status,
            status=status,
            user_deleted=user_deleted,
            epx_client_version=epx_client_version
        )
    
    @classmethod
    def create_persisted(
        cls,
        run_id: int,
        job_id: int,
        user_id: int,
        created_at: str,
        updated_at: str,
        request: Dict[str, Any],
        pod_phase: PodPhase = PodPhase.RUNNING,
        container_status: Optional[str] = None,
        status: RunStatus = RunStatus.SUBMITTED,
        user_deleted: bool = False,
        epx_client_version: str = "1.2.2"
    ) -> "Run":
        """
        Create a persisted run (loaded from repository).
        
        Args:
            run_id: ID of the run
            job_id: ID of the associated job
            user_id: ID of the user who created the run
            created_at: ISO timestamp string
            updated_at: ISO timestamp string
            request: Full run request data
            pod_phase: Phase of the pod
            container_status: Status of the container
            status: Status of the run
            user_deleted: Whether the user has deleted the run
            epx_client_version: Version of the EPX client
            
        Returns:
            A new Run instance with the specified ID
        """
        return cls(
            job_id=job_id,
            user_id=user_id,
            created_at=created_at,
            updated_at=updated_at,
            request=request,
            id=run_id,
            pod_phase=pod_phase,
            container_status=container_status,
            status=status,
            user_deleted=user_deleted,
            epx_client_version=epx_client_version
        )
    
    def is_persisted(self) -> bool:
        """Check if this run has been persisted to a repository."""
        return self.id is not None
    
    def update_status(self, status: RunStatus) -> None:
        """Update the run status."""
        self.status = status
    
    def update_pod_phase(self, pod_phase: PodPhase) -> None:
        """Update the pod phase."""
        self.pod_phase = pod_phase
    
    # TODO: See if field from dataclass lets you alias names, if so asdict can be used which
    # supports serializing nested dataclasses and enums automatically.
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the run to a dictionary representation.
        
        Returns:
            Dictionary representation of the run
        """
        return {
            "id": self.id,
            "jobId": self.job_id,
            "userId": self.user_id,
            "createdTs": self.created_at,
            "request": self.request,
            "podPhase": self.pod_phase.value,
            "containerStatus": self.container_status,
            "status": self.status.value,
            "userDeleted": self.user_deleted,
            "epxClientVersion": self.epx_client_version
        }
    
    def to_run_response_dict(self) -> Dict[str, Any]:
        """
        Convert the run to a run response dictionary format.
        
        Returns:
            Dictionary representation suitable for run responses
        """
        return {
            "runId": self.id,
            "jobId": self.job_id,
            "status": self.status.value,
            "errors": None,
            "runRequest": self.request
        }
    
    def __eq__(self, other: object) -> bool:
        """Check equality based on run ID and other fields."""
        if not isinstance(other, Run):
            return False
        return self.to_dict() == other.to_dict()

    
@dataclass
class RunConfigLocation:
    """
    Represents the location of a run configuration.
    
    This is used to return the pre-signed URL for uploading run configurations.
    """
    
    url: str

    def to_dict(self) -> Dict[str, str]:
        return {"url": self.url}
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, RunConfigLocation):
            return False
        return self.url == other.url
    
    def __repr__(self):
        return f"RunConfigLocation(url={self.url})"
