"""
Tests for SQLAlchemy job repository implementation.
"""

import os
import pytest
from freezegun import freeze_time
from datetime import datetime

from epistemix_api.models.job import Job, JobStatus
from epistemix_api.repositories import SQLAlchemyJobRepository
from epistemix_api.repositories.interfaces import IJobRepository
from epistemix_api.repositories.database import get_database_manager

@pytest.fixture
def repository():
    """Create a fresh repository for each test."""
    test_db_url = "sqlite:///test_sqlalchemy_job_repository.db"
    test_db_manager = get_database_manager(test_db_url)
    test_db_manager.drop_tables()
    test_db_manager.create_tables()

    # Create a repository with a session factory that uses the test database
    yield SQLAlchemyJobRepository(get_db_session_fn=test_db_manager.get_session)

    try:
        test_db_manager.drop_tables()
        os.remove("test_sqlalchemy_job_repository.db")
    except FileNotFoundError:
        pass

class TestSQLAlchemyJobRepository:
    """Test cases for the SQLAlchemyJobRepository implementation."""
    
    @pytest.fixture
    def sample_job(self) -> Job:
        """Create a sample unpersisted job for testing."""
        with freeze_time("2025-01-01 12:00:00"):
            return Job.create_new(user_id=456, tags=["info_job"])
    
    def test_repository_implements_interface(self, repository):
        """Test that SQLAlchemyJobRepository implements IJobRepository."""
        assert isinstance(repository, IJobRepository)
    
    @freeze_time("2025-01-01 12:00:00")
    def test_save_creates_new_job(self, repository, sample_job):
        """Test that save() creates a new job and assigns an ID."""
        
        # Act
        saved_job = repository.save(sample_job)
        
        # Assert
        expected_job = Job.create_persisted(
            job_id=1,
            user_id=456,
            tags=["info_job"],
            status=JobStatus.CREATED,
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            updated_at=datetime(2025, 1, 1, 12, 0, 0)
        )
        assert saved_job == expected_job
    
    @freeze_time("2025-01-01 12:00:00")
    def test_save_updates_existing_job(self, repository, sample_job):
        """Test that save() updates an existing job."""
        # Arrange - First create and save a job
        saved_job = repository.save(sample_job)
        original_id = saved_job.id
        original_created_at = saved_job.created_at
        
        # Move time forward for the update
        with freeze_time("2025-01-01 12:05:00"):
            # Modify the job
            saved_job.add_tag("analysis_job")
            saved_job.update_status(JobStatus.SUBMITTED)
            saved_job.metadata["test_key"] = "test_value"
            
            # Act - Save the modified job
            updated_job = repository.save(saved_job)
        
        # Assert
        expected_job = Job.create_persisted(
            job_id=original_id,
            user_id=saved_job.user_id,
            tags=saved_job.tags,
            status=JobStatus.SUBMITTED,
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            updated_at=datetime(2025, 1, 1, 12, 5, 0),
            metadata=saved_job.metadata
        )
        assert updated_job == expected_job
    
    @freeze_time("2025-01-01 12:00:00")
    def test_find_by_id_returns_existing_job(self, repository, sample_job):
        """Test that find_by_id() returns an existing job."""
        # Arrange - First create and save a job
        saved_job = repository.save(sample_job)
        job_id = saved_job.id
        
        # Act
        found_job = repository.find_by_id(job_id)
        
        # Assert
        assert found_job is not None
        expected_job = Job.create_persisted(
            job_id=job_id,
            user_id=sample_job.user_id,
            tags=sample_job.tags,
            status=sample_job.status,
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            updated_at=datetime(2025, 1, 1, 12, 0, 0)
        )
        assert found_job == expected_job
    
    def test_find_by_id_returns_none_for_nonexistent_job(self, repository):
        """Test that find_by_id() returns None for a non-existent job ID."""
        # Act
        found_job = repository.find_by_id(999)
        
        # Assert
        assert found_job is None
    
    @freeze_time("2025-01-01 12:00:00")
    def test_find_by_id_returns_job_with_updated_data(self, repository, sample_job):
        """Test that find_by_id() returns a job with its most recent data after updates."""
        # Arrange - Create, save, and update a job
        saved_job = repository.save(sample_job)
        job_id = saved_job.id
        
        # Move time forward and update the job
        with freeze_time("2025-01-01 12:10:00"):
            saved_job.add_tag("analysis_job")
            saved_job.update_status(JobStatus.SUBMITTED)
            saved_job.metadata["updated"] = True
            updated_job = repository.save(saved_job)
        
        # Act - Find the job by ID
        found_job = repository.find_by_id(job_id)
        
        # Assert
        assert found_job is not None
        expected_job = Job.create_persisted(
            job_id=job_id,
            user_id=sample_job.user_id,
            tags=["info_job", "analysis_job"],
            status=JobStatus.SUBMITTED,
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            updated_at=datetime(2025, 1, 1, 12, 10, 0),
            metadata={"updated": True}
        )
        assert found_job == expected_job
    
    @freeze_time("2025-01-01 12:00:00")
    def test_find_by_user_id_returns_all_user_jobs(self, repository):
        """Test that find_by_user_id() returns all jobs for a specific user."""
        # Arrange - Create jobs for different users
        user_123_job1 = Job.create_new(user_id=123, tags=["job1"])
        user_123_job2 = Job.create_new(user_id=123, tags=["job2"])
        user_456_job = Job.create_new(user_id=456, tags=["other_user"])
        
        # Save all jobs
        saved_job1 = repository.save(user_123_job1)
        saved_job2 = repository.save(user_123_job2)
        saved_job3 = repository.save(user_456_job)
        
        # Act
        user_123_jobs = repository.find_by_user_id(123)
        
        # Assert
        assert user_123_jobs == [saved_job1, saved_job2]
        
        for job in user_123_jobs:
            assert job.user_id == 123
    
    def test_find_by_user_id_returns_empty_list_for_nonexistent_user(self, repository):
        """Test that find_by_user_id() returns empty list for user with no jobs."""
        # Arrange - Create a job for a different user
        other_user_job = Job.create_new(user_id=999, tags=["other"])
        repository.save(other_user_job)
        
        # Act - Look for jobs for a user that has none
        user_jobs = repository.find_by_user_id(123)
        
        # Assert
        assert user_jobs == []
    
    @freeze_time("2025-01-01 12:00:00")
    def test_find_by_user_id_returns_updated_job_data(self, repository):
        """Test that find_by_user_id() returns jobs with their most recent data."""
        # Arrange - Create and save a job
        user_id = 123
        job = Job.create_new(user_id=user_id, tags=["original"])
        saved_job = repository.save(job)
        original_created_at = saved_job.created_at
        
        # Update the job
        with freeze_time("2025-01-01 12:10:00"):
            saved_job.add_tag("updated")
            saved_job.metadata["modified"] = True
            repository.save(saved_job)
        
        # Act
        user_jobs = repository.find_by_user_id(user_id)
        
        # Assert
        assert len(user_jobs) == 1
        found_job = user_jobs[0]
        assert found_job.tags == ["original", "updated"]
        assert found_job.metadata["modified"] is True
        assert found_job.created_at == original_created_at  # Should remain unchanged
        assert found_job.updated_at == datetime(2025, 1, 1, 12, 10, 0)  # Should be updated
    
    @freeze_time("2025-01-01 12:00:00")
    def test_find_by_status_returns_jobs_with_specified_status(self, repository):
        """Test that find_by_status() returns all jobs with the specified status."""
        new_job = Job.create_new(user_id=123, tags=[])
        
        # Created job can be found by status
        created_job = repository.save(new_job)
        assert created_job.status == JobStatus.CREATED

        created_jobs = repository.find_by_status(JobStatus.CREATED)
        assert created_jobs == [created_job]
        
        
        # Job can be found after status update
        with freeze_time("2025-01-01 12:05:00"):
            created_job.update_status(JobStatus.SUBMITTED)
            submitted_job = repository.save(created_job)
                
        submitted_jobs = repository.find_by_status(JobStatus.SUBMITTED)
        assert submitted_jobs == [submitted_job]
    
    def test_find_by_status_returns_empty_list_for_nonexistent_status(self, repository):
        """Test that find_by_status() returns empty list when no jobs have the specified status."""
        # Arrange - Create a job with CREATED status
        job = Job.create_new(user_id=123, tags=[])
        repository.save(job)
        
        # Act - Look for jobs with COMPLETED status (none exist)
        completed_jobs = repository.find_by_status(JobStatus.COMPLETED)
        
        # Assert
        assert completed_jobs == []
    
    @freeze_time("2025-01-01 12:00:00")
    def test_find_by_status_returns_jobs_across_different_users(self, repository):
        """Test that find_by_status() returns jobs from different users with the same status."""
        # Arrange - Create jobs for different users with the same status
        user1_job = Job.create_new(user_id=123, tags=["user1"])
        user2_job = Job.create_new(user_id=456, tags=["user2"])
        user3_job = Job.create_new(user_id=789, tags=["user3"])
        
        # Save all jobs (they'll all have CREATED status)
        saved_job1 = repository.save(user1_job)
        saved_job2 = repository.save(user2_job)
        saved_job3 = repository.save(user3_job)
        
        # Act
        created_jobs = repository.find_by_status(JobStatus.CREATED)
        
        # Assert
        assert created_jobs == [saved_job1, saved_job2, saved_job3]
