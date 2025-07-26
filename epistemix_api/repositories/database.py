"""
SQLAlchemy database models and configuration for the Epistemix API.
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, Enum
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import enum

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
    SUBMITTED = "Submitted"
    RUNNING = "Running"
    DONE = "DONE"
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
    __tablename__ = 'jobs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    tags = Column(JSON, nullable=False, default=list)
    status = Column(Enum(JobStatusEnum), nullable=False, default=JobStatusEnum.CREATED)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    job_metadata = Column(JSON, nullable=False, default=dict)  # Renamed from 'metadata' to avoid SQLAlchemy conflict


class RunRecord(Base):
    """SQLAlchemy record for Run entities."""
    __tablename__ = 'runs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    created_ts = Column(String, nullable=False)  # ISO timestamp string
    request = Column(JSON, nullable=False)  # Full run request data
    pod_phase = Column(Enum(PodPhaseEnum), nullable=False, default=PodPhaseEnum.RUNNING)
    container_status = Column(String, nullable=True)
    status = Column(Enum(RunStatusEnum), nullable=False, default=RunStatusEnum.SUBMITTED)
    user_deleted = Column(Integer, nullable=False, default=0)  # SQLite doesn't have native boolean
    epx_client_version = Column(String, nullable=False, default="1.2.2")


class DatabaseManager:
    """Manages database connections and sessions."""
    
    def __init__(self, database_url: str = "sqlite:///epistemix_jobs.db"):
        """
        Initialize the database manager.
        
        Args:
            database_url: SQLAlchemy database URL
        """
        self.engine = create_engine(database_url, echo=False)
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


def get_database_manager(database_url: str = "sqlite:///epistemix_jobs.db") -> DatabaseManager:
    """Get or create a database manager instance for the given URL."""
    return DatabaseManager(database_url)

def get_db_session():
    """Get a new database session."""
    return get_database_manager().get_session()
