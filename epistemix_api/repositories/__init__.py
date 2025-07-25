"""
Repositories package for the Epistemix API.
Contains data persistence abstractions and implementations.
"""

from .interfaces import IJobRepository
from .job_repository import InMemoryJobRepository, SQLAlchemyJobRepository
from .database import get_database_manager

__all__ = [
    'IJobRepository',
    'InMemoryJobRepository', 
    'SQLAlchemyJobRepository',
    'get_database_manager'
]
