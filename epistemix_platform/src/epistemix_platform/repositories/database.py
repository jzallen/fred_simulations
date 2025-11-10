"""
SQLAlchemy database models and configuration for the Epistemix API.
"""

import enum
import os
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Column, DateTime, Enum, ForeignKey, Integer, String, create_engine
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
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    user_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    request = Column(JSON, nullable=False)
    pod_phase = Column(Enum(PodPhaseEnum), nullable=False, default=PodPhaseEnum.RUNNING)
    container_status = Column(String, nullable=True)
    status = Column(Enum(RunStatusEnum), nullable=False, default=RunStatusEnum.SUBMITTED)
    user_deleted = Column(Integer, nullable=False, default=0)  # SQLite doesn't have native boolean
    epx_client_version = Column(String, nullable=False, default="1.2.2")
    config_url = Column(String, nullable=True)  # Presigned URL for run config (renamed from 'url')
    results_url = Column(String, nullable=True)  # Presigned URL for run results ZIP
    results_uploaded_at = Column(DateTime, nullable=True)  # Timestamp when results were uploaded


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
        connect_args={"check_same_thread": False},  # Required for SQLite in multi-threaded apps
    )


def create_postgresql_engine_with_iam(
    host: str,
    port: int,
    database: str,
    user: str,
    region: str,
    config: "Config",
) -> Engine:
    """Create PostgreSQL engine using RDS IAM authentication.

    Uses SQLAlchemy event listener to generate fresh IAM tokens (valid 15 minutes)
    for each new connection. This prevents token expiration failures.

    The connection pool recycles connections every 10 minutes (before 15-min token expiry)
    and uses pool_pre_ping to detect dead connections.

    Args:
        host: RDS endpoint hostname
        port: Database port (typically 5432)
        database: Database name
        user: IAM database username (must exist in RDS with rds_iam role)
        region: AWS region for RDS instance
        config: Configuration object with pool settings

    Returns:
        SQLAlchemy Engine configured for IAM authentication

    Security:
        - Token is never logged (even in debug mode)
        - SSL/TLS enforced (required by RDS for IAM auth)
        - Fresh token generated per connection (no expiration issues)

    Implementation:
        Uses AWS best practice pattern with do_connect event listener to
        generate tokens dynamically instead of embedding in connection URL.
        Reference: AWS RDS IAM authentication documentation

    Example:
        >>> engine = create_postgresql_engine_with_iam(
        ...     host="mydb.abc123.us-east-1.rds.amazonaws.com",
        ...     port=5432,
        ...     database="epistemixdb",
        ...     user="epistemix_api",
        ...     region="us-east-1",
        ...     config=config
        ... )
    """
    import logging

    import boto3
    from sqlalchemy import event

    logger = logging.getLogger(__name__)

    # Log connection attempt (metadata only, never log token!)
    logger.info(
        "Creating IAM-authenticated database connection",
        extra={"host": host, "port": port, "database": database, "user": user, "region": region},
    )

    # Create empty connection URL (no credentials)
    # Credentials will be provided by do_connect event listener
    connection_url = "postgresql://"

    # Create engine with IAM-appropriate settings
    engine = create_engine(
        connection_url,
        pool_size=config.DATABASE_POOL_SIZE,
        max_overflow=config.DATABASE_MAX_OVERFLOW,
        pool_timeout=config.DATABASE_POOL_TIMEOUT,
        pool_recycle=600,  # Recycle connections every 10 min (before 15-min token expiry)
        pool_pre_ping=True,  # Detect dead connections
        connect_args={
            "sslmode": "require",  # Required for IAM auth
            "connect_timeout": 10,
        },
    )

    # Event listener to generate fresh IAM token per connection
    @event.listens_for(engine, "do_connect")
    def provide_token(dialect, conn_rec, cargs, cparams):  # noqa: ARG001
        """Generate fresh IAM token for each database connection.

        This event listener runs before each connection attempt, ensuring
        we always use a valid token (never expired).

        Args:
            dialect: SQLAlchemy dialect (unused)
            conn_rec: Connection record (unused)
            cargs: Positional connection args (unused)
            cparams: Connection parameters dict (modified in-place)
        """
        # Generate fresh IAM token (valid 15 minutes)
        rds_client = boto3.client("rds", region_name=region)
        token = rds_client.generate_db_auth_token(
            DBHostname=host, Port=port, DBUsername=user, Region=region
        )

        # Provide connection parameters with fresh token
        cparams["host"] = host
        cparams["port"] = port
        cparams["user"] = user
        cparams["password"] = token  # Fresh token per connection
        cparams["database"] = database

    return engine


def create_engine_from_config(config: "Config" = None, database_url: str = None) -> Engine:
    """Factory function to create appropriate database engine based on configuration.

    Supports three authentication modes:
    1. IAM authentication (USE_IAM_AUTH=true) - short-lived tokens, no password
    2. Password authentication (DATABASE_URL) - traditional
    3. SQLite (sqlite:// URL) - local development

    Args:
        config: Configuration object (if None, will import and use default Config)
        database_url: Optional database URL to override config

    Returns:
        Configured SQLAlchemy engine based on the database URL and auth mode

    Raises:
        ValueError: If IAM auth is enabled but required env vars are missing
    """
    if config is None:
        from epistemix_platform.config import Config

        config = Config

    # Check for IAM authentication mode
    if os.getenv("USE_IAM_AUTH") == "true":
        # Parse connection parameters from environment
        host = os.getenv("DATABASE_HOST")
        port = int(os.getenv("DATABASE_PORT", "5432"))
        database = os.getenv("DATABASE_NAME")
        user = os.getenv("DATABASE_IAM_USER")
        region = os.getenv("AWS_REGION", "us-east-1")

        # Validate required parameters (fail fast with clear error message)
        if not all([host, database, user]):
            raise ValueError(
                "IAM authentication requires DATABASE_HOST, DATABASE_NAME, and DATABASE_IAM_USER "
                "environment variables"
            )

        return create_postgresql_engine_with_iam(host, port, database, user, region, config)

    # Traditional password authentication or SQLite
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


