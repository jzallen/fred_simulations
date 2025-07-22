"""
Tests demonstrating dependency inversion with repository interfaces.
Shows how the JobService can work with different repository implementations.
"""

import pytest
from typing import Dict, List, Optional

from epistemix_api.models.job import Job, JobStatus
from epistemix_api.services.job_service import JobService
from epistemix_api.repositories.interfaces import IJobRepository
from epistemix_api.repositories.job_repository import InMemoryJobRepository


class MockJobRepository:
    """
    Mock repository implementation for testing.
    Demonstrates how the service can work with different repository implementations.
    """
    
    def __init__(self):
        self._jobs: Dict[int, Job] = {}
        self._next_id = 1000  # Different starting ID to show it's a different impl
        self.save_calls = 0
        self.find_calls = 0
    
    def save(self, job: Job) -> Job:
        """Save with call tracking and ID assignment for unpersisted jobs."""
        self.save_calls += 1
        
        # Assign ID to unpersisted jobs like the real repository
        if not job.is_persisted():
            job.id = self.get_next_id()
        
        self._jobs[job.id] = job
        return job
    
    def find_by_id(self, job_id: int) -> Optional[Job]:
        """Find with call tracking."""
        self.find_calls += 1
        return self._jobs.get(job_id)
    
    def find_by_user_id(self, user_id: int) -> List[Job]:
        """Find by user ID."""
        return [job for job in self._jobs.values() if job.user_id == user_id]
    
    def find_by_status(self, status: JobStatus) -> List[Job]:
        """Find by status."""
        return [job for job in self._jobs.values() if job.status == status]
    
    def get_next_id(self) -> int:
        """Get next ID with different numbering."""
        current_id = self._next_id
        self._next_id += 1
        return current_id
    
    def exists(self, job_id: int) -> bool:
        """Check existence."""
        return job_id in self._jobs
    
    def delete(self, job_id: int) -> bool:
        """Delete job."""
        if job_id in self._jobs:
            del self._jobs[job_id]
            return True
        return False
    
    def find_all(self) -> List[Job]:
        """Find all jobs."""
        return list(self._jobs.values())


class TestDependencyInversion:
    """Test dependency inversion with different repository implementations."""
    
    def test_service_works_with_in_memory_repository(self):
        """Test that service works with InMemoryJobRepository."""
        repository = InMemoryJobRepository(starting_id=500)
        service = JobService(repository)
        
        # Register a job
        job = service.register_job(user_id=456, tags=["test_job"])
        
        # Verify it uses the repository's ID generation
        assert job.id == 500
        assert job.user_id == 456
        assert job.tags == ["test_job"]
        
        # Verify we can retrieve it
        retrieved_job = service.get_job(job.id)
        assert retrieved_job == job
    
    def test_service_works_with_mock_repository(self):
        """Test that service works with MockJobRepository."""
        repository = MockJobRepository()
        service = JobService(repository)
        
        # Register a job
        job = service.register_job(user_id=456, tags=["mock_test"])
        
        # Verify it uses the mock repository's ID generation
        assert job.id == 1000  # MockJobRepository starts at 1000
        assert job.user_id == 456
        assert job.tags == ["mock_test"]
        
        # Verify repository method calls were tracked
        assert repository.save_calls == 1
        
        # Retrieve the job
        retrieved_job = service.get_job(job.id)
        assert retrieved_job == job
        assert repository.find_calls == 1
    
    def test_service_interface_compliance(self):
        """Test that service only uses repository interface methods."""
        repository = MockJobRepository()
        service = JobService(repository)
        
        # Register and submit a job
        job = service.register_job(user_id=456, tags=["interface_test"])
        response = service.submit_job(job.id)
        
        # Verify business logic works regardless of repository implementation
        assert response["url"] == "http://localhost:5001/pre-signed-url"
        
        # Verify job status was updated
        updated_job = service.get_job(job.id)
        assert updated_job.status == JobStatus.SUBMITTED
    
    def test_repository_swapping(self):
        """Test that repositories can be swapped without affecting business logic."""
        # Create services with different repositories
        in_memory_repo = InMemoryJobRepository(starting_id=100)
        mock_repo = MockJobRepository()
        
        service1 = JobService(in_memory_repo)
        service2 = JobService(mock_repo)
        
        # Register jobs with both services
        job1 = service1.register_job(user_id=456, tags=["repo1"])
        job2 = service2.register_job(user_id=456, tags=["repo2"])
        
        # They should have different IDs based on their repository
        assert job1.id == 100  # InMemoryJobRepository starting ID
        assert job2.id == 1000  # MockJobRepository starting ID
        
        # But same business logic
        assert job1.user_id == job2.user_id == 456
        assert job1.status == job2.status == JobStatus.CREATED
        
        # Submit both jobs
        response1 = service1.submit_job(job1.id)
        response2 = service2.submit_job(job2.id)
        
        # Both should return the same business response
        assert response1 == response2
        
        # Both jobs should be submitted
        updated_job1 = service1.get_job(job1.id)
        updated_job2 = service2.get_job(job2.id)
        
        assert updated_job1.status == JobStatus.SUBMITTED
        assert updated_job2.status == JobStatus.SUBMITTED
    
    def test_statistics_work_with_different_repositories(self):
        """Test that statistics work regardless of repository implementation."""
        # Test each repository type independently
        
        # Test 1: InMemoryJobRepository
        repo1 = InMemoryJobRepository(starting_id=200)
        service1 = JobService(repo1)
        
        # Register some jobs
        service1.register_job(user_id=456, tags=["stats_test"])
        service1.register_job(user_id=789, tags=["stats_test"])
        
        # Get statistics
        stats1 = service1.get_job_statistics()
        
        # Should work correctly
        assert stats1["total_jobs"] == 2
        assert stats1["status_breakdown"]["created"] == 2
        assert stats1["tag_breakdown"]["stats_test"] == 2
        
        # Test 2: MockJobRepository
        repo2 = MockJobRepository()
        service2 = JobService(repo2)
        
        # Register some jobs
        service2.register_job(user_id=456, tags=["stats_test"])
        service2.register_job(user_id=789, tags=["stats_test"])
        
        # Get statistics
        stats2 = service2.get_job_statistics()
        
        # Should work the same regardless of repository
        assert stats2["total_jobs"] == 2
        assert stats2["status_breakdown"]["created"] == 2
        assert stats2["tag_breakdown"]["stats_test"] == 2


class TestRepositoryAbstraction:
    """Test that the repository abstraction provides proper isolation."""
    
    def test_repository_interface_methods_only(self):
        """Test that service only uses interface methods."""
        # This test ensures we're not accidentally using implementation details
        repository = MockJobRepository()
        service = JobService(repository)
        
        # Use service methods that should only call interface methods
        job = service.register_job(user_id=456, tags=["interface_only"])
        service.submit_job(job.id)
        service.get_job(job.id)
        service.get_jobs_for_user(456)
        stats = service.get_job_statistics()
        
        # Verify that the service worked without accessing private repository details
        assert job.id == 1000  # MockJobRepository behavior
        assert stats["total_jobs"] == 1
        
        # The fact that this test passes means the service is properly
        # using only the interface methods, not implementation details
    
    def test_type_checking_compliance(self):
        """Test that our implementations satisfy the Protocol."""
        # This is more of a static typing test, but we can verify at runtime
        repositories = [
            InMemoryJobRepository(),
            MockJobRepository()
        ]
        
        for repo in repositories:
            # Verify all interface methods exist
            assert hasattr(repo, 'save')
            assert hasattr(repo, 'find_by_id')
            assert hasattr(repo, 'find_by_user_id')
            assert hasattr(repo, 'find_by_status')
            assert hasattr(repo, 'get_next_id')
            assert hasattr(repo, 'exists')
            assert hasattr(repo, 'delete')
            assert hasattr(repo, 'find_all')
            
            # Verify they're callable
            assert callable(repo.save)
            assert callable(repo.find_by_id)
            assert callable(repo.find_by_user_id)
            assert callable(repo.find_by_status)
            assert callable(repo.get_next_id)
            assert callable(repo.exists)
            assert callable(repo.delete)
            assert callable(repo.find_all)
