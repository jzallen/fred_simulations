"""
JobUpload domain model for the Epistemix API.
Contains the core business logic for job upload entities.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from epistemix_platform.models.upload_location import UploadLocation


@dataclass
class JobUpload:
    """
    Domain entity representing an upload associated with a job or run.

    This is a core business entity that represents metadata about
    an uploaded file without including the actual content.
    The storage implementation details are encapsulated in the UploadLocation.
    """

    context: str  # "job" or "run"
    upload_type: str  # "config", "input", "output", "results", "logs"
    job_id: int
    location: Optional[UploadLocation] = None
    run_id: Optional[int] = None

    def __post_init__(self):
        """Post-initialization validation."""
        self._validate()

    def _validate(self):
        """Validate the upload entity according to business rules."""
        if self.job_id <= 0:
            raise ValueError("Job ID must be positive")

        # Location is optional during creation (before upload location is generated)
        if self.location and not self.location.url:
            raise ValueError("Upload location URL cannot be empty when location is provided")

        if self.run_id is not None and self.run_id <= 0:
            raise ValueError("Run ID must be positive when provided")

        valid_contexts = ["job", "run"]
        if self.context not in valid_contexts:
            raise ValueError(f"Invalid context: {self.context}. Must be one of {valid_contexts}")

        valid_job_types = ["config", "input", "output", "results", "logs"]
        if self.upload_type not in valid_job_types:
            raise ValueError(
                f"Invalid job_type: {self.upload_type}. Must be one of {valid_job_types}"
            )

        # Validate context-type combinations
        if self.context == "job" and self.upload_type not in ["config", "input"]:
            raise ValueError(
                f"Job context only supports 'config' and 'input' types, got '{self.upload_type}'"
            )

        if self.context == "run" and self.upload_type not in [
            "config",
            "output",
            "results",
            "logs",
        ]:
            raise ValueError(
                f"Run context only supports 'config', 'output', 'results', and 'logs' types, "
                f"got '{self.upload_type}'"
            )

    def is_job_upload(self) -> bool:
        """Check if this is a job-level upload (not run-specific)."""
        return self.context == "job"

    def is_run_upload(self) -> bool:
        """Check if this is a run-level upload."""
        return self.context == "run"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the upload to a dictionary for API responses."""
        result = {
            "context": self.context,
            "uploadType": self.upload_type,
            "jobId": self.job_id,
            "runId": self.run_id,
        }
        if self.location:
            result["location"] = self.location.to_dict()
        return result

    def to_sanitized_dict(self) -> Dict[str, Any]:
        """Serialize the upload to a dictionary with sanitized location URL."""
        result = {
            "context": self.context,
            "uploadType": self.upload_type,
            "jobId": self.job_id,
            "runId": self.run_id,
        }
        if self.location:
            result["location"] = self.location.to_sanitized_dict()
        return result

    def get_default_filename(self) -> str:
        """
        Get a default filename for this upload based on its context and type.

        Returns:
            A filename with appropriate extension based on upload type
        """
        # Determine file extension based on upload type
        if self.upload_type == "config":
            extension = ".json"
        elif self.upload_type == "input":
            extension = ".zip"
        elif self.upload_type in ["output", "results"]:
            extension = ".csv"
        elif self.upload_type == "logs":
            extension = ".log"
        else:
            extension = ".txt"

        # Build filename based on context
        if self.context == "job":
            return f"job_{self.job_id}_{self.upload_type}{extension}"
        elif self.context == "run" and self.run_id:
            return f"run_{self.run_id}_{self.upload_type}{extension}"
        else:
            return f"{self.context}_{self.upload_type}{extension}"

    def __repr__(self) -> str:
        run_str = f", run_id={self.run_id}" if self.run_id else ""
        location_str = f", location={self.location.url}" if self.location else ""
        return (
            f"JobUpload(context={self.context}, type={self.upload_type}, "
            f"job_id={self.job_id}{run_str}{location_str})"
        )
