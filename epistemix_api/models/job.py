"""
Job domain model for the Epistemix API.
Contains the core business logic and rules for job entities.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
import uuid


class JobStatus(Enum):
    """Enumeration of possible job statuses."""
    CREATED = "created"
    SUBMITTED = "submitted"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobTag(Enum):
    """Enumeration of possible job tags."""
    INFO_JOB = "info_job"
    SIMULATION_JOB = "simulation_job"
    ANALYSIS_JOB = "analysis_job"
    DATA_JOB = "data_job"


@dataclass
class Job:
    """
    Job domain entity representing a job in the Epistemix system.
    
    This is a core business entity that encapsulates the essential
    properties and behaviors of a job.
    
    A Job can exist in two states:
    - Unpersisted: id is None (job has not been saved to repository)
    - Persisted: id is an integer (job has been saved and assigned an ID by repository)
    """
    
    # Required fields
    user_id: int
    tags: List[str] = field(default_factory=list)
    
    # Repository-managed field (None until persisted)
    id: Optional[int] = None
    
    # Optional fields with defaults
    status: JobStatus = JobStatus.CREATED
    created_at: datetime = field(default_factory=lambda: datetime.utcnow())
    updated_at: datetime = field(default_factory=lambda: datetime.utcnow())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization validation and setup."""
        self._validate()
    
    def _validate(self):
        """Validate the job entity according to business rules."""
        if self.id is not None and self.id <= 0:
            raise ValueError("Job ID must be positive when set")
        
        if self.user_id <= 0:
            raise ValueError("User ID must be positive")
        
        # Validate tags against known values
        valid_tag_values = [tag.value for tag in JobTag]
        for tag in self.tags:
            if tag not in valid_tag_values:
                # Allow unknown tags but log a warning in a real system
                pass
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the job if it doesn't already exist."""
        if tag not in self.tags:
            self.tags.append(tag)
            self._touch_updated_at()
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the job if it exists."""
        if tag in self.tags:
            self.tags.remove(tag)
            self._touch_updated_at()
    
    def update_status(self, new_status: JobStatus) -> None:
        """Update the job status with business logic validation."""
        if not self._is_valid_status_transition(self.status, new_status):
            raise ValueError(f"Invalid status transition from {self.status.value} to {new_status.value}")
        
        self.status = new_status
        self._touch_updated_at()
    
    def _is_valid_status_transition(self, from_status: JobStatus, to_status: JobStatus) -> bool:
        """Validate if a status transition is allowed according to business rules."""
        # Define valid transitions
        valid_transitions = {
            JobStatus.CREATED: [JobStatus.SUBMITTED, JobStatus.CANCELLED],
            JobStatus.SUBMITTED: [JobStatus.PROCESSING, JobStatus.CANCELLED],
            JobStatus.SUBMITTED: [JobStatus.PROCESSING, JobStatus.CANCELLED],
            JobStatus.PROCESSING: [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED],
            JobStatus.COMPLETED: [],  # Terminal state
            JobStatus.FAILED: [JobStatus.SUBMITTED],  # Can retry
            JobStatus.CANCELLED: []  # Terminal state
        }
        
        return to_status in valid_transitions.get(from_status, [])
    
    def _touch_updated_at(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()
    
    def is_persisted(self) -> bool:
        """Check if the job has been persisted (has an ID assigned by repository)."""
        return self.id is not None
    
    def is_active(self) -> bool:
        """Check if the job is in an active (non-terminal) state."""
        terminal_states = {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}
        return self.status not in terminal_states
    
    def has_tag(self, tag: str) -> bool:
        """Check if the job has a specific tag."""
        return tag in self.tags
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializes the job to a dictionary for API responses."""
       
        return {
            "id": self.id,
            "userId": self.user_id,  # Note: API uses camelCase
            "tags": self.tags,
            "status": self.status.value,
            "createdAt": self.created_at.isoformat(),
            "updatedAt": self.updated_at.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def create_new(cls, user_id: int, tags: List[str] = None) -> 'Job':
        """
        Factory method to create a new unpersisted job.
        
        This creates a job without an ID. The ID will be assigned by the repository
        when the job is persisted via repository.save().
        
        Args:
            user_id: ID of the user creating the job
            tags: Optional list of tags for the job
            
        Returns:
            A new Job instance with CREATED status and no ID (unpersisted)
        """
        if tags is None:
            tags = []
        
        job = cls(
            user_id=user_id,
            tags=tags.copy(),  # Defensive copy
            status=JobStatus.CREATED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        return job
    
    @classmethod
    def create_persisted(
        cls, 
        job_id: int, 
        user_id: int, 
        tags: List[str] = None, 
        status: JobStatus = JobStatus.CREATED,
        created_at: datetime = None,
        updated_at: datetime = None,
        metadata: Dict[str, Any] = None,
    ) -> 'Job':
        """
        Factory method to create a job with an existing ID (for loading from repository).
        
        This method should only be used by repository implementations when
        reconstructing jobs from persistent storage.
        
        Args:
            job_id: Existing ID assigned by the repository
            user_id: ID of the user who owns the job
            tags: Optional list of tags for the job
            status: Job status (defaults to CREATED)
            created_at: Creation timestamp (defaults to current time)
            updated_at: Last update timestamp (defaults to current time)
            metadata: Job metadata (defaults to empty dict)
            
        Returns:
            A new Job instance with the specified ID (persisted)
        """
        if tags is None:
            tags = []
        if created_at is None:
            created_at = datetime.utcnow()
        if updated_at is None:
            updated_at = datetime.utcnow()
        if metadata is None:
            metadata = {}
        
        job = cls(
            id=job_id,
            user_id=user_id,
            tags=tags.copy(),
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            metadata=metadata
        )
        
        return job
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Job):
            return False
        
        return self.to_dict() == other.to_dict()

    def __hash__(self) -> int:
        if self.is_persisted():
            return hash(self.id)
        return hash(id(self))  # Use object ID for unpersisted jobs
    
    def __repr__(self) -> str:
        id_str = str(self.id) if self.is_persisted() else "unpersisted"
        return f"Job(id={id_str}, user_id={self.user_id}, status={self.status.value}, tags={self.tags})"


@dataclass
class JobInputLocation:
    """URL where job input is stored."""
    url: str

    def to_dict(self) -> Dict[str, str]:
        return {"url": self.url}
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, JobInputLocation):
            return False
        return self.url == other.url
    
    def __repr__(self):
        return f"JobInputLocation(url={self.url})"



@dataclass
class JobConfigLocation:
    """URL where job configuration is stored."""
    url: str

    def to_dict(self) -> Dict[str, str]:
        return {"url": self.url}
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, JobConfigLocation):
            return False
        return self.url == other.url
    
    def __repr__(self):
        return f"JobConfigLocation(url={self.url})"
