"""
Run domain model for the Epistemix API.
Contains the core business logic and rules for run entities.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class RunStatus(Enum):
    """Enumeration of possible run statuses."""

    QUEUED = "QUEUED"
    NOT_STARTED = "NOT_STARTED"
    RUNNING = "RUNNING"
    ERROR = "ERROR"
    DONE = "DONE"
    # Legacy values for backward compatibility
    SUBMITTED = "Submitted"  # Maps to QUEUED
    FAILED = "Failed"  # Maps to ERROR
    CANCELLED = "Cancelled"  # Maps to ERROR


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
    created_at: datetime
    updated_at: datetime
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
    url: Optional[str] = None  # Presigned URL for this run

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
        epx_client_version: str = "1.2.2",
        url: Optional[str] = None,
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
            epx_client_version=epx_client_version,
            url=url,
        )

    @classmethod
    def create_persisted(
        cls,
        run_id: int,
        job_id: int,
        user_id: int,
        created_at: datetime,
        updated_at: datetime,
        request: Dict[str, Any],
        pod_phase: PodPhase = PodPhase.RUNNING,
        container_status: Optional[str] = None,
        status: RunStatus = RunStatus.SUBMITTED,
        user_deleted: bool = False,
        epx_client_version: str = "1.2.2",
        url: Optional[str] = None,
    ) -> "Run":
        """
        Create a persisted run (loaded from repository).

        Args:
            run_id: ID of the run
            job_id: ID of the associated job
            user_id: ID of the user who created the run
            created_at: Datetime object
            updated_at: Datetime object
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
            epx_client_version=epx_client_version,
            url=url,
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
        # Map legacy status values to expected client values
        status_mapping = {
            RunStatus.SUBMITTED: "QUEUED",
            RunStatus.FAILED: "ERROR",
            RunStatus.CANCELLED: "ERROR",
            # Direct mappings for new values
            RunStatus.QUEUED: "QUEUED",
            RunStatus.NOT_STARTED: "NOT_STARTED",
            RunStatus.RUNNING: "RUNNING",
            RunStatus.ERROR: "ERROR",
            RunStatus.DONE: "DONE",
        }

        mapped_status = status_mapping.get(self.status, self.status.value)

        return {
            "id": self.id,
            "jobId": self.job_id,
            "userId": self.user_id,
            "createdTs": self.created_at.isoformat(),
            "request": self.request,
            "podPhase": self.pod_phase.value,
            "containerStatus": self.container_status,
            "status": mapped_status,
            "userDeleted": self.user_deleted,
            "epxClientVersion": self.epx_client_version,
            "url": self.url,
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
            "runRequest": self.request,
        }

    def __eq__(self, other: object) -> bool:
        """Check equality based on run ID and other fields."""
        if not isinstance(other, Run):
            return False
        return self.to_dict() == other.to_dict()
