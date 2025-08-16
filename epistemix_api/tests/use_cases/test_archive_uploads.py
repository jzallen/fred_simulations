"""
Tests for the archive_uploads use case.
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch, call
from copy import deepcopy

import pytest
from freezegun import freeze_time

from epistemix_api.models.upload_location import UploadLocation
from epistemix_api.repositories.interfaces import IUploadLocationRepository
from epistemix_api.use_cases.archive_uploads import archive_uploads


class TestArchiveUploadsUseCase:
    """Test cases for the archive_uploads use case."""

    @pytest.fixture
    def mock_repository(self):
        """Create a mock upload repository."""
        repo = Mock()  # Don't use spec since archive methods aren't in the interface yet
        # Set default return values
        repo.archive_uploads.return_value = []
        repo.filter_by_age.return_value = []
        return repo

    @pytest.fixture
    def sample_upload_locations(self):
        """Create sample upload locations for testing."""
        location1 = Mock(spec=UploadLocation)
        location1.url = "https://s3.amazonaws.com/bucket/job1/file1.txt"
        location1.get_sanitized_url.return_value = "https://s3.amazonaws.com/bucket/job1/file1.txt"
        
        location2 = Mock(spec=UploadLocation)
        location2.url = "https://s3.amazonaws.com/bucket/job1/file2.txt"
        location2.get_sanitized_url.return_value = "https://s3.amazonaws.com/bucket/job1/file2.txt"
        
        location3 = Mock(spec=UploadLocation)
        location3.url = "https://s3.amazonaws.com/bucket/job2/file3.txt"
        location3.get_sanitized_url.return_value = "https://s3.amazonaws.com/bucket/job2/file3.txt"
        
        return [location1, location2, location3]

    def test_returns_empty_list_when_no_upload_locations(self, mock_repository):
        """Test that empty upload list returns empty result without calling repository."""
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
        """Test dry run without threshold returns all locations without repository calls."""
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
        """Test dry run with hours threshold calls filter_by_age but not archive_uploads."""
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
        """Test dry run with days threshold calls filter_by_age but not archive_uploads."""
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
        """Test that hours_since_create takes precedence over days_since_create."""
        mock_repository.archive_uploads.return_value = sample_upload_locations
        
        result = archive_uploads(
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
        """Test archive with hours threshold computes correct age threshold."""
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
        """Test archive with days threshold computes correct age threshold."""
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
        """Test archive without threshold passes None as age_threshold."""
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
        """Test that repository result is returned without modification."""
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
        """Test dry run without threshold doesn't call filter_by_age."""
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
        
        result = archive_uploads(
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
        """Test non-dry run calls archive_uploads exactly once with correct params."""
        mock_repository.archive_uploads.return_value = sample_upload_locations
        
        result = archive_uploads(
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

    @patch("epistemix_api.use_cases.archive_uploads.logger")
    def test_logs_include_dry_run_prefix_when_dry_run_true(
        self, mock_logger, mock_repository, sample_upload_locations
    ):
        """Test that DRY RUN prefix appears in logs when dry_run=True."""
        result = archive_uploads(
            upload_repository=mock_repository,
            upload_locations=sample_upload_locations,
            dry_run=True,
        )
        
        # Check info logs contain DRY RUN prefix
        info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any("DRY RUN:" in msg for msg in info_calls)
        assert any("Dry run mode" in msg for msg in info_calls)
        assert any("Would archive" in msg for msg in info_calls)

    @patch("epistemix_api.use_cases.archive_uploads.logger")
    def test_logs_report_number_of_locations_provided(
        self, mock_logger, mock_repository, sample_upload_locations
    ):
        """Test that logs report the number of locations provided."""
        mock_repository.archive_uploads.return_value = sample_upload_locations[:2]
        
        result = archive_uploads(
            upload_repository=mock_repository,
            upload_locations=sample_upload_locations,
        )
        
        # Check that number of locations is logged
        info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any("3 locations provided" in msg for msg in info_calls)
        assert any("Successfully archived 2 uploads" in msg for msg in info_calls)

    @patch("epistemix_api.use_cases.archive_uploads.logger")
    def test_logs_sanitized_urls_for_each_location_in_dry_run(
        self, mock_logger, mock_repository, sample_upload_locations
    ):
        """Test that sanitized URLs are logged for each location in dry run."""
        result = archive_uploads(
            upload_repository=mock_repository,
            upload_locations=sample_upload_locations,
            dry_run=True,
        )
        
        # Verify debug logs contain sanitized URLs
        debug_calls = [call[0][0] for call in mock_logger.debug.call_args_list]
        
        # Each location should have its sanitized URL logged
        for location in sample_upload_locations:
            sanitized = location.get_sanitized_url()
            assert any(sanitized in msg for msg in debug_calls)
            assert any("Would archive:" in msg and sanitized in msg for msg in debug_calls)

    @patch("epistemix_api.use_cases.archive_uploads.logger")
    def test_logs_sanitized_urls_for_each_location_in_archive_path(
        self, mock_logger, mock_repository, sample_upload_locations
    ):
        """Test that sanitized URLs are logged for archived locations."""
        archived = sample_upload_locations[:2]
        mock_repository.archive_uploads.return_value = archived
        
        result = archive_uploads(
            upload_repository=mock_repository,
            upload_locations=sample_upload_locations,
        )
        
        # Verify debug logs contain sanitized URLs for archived items
        debug_calls = [call[0][0] for call in mock_logger.debug.call_args_list]
        
        for location in archived:
            sanitized = location.get_sanitized_url()
            assert any("Archived:" in msg and sanitized in msg for msg in debug_calls)

    def test_does_not_mutate_input_upload_locations_list(
        self, mock_repository, sample_upload_locations
    ):
        """Test that the input list is not mutated during processing."""
        # Store original references to check list wasn't mutated
        original_length = len(sample_upload_locations)
        original_refs = sample_upload_locations.copy()  # Shallow copy to keep references
        mock_repository.archive_uploads.return_value = sample_upload_locations[:1]
        
        result = archive_uploads(
            upload_repository=mock_repository,
            upload_locations=sample_upload_locations,
        )
        
        # Input list should remain unchanged
        assert len(sample_upload_locations) == original_length
        assert sample_upload_locations == original_refs
        # Verify the same objects are still in the list
        for i, location in enumerate(sample_upload_locations):
            assert location is original_refs[i]

    @freeze_time("2025-01-15 14:30:00")
    def test_handles_zero_hours_threshold_as_now_boundary(
        self, mock_repository, sample_upload_locations
    ):
        """Test that zero hours threshold means current time."""
        mock_repository.archive_uploads.return_value = []
        
        result = archive_uploads(
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
        """Test that zero days threshold means current time."""
        mock_repository.archive_uploads.return_value = []
        
        result = archive_uploads(
            upload_repository=mock_repository,
            upload_locations=sample_upload_locations,
            days_since_create=0,
        )
        
        # Threshold should be current time
        threshold = mock_repository.archive_uploads.call_args[1]["age_threshold"]
        expected = datetime(2025, 1, 15, 14, 30, 0)
        assert abs((threshold - expected).total_seconds()) < 1

    def test_preserves_duplicate_locations_in_results(
        self, mock_repository
    ):
        """Test that duplicate locations are preserved in results."""
        location1 = Mock(spec=UploadLocation)
        location1.url = "https://s3.amazonaws.com/bucket/file.txt"
        location1.get_sanitized_url.return_value = "https://s3.amazonaws.com/bucket/file.txt"
        
        # Create list with duplicates
        locations_with_dupes = [location1, location1, location1]
        mock_repository.archive_uploads.return_value = locations_with_dupes
        
        result = archive_uploads(
            upload_repository=mock_repository,
            upload_locations=locations_with_dupes,
        )
        
        # All duplicates should be preserved
        assert len(result) == 3
        assert all(loc is location1 for loc in result)

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
        result = archive_uploads(
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