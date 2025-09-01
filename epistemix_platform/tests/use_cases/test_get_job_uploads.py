"""
Tests for the get_job_uploads use case.
"""

from datetime import datetime
from unittest.mock import Mock

import pytest

from epistemix_platform.models.job import Job
from epistemix_platform.models.run import PodPhase, Run, RunStatus
from epistemix_platform.models.upload_location import UploadLocation
from epistemix_platform.use_cases.get_job_uploads import get_job_uploads


class TestGetJobUploads:
    """Tests for the get_job_uploads use case."""

    @pytest.fixture
    def job_repository(self):
        """Create a mock job repository."""
        return Mock()

    @pytest.fixture
    def run_repository(self):
        """Create a mock run repository."""
        return Mock()

    def test_get_job_uploads__job_not_found__raises_value_error(
        self, job_repository, run_repository
    ):
        """Test that ValueError is raised when job doesn't exist."""
        # Arrange
        job_repository.find_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match="Job 1 not found"):
            get_job_uploads(job_repository, run_repository, job_id=1)

    def test_get_job_uploads__job_with_no_uploads__returns_empty_list(
        self, job_repository, run_repository
    ):
        """Test that empty list is returned when job has no uploads."""
        # Arrange
        job = Job.create_persisted(job_id=1, user_id=123)
        job_repository.find_by_id.return_value = job
        run_repository.find_by_job_id.return_value = []

        # Act
        uploads = get_job_uploads(job_repository, run_repository, job_id=1)

        # Assert
        assert uploads == []

    def test_get_job_uploads__job_with_input_location__returns_job_input_upload(
        self, job_repository, run_repository
    ):
        """Test that job input upload is returned when job has input_location."""
        # Arrange
        job = Job.create_persisted(
            job_id=1, user_id=123, input_location="https://s3.amazonaws.com/bucket/job_1_input"
        )
        job_repository.find_by_id.return_value = job
        run_repository.find_by_job_id.return_value = []

        # Act
        uploads = get_job_uploads(job_repository, run_repository, job_id=1)

        # Assert
        assert len(uploads) == 1
        upload = uploads[0]
        assert upload.context == "job"
        assert upload.upload_type == "input"
        assert upload.job_id == 1
        assert upload.location.url == "https://s3.amazonaws.com/bucket/job_1_input"
        assert upload.run_id is None

    def test_get_job_uploads__job_with_config_location__returns_job_config_upload(
        self, job_repository, run_repository
    ):
        """Test that job config upload is returned when job has config_location."""
        # Arrange
        job = Job.create_persisted(
            job_id=1, user_id=123, config_location="https://s3.amazonaws.com/bucket/job_1_config"
        )
        job_repository.find_by_id.return_value = job
        run_repository.find_by_job_id.return_value = []

        # Act
        uploads = get_job_uploads(job_repository, run_repository, job_id=1)

        # Assert
        assert len(uploads) == 1
        upload = uploads[0]
        assert upload.context == "job"
        assert upload.upload_type == "config"
        assert upload.job_id == 1
        assert upload.location.url == "https://s3.amazonaws.com/bucket/job_1_config"
        assert upload.run_id is None

    def test_get_job_uploads__job_with_runs__returns_run_uploads(
        self, job_repository, run_repository
    ):
        """Test that run uploads are returned for job's runs."""
        # Arrange
        job = Job.create_persisted(job_id=1, user_id=123)
        run1 = Run.create_persisted(
            run_id=1,
            job_id=1,
            user_id=123,
            status=RunStatus.DONE,
            pod_phase=PodPhase.SUCCEEDED,
            request={},
            config_url="https://s3.amazonaws.com/bucket/run_1_output",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        run2 = Run.create_persisted(
            run_id=2,
            job_id=1,
            user_id=123,
            status=RunStatus.DONE,
            pod_phase=PodPhase.SUCCEEDED,
            request={},
            config_url="https://s3.amazonaws.com/bucket/run_2_output",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        job_repository.find_by_id.return_value = job
        run_repository.find_by_job_id.return_value = [run1, run2]

        # Act
        uploads = get_job_uploads(job_repository, run_repository, job_id=1)

        # Assert
        assert len(uploads) == 2

        upload1 = uploads[0]
        assert upload1.context == "run"
        assert upload1.upload_type == "config"  # config_url should be config type
        assert upload1.job_id == 1
        assert upload1.run_id == 1
        assert upload1.location.url == "https://s3.amazonaws.com/bucket/run_1_output"

        upload2 = uploads[1]
        assert upload2.context == "run"
        assert upload2.upload_type == "config"  # config_url should be config type
        assert upload2.job_id == 1
        assert upload2.run_id == 2
        assert upload2.location.url == "https://s3.amazonaws.com/bucket/run_2_output"

    def test_get_job_uploads__complete_job__returns_all_uploads(
        self, job_repository, run_repository
    ):
        """Test that all upload types are returned for a complete job."""
        # Arrange
        job = Job.create_persisted(
            job_id=1,
            user_id=123,
            input_location="https://s3.amazonaws.com/bucket/job_1_input",
            config_location="https://s3.amazonaws.com/bucket/job_1_config",
        )
        run = Run.create_persisted(
            run_id=1,
            job_id=1,
            user_id=123,
            status=RunStatus.DONE,
            pod_phase=PodPhase.SUCCEEDED,
            request={},
            config_url="https://s3.amazonaws.com/bucket/run_1_output",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        job_repository.find_by_id.return_value = job
        run_repository.find_by_job_id.return_value = [run]

        # Act
        uploads = get_job_uploads(job_repository, run_repository, job_id=1)

        # Assert
        assert len(uploads) == 3

        # Check upload types by combining context and job_type
        upload_types = [(u.context, u.upload_type) for u in uploads]
        assert ("job", "input") in upload_types
        assert ("job", "config") in upload_types
        assert ("run", "config") in upload_types  # config_url should be config type

        # Verify all have correct job_id
        for upload in uploads:
            assert upload.job_id == 1
            assert isinstance(upload.location, UploadLocation)
