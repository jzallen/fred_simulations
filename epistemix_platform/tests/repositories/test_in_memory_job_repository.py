"""
Tests for in-memory job repository implementation.
"""

import pytest

from epistemix_platform.models.job import Job, JobStatus
from epistemix_platform.repositories import InMemoryJobRepository
from epistemix_platform.repositories.interfaces import IJobRepository


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
        assert isinstance(repository, IJobRepository)

    def test_find_by_id__given_a_job_id_and_job_exists__returns_job(self, repository, sample_job):
        saved_job = repository.save(sample_job)

        found_job = repository.find_by_id(100)
        expected_job = Job.create_persisted(
            job_id=100,
            user_id=456,
            tags=["info_job"],
            status=JobStatus.CREATED,
            created_at=saved_job.created_at,
            updated_at=saved_job.updated_at,
        )
        assert found_job == expected_job

    def test_find_by_id__given_job_id_and_no_job_exists__returns_none(self, repository):
        found_job = repository.find_by_id(999)
        assert found_job is None

    def test_get_next_id(self, repository):
        first_id = repository.get_next_id()
        second_id = repository.get_next_id()
        third_id = repository.get_next_id()

        assert first_id == 100
        assert second_id == 101
        assert third_id == 102

    def test_exists__given_job_id_and_job_exists__returns_true(self, repository, sample_job):
        repository.save(sample_job)

        assert repository.exists(100)
        assert not repository.exists(999)

    def test_exists__given_job_id_and_no_job_exists__returns_false(self, repository):
        assert not repository.exists(999)

    def test_delete__given_job_id_and_job_exists__deletes_and_returns_true(self, repository, sample_job):
        repository.save(sample_job)

        deleted = repository.delete(100)
        assert deleted is True

    def test_delete__given_job_id_and_no_job_exists__returns_false(self, repository):
        deleted_again = repository.delete(100)
        assert deleted_again is False

    def test_find_by_user_id__given_user_id_and_jobs_exist__returns_jobs_only_for_specified_user(self, repository):
        job1 = Job.create_new(user_id=456, tags=["job1"])
        job2 = Job.create_new(user_id=456, tags=["job2"])
        job3 = Job.create_new(user_id=789, tags=["job3"])

        repository.save(job1)
        repository.save(job2)
        repository.save(job3)

        # Find jobs for user 456
        user_456_jobs = repository.find_by_user_id(456)
        assert len(user_456_jobs) == 2
        assert all(job.user_id == 456 for job in user_456_jobs)

    def test_find_by_user_id__given_user_id_and_no_jobs_exist_for_user__returns_empty_list(self, repository):
        job1 = Job.create_new(user_id=456, tags=["job1"])
        repository.save(job1)

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
