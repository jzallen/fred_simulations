"""
Unit tests for AWS Batch status mapping to RunStatus.

CRITICAL for epx alignment: Only set DONE when results are uploaded.
"""

import pytest
from epistemix_platform.models.run import RunStatus
from epistemix_platform.services.batch_status_mapper import map_batch_status_to_run_status


class TestBatchStatusMapper:
    """Tests for Batch status to RunStatus mapping.

    CRITICAL: epx expects status=DONE only when results are available.
    """

    def test_batch_succeeded_with_results_uploaded_maps_to_done(self):
        """RED: epx expects DONE only when results are available."""
        # ARRANGE & ACT
        status = map_batch_status_to_run_status("SUCCEEDED", results_uploaded=True)

        # ASSERT
        assert status == RunStatus.DONE

    def test_batch_succeeded_without_results_uploaded_maps_to_running(self):
        """RED: CRITICAL: Stay RUNNING until results upload completes."""
        # ARRANGE & ACT
        status = map_batch_status_to_run_status("SUCCEEDED", results_uploaded=False)

        # ASSERT
        assert status == RunStatus.RUNNING  # NOT DONE yet!

    def test_batch_failed_maps_to_error(self):
        """RED: Test FAILED status mapping."""
        # ARRANGE & ACT
        status = map_batch_status_to_run_status("FAILED")

        # ASSERT
        assert status == RunStatus.ERROR

    def test_batch_submitted_maps_to_queued(self):
        """RED: Test SUBMITTED status mapping."""
        # ARRANGE & ACT
        status = map_batch_status_to_run_status("SUBMITTED")

        # ASSERT
        assert status == RunStatus.QUEUED

    def test_batch_pending_maps_to_queued(self):
        """RED: Test PENDING status mapping."""
        # ARRANGE & ACT
        status = map_batch_status_to_run_status("PENDING")

        # ASSERT
        assert status == RunStatus.QUEUED

    def test_batch_runnable_maps_to_queued(self):
        """RED: Test RUNNABLE status mapping."""
        # ARRANGE & ACT
        status = map_batch_status_to_run_status("RUNNABLE")

        # ASSERT
        assert status == RunStatus.QUEUED

    def test_batch_starting_maps_to_running(self):
        """RED: Test STARTING status mapping."""
        # ARRANGE & ACT
        status = map_batch_status_to_run_status("STARTING")

        # ASSERT
        assert status == RunStatus.RUNNING

    def test_batch_running_maps_to_running(self):
        """RED: Test RUNNING status mapping."""
        # ARRANGE & ACT
        status = map_batch_status_to_run_status("RUNNING")

        # ASSERT
        assert status == RunStatus.RUNNING

    def test_unknown_batch_status_maps_to_error(self):
        """RED: Safety: Unknown states default to ERROR."""
        # ARRANGE & ACT
        status = map_batch_status_to_run_status("UNKNOWN_STATE")

        # ASSERT
        assert status == RunStatus.ERROR

    def test_results_uploaded_defaults_to_false(self):
        """RED: Test default value for results_uploaded parameter."""
        # ARRANGE & ACT
        status = map_batch_status_to_run_status("SUCCEEDED")

        # ASSERT - Without results_uploaded=True, stays RUNNING
        assert status == RunStatus.RUNNING
