"""
Upload location domain model for the Epistemix API.
Contains the unified model for handling presigned URLs for various upload scenarios.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class UploadLocation:
    """
    Represents a location for uploading content.
    
    This unified model replaces JobInputLocation, JobConfigLocation, and RunConfigLocation
    to provide a consistent interface for handling presigned URLs across different upload scenarios.
    """
    
    url: str

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary representation."""
        return {"url": self.url}
    
    def __eq__(self, other) -> bool:
        """Check equality based on URL."""
        if not isinstance(other, UploadLocation):
            return False
        return self.url == other.url
    
    def __repr__(self):
        """String representation for debugging."""
        return f"UploadLocation(url={self.url})"
