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
    REGISTERED = "registered"
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
    """
    
    # Required fields
    id: int
    user_id: int
    tags: List[str] = field(default_factory=list)
    
    # Optional fields with defaults
    status: JobStatus = JobStatus.CREATED
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization validation and setup."""
        self._validate()
    
    def _validate(self):
        """Validate the job entity according to business rules."""
        if self.id <= 0:
            raise ValueError("Job ID must be positive")
        
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
            JobStatus.CREATED: [JobStatus.REGISTERED, JobStatus.CANCELLED],
            JobStatus.REGISTERED: [JobStatus.SUBMITTED, JobStatus.CANCELLED],
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
    
    def is_active(self) -> bool:
        """Check if the job is in an active (non-terminal) state."""
        terminal_states = {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}
        return self.status not in terminal_states
    
    def has_tag(self, tag: str) -> bool:
        """Check if the job has a specific tag."""
        return tag in self.tags
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the job to a dictionary representation."""
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
    def create_new(cls, job_id: int, user_id: int, tags: List[str] = None) -> 'Job':
        """
        Factory method to create a new job with proper initialization.
        
        Args:
            job_id: Unique identifier for the job
            user_id: ID of the user creating the job
            tags: Optional list of tags for the job
            
        Returns:
            A new Job instance with CREATED status
        """
        if tags is None:
            tags = []
        
        job = cls(
            id=job_id,
            user_id=user_id,
            tags=tags.copy(),  # Defensive copy
            status=JobStatus.CREATED
        )
        
        return job
    
    @classmethod
    def register(cls, job_id: int, user_id: int, tags: List[str] = None) -> 'Job':
        """
        Factory method to create a registered job (as per the /jobs/register endpoint).
        
        Args:
            job_id: Unique identifier for the job
            user_id: ID of the user registering the job
            tags: Optional list of tags for the job
            
        Returns:
            A new Job instance with REGISTERED status
        """
        if tags is None:
            tags = []
        
        job = cls(
            id=job_id,
            user_id=user_id,
            tags=tags.copy(),
            status=JobStatus.REGISTERED
        )
        
        return job
    
    def __eq__(self, other) -> bool:
        """Check equality based on job ID."""
        if not isinstance(other, Job):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        """Hash based on job ID."""
        return hash(self.id)
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"Job(id={self.id}, user_id={self.user_id}, status={self.status.value}, tags={self.tags})"
