from datetime import datetime
from unittest.mock import Mock

import pytest
from freezegun import freeze_time

from epistemix_platform.mappers.job_mapper import JobMapper
from epistemix_platform.models.job import Job, JobStatus
from epistemix_platform.models.job_upload import JobUpload
from epistemix_platform.models.upload_location import UploadLocation
from epistemix_platform.repositories import (
    IJobRepository,
    IUploadLocationRepository,
    SQLAlchemyJobRepository,
)
from epistemix_platform.use_cases.submit_job import submit_job


@freeze_time("2025-01-01 12:00:00")
class TestSubmitJobUseCase:
    @pytest.fixture
    def mock_repository(self):
        repo = Mock(spec=IJobRepository)
        return repo

    @pytest.fixture
    def mock_upload_location_repository(self):
        repo = Mock(spec=IUploadLocationRepository)
        repo.get_upload_location.return_value = UploadLocation(
            url="https://s3.amazonaws.com/test-bucket/presigned-url"
        )
        return repo

    @pytest.fixture
    def created_job(self):
        return Job(
            id=1,
            user_id=123,
            status=JobStatus.CREATED,
            tags=["info_job"],
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            updated_at=datetime(2025, 1, 1, 12, 0, 0),
        )

    @pytest.fixture
    def submitted_job(self):
        return Job(
            id=2,
            user_id=123,
            status=JobStatus.SUBMITTED,
            tags=["simulation_job"],
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            updated_at=datetime(2025, 1, 1, 12, 0, 0),
        )

    def test_submit_job_success__returns_job_input_location_for_submitted_job(
        self, mock_repository, mock_upload_location_repository, created_job
    ):
        mock_repository.find_by_id.return_value = created_job
        mock_repository.save.return_value = None
        job_upload = JobUpload(context="job", upload_type="input", job_id=1)

        result = submit_job(mock_repository, mock_upload_location_repository, job_upload)

        assert isinstance(result, UploadLocation)
        assert result.url == "https://s3.amazonaws.com/test-bucket/presigned-url"

    def test_submit_job__when_job_not_found__raises_value_error(
        self, mock_repository, mock_upload_location_repository
    ):
        mock_repository.find_by_id.return_value = None
        job_upload = JobUpload(context="job", upload_type="input", job_id=999)

        with pytest.raises(ValueError, match="Job 999 not found"):
            submit_job(mock_repository, mock_upload_location_repository, job_upload)

    def test_submit_job__when_created_job_has_non_created_status__value_error_raised(
        self, mock_repository, mock_upload_location_repository, submitted_job
    ):
        mock_repository.find_by_id.return_value = submitted_job
        job_upload = JobUpload(context="job", upload_type="input", job_id=2)

        with pytest.raises(
            ValueError,
            match="Job 2 must be in CREATED status to be submitted, current status: submitted",
        ):
            submit_job(mock_repository, mock_upload_location_repository, job_upload)


class TestSubmitJobSLAlchemyJobRepositoryIntegration:
    @pytest.fixture
    def job_repository(self, db_session):
        job_mapper = JobMapper()
        return SQLAlchemyJobRepository(job_mapper=job_mapper, get_db_session_fn=lambda: db_session)

    @pytest.fixture
    def upload_location_repository(self):
        repo = Mock(spec=IUploadLocationRepository)
        repo.get_upload_location.return_value = UploadLocation(
            url="https://s3.amazonaws.com/test-bucket/presigned-url"
        )
        return repo

    def test_submit_job__returns_job_input_location(
        self, job_repository, upload_location_repository, db_session
    ):
        job = Job.create_new(user_id=123, tags=["test"])
        persisted_job = job_repository.save(job)
        db_session.commit()
        job_upload = JobUpload(context="job", upload_type="input", job_id=persisted_job.id)
        result = submit_job(job_repository, upload_location_repository, job_upload)

        assert isinstance(result, UploadLocation)
        assert result.url == "https://s3.amazonaws.com/test-bucket/presigned-url"

    def test_submit_job__when_job_not_found__raises_value_error(
        self, job_repository, upload_location_repository
    ):
        job_upload = JobUpload(context="job", upload_type="input", job_id=999)
        with pytest.raises(ValueError, match="Job 999 not found"):
            submit_job(job_repository, upload_location_repository, job_upload)

    def test_submit_job__when_job_not_in_created_status__raises_value_error(
        self, job_repository, upload_location_repository
    ):
        job = Job.create_new(user_id=123, tags=["test"])
        job.status = JobStatus.SUBMITTED
        job_repository.save(job)
        job_upload = JobUpload(context="job", upload_type="input", job_id=1)

        with pytest.raises(
            ValueError,
            match="Job 1 must be in CREATED status to be submitted, current status: submitted",
        ):
            submit_job(job_repository, upload_location_repository, job_upload)

    @freeze_time("2025-01-01 12:00:00")
    def test_submit_job__updates_job_status_to_submitted(
        self, job_repository, upload_location_repository
    ):
        new_job = Job.create_new(user_id=123, tags=["test"])
        persisted = job_repository.save(new_job)
        assert persisted.updated_at == datetime(2025, 1, 1, 12, 0, 0)

        with freeze_time("2025-01-01 12:30:00"):
            job_upload = JobUpload(context="job", upload_type="input", job_id=persisted.id)
            submit_job(job_repository, upload_location_repository, job_upload)

        updated_job = job_repository.find_by_id(persisted.id)
        assert updated_job.status == JobStatus.SUBMITTED
        assert updated_job.updated_at == datetime(2025, 1, 1, 12, 30, 0)
