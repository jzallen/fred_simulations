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
from unittest.mock import Mock, call

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
    service._update_run_status = Mock(return_value=True)
    service._get_run_results = Mock(return_value=[])
    service._upload_results = Mock(return_value="https://s3.amazonaws.com/bucket/results.zip")
    service.job_repository = Mock()
    service.run_repository = Mock()
    service.results_repository = Mock()
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


@pytest.fixture
def bearer_token():
    token_data = {"user_id": 123, "scopes_hash": "abc123"}
    token_json = json.dumps(token_data)
    token_b64 = base64.b64encode(token_json.encode()).decode()
    return f"Bearer {token_b64}"


class TestJobController:
    def test_register_job__given_user_token_and_tags__calls_internal_register_job_use_case(
        self, service
    ):
        service.register_job(user_token_value="token", tags=["info_job"])
        service._register_job.assert_called_once_with(user_token_value="token", tags=["info_job"])

    def test_register_job__when_no_exceptions__returns_success_result_with_job_data(self, service):
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

    def test_submit_job__given_job_id_context_and_job_type__calls_internal_submit_job_use_case(
        self, service
    ):
        service.submit_job(job_id=1, context="job", job_type="input")
        expected_job_upload = JobUpload(context="job", upload_type="input", job_id=1, run_id=None)
        service._submit_job.assert_called_once_with(expected_job_upload)

    def test_submit_job__when_no_exceptions__returns_success_result_with_response_data(
        self, service
    ):
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

    def test_submit_runs__given_run_requests_and_user_token__calls_internal_submit_runs_use_case(
        self, service, run_requests
    ):
        bearer_token = "Bearer valid_token"
        service.submit_runs(user_token_value=bearer_token, run_requests=run_requests)
        service._submit_runs.assert_called_once_with(
            run_requests=run_requests, user_token_value=bearer_token, epx_version="epx_client_1.2.2"
        )

    def test_submit_runs__when_no_exceptions__returns_success_result_with_run_responses(
        self, service, run_requests
    ):
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

    def test_submit_job__given_type_config__calls_internal_submit_job_config_use_case(
        self, service
    ):
        service.submit_job(job_id=1, context="job", job_type="config")
        expected_job_upload = JobUpload(context="job", upload_type="config", job_id=1, run_id=None)
        service._submit_job_config.assert_called_once_with(expected_job_upload)

    def test_submit_job__given_type_config__when_no_exceptions__returns_success_result_with_response_data(
        self, service
    ):
        expected_response = {"url": "http://example.com/pre-signed-url-job-config"}
        job_result = service.submit_job(job_id=1, context="job", job_type="config")
        assert is_successful(job_result)
        assert job_result.unwrap() == expected_response

    def test_submit_job__given_context_run_type_config__calls_internal_submit_run_config_use_case(
        self, service
    ):
        service.submit_job(job_id=1, run_id=2, context="run", job_type="config")
        expected_job_upload = JobUpload(context="run", upload_type="config", job_id=1, run_id=2)
        service._submit_run_config.assert_called_once_with(expected_job_upload)

    def test_submit_job__given_context_run_type_config__when_no_exceptions__returns_success_result_with_response_data(
        self, service
    ):
        expected_response = {"url": "http://example.com/pre-signed-url-run-config"}
        job_result = service.submit_job(job_id=1, run_id=2, context="run", job_type="config")
        assert is_successful(job_result)
        assert job_result.unwrap() == expected_response

    def test_get_runs__given_job_id__calls_internal_get_runs_by_job_id_use_case(self, service):
        service.get_runs(job_id=1)
        service._get_runs_by_job_id.assert_called_once_with(job_id=1)

    def test_get_runs__when_no_exceptions__returns_success_result_with_run_data(self, service):
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

    def test_get_runs__when_value_error_raised__returns_failure_result(self, service):
        service._get_runs_by_job_id.side_effect = ValueError("Invalid job ID")

        result = service.get_runs(job_id=999)

        assert not is_successful(result)
        assert result.failure() == "Invalid job ID"

    def test_get_runs__when_exception_raised__returns_failure_result(self, service):
        service._get_runs_by_job_id.side_effect = Exception("Database error")

        result = service.get_runs(job_id=1)

        assert not is_successful(result)
        assert result.failure() == "An unexpected error occurred while retrieving the runs"

    def test_get_job_uploads__given_job_id__calls_internal_get_job_uploads_use_case(self, service):
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

    def test_get_job_uploads__when_no_exceptions__returns_success_result_with_content(self, service):
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
        assert uploads == [
            {
                "context": "job",
                "uploadType": "input",
                "jobId": 1,
                "runId": None,
                "location": {"url": "http://example.com/job-input"},
                "content": {
                    "contentType": "text",
                    "content": "test file content",
                    "encoding": "utf-8",
                    "size": 17,
                },
            }
        ]

    def test_get_job_uploads__when_read_content_fails__includes_error_message(self, service):
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
        assert uploads == [
            {
                "context": "job",
                "uploadType": "input",
                "jobId": 1,
                "runId": None,
                "location": {"url": "http://example.com/job-input"},
                "error": "S3 error",
            }
        ]

    def test_get_run_results_download__when_no_exceptions__returns_success_result_with_presigned_urls(
        self, service
    ):
        from epistemix_platform.models.run_results import RunResults

        service._get_run_results.return_value = [
            RunResults(run_id=1, url="https://s3.amazonaws.com/bucket/results1.zip"),
            RunResults(run_id=2, url="https://s3.amazonaws.com/bucket/results2.zip"),
        ]

        result = service.get_run_results_download(job_id=1, bucket_name="test-bucket")

        assert is_successful(result)
        urls = result.unwrap()
        assert urls == [
            {"run_id": 1, "url": "https://s3.amazonaws.com/bucket/results1.zip"},
            {"run_id": 2, "url": "https://s3.amazonaws.com/bucket/results2.zip"},
        ]

    def test_get_run_results_download__when_value_error_raised__returns_failure_result(self, service):
        service._get_run_results.side_effect = ValueError("Invalid job ID")

        result = service.get_run_results_download(job_id=999, bucket_name="test-bucket")

        assert not is_successful(result)
        assert result.failure() == "Invalid job ID"

    def test_get_run_results_download__when_exception_raised__returns_failure_result(self, service):
        service._get_run_results.side_effect = Exception("S3 error")

        result = service.get_run_results_download(job_id=1, bucket_name="test-bucket")

        assert not is_successful(result)
        assert "Failed to generate download URLs" in result.failure()

    def test_archive_job_uploads__given_job_id_and_days_since_create_with_dry_run_true__calls_internal_archive_uploads_use_case(self, service):
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

    def test_archive_job_uploads__when_no_exceptions__returns_success_result_with_archived_locations(self, service):
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

    def test_upload_results_from_directory__when_no_exceptions__returns_success_result_with_url(
        self, service
    ):
        service._upload_results.return_value = "https://s3.amazonaws.com/bucket/results.zip"

        result = service.upload_results_from_directory(
            job_id=1, run_id=1, results_dir=Path("/tmp/results")
        )

        assert is_successful(result)
        assert result.unwrap() == "https://s3.amazonaws.com/bucket/results.zip"
        service._upload_results.assert_called_once_with(
            job_id=1, run_id=1, results_dir=Path("/tmp/results")
        )

    def test_upload_results_from_directory__when_value_error_raised__returns_failure_result(
        self, service
    ):
        service._upload_results.side_effect = ValueError("Results directory not found")

        result = service.upload_results_from_directory(
            job_id=1, run_id=1, results_dir=Path("/tmp/missing")
        )

        assert not is_successful(result)
        assert result.failure() == "Results directory not found"

    def test_upload_results_from_directory__when_exception_raised__returns_failure_result(
        self, service
    ):
        service._upload_results.side_effect = Exception("S3 upload failed")

        result = service.upload_results_from_directory(
            job_id=1, run_id=1, results_dir=Path("/tmp/results")
        )

        assert not is_successful(result)
        assert result.failure() == "An unexpected error occurred while uploading results"

    def test_submit_runs__given_user_token_and_run_requests__calls_internal_run_simulation_use_case_for_each_run(
        self, service, run_requests
    ):
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

        # Verify _run_simulation was called with the correct runs
        expected_calls = [
            call(run=run1),
            call(run=run2),
        ]
        service._run_simulation.assert_has_calls(expected_calls)
