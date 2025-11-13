"""
Tests for JobController download functionality with force flag behavior.
"""

import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pytest
from freezegun import freeze_time
from returns.pipeline import is_successful

from epistemix_platform.controllers.job_controller import JobController
from epistemix_platform.models.job import Job, JobStatus
from epistemix_platform.models.job_upload import JobUpload
from epistemix_platform.models.run import PodPhase, Run, RunStatus
from epistemix_platform.models.upload_content import UploadContent
from epistemix_platform.models.upload_location import UploadLocation


@pytest.fixture
def service():
    """Shared mock service fixture for download tests."""
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
    service._get_runs_by_job_id = Mock(return_value=[run])
    service._get_job_uploads = Mock(return_value=[mock_upload1, mock_upload2])
    service._read_upload_content = Mock(return_value=UploadContent.create_text("test content"))
    service._write_to_local = Mock(return_value=None)
    return service


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

    def test_download_job_uploads__when_no_uploads_found__returns_failure_result(self, service):
        service._get_job_uploads.return_value = []

        result = service.download_job_uploads(job_id=999, base_path=Path("/tmp/downloads"))

        assert not is_successful(result)
        assert result.failure() == "No uploads found for job 999"

    def test_download_job_uploads__when_filename_extraction_fails__uses_default_filename(
        self, service
    ):
        # Create upload with URL that has no filename
        upload = JobUpload(
            context="job",
            upload_type="input",
            job_id=1,
            location=UploadLocation(url="http://example.com/"),
            run_id=None,
        )
        service._get_job_uploads.return_value = [upload]
        service._read_upload_content.return_value = UploadContent.create_text("test content")

        # Mock write_to_local to actually write the file
        def mock_write_to_local(file_path, content, force=False):  # noqa: ARG001
            file_path.write_text(content.raw_content)

        service._write_to_local = Mock(side_effect=mock_write_to_local)

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir)

            result = service.download_job_uploads(job_id=1, base_path=temp_path)

            assert is_successful(result)
            # Verify default filename was used (job_1_input.zip from get_default_filename)
            expected_file = temp_path / "job_1_input.zip"
            assert expected_file.exists()

    def test_download_job_uploads__when_individual_file_fails__continues_with_other_files(
        self, service
    ):
        upload1 = JobUpload(
            context="job",
            upload_type="input",
            job_id=1,
            location=UploadLocation(url="http://example.com/file1.txt"),
            run_id=None,
        )
        upload2 = JobUpload(
            context="run",
            upload_type="config",
            job_id=1,
            run_id=1,
            location=UploadLocation(url="http://example.com/file2.txt"),
        )
        service._get_job_uploads.return_value = [upload1, upload2]

        # First upload fails, second succeeds
        service._read_upload_content.side_effect = [
            Exception("S3 read error"),
            UploadContent.create_text("content 2"),
        ]

        # Mock write_to_local to actually write the file
        def mock_write_to_local(file_path, content, force=False):  # noqa: ARG001
            file_path.write_text(content.raw_content)

        service._write_to_local = Mock(side_effect=mock_write_to_local)

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir)

            result = service.download_job_uploads(job_id=1, base_path=temp_path)

            # Should succeed with partial results
            assert is_successful(result)
            assert result.unwrap() == str(temp_path)

            # Verify second file was downloaded
            file2 = temp_path / "file2.txt"
            assert file2.exists()

    def test_download_job_uploads__when_all_files_fail__returns_failure_result(self, service):
        upload = JobUpload(
            context="job",
            upload_type="input",
            job_id=1,
            location=UploadLocation(url="http://example.com/file.txt"),
            run_id=None,
        )
        service._get_job_uploads.return_value = [upload]
        service._read_upload_content.side_effect = Exception("S3 read error")

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir)

            result = service.download_job_uploads(job_id=1, base_path=temp_path)

            assert not is_successful(result)
            assert "Failed to download any files" in result.failure()

    def test_download_job_uploads__when_value_error_raised__returns_failure_result(self, service):
        service._get_job_uploads.side_effect = ValueError("Invalid job ID")

        result = service.download_job_uploads(job_id=999, base_path=Path("/tmp/downloads"))

        assert not is_successful(result)
        assert result.failure() == "Invalid job ID"

    def test_download_job_uploads__when_exception_raised__returns_failure_result(self, service):
        service._get_job_uploads.side_effect = Exception("Database error")

        result = service.download_job_uploads(job_id=1, base_path=Path("/tmp/downloads"))

        assert not is_successful(result)
        assert result.failure() == "An unexpected error occurred while downloading uploads"
