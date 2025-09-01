"""
Unit tests for JobMapper class.
"""

import datetime

from epistemix_platform.mappers.job_mapper import JobMapper
from epistemix_platform.models.job import Job, JobStatus
from epistemix_platform.repositories.database import JobRecord, JobStatusEnum


class TestJobMapper:
    """Test cases for JobMapper conversion methods."""

    def test_record_to_domain__converts_all_fields_correctly(self):
        """Test that record_to_domain converts all fields from JobRecord to Job."""
        # Arrange
        created_at = datetime.datetime(2025, 1, 15, 10, 30, 0)
        updated_at = datetime.datetime(2025, 1, 15, 11, 30, 0)

        job_record = JobRecord(
            id=123,
            user_id=456,
            tags=["test", "demo", "development"],
            status=JobStatusEnum.PROCESSING,
            created_at=created_at,
            updated_at=updated_at,
            job_metadata={"config": "test_config.json", "priority": "high"},
        )

        # Act
        job = JobMapper.record_to_domain(job_record)

        # Assert
        assert job.id == 123
        assert job.user_id == 456
        assert job.tags == ["test", "demo", "development"]
        assert job.status == JobStatus.PROCESSING
        assert job.created_at == created_at
        assert job.updated_at == updated_at
        assert job.metadata == {"config": "test_config.json", "priority": "high"}
        assert job.is_persisted() is True

    def test_record_to_domain__with_empty_metadata(self):
        """Test record_to_domain conversion when metadata is empty."""
        # Arrange
        job_record = JobRecord(
            id=789,
            user_id=101,
            tags=["minimal"],
            status=JobStatusEnum.CREATED,
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
            job_metadata={},
        )

        # Act
        job = JobMapper.record_to_domain(job_record)

        # Assert
        assert job.metadata == {}

    def test_record_to_domain__with_all_job_statuses(self):
        """Test record_to_domain conversion for all possible job statuses."""
        base_record = JobRecord(
            id=1,
            user_id=1,
            tags=["status_test"],
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
            job_metadata={},
        )

        status_mappings = [
            (JobStatusEnum.CREATED, JobStatus.CREATED),
            (JobStatusEnum.SUBMITTED, JobStatus.SUBMITTED),
            (JobStatusEnum.PROCESSING, JobStatus.PROCESSING),
            (JobStatusEnum.COMPLETED, JobStatus.COMPLETED),
            (JobStatusEnum.FAILED, JobStatus.FAILED),
            (JobStatusEnum.CANCELLED, JobStatus.CANCELLED),
        ]

        for db_status, expected_domain_status in status_mappings:
            # Arrange
            base_record.status = db_status

            # Act
            job = JobMapper.record_to_domain(base_record)

            # Assert
            assert job.status == expected_domain_status

    def test_domain_to_record__converts_all_fields_correctly(self):
        """Test that domain_to_record converts all fields from Job to JobRecord."""
        # Arrange
        created_at = datetime.datetime(2025, 1, 15, 10, 30, 0)
        updated_at = datetime.datetime(2025, 1, 15, 11, 30, 0)

        job = Job.create_persisted(
            job_id=456,
            user_id=789,
            tags=["production", "urgent"],
            status=JobStatus.COMPLETED,
            created_at=created_at,
            updated_at=updated_at,
            metadata={"result": "success", "output_file": "results.csv"},
        )

        # Act
        job_record = JobMapper.domain_to_record(job)

        # Assert
        assert job_record.id == 456
        assert job_record.user_id == 789
        assert job_record.tags == ["production", "urgent"]
        assert job_record.status == JobStatusEnum.COMPLETED
        assert job_record.created_at == created_at
        assert job_record.updated_at == updated_at
        assert job_record.job_metadata == {"result": "success", "output_file": "results.csv"}

    def test_domain_to_record__with_none_metadata(self):
        """Test domain_to_record conversion when job metadata is None."""
        # Arrange
        job = Job.create_persisted(
            job_id=999,
            user_id=111,
            tags=["test"],
            status=JobStatus.CREATED,
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
            metadata=None,
        )

        # Act
        job_record = JobMapper.domain_to_record(job)

        # Assert
        assert job_record.job_metadata == {}

    def test_domain_to_record__with_all_job_statuses(self):
        """Test domain_to_record conversion for all possible job statuses."""
        base_job = Job.create_persisted(
            job_id=1,
            user_id=1,
            tags=["status_test"],
            status=JobStatus.CREATED,  # Will be overridden
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
            metadata={},
        )

        status_mappings = [
            (JobStatus.CREATED, JobStatusEnum.CREATED),
            (JobStatus.SUBMITTED, JobStatusEnum.SUBMITTED),
            (JobStatus.PROCESSING, JobStatusEnum.PROCESSING),
            (JobStatus.COMPLETED, JobStatusEnum.COMPLETED),
            (JobStatus.FAILED, JobStatusEnum.FAILED),
            (JobStatus.CANCELLED, JobStatusEnum.CANCELLED),
        ]

        for domain_status, expected_db_status in status_mappings:
            # Arrange
            base_job.status = domain_status

            # Act
            job_record = JobMapper.domain_to_record(base_job)

            # Assert
            assert job_record.status == expected_db_status

    def test_round_trip_conversion__preserves_all_data(self):
        """Test that converting record -> domain -> record preserves all data."""
        # Arrange
        original_record = JobRecord(
            id=555,
            user_id=666,
            tags=["round_trip", "test", "data_integrity"],
            status=JobStatusEnum.PROCESSING,
            created_at=datetime.datetime(2025, 2, 1, 14, 15, 16),
            updated_at=datetime.datetime(2025, 2, 1, 15, 20, 25),
            job_metadata={"param1": "value1", "param2": 42, "param3": [1, 2, 3]},
        )

        # Act
        job = JobMapper.record_to_domain(original_record)
        final_record = JobMapper.domain_to_record(job)

        # Assert
        assert final_record.id == original_record.id
        assert final_record.user_id == original_record.user_id
        assert final_record.tags == original_record.tags
        assert final_record.status == original_record.status
        assert final_record.created_at == original_record.created_at
        assert final_record.updated_at == original_record.updated_at
        assert final_record.job_metadata == original_record.job_metadata

    def test_reverse_round_trip_conversion__preserves_all_data(self):
        """Test that converting domain -> record -> domain preserves all data."""
        # Arrange
        original_job = Job.create_persisted(
            job_id=777,
            user_id=888,
            tags=["reverse", "round_trip", "validation"],
            status=JobStatus.FAILED,
            created_at=datetime.datetime(2025, 3, 10, 9, 0, 0),
            updated_at=datetime.datetime(2025, 3, 10, 10, 30, 45),
            metadata={"error_code": 500, "error_message": "Internal server error"},
        )

        # Act
        job_record = JobMapper.domain_to_record(original_job)
        final_job = JobMapper.record_to_domain(job_record)

        # Assert
        assert final_job.id == original_job.id
        assert final_job.user_id == original_job.user_id
        assert final_job.tags == original_job.tags
        assert final_job.status == original_job.status
        assert final_job.created_at == original_job.created_at
        assert final_job.updated_at == original_job.updated_at
        assert final_job.metadata == original_job.metadata
        assert final_job.is_persisted() == original_job.is_persisted()

    def test_record_to_domain__with_empty_tags_list(self):
        """Test record_to_domain conversion with empty tags list."""
        # Arrange
        job_record = JobRecord(
            id=100,
            user_id=200,
            tags=[],  # Empty list
            status=JobStatusEnum.CREATED,
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
            job_metadata={"note": "no tags"},
        )

        # Act
        job = JobMapper.record_to_domain(job_record)

        # Assert
        assert job.tags == []

    def test_domain_to_record__with_empty_tags_list(self):
        """Test domain_to_record conversion with empty tags list."""
        # Arrange
        job = Job.create_persisted(
            job_id=300,
            user_id=400,
            tags=[],  # Empty list
            status=JobStatus.SUBMITTED,
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
            metadata={"note": "no tags"},
        )

        # Act
        job_record = JobMapper.domain_to_record(job)

        # Assert
        assert job_record.tags == []
