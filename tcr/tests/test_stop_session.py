"""Tests for stop_session functionality."""

import subprocess
from unittest.mock import Mock, call, patch

import pytest

from tcr.tcr import stop_session


class TestStopSession:
    """Test suite for stop_session function."""

    @patch('subprocess.run')
    @patch('tcr.tcr.logger')
    def test_stop_session__when_single_session_found__sends_sigint(self, mock_logger, mock_run):
        """Test that stop_session sends SIGINT to matching process."""
        # First call is pgrep, second is kill
        mock_run.side_effect = [
            Mock(returncode=0, stdout='12345 tcr:my-feature\n'),  # pgrep result
            Mock(returncode=0)  # kill result
        ]

        stop_session('my-feature')

        # Check pgrep was called correctly
        assert mock_run.call_args_list[0] == call(
            ['pgrep', '-a', 'tcr:my-feature'],
            capture_output=True,
            text=True
        )

        # Check kill was called with SIGINT
        assert mock_run.call_args_list[1] == call(
            ['kill', '-INT', '12345'],
            check=True
        )

        # Check success was logged
        mock_logger.info.assert_called_with("Sent SIGINT to process 12345 (session: my-feature)")

    @patch('subprocess.run')
    @patch('tcr.tcr.logger')
    def test_stop_session__when_no_session_found__logs_error(self, mock_logger, mock_run):
        """Test that stop_session logs error when no matching session."""
        # pgrep returns 1 when no processes found
        mock_run.return_value = Mock(returncode=1, stdout='')

        stop_session('nonexistent')

        mock_run.assert_called_once_with(
            ['pgrep', '-a', 'tcr:nonexistent'],
            capture_output=True,
            text=True
        )

        mock_logger.error.assert_called_with("No TCR session found with session_id: nonexistent")

    @patch('subprocess.run')
    @patch('tcr.tcr.logger')
    def test_stop_session__when_multiple_sessions_found__stops_all(self, mock_logger, mock_run):
        """Test that stop_session handles multiple matching sessions."""
        # First call is pgrep, then kill for each PID
        mock_run.side_effect = [
            Mock(returncode=0, stdout='12345 tcr:test\n67890 tcr:test\n'),  # pgrep result
            Mock(returncode=0),  # first kill
            Mock(returncode=0)   # second kill
        ]

        stop_session('test')

        # Check warning was logged
        calls = mock_logger.warning.call_args_list
        assert any("Multiple sessions found matching 'test': PIDs 12345, 67890" in str(call) for call in calls)

        # Check both processes were killed
        assert mock_run.call_args_list[1] == call(['kill', '-INT', '12345'], check=True)
        assert mock_run.call_args_list[2] == call(['kill', '-INT', '67890'], check=True)

    @patch('subprocess.run')
    @patch('tcr.tcr.logger')
    def test_stop_session__when_kill_fails__logs_error(self, mock_logger, mock_run):
        """Test that stop_session logs error when kill command fails."""
        # First call is pgrep, second is kill that fails
        mock_run.side_effect = [
            Mock(returncode=0, stdout='12345 tcr:my-session\n'),  # pgrep result
            subprocess.CalledProcessError(1, ['kill', '-INT', '12345'])  # kill fails
        ]

        stop_session('my-session')

        # Check error was logged
        calls = mock_logger.error.call_args_list
        assert any("Failed to stop process 12345" in str(call) for call in calls)

    @patch('subprocess.run')
    @patch('tcr.tcr.logger')
    def test_stop_session__when_pgrep_not_found__logs_error(self, mock_logger, mock_run):
        """Test that stop_session handles missing pgrep gracefully."""
        mock_run.side_effect = FileNotFoundError("pgrep not found")

        stop_session('any-session')

        mock_logger.error.assert_called_with("pgrep or kill command not found. Please ensure procps is installed.")

    @patch('subprocess.run')
    @patch('tcr.tcr.logger')
    def test_stop_session__when_unexpected_error__logs_error(self, mock_logger, mock_run):
        """Test that stop_session handles unexpected errors gracefully."""
        mock_run.side_effect = Exception("Unexpected error")

        stop_session('any-session')

        mock_logger.error.assert_called_with("Error stopping session: Unexpected error")

    @patch('subprocess.run')
    @patch('tcr.tcr.logger')
    def test_stop_session__with_special_characters_in_session_id(self, mock_logger, mock_run):
        """Test that stop_session handles session IDs with special characters."""
        mock_run.return_value = Mock(returncode=0, stdout='12345 tcr:feature-123_test\n')
        mock_run.side_effect = [
            Mock(returncode=0, stdout='12345 tcr:feature-123_test\n'),  # pgrep result
            Mock(returncode=0)  # kill result
        ]

        stop_session('feature-123_test')

        # Check pgrep was called with the exact session_id
        assert mock_run.call_args_list[0] == call(
            ['pgrep', '-a', 'tcr:feature-123_test'],
            capture_output=True,
            text=True
        )

        # Check kill was called
        assert mock_run.call_args_list[1] == call(['kill', '-INT', '12345'], check=True)