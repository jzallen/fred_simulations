"""
Pydantic models for API request validation.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class RegisterJobRequest(BaseModel):
    """Request model for job registration."""

    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={"example": {"userId": "user123", "tags": ["simulation", "covid19"]}},
    )

    userId: int = Field(default_factory=int, description="User ID for the job registration")
    tags: List[str] = Field(
        default_factory=list, description="List of tags associated with the job"
    )


class SubmitJobRequest(BaseModel):
    """Request model for job submission."""

    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={"example": {"jobId": 12345, "context": "job", "type": "input"}},
    )

    jobId: int = Field(description="ID of the job to submit")
    context: str = Field(default="job", description="Context for the job submission")
    type: str = Field(default="input", description="Type of the job submission")


class FredArg(BaseModel):
    """Model for FRED command line arguments."""

    model_config = ConfigDict(extra="ignore")

    flag: str = Field(description="Command line flag (e.g., '-p')")
    value: str = Field(description="Value for the flag")


class Population(BaseModel):
    """Model for population configuration."""

    model_config = ConfigDict(extra="ignore")

    version: str = Field(description="Population version (e.g., 'US_2010.v5')")
    locations: List[str] = Field(description="List of location names")


class RunRequest(BaseModel):
    """Individual run request model for FRED simulations."""

    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={
            "example": {
                "jobId": 123,
                "workingDir": "/workspaces/fred_simulations",
                "size": "hot",
                "fredVersion": "latest",
                "population": {"version": "US_2010.v5", "locations": ["Loving_County_TX"]},
                "fredArgs": [{"flag": "-p", "value": "main.fred"}],
                "fredFiles": [
                    "/workspaces/fred_simulations/simulations/agent_info_demo/agent_info.fred"
                ],
            }
        },
    )

    jobId: int = Field(description="ID of the job for this run")
    workingDir: str = Field(description="Working directory for the simulation")
    size: str = Field(description="Size configuration for the run (e.g., 'hot')")
    fredVersion: str = Field(description="Version of FRED to use")
    population: Population = Field(description="Population configuration")
    fredArgs: List[FredArg] = Field(description="FRED command line arguments")
    fredFiles: List[str] = Field(description="List of FRED configuration files")


class SubmitRunsRequest(BaseModel):
    """Request model for submitting multiple runs."""

    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={
            "example": {
                "runRequests": [
                    {
                        "jobId": 123,
                        "workingDir": "/workspaces/fred_simulations",
                        "size": "hot",
                        "fredVersion": "latest",
                        "population": {"version": "US_2010.v5", "locations": ["Loving_County_TX"]},
                        "fredArgs": [{"flag": "-p", "value": "main.fred"}],
                        "fredFiles": [
                            "/workspaces/fred_simulations/simulations/agent_info_demo/agent_info.fred"
                        ],
                    }
                ]
            }
        },
    )

    runRequests: List[RunRequest] = Field(description="List of run requests to submit")
