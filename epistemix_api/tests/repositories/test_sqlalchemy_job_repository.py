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
from epistemix_api.repositories.database import get_database_manager, JobRecord

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
    
    @pytest.fixture
    def sample_job(self) -> Job:
        """Create a sample unpersisted job for testing."""
        with freeze_time("2025-01-01 12:00:00"):
            return Job.create_new(user_id=456, tags=["info_job"])
    
    def test_repository_implements_interface(self, repository):
        assert isinstance(repository, IJobRepository)
    
    @freeze_time("2025-01-01 12:00:00")
    def test_save_creates_new_job(self, repository, sample_job):
        
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
        # Arrange - Create jobs for different users
        user_123_job1 = Job.create_new(user_id=123, tags=["job1"])
        user_123_job2 = Job.create_new(user_id=123, tags=["job2"])
        user_456_job = Job.create_new(user_id=456, tags=["other_user"])
        
        # Save all jobs
        saved_job1 = repository.save(user_123_job1)
        saved_job2 = repository.save(user_123_job2)
        repository.save(user_456_job)
        
        # Act
        user_123_jobs = repository.find_by_user_id(123)
        
        # Assert
        assert user_123_jobs == [saved_job1, saved_job2]
        
        for job in user_123_jobs:
            assert job.user_id == 123
    
    def test_find_by_user_id_returns_empty_list_if_no_jobs_for_user(self, repository):
        # Sanity Check - no jobs exist initially
        with repository._get_session() as session:
            assert session.query(JobRecord).count() == 0

        # Act
        user_jobs = repository.find_by_user_id(123)
        
        # Assert
        assert user_jobs == []
    
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
    
    def test_find_by_status_returns_empty_list_if_no_job_has_provided_status(self, repository):
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
    
    def test_exists_returns_true_for_existing_job(self, repository, sample_job):
        saved_job = repository.save(sample_job)
        job_exists = repository.exists(saved_job.id)
        assert job_exists is True
    
    def test_exists_returns_false_for_nonexistent_job(self, repository):
        job_exists = repository.exists(999)
        assert job_exists is False
    
    @freeze_time("2025-01-01 12:00:00")
    def test_delete_returns_true_for_existing_job(self, repository, sample_job):
        """Test that delete() returns True when deleting an existing job."""
        # Arrange - Create and save a job
        saved_job = repository.save(sample_job)
        job_id = saved_job.id
        
        # Verify job exists before deletion
        assert repository.exists(job_id) is True
        
        # Act
        deletion_result = repository.delete(job_id)
        
        # Assert
        assert deletion_result is True
        assert repository.exists(job_id) is False
        assert repository.find_by_id(job_id) is None
    
    def test_delete_returns_false_for_nonexistent_job(self, repository):
        """Test that delete() returns False when trying to delete a non-existent job."""
        # Act
        deletion_result = repository.delete(999)
        
        # Assert
        assert deletion_result is False
    
    @freeze_time("2025-01-01 12:00:00")
    def test_delete_removes_job_from_user_jobs(self, repository):
        """Test that delete() removes the job from user's job list."""
        # Arrange - Create multiple jobs for a user
        user_id = 123
        job1 = Job.create_new(user_id=user_id, tags=[])
        job2 = Job.create_new(user_id=user_id, tags=[])
        job3 = Job.create_new(user_id=user_id, tags=[])
        
        saved_job1 = repository.save(job1)
        saved_job2 = repository.save(job2)
        saved_job3 = repository.save(job3)
        
        # Verify all jobs exist
        user_jobs = repository.find_by_user_id(user_id)
        assert user_jobs == [saved_job1, saved_job2, saved_job3]
        
        # Act - Delete one job
        deletion_result = repository.delete(saved_job2.id)
        
        # Assert
        user_jobs_after_deletion = repository.find_by_user_id(user_id)
        assert user_jobs_after_deletion == [saved_job1, saved_job3]
    
    @freeze_time("2025-01-01 12:00:00")
    def test_delete_can_be_called_multiple_times_safely(self, repository, sample_job):
        # Arrange - Create and save a job
        saved_job = repository.save(sample_job)
        job_id = saved_job.id
        
        # Act - Delete the job twice
        first_deletion = repository.delete(job_id)
        second_deletion = repository.delete(job_id)
        
        # Assert
        assert first_deletion is True
        assert second_deletion is False
        assert repository.exists(job_id) is False
