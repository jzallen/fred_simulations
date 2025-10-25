"""
Unit tests for JobS3Prefix value object.

These tests verify the JobS3Prefix value object behavior using Gherkin-style
behavioral specifications.

Behavioral Specifications:
==========================

Scenario 1: Create prefix from Job domain model
  Given a Job with id=12 and created_at=2025-10-23 21:15:00 UTC
  When I call JobS3Prefix.from_job(job)
  Then a JobS3Prefix is returned
  And job_id is 12
  And timestamp is 2025-10-23 21:15:00 UTC

Scenario 2: Generate consistent base prefix from timestamp
  Given a JobS3Prefix with job_id=12 and timestamp=2025-10-23 21:15:00 UTC
  When I access the base_prefix property
  Then I get "jobs/12/2025/10/23/211500"

Scenario 3: Generate job config key
  Given a JobS3Prefix with job_id=12 and timestamp=2025-10-23 21:15:00 UTC
  When I call job_config_key()
  Then I get "jobs/12/2025/10/23/211500/job_config.json"

Scenario 4: Generate job input key
  Given a JobS3Prefix with job_id=12 and timestamp=2025-10-23 21:15:00 UTC
  When I call job_input_key()
  Then I get "jobs/12/2025/10/23/211500/job_input.zip"

Scenario 5: Generate run config key
  Given a JobS3Prefix with job_id=12 and timestamp=2025-10-23 21:15:00 UTC
  When I call run_config_key(run_id=4)
  Then I get "jobs/12/2025/10/23/211500/run_4_config.json"

Scenario 6: Generate run results key
  Given a JobS3Prefix with job_id=12 and timestamp=2025-10-23 21:15:00 UTC
  When I call run_results_key(run_id=4)
  Then I get "jobs/12/2025/10/23/211500/run_4_results.zip"

Scenario 7: Generate run logs key
  Given a JobS3Prefix with job_id=12 and timestamp=2025-10-23 21:15:00 UTC
  When I call run_logs_key(run_id=4)
  Then I get "jobs/12/2025/10/23/211500/run_4_logs.log"

Scenario 8: Ensure immutability (frozen dataclass)
  Given a JobS3Prefix instance
  When I try to modify job_id or timestamp
  Then a FrozenInstanceError is raised

Scenario 9: Handle midnight timestamps correctly
  Given a JobS3Prefix with timestamp=2025-10-23 00:00:00 UTC
  When I access the base_prefix property
  Then I get "jobs/12/2025/10/23/000000"
  And the timestamp formatting is correct

Scenario 10: Handle different job IDs
  Given JobS3Prefix instances with job_ids 1, 99, 12345
  When I generate base prefixes
  Then each uses the correct job_id in the path

Scenario 11: Consistency - same timestamp yields same prefix
  Given a JobS3Prefix with a specific timestamp
  When I call base_prefix multiple times
  Then I get the same result every time (value object immutability)
"""

from datetime import datetime

import pytest

from epistemix_platform.models.job import Job
from epistemix_platform.models.job_s3_prefix import JobS3Prefix


class TestJobS3Prefix:
    """Test suite for JobS3Prefix value object."""

    @pytest.fixture
    def sample_job(self):
        """Create a sample Job for testing."""
        return Job(
            id=12,
            user_id=1,
            tags=["simulation_job"],
            created_at=datetime(2025, 10, 23, 21, 15, 0),  # 2025-10-23 21:15:00 UTC
        )

    @pytest.fixture
    def sample_prefix(self):
        """Create a sample JobS3Prefix for testing."""
        return JobS3Prefix(
            job_id=12,
            timestamp=datetime(2025, 10, 23, 21, 15, 0),  # 2025-10-23 21:15:00 UTC
        )

    # ==========================================================================
    # Scenario 1: Create prefix from Job domain model
    # ==========================================================================

    def test_create_from_job(self, sample_job):
        """
        Given a Job with id=12 and created_at=2025-10-23 21:15:00 UTC
        When I call JobS3Prefix.from_job(job)
        Then a JobS3Prefix is returned
        And job_id is 12
        And timestamp is 2025-10-23 21:15:00 UTC
        """
        # Act
        prefix = JobS3Prefix.from_job(sample_job)

        # Assert
        assert isinstance(prefix, JobS3Prefix)
        assert prefix.job_id == 12
        assert prefix.timestamp == datetime(2025, 10, 23, 21, 15, 0)

    # ==========================================================================
    # Scenario 2: Generate consistent base prefix from timestamp
    # ==========================================================================

    def test_generate_base_prefix(self, sample_prefix):
        """
        Given a JobS3Prefix with job_id=12 and timestamp=2025-10-23 21:15:00 UTC
        When I access the base_prefix property
        Then I get "jobs/12/2025/10/23/211500"
        """
        # Act
        base_prefix = sample_prefix.base_prefix

        # Assert
        assert base_prefix == "jobs/12/2025/10/23/211500"

    # ==========================================================================
    # Scenario 3: Generate job config key
    # ==========================================================================

    def test_generate_job_config_key(self, sample_prefix):
        """
        Given a JobS3Prefix with job_id=12 and timestamp=2025-10-23 21:15:00 UTC
        When I call job_config_key()
        Then I get "jobs/12/2025/10/23/211500/job_config.json"
        """
        # Act
        key = sample_prefix.job_config_key()

        # Assert
        assert key == "jobs/12/2025/10/23/211500/job_config.json"

    # ==========================================================================
    # Scenario 4: Generate job input key
    # ==========================================================================

    def test_generate_job_input_key(self, sample_prefix):
        """
        Given a JobS3Prefix with job_id=12 and timestamp=2025-10-23 21:15:00 UTC
        When I call job_input_key()
        Then I get "jobs/12/2025/10/23/211500/job_input.zip"
        """
        # Act
        key = sample_prefix.job_input_key()

        # Assert
        assert key == "jobs/12/2025/10/23/211500/job_input.zip"

    # ==========================================================================
    # Scenario 5: Generate run config key
    # ==========================================================================

    def test_generate_run_config_key(self, sample_prefix):
        """
        Given a JobS3Prefix with job_id=12 and timestamp=2025-10-23 21:15:00 UTC
        When I call run_config_key(run_id=4)
        Then I get "jobs/12/2025/10/23/211500/run_4_config.json"
        """
        # Act
        key = sample_prefix.run_config_key(run_id=4)

        # Assert
        assert key == "jobs/12/2025/10/23/211500/run_4_config.json"

    # ==========================================================================
    # Scenario 6: Generate run results key
    # ==========================================================================

    def test_generate_run_results_key(self, sample_prefix):
        """
        Given a JobS3Prefix with job_id=12 and timestamp=2025-10-23 21:15:00 UTC
        When I call run_results_key(run_id=4)
        Then I get "jobs/12/2025/10/23/211500/run_4_results.zip"
        """
        # Act
        key = sample_prefix.run_results_key(run_id=4)

        # Assert
        assert key == "jobs/12/2025/10/23/211500/run_4_results.zip"

    # ==========================================================================
    # Scenario 7: Generate run logs key
    # ==========================================================================

    def test_generate_run_logs_key(self, sample_prefix):
        """
        Given a JobS3Prefix with job_id=12 and timestamp=2025-10-23 21:15:00 UTC
        When I call run_logs_key(run_id=4)
        Then I get "jobs/12/2025/10/23/211500/run_4_logs.log"
        """
        # Act
        key = sample_prefix.run_logs_key(run_id=4)

        # Assert
        assert key == "jobs/12/2025/10/23/211500/run_4_logs.log"

    # ==========================================================================
    # Scenario 8: Ensure immutability (frozen dataclass)
    # ==========================================================================

    def test_immutability(self, sample_prefix):
        """
        Given a JobS3Prefix instance
        When I try to modify job_id or timestamp
        Then a FrozenInstanceError is raised
        """
        # Act & Assert
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            sample_prefix.job_id = 999

        with pytest.raises(Exception):
            sample_prefix.timestamp = datetime(2025, 12, 31, 23, 59, 59)

    # ==========================================================================
    # Scenario 9: Handle midnight timestamps correctly
    # ==========================================================================

    def test_midnight_timestamp_formatting(self):
        """
        Given a JobS3Prefix with timestamp=2025-10-23 00:00:00 UTC
        When I access the base_prefix property
        Then I get "jobs/12/2025/10/23/000000"
        And the timestamp formatting is correct
        """
        # Arrange
        midnight_prefix = JobS3Prefix(
            job_id=12,
            timestamp=datetime(2025, 10, 23, 0, 0, 0),  # Midnight
        )

        # Act
        base_prefix = midnight_prefix.base_prefix

        # Assert
        assert base_prefix == "jobs/12/2025/10/23/000000"
        # Verify leading zeros are preserved
        assert "000000" in base_prefix

    # ==========================================================================
    # Scenario 10: Handle different job IDs
    # ==========================================================================

    @pytest.mark.parametrize(
        "job_id,expected_path_segment",
        [
            (1, "jobs/1/"),
            (99, "jobs/99/"),
            (12345, "jobs/12345/"),
        ],
    )
    def test_different_job_ids(self, job_id, expected_path_segment):
        """
        Given JobS3Prefix instances with job_ids 1, 99, 12345
        When I generate base prefixes
        Then each uses the correct job_id in the path
        """
        # Arrange
        prefix = JobS3Prefix(
            job_id=job_id,
            timestamp=datetime(2025, 10, 23, 21, 15, 0),
        )

        # Act
        base_prefix = prefix.base_prefix

        # Assert
        assert base_prefix.startswith(expected_path_segment)

    # ==========================================================================
    # Scenario 11: Consistency - same timestamp yields same prefix
    # ==========================================================================

    def test_consistency_same_prefix_on_multiple_calls(self, sample_prefix):
        """
        Given a JobS3Prefix with a specific timestamp
        When I call base_prefix multiple times
        Then I get the same result every time (value object immutability)
        """
        # Act
        prefix1 = sample_prefix.base_prefix
        prefix2 = sample_prefix.base_prefix
        prefix3 = sample_prefix.base_prefix

        # Assert
        assert prefix1 == prefix2 == prefix3 == "jobs/12/2025/10/23/211500"

    # ==========================================================================
    # Additional Tests: Edge Cases
    # ==========================================================================

    def test_multiple_runs_use_same_base_prefix(self, sample_prefix):
        """
        Verify that multiple run artifacts for the same job use the same base prefix.
        """
        # Act
        run_4_config = sample_prefix.run_config_key(run_id=4)
        run_4_results = sample_prefix.run_results_key(run_id=4)
        run_5_config = sample_prefix.run_config_key(run_id=5)

        # Assert - all share same base prefix
        expected_base = "jobs/12/2025/10/23/211500"
        assert run_4_config.startswith(expected_base)
        assert run_4_results.startswith(expected_base)
        assert run_5_config.startswith(expected_base)

        # But have different filenames
        assert "run_4_config" in run_4_config
        assert "run_4_results" in run_4_results
        assert "run_5_config" in run_5_config

    def test_value_object_equality(self):
        """
        Verify that two JobS3Prefix instances with same values are equal.
        """
        # Arrange
        timestamp = datetime(2025, 10, 23, 21, 15, 0)
        prefix1 = JobS3Prefix(job_id=12, timestamp=timestamp)
        prefix2 = JobS3Prefix(job_id=12, timestamp=timestamp)

        # Assert
        assert prefix1 == prefix2
        assert hash(prefix1) == hash(prefix2)  # Can be used in sets/dicts
