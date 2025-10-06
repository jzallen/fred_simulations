"""
SQLAlchemy database models and configuration for the Epistemix API.
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Column, DateTime, Enum, Integer, String, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

if TYPE_CHECKING:
    from epistemix_platform.config import Config

Base = declarative_base()


class JobStatusEnum(enum.Enum):
    """SQLAlchemy enum for job status."""

    CREATED = "created"
    SUBMITTED = "submitted"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunStatusEnum(enum.Enum):
    """SQLAlchemy enum for run status."""

    # New expected values
    QUEUED = "QUEUED"
    NOT_STARTED = "NOT_STARTED"
    RUNNING = "RUNNING"
    ERROR = "ERROR"
    DONE = "DONE"
    # Legacy values for backward compatibility
    SUBMITTED = "Submitted"
    RUNNING_LEGACY = "Running"
    FAILED = "Failed"
    CANCELLED = "Cancelled"


class PodPhaseEnum(enum.Enum):
    """SQLAlchemy enum for pod phase."""

    PENDING = "Pending"
    RUNNING = "Running"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    UNKNOWN = "Unknown"


class JobRecord(Base):
    """SQLAlchemy record for Job entities."""

    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    tags = Column(JSON, nullable=False, default=list)
    status = Column(Enum(JobStatusEnum), nullable=False, default=JobStatusEnum.CREATED)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    input_location = Column(String, nullable=True)  # S3 URL for job input
    config_location = Column(String, nullable=True)  # S3 URL for job config
    job_metadata = Column(
        JSON, nullable=False, default=dict
    )  # Renamed from 'metadata' to avoid SQLAlchemy conflict


class RunRecord(Base):
    """SQLAlchemy record for Run entities."""

    __tablename__ = "runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    request = Column(JSON, nullable=False)
    pod_phase = Column(Enum(PodPhaseEnum), nullable=False, default=PodPhaseEnum.RUNNING)
    container_status = Column(String, nullable=True)
    status = Column(Enum(RunStatusEnum), nullable=False, default=RunStatusEnum.SUBMITTED)
    user_deleted = Column(Integer, nullable=False, default=0)  # SQLite doesn't have native boolean
    epx_client_version = Column(String, nullable=False, default="1.2.2")
    url = Column(String, nullable=True)  # Store the presigned URL for this run


def create_postgresql_engine(database_url: str, config: "Config") -> Engine:
    """
    Create a PostgreSQL engine with connection pooling.

    Args:
        database_url: PostgreSQL connection string
        config: Configuration object with pool settings

    Returns:
        Configured SQLAlchemy engine for PostgreSQL
    """
    return create_engine(
        database_url,
        echo=False,
        pool_size=config.DATABASE_POOL_SIZE,
        max_overflow=config.DATABASE_MAX_OVERFLOW,
        pool_timeout=config.DATABASE_POOL_TIMEOUT,
        pool_pre_ping=True,  # Verify connections before using
    )


def create_sqlite_engine(database_url: str) -> Engine:
    """
    Create a SQLite engine with appropriate settings for multi-threaded apps.

    Args:
        database_url: SQLite connection string

    Returns:
        Configured SQLAlchemy engine for SQLite
    """
    return create_engine(
        database_url,
        echo=False,
        connect_args={"check_same_thread": False}  # Required for SQLite in multi-threaded apps
    )


def create_engine_from_config(config: "Config" = None, database_url: str = None) -> Engine:
    """
    Factory function to create the appropriate database engine based on configuration.

    Args:
        config: Configuration object (if None, will import and use default Config)
        database_url: Optional database URL to override config

    Returns:
        Configured SQLAlchemy engine based on the database URL
    """
    if config is None:
        from epistemix_platform.config import Config
        config = Config

    if database_url is None:
        database_url = config.get_database_url()

    # Normalize legacy postgres scheme for SQLAlchemy compatibility
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    # Choose appropriate engine based on database type
    if database_url.startswith("postgresql"):
        return create_postgresql_engine(database_url, config)
    else:
        return create_sqlite_engine(database_url)


class DatabaseManager:
    """Manages database connections and sessions."""

    def __init__(self, database_url: str = None, config: "Config" = None):
        """
        Initialize the database manager using the engine factory.

        Args:
            database_url: Optional SQLAlchemy database URL to override config
            config: Optional configuration object for database settings
        """
        self.engine = create_engine_from_config(config, database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def create_tables(self):
        """Create all database tables."""
        Base.metadata.create_all(bind=self.engine)

    def get_session(self):
        """Get a new database session."""
        return self.SessionLocal()

    def drop_tables(self):
        """Drop all database tables (useful for testing)."""
        Base.metadata.drop_all(bind=self.engine)


def get_database_manager(database_url: str = None, config: "Config" = None) -> DatabaseManager:
    """
    Get or create a database manager instance.

    Args:
        database_url: Optional SQLAlchemy database URL
        config: Optional configuration object

    Returns:
        DatabaseManager instance
    """
    return DatabaseManager(database_url, config)


def get_db_session():
    """Get a new database session."""
    return get_database_manager().get_session()
