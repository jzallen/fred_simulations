"""
Tests for the refactored Flask app using Clean Architecture.
"""

import base64
import json
import os
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import boto3
import pytest
from botocore.stub import Stubber
from freezegun import freeze_time
from returns.pipeline import is_successful

from epistemix_platform.controllers.job_controller import JobController
from epistemix_platform.mappers.job_mapper import JobMapper
from epistemix_platform.mappers.run_mapper import RunMapper
from epistemix_platform.models.job import Job, JobStatus
from epistemix_platform.models.job_upload import JobUpload
from epistemix_platform.models.requests import RunRequest
from epistemix_platform.models.run import PodPhase, Run, RunStatus
from epistemix_platform.models.upload_content import UploadContent
from epistemix_platform.models.upload_location import UploadLocation
from epistemix_platform.repositories import (
    S3UploadLocationRepository,
    SQLAlchemyJobRepository,
    SQLAlchemyRunRepository,
)


@pytest.fixture
def service():
    with freeze_time("2025-01-01 12:00:00"):
        job = Job.create_persisted(job_id=1, user_id=456, tags=["info_job"])

    run = Run.create_persisted(
        run_id=1,
        job_id=1,
        user_id=456,
        status=RunStatus.SUBMITTED,
        pod_phase=PodPhase.PENDING,
        request={},
        created_at=datetime(2025, 1, 1, 12, 0, 0),
        updated_at=datetime(2025, 1, 1, 12, 0, 0),
    )

    # Create mock locations for archive testing
    mock_location1 = UploadLocation("http://s3.amazonaws.com/bucket/job1/file1.txt")
    mock_location2 = UploadLocation("http://s3.amazonaws.com/bucket/job1/file2.txt")

    mock_upload1 = JobUpload(
        context="job", upload_type="input", job_id=1, location=mock_location1, run_id=None
    )
    mock_upload2 = JobUpload(
        context="job", upload_type="config", job_id=1, location=mock_location2, run_id=None
    )

    service = JobController()
    service._register_job = Mock(return_value=job)
    service._submit_job = Mock(return_value=UploadLocation(url="http://example.com/pre-signed-url"))
    service._submit_job_config = Mock(
        return_value=UploadLocation(url="http://example.com/pre-signed-url-job-config")
    )
    service._submit_runs = Mock(return_value=[run])
    service._submit_run_config = Mock(
        return_value=UploadLocation(url="http://example.com/pre-signed-url-run-config")
    )
    service._get_runs_by_job_id = Mock(return_value=[run])
    service._get_job_uploads = Mock(return_value=[mock_upload1, mock_upload2])
    service._read_upload_content = Mock(return_value=UploadContent.create_text("test content"))
    service._write_to_local = Mock(return_value=None)
    service._archive_uploads = Mock(return_value=[mock_location1, mock_location2])
    service._run_simulation = Mock(return_value=run)
    return service


@pytest.fixture
def run_requests():
    return [
        RunRequest(
            jobId=1,
            workingDir="/tmp",
            size="hot",
            fredVersion="latest",
            population={"version": "US_2010.v5", "locations": ["New York", "Los Angeles"]},
            fredArgs=[{"flag": "-p", "value": "param"}],
            fredFiles=["/path/to/fred/file"],
        ).model_dump()
    ]


class TestJobController:
    def test_register_job__calls_register_job_fn_with_created_job(self, service):
        service.register_job(user_token_value="token", tags=["info_job"])
        service._register_job.assert_called_once_with(user_token_value="token", tags=["info_job"])

    def test_register_job__returns_success_result_with_job_data(self, service):
        job_result = service.register_job(user_token_value="token", tags=["info_job"])
        assert is_successful(job_result)
        expected_job_data = {
            "id": 1,
            "userId": 456,
            "tags": ["info_job"],
            "status": JobStatus.CREATED.value,
            "createdAt": "2025-01-01T12:00:00",
            "updatedAt": "2025-01-01T12:00:00",
            "metadata": {},
        }
        assert job_result.unwrap() == expected_job_data

    def test_register_job__when_value_error_raised__returns_failure_result(
        self, service, bearer_token
    ):
        service._register_job.side_effect = ValueError("Invalid user ID")
        job_result = service.register_job(user_token_value=bearer_token, tags=["info_job"])
        assert not is_successful(job_result)
        assert job_result.failure() == "Invalid user ID"

    def test_register_job__when_exception_raised__returns_failure_result(
        self, service, bearer_token
    ):
        service._register_job.side_effect = Exception("Unexpected error")
        job_result = service.register_job(user_token_value=bearer_token, tags=["info_job"])
        assert not is_successful(job_result)
        assert job_result.failure() == "An unexpected error occurred while registering the job"

    def test_submit_job__calls_submit_job_fn_with_correct_parameters(self, service):
        service.submit_job(job_id=1, context="job", job_type="input")
        expected_job_upload = JobUpload(context="job", upload_type="input", job_id=1, run_id=None)
        service._submit_job.assert_called_once_with(expected_job_upload)

    def test_submit_job__returns_success_result_with_response_data(self, service):
        expected_response = {"url": "http://example.com/pre-signed-url"}
        job_result = service.submit_job(job_id=1, context="job", job_type="input")
        assert is_successful(job_result)
        assert job_result.unwrap() == expected_response

    def test_submit_job__when_value_error_raised__returns_failure_result(self, service):
        # The ValueError will be raised during JobUpload creation due to validation
        job_result = service.submit_job(job_id=0, context="job", job_type="input")
        assert not is_successful(job_result)
        assert "Job ID must be positive" in job_result.failure()

    def test_submit_job__when_exception_raised__returns_failure_result(self, service):
        service._submit_job.side_effect = Exception("Unexpected error")
        job_result = service.submit_job(job_id=1, context="job", job_type="input")
        assert not is_successful(job_result)
        assert job_result.failure() == "An unexpected error occurred while submitting the job"

    def test_submit_runs__calls_submit_runs_fn_with_correct_parameters(self, service, run_requests):
        bearer_token = "Bearer valid_token"
        service.submit_runs(user_token_value=bearer_token, run_requests=run_requests)
        service._submit_runs.assert_called_once_with(
            run_requests=run_requests, user_token_value=bearer_token, epx_version="epx_client_1.2.2"
        )

    def test_submit_runs__returns_success_result_with_run_responses(self, service, run_requests):
        expected_response = [
            Run.create_persisted(
                run_id=1,
                job_id=1,
                user_id=456,
                status=RunStatus.SUBMITTED,
                pod_phase=PodPhase.PENDING,
                request={},
                created_at=datetime(2025, 1, 1, 12, 0, 0),
                updated_at=datetime(2025, 1, 1, 12, 0, 0),
            ).to_run_response_dict()
        ]
        bearer_token = "Bearer valid_token"
        restult = service.submit_runs(
            user_token_value=bearer_token, run_requests=run_requests, epx_version="epx_client_1.2.2"
        )
        assert is_successful(restult)
        assert restult.unwrap() == expected_response

    def test_submit_runs__when_value_error_raised__returns_failure_result(
        self, service, run_requests
    ):
        service._submit_runs.side_effect = ValueError("Invalid run request")
        bearer_token = "Bearer valid_token"
        result = service.submit_runs(
            user_token_value=bearer_token, run_requests=run_requests, epx_version="epx_client_1.2.2"
        )
        assert not is_successful(result)
        assert result.failure() == "Invalid run request"

    def test_submit_runs__when_exception_raised__returns_failure_result(
        self, service, run_requests
    ):
        service._submit_runs.side_effect = Exception("Unexpected error")
        bearer_token = "Bearer valid_token"
        result = service.submit_runs(
            user_token_value=bearer_token, run_requests=run_requests, epx_version="epx_client_1.2.2"
        )
        assert not is_successful(result)
        assert result.failure() == "An unexpected error occurred while submitting the runs"

    def test_submit_job___type_config__calls_submit_job_config_fn_with_correct_parameters(
        self, service
    ):
        service.submit_job(job_id=1, context="job", job_type="config")
        expected_job_upload = JobUpload(context="job", upload_type="config", job_id=1, run_id=None)
        service._submit_job_config.assert_called_once_with(expected_job_upload)

    def test_submit_job__type_config__returns_success_result_with_response_data(self, service):
        expected_response = {"url": "http://example.com/pre-signed-url-job-config"}
        job_result = service.submit_job(job_id=1, context="job", job_type="config")
        assert is_successful(job_result)
        assert job_result.unwrap() == expected_response

    def test_submit_job__context_run_type_config__calls_submit_run_config_fn_with_correct_parameters(  # noqa: E501
        self, service
    ):
        service.submit_job(job_id=1, run_id=2, context="run", job_type="config")
        expected_job_upload = JobUpload(context="run", upload_type="config", job_id=1, run_id=2)
        service._submit_run_config.assert_called_once_with(expected_job_upload)

    def test_submit_job__context_run_type_config__returns_success_result_with_response_data(
        self, service
    ):
        expected_response = {"url": "http://example.com/pre-signed-url-run-config"}
        job_result = service.submit_job(job_id=1, run_id=2, context="run", job_type="config")
        assert is_successful(job_result)
        assert job_result.unwrap() == expected_response

    def test_get_runs__calls_get_runs_by_job_id_fn_with_correct_job_id(self, service):
        service.get_runs(job_id=1)
        service._get_runs_by_job_id.assert_called_once_with(job_id=1)

    def test_get_runs__returns_success_result_with_run_data(self, service):
        expected_run = Run.create_persisted(
            run_id=1,
            job_id=1,
            user_id=456,
            status=RunStatus.SUBMITTED,
            pod_phase=PodPhase.PENDING,
            request={},
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            updated_at=datetime(2025, 1, 1, 12, 0, 0),
        )
        service._get_runs_by_job_id.return_value = [expected_run]

        runs_result = service.get_runs(job_id=1)
        assert is_successful(runs_result)
        assert runs_result.unwrap() == [expected_run.to_dict()]

    def test_get_job_uploads__calls_dependencies_with_correct_parameters(self, service):
        upload = JobUpload(
            context="job",
            upload_type="input",
            job_id=1,
            location=UploadLocation(url="http://example.com/job-input"),
            run_id=None,
        )
        service._get_job_uploads.return_value = [upload]

        service.get_job_uploads(job_id=1)

        service._get_job_uploads.assert_called_once_with(job_id=1)
        service._read_upload_content.assert_called_once_with(upload.location)

    def test_get_job_uploads__returns_success_result_with_content(self, service):
        upload = JobUpload(
            context="job",
            upload_type="input",
            job_id=1,
            location=UploadLocation(url="http://example.com/job-input"),
            run_id=None,
        )
        content = UploadContent.create_text("test file content")
        service._get_job_uploads.return_value = [upload]
        service._read_upload_content.return_value = content

        result = service.get_job_uploads(job_id=1)

        assert is_successful(result)
        uploads = result.unwrap()
        assert len(uploads) == 1
        assert uploads[0]["context"] == "job"
        assert uploads[0]["uploadType"] == "input"
        assert uploads[0]["jobId"] == 1
        assert uploads[0]["content"]["contentType"] == "text"
        assert uploads[0]["content"]["content"] == "test file content"

    def test_get_job_uploads__when_read_content_fails__includes_error(self, service):
        upload = JobUpload(
            context="job",
            upload_type="input",
            job_id=1,
            location=UploadLocation(url="http://example.com/job-input"),
            run_id=None,
        )
        service._get_job_uploads.return_value = [upload]
        service._read_upload_content.side_effect = ValueError("S3 error")

        result = service.get_job_uploads(job_id=1)

        assert is_successful(result)
        uploads = result.unwrap()
        assert len(uploads) == 1
        assert uploads[0]["context"] == "job"
        assert uploads[0]["uploadType"] == "input"
        assert uploads[0]["error"] == "S3 error"
        assert "content" not in uploads[0]

    def test_archive_job_uploads__calls_archive_uploads_fn_with_correct_parameters(self, service):
        # Setup mock uploads with proper UploadLocation
        mock_location = UploadLocation(url="http://example.com/file.txt")
        mock_upload = JobUpload(
            context="job", upload_type="input", job_id=1, location=mock_location, run_id=None
        )
        service._get_job_uploads.return_value = [mock_upload]

        service.archive_job_uploads(job_id=1, days_since_create=7, dry_run=True)

        service._get_job_uploads.assert_called_once_with(job_id=1)
        service._archive_uploads.assert_called_once_with(
            upload_locations=[mock_location],
            days_since_create=7,
            hours_since_create=None,
            dry_run=True,
        )

    def test_archive_job_uploads__returns_success_result_with_archived_locations(self, service):
        result = service.archive_job_uploads(job_id=1)
        expected_locations = [
            UploadLocation("http://s3.amazonaws.com/bucket/job1/file1.txt").to_sanitized_dict(),
            UploadLocation("http://s3.amazonaws.com/bucket/job1/file2.txt").to_sanitized_dict(),
        ]

        assert is_successful(result)
        archived = result.unwrap()
        assert archived == expected_locations

    def test_archive_job_uploads__when_no_uploads_found__returns_empty_list(self, service):
        service._get_job_uploads.return_value = []

        result = service.archive_job_uploads(job_id=999)

        assert is_successful(result)
        assert result.unwrap() == []
        service._archive_uploads.assert_not_called()

    def test_archive_job_uploads__when_value_error_raised__returns_failure_result(self, service):
        mock_location = UploadLocation(url="http://example.com/file.txt")
        mock_upload = JobUpload(
            context="job", upload_type="input", job_id=1, location=mock_location, run_id=None
        )
        service._get_job_uploads.return_value = [mock_upload]
        service._archive_uploads.side_effect = ValueError("Invalid age threshold")

        result = service.archive_job_uploads(job_id=1, days_since_create=-1)

        assert not is_successful(result)
        assert result.failure() == "Invalid age threshold"

    def test_archive_job_uploads__when_exception_raised__returns_failure_result(self, service):
        mock_location = UploadLocation(url="http://example.com/file.txt")
        mock_upload = JobUpload(
            context="job", upload_type="input", job_id=1, location=mock_location, run_id=None
        )
        service._get_job_uploads.return_value = [mock_upload]
        service._archive_uploads.side_effect = Exception("S3 error")

        result = service.archive_job_uploads(job_id=1)

        assert not is_successful(result)
        assert result.failure() == "An unexpected error occurred while archiving uploads"

    def test_submit_runs__calls_run_simulation_for_each_run_when_configured(
        self, service, run_requests
    ):
        """Test that submit_runs calls _run_simulation for each run when simulation_runner is configured."""
        bearer_token = "Bearer valid_token"
        run1 = Run.create_persisted(
            run_id=1,
            job_id=1,
            user_id=456,
            status=RunStatus.SUBMITTED,
            pod_phase=PodPhase.PENDING,
            request={},
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            updated_at=datetime(2025, 1, 1, 12, 0, 0),
        )
        run2 = Run.create_persisted(
            run_id=2,
            job_id=1,
            user_id=456,
            status=RunStatus.SUBMITTED,
            pod_phase=PodPhase.PENDING,
            request={},
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            updated_at=datetime(2025, 1, 1, 12, 0, 0),
        )
        service._submit_runs.return_value = [run1, run2]
        service._run_simulation = Mock(return_value=run1)

        service.submit_runs(user_token_value=bearer_token, run_requests=run_requests)

        # Verify _run_simulation was called twice (once per run)
        assert service._run_simulation.call_count == 2
        # Verify the runs were passed correctly by checking the call arguments
        calls = service._run_simulation.call_args_list
        assert calls[0][1]['run'].id == run1.id
        assert calls[1][1]['run'].id == run2.id

    def test_submit_runs__always_calls_run_simulation(
        self, service, run_requests
    ):
        """Test that submit_runs ALWAYS calls _run_simulation for each run (simulation_runner is required)."""
        bearer_token = "Bearer valid_token"
        run1 = Run.create_persisted(
            run_id=1,
            job_id=1,
            user_id=456,
            status=RunStatus.SUBMITTED,
            pod_phase=PodPhase.PENDING,
            request={},
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            updated_at=datetime(2025, 1, 1, 12, 0, 0),
        )
        service._submit_runs.return_value = [run1]
        service._run_simulation = Mock(return_value=run1)

        result = service.submit_runs(user_token_value=bearer_token, run_requests=run_requests)

        # Should succeed and call _run_simulation
        assert is_successful(result)
        assert service._run_simulation.call_count == 1


@pytest.fixture
def job_repository(db_session):
    """Create a job repository using the shared db_session fixture."""
    job_mapper = JobMapper()
    return SQLAlchemyJobRepository(job_mapper=job_mapper, get_db_session_fn=lambda: db_session)


@pytest.fixture
def run_repository(db_session):
    """Create a run repository using the shared db_session fixture."""
    run_mapper = RunMapper()
    return SQLAlchemyRunRepository(run_mapper=run_mapper, get_db_session_fn=lambda: db_session)


@pytest.fixture
def s3_stubber():
    os.environ["AWS_ACCESS_KEY_ID"] = "test-access-key"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "test-secret-key"

    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_stub = Stubber(s3_client)

    try:
        s3_stub.activate()
        yield s3_client, s3_stub
    finally:
        s3_stub.deactivate()
        os.environ.pop("AWS_ACCESS_KEY_ID", None)
        os.environ.pop("AWS_SECRET_ACCESS_KEY", None)


@pytest.fixture
def upload_location_repository(s3_stubber):
    s3_client, _ = s3_stubber
    repo = S3UploadLocationRepository(
        bucket_name="test-bucket", region_name="us-east-1", s3_client=s3_client
    )
    return repo


@pytest.fixture
def results_repository(s3_stubber):
    from epistemix_platform.repositories.s3_results_repository import S3ResultsRepository

    s3_client, _ = s3_stubber
    repo = S3ResultsRepository(s3_client=s3_client, bucket_name="test-bucket")
    return repo


@pytest.fixture
def simulation_runner_mock():
    """Create a mock simulation runner gateway."""
    from unittest.mock import Mock
    mock_runner = Mock()
    return mock_runner


@pytest.fixture
def job_controller(job_repository, run_repository, upload_location_repository, results_repository, simulation_runner_mock):
    return JobController.create_with_repositories(
        job_repository, run_repository, upload_location_repository, results_repository, simulation_runner_mock
    )


@pytest.fixture
def bearer_token():
    token_data = {"user_id": 123, "scopes_hash": "abc123"}
    token_json = json.dumps(token_data)
    token_b64 = base64.b64encode(token_json.encode()).decode()
    return f"Bearer {token_b64}"


@pytest.fixture
def querystring_pattern():
    expected_expiration = int(
        sum((datetime.fromisoformat("2025-01-01 12:00:00").timestamp(), 3600))
    )
    querystring_pattern = "&".join(
        ["AWSAccessKeyId=test-access-key", "Signature=.*", f"Expires={expected_expiration}"]
    )
    return querystring_pattern


@pytest.fixture
def base_url_location():
    return "https://test-bucket.s3.amazonaws.com/jobs/1/2025/01/01/120000"


@pytest.fixture
def job_input_url_pattern(base_url_location, querystring_pattern):
    job_input_url = base_url_location + "/job_input.zip"
    job_input_url_pattern = r"\?".join([job_input_url, querystring_pattern])
    return job_input_url_pattern


@pytest.fixture
def job_config_url_pattern(base_url_location, querystring_pattern):
    job_config_url = base_url_location + "/job_config.json"
    job_config_url_pattern = r"\?".join([job_config_url, querystring_pattern])
    return job_config_url_pattern


@pytest.fixture
def run_config_url_pattern(base_url_location, querystring_pattern):
    run_config_url = base_url_location + "/run_1_config.json"
    run_config_url_pattern = r"\?".join([run_config_url, querystring_pattern])
    return run_config_url_pattern


@freeze_time("2025-01-01 12:00:00")
class TestJobControllerIntegration:
    def test_register_job__returns_success_result_with_job_data(self, job_controller, bearer_token):
        result = job_controller.register_job(user_token_value=bearer_token, tags=["test_job"])
        assert is_successful(result)
        job_dict = result.unwrap()

        expected_job_data = {
            "id": 1,
            "userId": 123,
            "tags": ["test_job"],
            "status": JobStatus.CREATED.value,
            "createdAt": job_dict["createdAt"],
            "updatedAt": job_dict["updatedAt"],
            "metadata": {},
        }
        assert job_dict == expected_job_data

    def test_register_job__persists_job(self, job_controller, job_repository, bearer_token):
        result = job_controller.register_job(user_token_value=bearer_token, tags=["mock_test"])
        assert is_successful(result)
        job_dict = result.unwrap()

        expected_job_data = {
            "id": job_dict["id"],
            "userId": 123,
            "tags": ["mock_test"],
            "status": JobStatus.CREATED.value,
            "createdAt": job_dict["createdAt"],
            "updatedAt": job_dict["updatedAt"],
            "metadata": {},
        }
        retrieved_job = job_repository.find_by_id(job_dict["id"])
        assert retrieved_job.to_dict() == expected_job_data

    @freeze_time("2025-01-01 12:00:00")
    def test_register_job__returns_success_result_with_job_config_url(
        self, job_controller, bearer_token
    ):
        register_result = job_controller.register_job(
            user_token_value=bearer_token, tags=["interface_test"]
        )
        job_dict = register_result.unwrap()

        submit_result = job_controller.submit_job(job_dict["id"])
        assert is_successful(submit_result)
        response = submit_result.unwrap()

        url, querystring = response["url"].split("?")
        key, sig, expir = querystring.split("&")
        expected_expiration_seconds = 3600
        expected_expiration = int(
            sum(
                (
                    datetime.fromisoformat("2025-01-01 12:00:00").timestamp(),
                    expected_expiration_seconds,
                )
            )
        )

        assert url == "https://test-bucket.s3.amazonaws.com/jobs/1/2025/01/01/120000/job_input.zip"
        assert key.startswith("AWSAccessKeyId=")
        assert sig.startswith("Signature=")
        assert expir == f"Expires={expected_expiration}"

    def test_submit_job__updates_job_status(self, job_controller, job_repository, bearer_token):
        register_result = job_controller.register_job(
            user_token_value=bearer_token, tags=["status_test"]
        )
        job_dict = register_result.unwrap()
        job_controller.submit_job(job_dict["id"])

        # Verify job status was updated
        updated_job = job_repository.find_by_id(job_dict["id"])
        assert updated_job.status == JobStatus.SUBMITTED

    def test_submit_runs__returns_success_result_with_run_responses(
        self, job_controller, run_requests, bearer_token
    ):
        # Create job first (submit_runs now requires job to exist for JobS3Prefix)
        job_result = job_controller.register_job(user_token_value=bearer_token, tags=["test_runs"])
        assert is_successful(job_result)

        result = job_controller.submit_runs(
            user_token_value=bearer_token, run_requests=run_requests, epx_version="epx_client_1.2.2"
        )

        assert is_successful(result)

        expected_response = [
            Run.create_persisted(
                run_id=1,
                job_id=1,
                user_id=123,
                status=RunStatus.SUBMITTED,
                pod_phase=PodPhase.PENDING,
                request=run_requests[0],
                created_at=datetime(2025, 1, 1, 12, 0, 0),
                updated_at=datetime(2025, 1, 1, 12, 0, 0),
            ).to_run_response_dict()
        ]
        run_responses = result.unwrap()
        assert run_responses == expected_response

    def test_submit_runs__persists_runs(
        self, job_controller, run_requests, bearer_token, run_repository, db_session
    ):
        # Create job first (submit_runs now requires job to exist for JobS3Prefix)
        job_result = job_controller.register_job(
            user_token_value=bearer_token, tags=["test_persist"]
        )
        assert is_successful(job_result)

        job_controller.submit_runs(
            user_token_value=bearer_token, run_requests=run_requests, epx_version="epx_client_1.2.2"
        )
        db_session.commit()

        expected_base_url = (
            "https://test-bucket.s3.amazonaws.com/jobs/1/2025/01/01/120000/run_1_config.json"
        )
        expected_expiration = int(
            sum((datetime.fromisoformat("2025-01-01 12:00:00").timestamp(), 3600))
        )
        expected_querystring = "&".join(
            ["AWSAccessKeyId=test-access-key", "Signature=.*", f"Expires={expected_expiration}"]
        )
        expected_config_url_pattern = r"\?".join([expected_base_url, expected_querystring])
        expected_run = Run.create_persisted(
            run_id=1,
            user_id=123,
            job_id=1,
            status=RunStatus.SUBMITTED,
            pod_phase=PodPhase.PENDING,
            request=run_requests[0],
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            updated_at=datetime(2025, 1, 1, 12, 0, 0),
            config_url=expected_config_url_pattern,
        )
        saved_run = run_repository.find_by_id(1)
        assert saved_run == expected_run

    @freeze_time("2025-01-01 12:00:00")
    def test_get_runs__given_job_id__returns_success_result_with_run_data(
        self, job_controller, run_requests, bearer_token, run_config_url_pattern
    ):
        # Create job first (submit_runs now requires job to exist for JobS3Prefix)
        job_result = job_controller.register_job(
            user_token_value=bearer_token, tags=["test_get_runs"]
        )
        assert is_successful(job_result)

        job_controller.submit_runs(
            user_token_value=bearer_token, run_requests=run_requests, epx_version="epx_client_1.2.2"
        )

        runs_result = job_controller.get_runs(job_id=1)
        assert is_successful(runs_result)

        expected_run_dict = Run.create_persisted(
            run_id=1,
            job_id=1,
            user_id=123,
            status=RunStatus.SUBMITTED,
            pod_phase=PodPhase.PENDING,
            request=run_requests[0],
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            updated_at=datetime(2025, 1, 1, 12, 0, 0),
            config_url=run_config_url_pattern,
        ).to_dict()
        expected_run_dict.pop("config_url")
        runs = runs_result.unwrap()
        assert len(runs) == 1

        config_url = runs[0].pop("config_url")
        assert runs == [expected_run_dict]
        assert bool(re.match(run_config_url_pattern, config_url))

    def test_get_runs__when_no_runs_for_job__returns_empty_list(self, job_controller):
        runs_result = job_controller.get_runs(job_id=999)
        assert is_successful(runs_result)
        assert runs_result.unwrap() == []

    def test_archive_job_uploads__when_only_job_id__returns_list_of_all_uploads(
        self, job_controller, bearer_token, base_url_location, run_requests
    ):
        # arrange
        register_result = job_controller.register_job(
            user_token_value=bearer_token, tags=["status_test"]
        )
        job_dict = register_result.unwrap()
        job_controller.submit_job(job_dict["id"])
        job_controller.submit_job(job_dict["id"], context="job", job_type="config")

        job_controller.submit_runs(
            user_token_value=bearer_token, run_requests=run_requests, epx_version="epx_client_1.2.2"
        )
        job_controller.submit_job(job_dict["id"], run_id=1, context="run", job_type="config")

        # act
        archive_result = job_controller.archive_job_uploads(job_id=1)
        archived_uploads = sorted(archive_result.unwrap(), key=lambda x: x["url"])

        # assert
        expected_uploads = [
            # sanitized url
            {"url": base_url_location + "/job_config.json"},
            {"url": base_url_location + "/job_input.zip"},
            {"url": base_url_location + "/run_1_config.json"},
        ]

        assert is_successful(archive_result)
        assert archived_uploads == expected_uploads


@pytest.fixture
def temp_download_dir():
    """Create a temporary directory for download testing."""
    test_dir = Path(tempfile.mkdtemp(prefix="test_force_"))
    yield test_dir
    # Cleanup after test
    shutil.rmtree(test_dir)


@pytest.fixture
def mock_controller_with_uploads():
    """Create a JobController with mocked dependencies for download testing."""
    # Create mock locations with url attribute
    mock_location1 = Mock(spec=UploadLocation)
    mock_location1.url = "http://example.com/test_file1.txt"
    mock_location1.extract_filename = Mock(return_value="test_file1.txt")

    mock_location2 = Mock(spec=UploadLocation)
    mock_location2.url = "http://example.com/test_file2.txt"
    mock_location2.extract_filename = Mock(return_value="test_file2.txt")

    # Create mock uploads (using valid types for job context)
    mock_upload1 = JobUpload(
        job_id=123, run_id=None, upload_type="config", location=mock_location1, context="job"
    )

    mock_upload2 = JobUpload(
        job_id=123, run_id=None, upload_type="input", location=mock_location2, context="job"
    )

    # Store mock content for reuse
    mock_content1 = UploadContent.create_text("Content for file 1")
    mock_content2 = UploadContent.create_text("Content for file 2")

    # Create controller and wire mocks
    controller = JobController()
    controller._register_job = Mock()
    controller._submit_job = Mock()
    controller._submit_job_config = Mock()
    controller._submit_runs = Mock()
    controller._submit_run_config = Mock()
    controller._get_runs_by_job_id = Mock()
    controller._get_job_uploads = Mock(return_value=[mock_upload1, mock_upload2])
    controller._read_upload_content = Mock(side_effect=[mock_content1, mock_content2])
    controller._write_to_local = Mock(return_value=None)

    # Store mock content for reuse in tests
    controller.mock_content1 = mock_content1
    controller.mock_content2 = mock_content2

    return controller, controller


class TestJobControllerDownloadForceFlag:
    """Test the force flag functionality for download_job_uploads."""

    def test_initial_download_creates_files(self, mock_controller_with_uploads, temp_download_dir):
        """Test that initial download creates files when directory is empty."""
        controller, _ = mock_controller_with_uploads

        # Setup read_upload_content mock
        controller._read_upload_content = Mock(
            side_effect=[controller.mock_content1, controller.mock_content2]
        )

        # Setup write_to_local mock to actually write files for testing
        def mock_write_to_local(file_path, content, force=False):  # noqa: ARG001
            file_path.write_text(content.raw_content)

        controller._write_to_local = Mock(side_effect=mock_write_to_local)

        # Download files
        result = controller.download_job_uploads(123, temp_download_dir, should_force=False)

        # Verify success
        assert is_successful(result)

        # Verify files were created
        file1 = temp_download_dir / "test_file1.txt"
        file2 = temp_download_dir / "test_file2.txt"
        assert file1.exists()
        assert file2.exists()
        assert file1.read_text() == "Content for file 1"
        assert file2.read_text() == "Content for file 2"

    def test_download_without_force_skips_existing_files(
        self, mock_controller_with_uploads, temp_download_dir
    ):
        """Test that download without force flag skips existing files."""
        controller, _ = mock_controller_with_uploads

        # Create existing files with different content
        file1 = temp_download_dir / "test_file1.txt"
        file2 = temp_download_dir / "test_file2.txt"
        file1.write_text("Modified content 1")
        file2.write_text("Modified content 2")

        # Setup read_upload_content mock
        controller._read_upload_content = Mock(
            side_effect=[controller.mock_content1, controller.mock_content2]
        )

        # Setup write_to_local mock that shouldn't be called for existing files
        controller._write_to_local = Mock()

        # Download without force
        result = controller.download_job_uploads(123, temp_download_dir, should_force=False)

        # Verify success
        assert is_successful(result)

        # Verify files were NOT overwritten
        assert file1.read_text() == "Modified content 1"
        assert file2.read_text() == "Modified content 2"

        # Verify read_upload_content was not called (files were skipped)
        assert controller._read_upload_content.call_count == 0

    def test_download_with_force_overwrites_existing_files(
        self, mock_controller_with_uploads, temp_download_dir
    ):
        """Test that download with force flag overwrites existing files."""
        controller, _ = mock_controller_with_uploads

        # Create existing files with different content
        file1 = temp_download_dir / "test_file1.txt"
        file2 = temp_download_dir / "test_file2.txt"
        file1.write_text("Modified content 1")
        file2.write_text("Modified content 2")

        # Setup read_upload_content mock
        controller._read_upload_content = Mock(
            side_effect=[controller.mock_content1, controller.mock_content2]
        )

        # Setup write_to_local mock to actually write files for testing
        def mock_write_to_local(file_path, content, force=False):  # noqa: ARG001
            file_path.write_text(content.raw_content)

        controller._write_to_local = Mock(side_effect=mock_write_to_local)

        # Download with force
        result = controller.download_job_uploads(123, temp_download_dir, should_force=True)

        # Verify success
        assert is_successful(result)

        # Verify files WERE overwritten
        assert file1.read_text() == "Content for file 1"
        assert file2.read_text() == "Content for file 2"

        # Verify read_upload_content was called for all files
        assert controller._read_upload_content.call_count == 2

    def test_partial_existing_files_behavior(self, mock_controller_with_uploads, temp_download_dir):
        """Test behavior when only some files exist in the directory."""
        controller, _ = mock_controller_with_uploads

        # Create only one existing file
        file1 = temp_download_dir / "test_file1.txt"
        file1.write_text("Modified content 1")

        # Setup read_upload_content mock - should only be called for file2
        controller._read_upload_content = Mock(return_value=controller.mock_content2)

        # Setup write_to_local mock to actually write files for testing
        def mock_write_to_local(file_path, content, force=False):  # noqa: ARG001
            file_path.write_text(content.raw_content)

        controller._write_to_local = Mock(side_effect=mock_write_to_local)

        # Download without force
        result = controller.download_job_uploads(123, temp_download_dir, should_force=False)

        # Verify success
        assert is_successful(result)

        # Verify file1 was not overwritten
        assert file1.read_text() == "Modified content 1"

        # Verify file2 was created
        file2 = temp_download_dir / "test_file2.txt"
        assert file2.exists()
        assert file2.read_text() == "Content for file 2"

        # Verify read_upload_content was called only once (for file2)
        assert controller._read_upload_content.call_count == 1
