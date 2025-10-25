"""
Tests for submit_job use case.
"""

import base64
import json
from datetime import datetime
from unittest.mock import Mock

import pytest
from freezegun import freeze_time

from epistemix_platform.mappers.run_mapper import RunMapper
from epistemix_platform.models.job import Job, JobStatus
from epistemix_platform.models.run import PodPhase, Run, RunStatus
from epistemix_platform.models.upload_location import UploadLocation
from epistemix_platform.repositories import (
    IJobRepository,
    IRunRepository,
    IUploadLocationRepository,
    SQLAlchemyRunRepository,
)
from epistemix_platform.use_cases.submit_runs import submit_runs


@pytest.fixture
def run_request():
    return {
        "jobId": 1,
        "workingDir": "/tmp",
        "size": "small",
        "fredVersion": "1.0.0",
        "population": {"version": "1.0", "locations": ["location1", "location2"]},
        "fredArgs": [{"flag": "--arg1", "value": "value1"}],
        "fredFiles": ["file1.fred"],
    }


@pytest.fixture
def bearer_token():
    token_data = {"user_id": 123, "scopes_hash": "abc123"}
    token_json = json.dumps(token_data)
    token_b64 = base64.b64encode(token_json.encode()).decode()
    return f"Bearer {token_b64}"


@freeze_time("2025-01-01 12:00:00")
class TestSubmitRunsUseCase:
    @pytest.fixture
    def mock_job_repository(self):
        repo = Mock(spec=IJobRepository)
        repo.find_by_id.return_value = Job(
            id=1,
            user_id=123,
            tags=[],
            status=JobStatus.CREATED,
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            updated_at=datetime(2025, 1, 1, 12, 0, 0),
        )
        return repo

    @pytest.fixture
    def mock_repository(self):
        repo = Mock(spec=IRunRepository)
        return repo

    @pytest.fixture
    def mock_upload_location_repository(self):
        repo = Mock(spec=IUploadLocationRepository)
        repo.get_upload_location.return_value = UploadLocation(
            url="https://example.com/presigned-url"
        )
        return repo

    def test_submit_runs__returns_run_responses(
        self, mock_job_repository, mock_repository, mock_upload_location_repository, run_request, bearer_token
    ):
        mock_repository.save.return_value = Run.create_persisted(
            run_id=1,
            user_id=123,
            job_id=1,
            status=RunStatus.SUBMITTED,
            pod_phase=PodPhase.PENDING,
            request=run_request,
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            updated_at=datetime(2025, 1, 1, 12, 0, 0),
            config_url="https://example.com/presigned-url",
        )

        expected_runs = [
            Run.create_persisted(
                run_id=1,
                user_id=123,
                job_id=1,
                status=RunStatus.SUBMITTED,
                pod_phase=PodPhase.PENDING,
                request=run_request,
                created_at=datetime(2025, 1, 1, 12, 0, 0),
                updated_at=datetime(2025, 1, 1, 12, 0, 0),
                config_url="https://example.com/presigned-url",
            )
        ]
        result = submit_runs(
            mock_job_repository, mock_repository, mock_upload_location_repository, [run_request], bearer_token
        )

        assert result == expected_runs

    def test_submit_runs__raises_value_error_when_invalid_token(
        self, mock_job_repository, mock_repository, mock_upload_location_repository, run_request
    ):
        invalid_token = "Bearer invalid_token"
        with pytest.raises(ValueError, match="Failed to decode base64 token"):
            submit_runs(
                mock_job_repository, mock_repository, mock_upload_location_repository, [run_request], invalid_token
            )


class TestSubmitRunsSQLAlchemyRunRepositoryIntegration:
    """
    Integration tests for submit_runs use case with SQLAlchemy run repository.
    This class assumes the repository is properly set up in the test environment.
    """

    @pytest.fixture
    def job_repository(self, db_session):
        """Create a job repository using the shared db_session fixture."""
        from epistemix_platform.mappers.job_mapper import JobMapper
        from epistemix_platform.repositories import SQLAlchemyJobRepository

        job_mapper = JobMapper()
        return SQLAlchemyJobRepository(job_mapper=job_mapper, get_db_session_fn=lambda: db_session)

    @pytest.fixture
    def run_repository(self, db_session):
        """Create a run repository using the shared db_session fixture."""
        run_mapper = RunMapper()
        return SQLAlchemyRunRepository(run_mapper=run_mapper, get_db_session_fn=lambda: db_session)

    @pytest.fixture
    def upload_location_repository(self):
        """Create a mock upload location repository."""
        repo = Mock(spec=IUploadLocationRepository)
        repo.get_upload_location.return_value = UploadLocation(
            url="https://example.com/presigned-url"
        )
        return repo

    @freeze_time("2025-01-01 12:00:00")
    def test_submit_runs__give_runs_and_valid_token__returns_runs(
        self, job_repository, run_repository, upload_location_repository, run_request, bearer_token, db_session
    ):
        # Create job first (required for JobS3Prefix)
        job = Job.create_new(user_id=123, tags=["test"])
        persisted_job = job_repository.save(job)
        db_session.commit()

        # Update run_request with the actual job_id
        run_request["jobId"] = persisted_job.id
        run_requests = [run_request]

        expected_runs = [
            Run.create_persisted(
                run_id=1,
                user_id=123,
                job_id=persisted_job.id,
                status=RunStatus.SUBMITTED,
                pod_phase=PodPhase.PENDING,
                request=run_request,
                created_at=datetime(2025, 1, 1, 12, 0, 0),
                updated_at=datetime(2025, 1, 1, 12, 0, 0),
                config_url="https://example.com/presigned-url",
            )
        ]
        result = submit_runs(job_repository, run_repository, upload_location_repository, run_requests, bearer_token)
        assert result == expected_runs

    @freeze_time("2025-01-01 12:00:00")
    def test_submit_runs__when_no_runs_provided__returns_empty_list(
        self, job_repository, run_repository, upload_location_repository, bearer_token
    ):
        result = submit_runs(job_repository, run_repository, upload_location_repository, [], bearer_token)
        assert result == []

    @freeze_time("2025-01-01 12:00:00")
    def test_submit_runs__when_runs_provided__saves_runs_to_repository_on_commit(
        self, job_repository, run_repository, upload_location_repository, run_request, bearer_token, db_session
    ):
        # Create job first (required for JobS3Prefix)
        job = Job.create_new(user_id=123, tags=["test"])
        persisted_job = job_repository.save(job)
        db_session.commit()

        # Update run_request with the actual job_id
        run_request["jobId"] = persisted_job.id
        run_requests = [run_request]
        submit_runs(job_repository, run_repository, upload_location_repository, run_requests, bearer_token)
        db_session.commit()

        expected_run = Run.create_persisted(
            run_id=1,
            user_id=123,
            job_id=persisted_job.id,
            status=RunStatus.SUBMITTED,
            pod_phase=PodPhase.PENDING,
            request=run_request,
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            updated_at=datetime(2025, 1, 1, 12, 0, 0),
            config_url="https://example.com/presigned-url",
        )
        saved_run = run_repository.find_by_id(1)
        assert saved_run == expected_run

    def test_submit_runs__when_invalid_token__raises_value_error(
        self, job_repository, run_repository, upload_location_repository, run_request
    ):
        invalid_token = "Bearer invalid_token"
        with pytest.raises(ValueError, match="Failed to decode base64 token"):
            submit_runs(job_repository, run_repository, upload_location_repository, [run_request], invalid_token)
