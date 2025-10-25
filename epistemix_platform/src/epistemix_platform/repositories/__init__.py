"""
Repositories package for the Epistemix API.
Contains data persistence abstractions and implementations.
"""

from .database import get_database_manager
from .interfaces import (
    IJobRepository,
    IResultsRepository,
    IRunRepository,
    IUploadLocationRepository,
)
from .job_repository import InMemoryJobRepository, SQLAlchemyJobRepository
from .run_repository import SQLAlchemyRunRepository
from .s3_results_repository import S3ResultsRepository  # pants: no-infer-dep
from .s3_upload_location_repository import S3UploadLocationRepository  # pants: no-infer-dep


__all__ = [
    # Interfaces
    "IJobRepository",
    "IRunRepository",
    "IUploadLocationRepository",
    "IResultsRepository",
    # Implementations
    "InMemoryJobRepository",
    "SQLAlchemyJobRepository",
    "SQLAlchemyRunRepository",
    "S3UploadLocationRepository",
    "S3ResultsRepository",
    # Utilities
    "get_database_manager",
]
