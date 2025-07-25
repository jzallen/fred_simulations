"""
Tests for in-memory job repository implementation.
"""

import pytest

from epistemix_api.models.job import Job, JobStatus
from epistemix_api.repositories import InMemoryJobRepository
from epistemix_api.repositories.interfaces import IJobRepository


class TestInMemoryJobRepository:
    """Test cases for the InMemoryJobRepository implementation."""
    
    @pytest.fixture
    def repository(self) -> InMemoryJobRepository:
        """Create a fresh repository for each test."""
        return InMemoryJobRepository(starting_id=100)
    
    @pytest.fixture
    def sample_job(self) -> Job:
        """Create a sample unpersisted job for testing."""
        return Job.create_new(user_id=456, tags=["info_job"])
    
    def test_repository_implements_interface(self, repository):
        """Test that InMemoryJobRepository implements IJobRepository."""
        assert isinstance(repository, IJobRepository)
    
    def test_save_and_find_by_id(self, repository, sample_job):
        """Test saving and retrieving a job by ID."""
        # Verify job starts unpersisted
        assert not sample_job.is_persisted()
        
        # Save the job - repository should assign ID
        saved_job = repository.save(sample_job)
        assert saved_job == sample_job  # Same object
        assert saved_job.is_persisted()
        assert saved_job.id == 100  # Repository starts at 100
        
        # Find by ID
        found_job = repository.find_by_id(100)
        expected_job = Job.create_persisted(
            job_id=100,
            user_id=456,
            tags=["info_job"],
            status=JobStatus.CREATED,
            created_at=saved_job.created_at,
            updated_at=saved_job.updated_at
        )
        assert found_job == expected_job
    
    def test_find_by_id_not_found(self, repository):
        """Test finding a job that doesn't exist."""
        found_job = repository.find_by_id(999)
        assert found_job is None
    
    def test_get_next_id(self, repository):
        """Test getting sequential IDs."""
        first_id = repository.get_next_id()
        second_id = repository.get_next_id()
        third_id = repository.get_next_id()
        
        assert first_id == 100
        assert second_id == 101
        assert third_id == 102
    
    def test_exists(self, repository, sample_job):
        """Test checking if a job exists."""
        # Job doesn't exist initially
        assert not repository.exists(100)
        
        # Save the job - repository assigns ID 100
        repository.save(sample_job)
        
        # Now it exists
        assert repository.exists(100)
        assert not repository.exists(999)
    
    def test_delete(self, repository, sample_job):
        """Test deleting a job."""
        # Save the job - repository assigns ID 100
        repository.save(sample_job)
        assert repository.exists(100)
        
        # Delete the job
        deleted = repository.delete(100)
        assert deleted is True
        assert not repository.exists(100)
        
        # Try to delete non-existent job
        deleted_again = repository.delete(100)
        assert deleted_again is False
    
    def test_find_by_user_id(self, repository):
        """Test finding jobs by user ID."""
        # Create unpersisted jobs for different users
        job1 = Job.create_new(user_id=456, tags=["job1"])
        job2 = Job.create_new(user_id=456, tags=["job2"])
        job3 = Job.create_new(user_id=789, tags=["job3"])
        
        # Save jobs - repository will assign IDs 100, 101, 102
        repository.save(job1)
        repository.save(job2)
        repository.save(job3)
        
        # Find jobs for user 456
        user_456_jobs = repository.find_by_user_id(456)
        assert len(user_456_jobs) == 2
        assert all(job.user_id == 456 for job in user_456_jobs)
        
        # Find jobs for user 789
        user_789_jobs = repository.find_by_user_id(789)
        assert len(user_789_jobs) == 1
        assert user_789_jobs[0].user_id == 789
        
        # Find jobs for non-existent user
        no_jobs = repository.find_by_user_id(999)
        assert len(no_jobs) == 0
    
    def test_find_by_status(self, repository):
        """Test finding jobs by status."""
        # Create unpersisted jobs with different statuses
        job1 = Job.create_new(user_id=456, tags=["job1"])
        job2 = Job.create_new(user_id=456, tags=["job2"])
        job3 = Job.create_new(user_id=456, tags=["job3"])
        
        # Update one job to SUBMITTED before saving
        job1.update_status(JobStatus.SUBMITTED)
        
        # Save jobs - repository will assign IDs 100, 101, 102
        saved_job1 = repository.save(job1)
        saved_job2 = repository.save(job2)
        saved_job3 = repository.save(job3)
        
        # Find created jobs
        created_jobs = repository.find_by_status(JobStatus.CREATED)
        assert len(created_jobs) == 2
        created_job_ids = {job.id for job in created_jobs}
        assert created_job_ids == {saved_job2.id, saved_job3.id}
        
        # Find submitted jobs
        submitted_jobs = repository.find_by_status(JobStatus.SUBMITTED)
        assert len(submitted_jobs) == 1
        assert submitted_jobs[0].id == saved_job1.id
    
    def test_reset_id_counter(self, repository):
        """Test resetting the ID counter."""
        # Get initial ID
        first_id = repository.get_next_id()
        assert first_id == 100
        
        # Reset counter
        repository.reset_id_counter(500)
        
        # Next ID should be from new counter
        next_id = repository.get_next_id()
        assert next_id == 500