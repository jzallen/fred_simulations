"""
Tests for the archive_uploads use case.
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, call, patch

import pytest
from freezegun import freeze_time

from epistemix_platform.models.upload_location import UploadLocation
from epistemix_platform.use_cases.archive_uploads import archive_uploads


class TestArchiveUploadsUseCase:

    @pytest.fixture
    def mock_repository(self):
        repo = Mock()  # Don't use spec since archive methods aren't in the interface yet
        # Set default return values
        repo.archive_uploads.return_value = []
        repo.filter_by_age.return_value = []
        return repo

    @pytest.fixture
    def sample_upload_locations(self):
        location1 = UploadLocation("https://s3.amazonaws.com/bucket/job1/file1.txt")

        location2 = UploadLocation("https://s3.amazonaws.com/bucket/job1/file2.txt")

        location3 = UploadLocation("https://s3.amazonaws.com/bucket/job2/file3.txt")

        return [location1, location2, location3]

    def test_returns_empty_list_when_no_upload_locations(self, mock_repository):
        result = archive_uploads(
            upload_repository=mock_repository,
            upload_locations=[],
        )

        assert result == []
        mock_repository.archive_uploads.assert_not_called()
        mock_repository.filter_by_age.assert_not_called()

    def test_dry_run_without_age_threshold_returns_original_list_and_skips_repo_calls(
        self, mock_repository, sample_upload_locations
    ):
        result = archive_uploads(
            upload_repository=mock_repository,
            upload_locations=sample_upload_locations,
            dry_run=True,
        )

        assert result == sample_upload_locations
        mock_repository.archive_uploads.assert_not_called()
        mock_repository.filter_by_age.assert_not_called()

    @freeze_time("2025-01-15 14:30:00")
    def test_dry_run_with_hours_threshold_uses_filter_by_age_and_skips_archive_uploads(
        self, mock_repository, sample_upload_locations
    ):
        filtered = sample_upload_locations[:2]
        mock_repository.filter_by_age.return_value = filtered

        result = archive_uploads(
            upload_repository=mock_repository,
            upload_locations=sample_upload_locations,
            hours_since_create=48,
            dry_run=True,
        )

        assert result == filtered
        mock_repository.archive_uploads.assert_not_called()

        # Verify filter_by_age was called with correct params
        mock_repository.filter_by_age.assert_called_once()
        call_args = mock_repository.filter_by_age.call_args[0]
        assert call_args[0] == sample_upload_locations

        # Check threshold is approximately 48 hours ago
        threshold = call_args[1]
        expected = datetime(2025, 1, 13, 14, 30, 0)
        assert abs((threshold - expected).total_seconds()) < 1

    @freeze_time("2025-01-15 14:30:00")
    def test_dry_run_with_days_threshold_uses_filter_by_age_and_skips_archive_uploads(
        self, mock_repository, sample_upload_locations
    ):
        filtered = sample_upload_locations[:1]
        mock_repository.filter_by_age.return_value = filtered

        result = archive_uploads(
            upload_repository=mock_repository,
            upload_locations=sample_upload_locations,
            days_since_create=7,
            dry_run=True,
        )

        assert result == filtered
        mock_repository.archive_uploads.assert_not_called()

        # Verify filter_by_age was called with correct params
        mock_repository.filter_by_age.assert_called_once()
        call_args = mock_repository.filter_by_age.call_args[0]
        assert call_args[0] == sample_upload_locations

        # Check threshold is approximately 7 days ago
        threshold = call_args[1]
        expected = datetime(2025, 1, 8, 14, 30, 0)
        assert abs((threshold - expected).total_seconds()) < 1

    @freeze_time("2025-01-15 14:30:00")
    def test_hours_threshold_takes_precedence_over_days_when_both_provided(
        self, mock_repository, sample_upload_locations
    ):
        mock_repository.archive_uploads.return_value = sample_upload_locations

        archive_uploads(
            upload_repository=mock_repository,
            upload_locations=sample_upload_locations,
            days_since_create=30,  # This should be ignored
            hours_since_create=12,  # This should take precedence
        )

        # Verify archive was called with hours-based threshold
        mock_repository.archive_uploads.assert_called_once()
        threshold = mock_repository.archive_uploads.call_args[1]["age_threshold"]

        # Should be 12 hours ago, not 30 days ago
        expected = datetime(2025, 1, 15, 2, 30, 0)
        assert abs((threshold - expected).total_seconds()) < 1

    @freeze_time("2025-01-15 14:30:00")
    def test_archive_path_calls_repository_with_computed_hours_threshold(
        self, mock_repository, sample_upload_locations
    ):
        mock_repository.archive_uploads.return_value = sample_upload_locations[:2]

        result = archive_uploads(
            upload_repository=mock_repository,
            upload_locations=sample_upload_locations,
            hours_since_create=72,
        )

        assert result == sample_upload_locations[:2]

        # Verify correct threshold computation (72 hours = 3 days ago)
        mock_repository.archive_uploads.assert_called_once()
        threshold = mock_repository.archive_uploads.call_args[1]["age_threshold"]
        expected = datetime(2025, 1, 12, 14, 30, 0)
        assert abs((threshold - expected).total_seconds()) < 1

    @freeze_time("2025-01-15 14:30:00")
    def test_archive_path_calls_repository_with_computed_days_threshold(
        self, mock_repository, sample_upload_locations
    ):
        mock_repository.archive_uploads.return_value = sample_upload_locations

        result = archive_uploads(
            upload_repository=mock_repository,
            upload_locations=sample_upload_locations,
            days_since_create=14,
        )

        assert result == sample_upload_locations

        # Verify correct threshold computation (14 days ago)
        mock_repository.archive_uploads.assert_called_once()
        threshold = mock_repository.archive_uploads.call_args[1]["age_threshold"]
        expected = datetime(2025, 1, 1, 14, 30, 0)
        assert abs((threshold - expected).total_seconds()) < 1

    def test_archive_path_with_no_threshold_calls_repository_with_none_age(
        self, mock_repository, sample_upload_locations
    ):
        mock_repository.archive_uploads.return_value = sample_upload_locations

        result = archive_uploads(
            upload_repository=mock_repository,
            upload_locations=sample_upload_locations,
        )

        assert result == sample_upload_locations
        mock_repository.archive_uploads.assert_called_once_with(
            sample_upload_locations, age_threshold=None
        )

    def test_returns_repository_result_from_archive_uploads_unchanged(
        self, mock_repository, sample_upload_locations
    ):
        # Return a subset in different order
        expected_result = [sample_upload_locations[2], sample_upload_locations[0]]
        mock_repository.archive_uploads.return_value = expected_result

        result = archive_uploads(
            upload_repository=mock_repository,
            upload_locations=sample_upload_locations,
        )

        # Should return exactly what repository returned
        assert result is expected_result
        assert result == expected_result

    def test_filter_by_age_not_called_in_dry_run_when_no_threshold(
        self, mock_repository, sample_upload_locations
    ):
        result = archive_uploads(
            upload_repository=mock_repository,
            upload_locations=sample_upload_locations,
            dry_run=True,
        )

        assert result == sample_upload_locations
        mock_repository.filter_by_age.assert_not_called()

    @freeze_time("2025-01-15 14:30:00")
    def test_filter_by_age_called_once_with_expected_threshold_in_dry_run(
        self, mock_repository, sample_upload_locations
    ):
        """Test dry run with threshold calls filter_by_age exactly once with correct params."""
        mock_repository.filter_by_age.return_value = sample_upload_locations[:1]

        archive_uploads(
            upload_repository=mock_repository,
            upload_locations=sample_upload_locations,
            days_since_create=5,
            dry_run=True,
        )

        # Verify single call with correct params
        mock_repository.filter_by_age.assert_called_once()
        call_args = mock_repository.filter_by_age.call_args[0]

        assert call_args[0] == sample_upload_locations
        threshold = call_args[1]
        expected = datetime(2025, 1, 10, 14, 30, 0)
        assert abs((threshold - expected).total_seconds()) < 1

    @freeze_time("2025-01-15 14:30:00")
    def test_archive_uploads_called_once_with_expected_threshold_in_non_dry_run(
        self, mock_repository, sample_upload_locations
    ):
        mock_repository.archive_uploads.return_value = sample_upload_locations

        archive_uploads(
            upload_repository=mock_repository,
            upload_locations=sample_upload_locations,
            hours_since_create=24,
        )

        # Verify single call with correct params
        mock_repository.archive_uploads.assert_called_once()
        call_args = mock_repository.archive_uploads.call_args

        assert call_args[0][0] == sample_upload_locations
        threshold = call_args[1]["age_threshold"]
        expected = datetime(2025, 1, 14, 14, 30, 0)
        assert abs((threshold - expected).total_seconds()) < 1

    @patch("epistemix_platform.use_cases.archive_uploads.logger")
    def test_logs_include_dry_run_prefix_when_dry_run_true(
        self, mock_logger, mock_repository, sample_upload_locations
    ):
        archive_uploads(
            upload_repository=mock_repository,
            upload_locations=sample_upload_locations,
            dry_run=True,
        )

        # Check that expected log calls were made with DRY RUN content
        expected_calls = [
            call("DRY RUN: Archiving all provided uploads (3 locations provided)"),
            call("Dry run mode - checking what would be archived"),
            call("Would archive 3 uploads"),
        ]
        mock_logger.info.assert_has_calls(expected_calls)

    @patch("epistemix_platform.use_cases.archive_uploads.logger")
    def test_logs_report_number_of_locations_provided(
        self, mock_logger, mock_repository, sample_upload_locations
    ):
        mock_repository.archive_uploads.return_value = sample_upload_locations[:2]

        archive_uploads(
            upload_repository=mock_repository,
            upload_locations=sample_upload_locations,
        )

        # Check that number of locations is logged
        expected_calls = [
            call("Archiving all provided uploads (3 locations provided)"),
            call("Successfully archived 2 uploads"),
        ]
        mock_logger.info.assert_has_calls(expected_calls)

    @patch("epistemix_platform.use_cases.archive_uploads.logger")
    def test_logs_sanitized_urls_for_each_location_in_dry_run(
        self, mock_logger, mock_repository, sample_upload_locations
    ):
        archive_uploads(
            upload_repository=mock_repository,
            upload_locations=sample_upload_locations,
            dry_run=True,
        )

        # Verify debug logs contain sanitized URLs for each location
        expected_debug_calls = [
            call(f"  Would archive: {location.get_sanitized_url()}")
            for location in sample_upload_locations
        ]

        mock_logger.debug.assert_has_calls(expected_debug_calls)

    @patch("epistemix_platform.use_cases.archive_uploads.logger")
    def test_logs_sanitized_urls_for_each_location_in_archive_path(
        self, mock_logger, mock_repository, sample_upload_locations
    ):
        archived = sample_upload_locations[:2]
        mock_repository.archive_uploads.return_value = archived

        archive_uploads(
            upload_repository=mock_repository,
            upload_locations=sample_upload_locations,
        )

        # Verify debug logs contain sanitized URLs for archived items
        expected_debug_calls = [
            call(f"  Archived: {location.get_sanitized_url()}") for location in archived
        ]

        mock_logger.debug.assert_has_calls(expected_debug_calls)

    @freeze_time("2025-01-15 14:30:00")
    def test_handles_zero_hours_threshold_as_now_boundary(
        self, mock_repository, sample_upload_locations
    ):
        mock_repository.archive_uploads.return_value = []

        archive_uploads(
            upload_repository=mock_repository,
            upload_locations=sample_upload_locations,
            hours_since_create=0,
        )

        # Threshold should be current time (or very close to it)
        threshold = mock_repository.archive_uploads.call_args[1]["age_threshold"]
        expected = datetime(2025, 1, 15, 14, 30, 0)
        assert abs((threshold - expected).total_seconds()) < 1

    @freeze_time("2025-01-15 14:30:00")
    def test_handles_zero_days_threshold_as_today_boundary(
        self, mock_repository, sample_upload_locations
    ):
        mock_repository.archive_uploads.return_value = []

        archive_uploads(
            upload_repository=mock_repository,
            upload_locations=sample_upload_locations,
            days_since_create=0,
        )

        # Threshold should be current time
        threshold = mock_repository.archive_uploads.call_args[1]["age_threshold"]
        expected = datetime(2025, 1, 15, 14, 30, 0)
        assert abs((threshold - expected).total_seconds()) < 1

    def test_duplicate_locations_are_deduplicated_in_repository_call(self, mock_repository):
        location1 = UploadLocation(
            url=(
                "https://s3.amazonaws.com/bucket/file.txt?"
                "AWSAccessKeyId=abc123"
                "&Signature=def456"
                "&Expires=789123"
            )
        )

        # Create list with duplicates
        locations_with_dupes = [location1, location1, location1]

        archive_uploads(
            upload_repository=mock_repository,
            upload_locations=locations_with_dupes,
        )

        mock_repository.archive_uploads.assert_called_once_with([location1], age_threshold=None)

    def test_raises_no_exception_when_repository_returns_empty_list(
        self, mock_repository, sample_upload_locations
    ):
        """Test that empty repository result doesn't raise exception."""
        mock_repository.archive_uploads.return_value = []

        # Should not raise any exception
        result = archive_uploads(
            upload_repository=mock_repository,
            upload_locations=sample_upload_locations,
        )

        assert result == []

    def test_passes_through_timezone_agnostic_threshold_computation(
        self, mock_repository, sample_upload_locations
    ):
        """Test that threshold computation doesn't depend on timezone."""
        mock_repository.archive_uploads.return_value = sample_upload_locations

        # Test with current time (no freeze_time) - should work regardless of timezone
        archive_uploads(
            upload_repository=mock_repository,
            upload_locations=sample_upload_locations,
            hours_since_create=24,
        )

        # Verify archive was called
        mock_repository.archive_uploads.assert_called_once()
        threshold = mock_repository.archive_uploads.call_args[1]["age_threshold"]

        # Threshold should be approximately 24 hours ago from now
        now = datetime.now()
        expected_delta = timedelta(hours=24)
        actual_delta = now - threshold

        # Allow for small timing differences during test execution
        assert abs((actual_delta - expected_delta).total_seconds()) < 2
