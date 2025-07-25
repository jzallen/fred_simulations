"""
Pydantic models for API request validation.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class RegisterJobRequest(BaseModel):
    """Request model for job registration."""
    
    model_config = ConfigDict(
        # Allow extra fields to be ignored rather than causing validation errors
        extra="ignore",
        # Generate example for documentation
        json_schema_extra={
            "example": {
                "userId": "user123",
                "tags": ["simulation", "covid19"]
            }
        }
    )
    
    userId: int = Field(
        default_factory=int, 
        description="User ID for the job registration"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="List of tags associated with the job"
    )
