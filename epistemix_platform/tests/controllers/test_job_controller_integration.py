"""
Integration tests for JobController with real repository implementations.
"""

import base64
import json
import os
import re
from datetime import datetime

import boto3
import pytest
from botocore.stub import Stubber
from freezegun import freeze_time
from returns.pipeline import is_successful

from epistemix_platform.controllers.job_controller import JobController
from epistemix_platform.mappers.job_mapper import JobMapper
from epistemix_platform.mappers.run_mapper import RunMapper
from epistemix_platform.models.job import JobStatus
from epistemix_platform.models.requests import RunRequest
from epistemix_platform.models.run import PodPhase, Run, RunStatus
from epistemix_platform.repositories import (
    S3UploadLocationRepository,
    SQLAlchemyJobRepository,
    SQLAlchemyRunRepository,
)


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
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

    client = boto3.client("s3", region_name="us-east-1")
    stubber = Stubber(client)

    # Enable the stubber
    stubber.activate()

    yield client, stubber

    # Deactivate the stubber after the test
    stubber.deactivate()


@pytest.fixture
def upload_location_repository(s3_stubber):
    s3_client, _ = s3_stubber
    repo = S3UploadLocationRepository(s3_client=s3_client, bucket_name="test-bucket")
    return repo


@pytest.fixture
def results_repository(s3_stubber):
    from epistemix_platform.repositories.s3_results_repository import S3ResultsRepository

    s3_client, _ = s3_stubber
    return S3ResultsRepository(s3_client=s3_client, bucket_name="test-bucket")


@pytest.fixture
def simulation_runner_mock():
    """Create a mock simulation runner gateway with describe_run support (FRED-46)."""
    from unittest.mock import Mock

    from epistemix_platform.models import RunStatusDetail

    mock_runner = Mock()
    # Mock describe_run to return current DB status (no change scenario)
    # Tests that need different behavior can override this
    mock_runner.describe_run.side_effect = lambda run: RunStatusDetail(
        status=run.status,
        pod_phase=run.pod_phase,
        message="Job status unchanged",
    )
    return mock_runner


@pytest.fixture
def job_controller(
    job_repository,
    run_repository,
    upload_location_repository,
    results_repository,
    simulation_runner_mock,
):
    return JobController.create_with_repositories(
        job_repository,
        run_repository,
        upload_location_repository,
        results_repository,
        simulation_runner_mock,
    )


@pytest.fixture
def bearer_token():
    token_data = {"user_id": 123, "scopes_hash": "abc123"}
    token_json = json.dumps(token_data)
    token_b64 = base64.b64encode(token_json.encode()).decode()
    return f"Bearer {token_b64}"


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
        params = querystring.split("&")
        expected_expiration_seconds = 3600
        expected_expiration = int(
            sum(
                (
                    datetime.fromisoformat("2025-01-01 12:00:00").timestamp(),
                    expected_expiration_seconds,
                )
            )
        )

        # Parse query string parameters into a dict
        param_dict = dict(param.split("=", 1) for param in params)

        assert url == "https://test-bucket.s3.amazonaws.com/jobs/1/2025/01/01/120000/job_input.zip"
        assert "AWSAccessKeyId" in param_dict
        assert "Signature" in param_dict
        assert param_dict.get("Expires") == str(expected_expiration)

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
