"""
Tests for the job repository implementations.
"""

import pytest
from datetime import datetime

from epistemix_api.models.job import Job, JobStatus, JobTag
from epistemix_api.repositories.job_repository import InMemoryJobRepository
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
        assert found_job is not None
        assert found_job.id == 100
        assert found_job.user_id == 456
        assert found_job.tags == ["info_job"]
    
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
        job1 = Job.create_new(user_id=456, tags=["job1"])  # CREATED
        job2 = Job.create_new(user_id=456, tags=["job2"])  # CREATED
        job3 = Job.create_new(user_id=456, tags=["job3"])  # CREATED
        
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
    
    def test_find_all(self, repository):
        """Test finding all jobs."""
        # Initially empty
        all_jobs = repository.find_all()
        assert len(all_jobs) == 0
        
        # Add some unpersisted jobs
        job1 = Job.create_new(user_id=456, tags=["job1"])
        job2 = Job.create_new(user_id=789, tags=["job2"])
        
        # Save jobs - repository will assign IDs 100, 101
        saved_job1 = repository.save(job1)
        saved_job2 = repository.save(job2)
        
        # Find all
        all_jobs = repository.find_all()
        assert len(all_jobs) == 2
        job_ids = {job.id for job in all_jobs}
        assert job_ids == {saved_job1.id, saved_job2.id}
    
    def test_clear(self, repository, sample_job):
        """Test clearing all jobs."""
        # Add a job
        repository.save(sample_job)
        assert repository.count() == 1
        
        # Clear all jobs
        repository.clear()
        assert repository.count() == 0
        assert len(repository.find_all()) == 0
    
    def test_count(self, repository):
        """Test counting jobs."""
        assert repository.count() == 0
        
        # Add unpersisted jobs
        job1 = Job.create_new(user_id=456, tags=["job1"])
        job2 = Job.create_new(user_id=456, tags=["job2"])
        
        # Save first job
        saved_job1 = repository.save(job1)
        assert repository.count() == 1
        
        # Save second job
        saved_job2 = repository.save(job2)
        assert repository.count() == 2
        
        # Delete a job
        repository.delete(saved_job1.id)
        assert repository.count() == 1
    
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


class TestRepositoryInterfaceCompliance:
    """Test that the repository properly implements the interface."""
    
    def test_interface_methods_exist(self):
        """Test that all interface methods are implemented."""
        repository = InMemoryJobRepository()
        
        # Check that all protocol methods exist and are callable
        assert hasattr(repository, 'save')
        assert callable(repository.save)
        
        assert hasattr(repository, 'find_by_id')
        assert callable(repository.find_by_id)
        
        assert hasattr(repository, 'find_by_user_id')
        assert callable(repository.find_by_user_id)
        
        assert hasattr(repository, 'find_by_status')
        assert callable(repository.find_by_status)
        
        assert hasattr(repository, 'get_next_id')
        assert callable(repository.get_next_id)
        
        assert hasattr(repository, 'exists')
        assert callable(repository.exists)
        
        assert hasattr(repository, 'delete')
        assert callable(repository.delete)
        
        assert hasattr(repository, 'find_all')
        assert callable(repository.find_all)
