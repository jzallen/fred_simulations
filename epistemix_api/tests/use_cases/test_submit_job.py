"""
Tests for submit_job use case.
"""
import os
from unittest.mock import Mock

import pytest
from freezegun import freeze_time
from datetime import datetime

from epistemix_api.models.job import Job, JobStatus, JobInputLocation
from epistemix_api.repositories import IJobRepository, SQLAlchemyJobRepository, get_database_manager
from epistemix_api.use_cases.submit_job import submit_job


@freeze_time("2025-01-01 12:00:00")
class TestSubmitJobUseCase:

    @pytest.fixture
    def mock_repository(self):
        repo = Mock(spec=IJobRepository)
        return repo

    @pytest.fixture
    def created_job(self):
        """Create a job in CREATED status for testing."""
        return Job(
            id=1,
            user_id=123,
            status=JobStatus.CREATED,
            tags=["info_job"],
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            updated_at=datetime(2025, 1, 1, 12, 0, 0)
        )

    @pytest.fixture
    def submitted_job(self):
        return Job(
            id=2,
            user_id=123,
            status=JobStatus.SUBMITTED,
            tags=["simulation_job"],
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            updated_at=datetime(2025, 1, 1, 12, 0, 0)
        )

    def test_submit_job_success__returns_job_input_location_for_submitted_job(self, mock_repository, created_job):
        mock_repository.find_by_id.return_value = created_job
        mock_repository.save.return_value = None
        
        result = submit_job(mock_repository, job_id=1)
        
        assert isinstance(result, JobInputLocation)
        assert result.url == "http://localhost:5001/pre-signed-url"

    def test_submit_job__when_job_not_found__raises_value_error(self, mock_repository):
        mock_repository.find_by_id.return_value = None
        
        with pytest.raises(ValueError, match="Job 999 not found"):
            submit_job(mock_repository, job_id=999)
        
        
    def test_submit_job__when_created_job_has_non_created_status__value_error_raised(self, mock_repository, submitted_job):
        mock_repository.find_by_id.return_value = submitted_job
        
        with pytest.raises(ValueError, match="Job 2 must be in CREATED status to be submitted, current status: submitted"):
            submit_job(mock_repository, job_id=2)


class TestSubmitJobSLAlchemyJobRepositoryIntegration:
    """
    Integration tests for submit_job use case with SQLAlchemy job repository.
    This class assumes the repository is properly set up in the test environment.
    """

    @pytest.fixture
    def job_repository(self):
        db_name = "test_submit_job_integration.db"
        test_db_url = f"sqlite:///{db_name}"
        test_db_manager = get_database_manager(test_db_url)
        test_db_manager.create_tables()

        yield SQLAlchemyJobRepository(get_db_session_fn=test_db_manager.get_session)

        try:
            os.remove(db_name)
        except FileNotFoundError:
            pass

    def test_submit_job__returns_job_input_location(self, job_repository):
        job = Job.create_new(user_id=123, tags=["test"])
        job_repository.save(job)
        result = submit_job(job_repository, job_id=job.id)
        
        # Assert
        assert isinstance(result, JobInputLocation)
        assert result.url == "http://localhost:5001/pre-signed-url"

    def test_submit_job__when_job_not_found__raises_value_error(self, job_repository):
        with pytest.raises(ValueError, match="Job 999 not found"):
            submit_job(job_repository, job_id=999)

    def test_submit_job__when_job_not_in_created_status__raises_value_error(self, job_repository):
        job = Job.create_new(user_id=123, tags=["test"])
        job.status = JobStatus.SUBMITTED
        job_repository.save(job)

        with pytest.raises(ValueError, match="Job 1 must be in CREATED status to be submitted, current status: submitted"):
            submit_job(job_repository, job_id=1)

    @freeze_time("2025-01-01 12:00:00")
    def test_submit_job__updates_job_status_to_submitted(self, job_repository):
        new_job = Job.create_new(user_id=123, tags=["test"])
        persisted = job_repository.save(new_job)
        assert persisted.updated_at == datetime(2025, 1, 1, 12, 0, 0)

        with freeze_time("2025-01-01 12:30:00"):
            submit_job(job_repository, job_id=persisted.id)

        updated_job = job_repository.find_by_id(persisted.id)
        assert updated_job.status == JobStatus.SUBMITTED
        assert updated_job.updated_at == datetime(2025, 1, 1, 12, 30, 0)