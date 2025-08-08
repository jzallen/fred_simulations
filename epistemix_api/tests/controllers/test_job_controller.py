"""
Tests for the refactored Flask app using Clean Architecture.
"""
import os
import json
import base64
import tempfile
import shutil
from pathlib import Path

import pytest
from unittest.mock import Mock

from freezegun import freeze_time
from datetime import datetime
from returns.pipeline import is_successful

from epistemix_api.controllers.job_controller import JobController, JobControllerDependencies
from epistemix_api.models.job import Job, JobStatus
from epistemix_api.models.upload_location import UploadLocation
from epistemix_api.models.job_upload import JobUpload
from epistemix_api.models.upload_content import UploadContent
from epistemix_api.models.requests import RunRequest
from epistemix_api.models.run import Run, RunStatus, PodPhase
from epistemix_api.repositories import IUploadLocationRepository
from epistemix_api.repositories import SQLAlchemyJobRepository, SQLAlchemyRunRepository


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
        updated_at=datetime(2025, 1, 1, 12, 0, 0)
    )

    service = JobController()
    service._dependencies = JobControllerDependencies(
        register_job_fn=Mock(return_value=job),
        submit_job_fn=Mock(return_value=UploadLocation(url="http://example.com/pre-signed-url")),
        submit_job_config_fn=Mock(return_value=UploadLocation(url="http://example.com/pre-signed-url-job-config")),
        submit_runs_fn=Mock(return_value=[run]),
        submit_run_config_fn=Mock(return_value=UploadLocation(url="http://example.com/pre-signed-url-run-config")),
        get_runs_by_job_id_fn=Mock(return_value=[run]),
        get_job_uploads_fn=Mock(return_value=[]),
        read_upload_content_fn=Mock(return_value=UploadContent.create_text("test content")),
    )
    return service


@pytest.fixture
def run_requests():
    return [
        RunRequest(
            jobId=1, 
            workingDir="/tmp", 
            size="hot",
            fredVersion="latest",
            population={
                "version": "US_2010.v5", 
                "locations": ["New York", "Los Angeles"]
            },
            fredArgs=[{"flag": "-p", "value": "param"}],
            fredFiles=["/path/to/fred/file"]
        ).model_dump()
    ]

class TestJobController:
    
    def test_register_job__calls_register_job_fn_with_created_job(self, service):
        service.register_job(user_token_value="token", tags=["info_job"])
        service._dependencies.register_job_fn.assert_called_once_with(user_token_value="token", tags=["info_job"])

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

    def test_register_job__when_value_error_raised__returns_failure_result(self, service, bearer_token):
        service._dependencies.register_job_fn.side_effect = ValueError("Invalid user ID")
        job_result = service.register_job(user_token_value=bearer_token, tags=["info_job"])
        assert not is_successful(job_result)
        assert job_result.failure() == "Invalid user ID"

    def test_register_job__when_exception_raised__returns_failure_result(self, service, bearer_token):
        service._dependencies.register_job_fn.side_effect = Exception("Unexpected error")
        job_result = service.register_job(user_token_value=bearer_token, tags=["info_job"])
        assert not is_successful(job_result)
        assert job_result.failure() == "An unexpected error occurred while registering the job"

    def test_submit_job__calls_submit_job_fn_with_correct_parameters(self, service):
        service.submit_job(job_id=1, context="job", job_type="input")
        expected_job_upload = JobUpload(context="job", upload_type="input", job_id=1, run_id=None)
        service._dependencies.submit_job_fn.assert_called_once_with(expected_job_upload)

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
        service._dependencies.submit_job_fn.side_effect = Exception("Unexpected error")
        job_result = service.submit_job(job_id=1, context="job", job_type="input")
        assert not is_successful(job_result)
        assert job_result.failure() == "An unexpected error occurred while submitting the job"

    def test_submit_runs__calls_submit_runs_fn_with_correct_parameters(self, service, run_requests):
        bearer_token = "Bearer valid_token"
        service.submit_runs(user_token_value=bearer_token, run_requests=run_requests)
        service._dependencies.submit_runs_fn.assert_called_once_with(
            run_requests=run_requests, 
            user_token_value=bearer_token,
            epx_version="epx_client_1.2.2"
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
                updated_at=datetime(2025, 1, 1, 12, 0, 0)
            ).to_run_response_dict()
        ]
        bearer_token = "Bearer valid_token"
        restult = service.submit_runs(
            user_token_value=bearer_token,
            run_requests=run_requests,
            epx_version="epx_client_1.2.2"
        )
        assert is_successful(restult)
        assert restult.unwrap() == expected_response
    
    def test_submit_runs__when_value_error_raised__returns_failure_result(self, service, run_requests):
        service._dependencies.submit_runs_fn.side_effect = ValueError("Invalid run request")
        bearer_token = "Bearer valid_token"
        result = service.submit_runs(
            user_token_value=bearer_token,
            run_requests=run_requests,
            epx_version="epx_client_1.2.2"
        )
        assert not is_successful(result)
        assert result.failure() == "Invalid run request"

    def test_submit_runs__when_exception_raised__returns_failure_result(self, service, run_requests):
        service._dependencies.submit_runs_fn.side_effect = Exception("Unexpected error")
        bearer_token = "Bearer valid_token"
        result = service.submit_runs(
            user_token_value=bearer_token,
            run_requests=run_requests,
            epx_version="epx_client_1.2.2"
        )
        assert not is_successful(result)
        assert result.failure() == "An unexpected error occurred while submitting the runs"

    def test_submit_job___type_config__calls_submit_job_config_fn_with_correct_parameters(self, service):
        service.submit_job(job_id=1, context="job", job_type="config")
        expected_job_upload = JobUpload(context="job", upload_type="config", job_id=1, run_id=None)
        service._dependencies.submit_job_config_fn.assert_called_once_with(expected_job_upload)

    def test_submit_job__type_config__returns_success_result_with_response_data(self, service):
        expected_response = {"url": "http://example.com/pre-signed-url-job-config"}
        job_result = service.submit_job(job_id=1, context="job", job_type="config")
        assert is_successful(job_result)
        assert job_result.unwrap() == expected_response

    def test_submit_job__context_run_type_config__calls_submit_run_config_fn_with_correct_parameters(self, service):
        service.submit_job(job_id=1, run_id=2, context="run", job_type="config")
        expected_job_upload = JobUpload(context="run", upload_type="config", job_id=1, run_id=2)
        service._dependencies.submit_run_config_fn.assert_called_once_with(expected_job_upload)

    def test_submit_job__context_run_type_config__returns_success_result_with_response_data(self, service):
        expected_response = {"url": "http://example.com/pre-signed-url-run-config"}
        job_result = service.submit_job(job_id=1, run_id=2, context="run", job_type="config")
        assert is_successful(job_result)
        assert job_result.unwrap() == expected_response

    def test_get_runs__calls_get_runs_by_job_id_fn_with_correct_job_id(self, service):
        service.get_runs(job_id=1)
        service._dependencies.get_runs_by_job_id_fn.assert_called_once_with(job_id=1)

    def test_get_runs__returns_success_result_with_run_data(self, service):
        expected_run = Run.create_persisted(
            run_id=1, 
            job_id=1, 
            user_id=456, 
            status=RunStatus.SUBMITTED, 
            pod_phase=PodPhase.PENDING, 
            request={},
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            updated_at=datetime(2025, 1, 1, 12, 0, 0)
        )
        service._dependencies.get_runs_by_job_id_fn.return_value = [expected_run]
        
        runs_result = service.get_runs(job_id=1)
        assert is_successful(runs_result)
        assert runs_result.unwrap() == [expected_run.to_dict()]
    
    def test_get_job_uploads__calls_dependencies_with_correct_parameters(self, service):
        upload = JobUpload(
            context="job",
            upload_type="input",
            job_id=1,
            location=UploadLocation(url="http://example.com/job-input"),
            run_id=None
        )
        service._dependencies.get_job_uploads_fn.return_value = [upload]
        
        service.get_job_uploads(job_id=1)
        
        service._dependencies.get_job_uploads_fn.assert_called_once_with(job_id=1)
        service._dependencies.read_upload_content_fn.assert_called_once_with(upload.location)
    
    def test_get_job_uploads__returns_success_result_with_content(self, service):
        upload = JobUpload(
            context="job",
            upload_type="input",
            job_id=1,
            location=UploadLocation(url="http://example.com/job-input"),
            run_id=None
        )
        content = UploadContent.create_text("test file content")
        service._dependencies.get_job_uploads_fn.return_value = [upload]
        service._dependencies.read_upload_content_fn.return_value = content
        
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
            run_id=None
        )
        service._dependencies.get_job_uploads_fn.return_value = [upload]
        service._dependencies.read_upload_content_fn.side_effect = ValueError("S3 error")
        
        result = service.get_job_uploads(job_id=1)
        
        assert is_successful(result)
        uploads = result.unwrap()
        assert len(uploads) == 1
        assert uploads[0]["context"] == "job"
        assert uploads[0]["uploadType"] == "input"
        assert uploads[0]["error"] == "S3 error"
        assert "content" not in uploads[0]


@pytest.fixture
def job_repository(db_session):
    """Create a job repository using the shared db_session fixture."""
    return SQLAlchemyJobRepository(get_db_session_fn=lambda: db_session)


@pytest.fixture
def run_repository(db_session):
    """Create a run repository using the shared db_session fixture."""
    return SQLAlchemyRunRepository(get_db_session_fn=lambda: db_session)


@pytest.fixture
def upload_location_repository():
    repo = Mock(spec=IUploadLocationRepository)
    repo.get_upload_location.return_value = UploadLocation(url="https://s3.amazonaws.com/test-bucket/presigned-url")
    repo.read_content.return_value = UploadContent.create_text("test content from repository")
    return repo


@pytest.fixture
def job_controller(job_repository, run_repository, upload_location_repository):
    return JobController.create_with_repositories(job_repository, run_repository, upload_location_repository)


@pytest.fixture
def bearer_token():
    token_data = {"user_id": 123, "scopes_hash": "abc123"}
    token_json = json.dumps(token_data)
    token_b64 = base64.b64encode(token_json.encode()).decode()
    return f"Bearer {token_b64}"


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
            "metadata": {}
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
            "metadata": {}
        }
        retrieved_job = job_repository.find_by_id(job_dict["id"])
        assert retrieved_job.to_dict() == expected_job_data

    def test_service__returns_success_result_with_job_config_url(self, job_controller, bearer_token):
        register_result = job_controller.register_job(user_token_value=bearer_token, tags=["interface_test"])
        job_dict = register_result.unwrap()

        submit_result = job_controller.submit_job(job_dict["id"])
        assert is_successful(submit_result)
        response = submit_result.unwrap()
        
        assert response["url"] == "https://s3.amazonaws.com/test-bucket/presigned-url"

    def test_submit_job__updates_job_status(self, job_controller, job_repository, bearer_token):
        register_result = job_controller.register_job(user_token_value=bearer_token, tags=["status_test"])
        job_dict = register_result.unwrap()
        job_controller.submit_job(job_dict["id"])
        
        # Verify job status was updated
        updated_job = job_repository.find_by_id(job_dict["id"])
        assert updated_job.status == JobStatus.SUBMITTED

    def test_submit_runs__returns_success_result_with_run_responses(self, job_controller, run_requests, bearer_token):
        result = job_controller.submit_runs(
            user_token_value=bearer_token,
            run_requests=run_requests,
            epx_version="epx_client_1.2.2"
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
                updated_at=datetime(2025, 1, 1, 12, 0, 0)
            ).to_run_response_dict()
        ]
        run_responses = result.unwrap()
        assert run_responses == expected_response

    def test_submit_runs__persists_runs(self, job_controller, run_requests, bearer_token, run_repository, db_session):
        job_controller.submit_runs(
            user_token_value=bearer_token,
            run_requests=run_requests,
            epx_version="epx_client_1.2.2"
        )
        db_session.commit()

        expected_run = Run.create_persisted(
            run_id=1,
            user_id=123,
            job_id=1,
            status=RunStatus.SUBMITTED,
            pod_phase=PodPhase.PENDING,
            request=run_requests[0],
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            updated_at=datetime(2025, 1, 1, 12, 0, 0),
            url="https://s3.amazonaws.com/test-bucket/presigned-url"
        )
        saved_run = run_repository.find_by_id(1)
        assert saved_run == expected_run

    def test_get_runs__givent_job_id__returns_success_result_with_run_data(self, job_controller, run_requests, bearer_token):
        job_controller.submit_runs(
            user_token_value=bearer_token,
            run_requests=run_requests,
            epx_version="epx_client_1.2.2"
        )
        
        runs_result = job_controller.get_runs(job_id=1)
        assert is_successful(runs_result)
        
        expected_run = Run.create_persisted(
            run_id=1, 
            job_id=1, 
            user_id=123, 
            status=RunStatus.SUBMITTED, 
            pod_phase=PodPhase.PENDING, 
            request=run_requests[0],
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            updated_at=datetime(2025, 1, 1, 12, 0, 0),
            url="https://s3.amazonaws.com/test-bucket/presigned-url"
        )
        assert runs_result.unwrap() == [expected_run.to_dict()]

    def test_get_runs__when_no_runs_for_job__returns_empty_list(self, job_controller):
        runs_result = job_controller.get_runs(job_id=999)
        assert is_successful(runs_result)
        assert runs_result.unwrap() == []


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
    mock_deps = Mock()
    
    # Create mock locations with url attribute
    mock_location1 = Mock(spec=UploadLocation)
    mock_location1.url = "http://example.com/test_file1.txt"
    mock_location1.extract_filename = Mock(return_value="test_file1.txt")
    
    mock_location2 = Mock(spec=UploadLocation)
    mock_location2.url = "http://example.com/test_file2.txt"
    mock_location2.extract_filename = Mock(return_value="test_file2.txt")
    
    # Create mock uploads (using valid types for job context)
    mock_upload1 = JobUpload(
        job_id=123,
        run_id=None,
        upload_type="config",
        location=mock_location1,
        context="job"
    )
    
    mock_upload2 = JobUpload(
        job_id=123,
        run_id=None,
        upload_type="input",
        location=mock_location2,
        context="job"
    )
    
    # Mock the get_job_uploads function
    mock_deps.get_job_uploads_fn = Mock(return_value=[mock_upload1, mock_upload2])
    
    # Store mock content for reuse
    mock_deps.mock_content1 = UploadContent.create_text("Content for file 1")
    mock_deps.mock_content2 = UploadContent.create_text("Content for file 2")
    
    controller = JobController()
    controller._dependencies = mock_deps
    return controller, mock_deps


class TestJobControllerDownloadForceFlag:
    """Test the force flag functionality for download_job_uploads."""

    def test_initial_download_creates_files(self, mock_controller_with_uploads, temp_download_dir):
        """Test that initial download creates files when directory is empty."""
        controller, mock_deps = mock_controller_with_uploads
        
        # Setup read_upload_content mock
        mock_deps.read_upload_content_fn = Mock(
            side_effect=[mock_deps.mock_content1, mock_deps.mock_content2]
        )
        
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

    def test_download_without_force_skips_existing_files(self, mock_controller_with_uploads, temp_download_dir):
        """Test that download without force flag skips existing files."""
        controller, mock_deps = mock_controller_with_uploads
        
        # Create existing files with different content
        file1 = temp_download_dir / "test_file1.txt"
        file2 = temp_download_dir / "test_file2.txt"
        file1.write_text("Modified content 1")
        file2.write_text("Modified content 2")
        
        # Setup read_upload_content mock
        mock_deps.read_upload_content_fn = Mock(
            side_effect=[mock_deps.mock_content1, mock_deps.mock_content2]
        )
        
        # Download without force
        result = controller.download_job_uploads(123, temp_download_dir, should_force=False)
        
        # Verify success
        assert is_successful(result)
        
        # Verify files were NOT overwritten
        assert file1.read_text() == "Modified content 1"
        assert file2.read_text() == "Modified content 2"
        
        # Verify read_upload_content was not called (files were skipped)
        assert mock_deps.read_upload_content_fn.call_count == 0

    def test_download_with_force_overwrites_existing_files(self, mock_controller_with_uploads, temp_download_dir):
        """Test that download with force flag overwrites existing files."""
        controller, mock_deps = mock_controller_with_uploads
        
        # Create existing files with different content
        file1 = temp_download_dir / "test_file1.txt"
        file2 = temp_download_dir / "test_file2.txt"
        file1.write_text("Modified content 1")
        file2.write_text("Modified content 2")
        
        # Setup read_upload_content mock
        mock_deps.read_upload_content_fn = Mock(
            side_effect=[mock_deps.mock_content1, mock_deps.mock_content2]
        )
        
        # Download with force
        result = controller.download_job_uploads(123, temp_download_dir, should_force=True)
        
        # Verify success
        assert is_successful(result)
        
        # Verify files WERE overwritten
        assert file1.read_text() == "Content for file 1"
        assert file2.read_text() == "Content for file 2"
        
        # Verify read_upload_content was called for all files
        assert mock_deps.read_upload_content_fn.call_count == 2

    def test_partial_existing_files_behavior(self, mock_controller_with_uploads, temp_download_dir):
        """Test behavior when only some files exist in the directory."""
        controller, mock_deps = mock_controller_with_uploads
        
        # Create only one existing file
        file1 = temp_download_dir / "test_file1.txt"
        file1.write_text("Modified content 1")
        
        # Setup read_upload_content mock - should only be called for file2
        mock_deps.read_upload_content_fn = Mock(return_value=mock_deps.mock_content2)
        
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
        assert mock_deps.read_upload_content_fn.call_count == 1
