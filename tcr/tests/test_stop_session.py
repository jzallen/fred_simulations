"""Tests for stop_session functionality."""

import subprocess
from unittest.mock import Mock, call, patch

import pytest

from tcr.cli import stop_session
from tcr.logging_config import LoggerType, logger_factory


class TestStopSession:
    """Test suite for stop_session function."""

    @patch('subprocess.run')
    
    def test_stop_session__when_single_session_found__sends_sigint(self, mock_run):
        """Test that stop_session sends SIGINT to matching process."""
        # First call is pgrep | grep, second is kill
        mock_run.side_effect = [
            Mock(returncode=0, stdout='12345 tcr:my-feature\n'),  # pgrep | grep result
            Mock(returncode=0)  # kill result
        ]

        mock_logger = Mock()
        stop_session('my-feature', mock_logger)

        # Check pgrep | grep was called correctly
        assert mock_run.call_args_list[0] == call(
            'pgrep -a "tcr:*" | grep "tcr:my-feature"',
            shell=True,
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
    
    def test_stop_session__when_no_session_found__logs_error(self, mock_run):
        """Test that stop_session logs error when no matching session."""
        # grep returns 1 when no lines match
        mock_run.return_value = Mock(returncode=1, stdout='')

        mock_logger = Mock()
        stop_session('nonexistent', mock_logger)

        mock_run.assert_called_once_with(
            'pgrep -a "tcr:*" | grep "tcr:nonexistent"',
            shell=True,
            capture_output=True,
            text=True
        )

        mock_logger.error.assert_called_with("No TCR session found with session_id: nonexistent")

    @patch('subprocess.run')
    
    def test_stop_session__when_multiple_sessions_found__stops_all(self, mock_run):
        """Test that stop_session handles multiple matching sessions."""
        # First call is pgrep | grep, then kill for each PID
        mock_run.side_effect = [
            Mock(returncode=0, stdout='12345 tcr:test\n67890 tcr:test\n'),  # pgrep | grep result
            Mock(returncode=0),  # first kill
            Mock(returncode=0)   # second kill
        ]

        mock_logger = Mock()
        stop_session('test', mock_logger)

        # Check warning was logged
        calls = mock_logger.warning.call_args_list
        assert any("Multiple sessions found matching 'test': PIDs 12345, 67890" in str(call) for call in calls)

        # Check both processes were killed
        assert mock_run.call_args_list[1] == call(['kill', '-INT', '12345'], check=True)
        assert mock_run.call_args_list[2] == call(['kill', '-INT', '67890'], check=True)

    @patch('subprocess.run')
    
    def test_stop_session__when_kill_fails__logs_error(self, mock_run):
        """Test that stop_session logs error when kill command fails."""
        # First call is pgrep | grep, second is kill that fails
        mock_run.side_effect = [
            Mock(returncode=0, stdout='12345 tcr:my-session\n'),  # pgrep | grep result
            subprocess.CalledProcessError(1, ['kill', '-INT', '12345'])  # kill fails
        ]

        mock_logger = Mock()
        stop_session('my-session', mock_logger)

        # Check error was logged
        calls = mock_logger.error.call_args_list
        assert any("Failed to stop process 12345" in str(call) for call in calls)

    @patch('subprocess.run')
    
    def test_stop_session__when_pgrep_not_found__logs_error(self, mock_run):
        """Test that stop_session handles missing pgrep gracefully."""
        mock_run.side_effect = FileNotFoundError("pgrep not found")

        mock_logger = Mock()
        stop_session('any-session', mock_logger)

        mock_logger.error.assert_called_with("pgrep or kill command not found. Please ensure procps is installed.")

    @patch('subprocess.run')
    
    def test_stop_session__when_unexpected_error__logs_error(self, mock_run):
        """Test that stop_session handles unexpected errors gracefully."""
        mock_run.side_effect = Exception("Unexpected error")

        mock_logger = Mock()
        stop_session('any-session', mock_logger)

        mock_logger.error.assert_called_with("Error stopping session: Unexpected error")

    @patch('subprocess.run')
    
    def test_stop_session__with_special_characters_in_session_id(self, mock_run):
        """Test that stop_session handles session IDs with special characters."""
        mock_run.return_value = Mock(returncode=0, stdout='12345 tcr:feature-123_test\n')
        mock_run.side_effect = [
            Mock(returncode=0, stdout='12345 tcr:feature-123_test\n'),  # pgrep | grep result
            Mock(returncode=0)  # kill result
        ]

        mock_logger = Mock()
        stop_session('feature-123_test', mock_logger)

        # Check that we're using shell=True with pipe to grep
        assert mock_run.call_args_list[0] == call(
            'pgrep -a "tcr:*" | grep "tcr:feature-123_test"',
            shell=True,
            capture_output=True,
            text=True
        )

        # Check kill was called
        assert mock_run.call_args_list[1] == call(['kill', '-INT', '12345'], check=True)

    @patch('subprocess.run')
    
    def test_stop_session__with_long_session_id(self, mock_run):
        """Test that stop_session handles long session IDs exceeding pgrep's 15 char limit."""
        long_session_id = 'this-is-a-very-long-session-id-that-exceeds-limit'
        mock_run.side_effect = [
            Mock(returncode=0, stdout=f'12345 tcr:{long_session_id}\n'),  # pgrep | grep result
            Mock(returncode=0)  # kill result
        ]

        mock_logger = Mock()
        stop_session(long_session_id, mock_logger)

        # Check that we're using shell=True with pipe to grep for long IDs
        assert mock_run.call_args_list[0] == call(
            f'pgrep -a "tcr:*" | grep "tcr:{long_session_id}"',
            shell=True,
            capture_output=True,
            text=True
        )

        # Check kill was called
        assert mock_run.call_args_list[1] == call(['kill', '-INT', '12345'], check=True)