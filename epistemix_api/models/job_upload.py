"""
JobUpload domain model for the Epistemix API.
Contains the core business logic for job upload entities.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any

from epistemix_api.models.upload_location import UploadLocation


@dataclass
class JobUpload:
    """
    Domain entity representing an upload associated with a job or run.
    
    This is a core business entity that represents metadata about
    an uploaded file without including the actual content.
    The storage implementation details are encapsulated in the UploadLocation.
    """
    
    upload_type: str  # "job_config", "job_input", "run_output", etc.
    job_id: int
    location: UploadLocation
    run_id: Optional[int] = None
    
    def __post_init__(self):
        """Post-initialization validation."""
        self._validate()
    
    def _validate(self):
        """Validate the upload entity according to business rules."""
        if self.job_id <= 0:
            raise ValueError("Job ID must be positive")
        
        if not self.location or not self.location.url:
            raise ValueError("Upload location cannot be empty")
        
        if self.run_id is not None and self.run_id <= 0:
            raise ValueError("Run ID must be positive when provided")
        
        valid_upload_types = ["job_config", "job_input", "run_output", "run_config", "run_results", "run_logs"]
        if self.upload_type not in valid_upload_types:
            raise ValueError(f"Invalid upload type: {self.upload_type}")
    
    def is_job_upload(self) -> bool:
        """Check if this is a job-level upload (not run-specific)."""
        return self.upload_type in ["job_config", "job_input"]
    
    def is_run_upload(self) -> bool:
        """Check if this is a run-level upload."""
        return self.upload_type in ["run_output", "run_config", "run_results", "run_logs"]
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize the upload to a dictionary for API responses."""
        return {
            "uploadType": self.upload_type,
            "jobId": self.job_id,
            "runId": self.run_id,
            "location": self.location.to_dict()
        }
    
    def __repr__(self) -> str:
        run_str = f", run_id={self.run_id}" if self.run_id else ""
        return f"JobUpload(type={self.upload_type}, job_id={self.job_id}{run_str}, location={self.location.url})"